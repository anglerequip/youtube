"""Two-lane ring-road traffic with the Intelligent Driver Model (IDM, Treiber et al. 2000).

Each lane is a closed loop (periodic boundary), cars follow the car ahead with IDM; no lane changes
(we measure what drivers *experience*, not lane-changing strategies). Dense lanes are unstable and
form stop-and-go waves that travel backwards, exactly like real congestion.

Used by the "other lane" episode:
  scenario "split":  same flow-seeking drivers, but one lane is denser -> slower. Share of drivers in it.
  scenario "equal":  both lanes have the same density and the same average speed, with waves in both.
                     We follow one car and measure how much of its time it is being overtaken.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

# IDM parameters (Treiber & Kesting, "Traffic Flow Dynamics", typical highway values; slightly
# "lazy" drivers so congestion forms stop-and-go waves)
V0 = 27.0      # desired speed (m/s) ~ 97 km/h
T = 1.5        # time headway (s)
A = 0.5        # max acceleration (m/s^2): gentle drivers, so dense traffic forms stop-and-go waves
B = 1.5        # comfortable deceleration (m/s^2)
S0 = 2.0       # jam distance (m)
CAR_L = 4.4    # vehicle length (m)
DELTA = 4


def idm_acc(v, gap, dv):
    s_star = S0 + np.maximum(0.0, v * T + v * dv / (2 * np.sqrt(A * B)))
    return A * (1 - (v / V0) ** DELTA - (s_star / np.maximum(gap, 0.1)) ** 2)


@dataclass
class LaneRun:
    t: np.ndarray        # (n_t,)
    x: np.ndarray        # (n_t, n_cars) position along the loop, unwrapped (m)
    v: np.ndarray        # (n_t, n_cars)
    a: np.ndarray        # (n_t, n_cars)
    length: float


def simulate_lane(n_cars: int, length: float, seed: int, t_warm: float = 900.0, t_rec: float = 90.0,
                  dt: float = 0.05, sample_dt: float = 1 / 30) -> LaneRun:
    rng = np.random.default_rng(seed)
    x = np.linspace(0, length, n_cars, endpoint=False) + rng.uniform(-1.0, 1.0, n_cars)
    x = np.sort(x)
    v = np.full(n_cars, 8.0) + rng.uniform(-0.5, 0.5, n_cars)
    steps_w = int(t_warm / dt)
    rec_every = max(1, int(round(sample_dt / dt)))
    ts, xs, vs, as_ = [], [], [], []
    total = steps_w + int(t_rec / dt) + 1
    for k in range(total):
        lead_x = np.roll(x, -1); lead_x[-1] += length
        gap = lead_x - x - CAR_L
        dv = v - np.roll(v, -1)
        acc = idm_acc(v, gap, dv) + rng.normal(0, 0.08, n_cars)      # small driver noise seeds waves
        v = np.maximum(0.0, v + acc * dt)
        x = x + v * dt
        if k >= steps_w and (k - steps_w) % rec_every == 0:
            ts.append((k - steps_w) * dt); xs.append(x.copy()); vs.append(v.copy()); as_.append(acc.copy())
    return LaneRun(np.array(ts), np.array(xs), np.array(vs), np.array(as_), length)


LENGTH = 2400.0


@lru_cache(maxsize=4)
def scenario(name: str):
    """-> (slow_lane, fast_lane) LaneRuns. Lane 0 is the right lane, lane 1 the left (passing) lane."""
    if name == "split":
        right = simulate_lane(96, LENGTH, seed=1)     # 40 cars/km: congested, stop-and-go
        left = simulate_lane(60, LENGTH, seed=2)      # 25 cars/km: moving better
    elif name == "equal":
        right = simulate_lane(72, LENGTH, seed=3, t_rec=240)
        left = simulate_lane(72, LENGTH, seed=4, t_rec=240)
    else:
        raise ValueError(name)
    return right, left


def share_in_slow_lane() -> dict:
    right, left = scenario("split")
    v_r, v_l = right.v.mean(), left.v.mean()
    n_r, n_l = right.x.shape[1], left.x.shape[1]
    slow_is_right = v_r < v_l
    share = (n_r if slow_is_right else n_l) / (n_r + n_l)
    return {"share": share, "v_slow": min(v_r, v_l), "v_fast": max(v_r, v_l),
            "flow_slow": (n_r / LENGTH) * v_r * 3600, "flow_fast": (n_l / LENGTH) * v_l * 3600}


def overtaken_fraction(ego: int | None = None) -> dict:
    """Follow car `ego` in the right lane for the recorded window: fraction of time a car in the
    other lane is moving faster than it (being overtaken) vs slower (it is overtaking)."""
    right, left = scenario("equal")
    egos = range(right.x.shape[1]) if ego is None else [ego]    # None: average over every driver
    fs, ss, vm = [], [], []
    xl = left.x % LENGTH
    for e in egos:
        ve = right.v[:, e]
        xe = right.x[:, e] % LENGTH
        d = (xl - xe[:, None] + LENGTH / 2) % LENGTH - LENGTH / 2      # nearest car in the other lane
        j = np.argmin(np.abs(d), axis=1)
        vn = left.v[np.arange(len(j)), j]
        fs.append(np.mean(vn > ve + 0.5)); ss.append(np.mean(vn < ve - 0.5)); vm.append(ve.mean())
    ve = np.array(vm)
    return {"passed_frac": float(np.mean(fs)), "passing_frac": float(np.mean(ss)),
            "v_right": float(right.v.mean()), "v_left": float(left.v.mean()),
            "ego_mean_v": float(ve.mean())}


def self_checks() -> dict:
    s = share_in_slow_lane()
    o = overtaken_fraction()
    eq = abs(o["v_right"] - o["v_left"]) / max(o["v_right"], o["v_left"])
    return {
        "slow_lane_is_denser_and_slower": (s["share"] > 0.5 and s["v_slow"] < s["v_fast"],
                                           f"{s['share']:.0%} of cars in the slow lane; {s['v_slow']*3.6:.0f} vs {s['v_fast']*3.6:.0f} km/h"),
        "equal_lanes_have_equal_speed": (eq < 0.05, f"lane mean speeds {o['v_right']*3.6:.1f} vs {o['v_left']*3.6:.1f} km/h ({eq:.1%} apart)"),
        "ego_overtaken_more_than_overtaking": (o["passed_frac"] > o["passing_frac"],
                                               f"ego overtaken {o['passed_frac']:.0%} of the time, overtaking {o['passing_frac']:.0%}"),
    }
