"""The other lane: render plan from the IDM traffic simulation (factory/simulation_engine/physics/traffic.py).

World: a straight two-lane highway along -z. Right lane x=+1.8, left (passing) lane x=-1.8.
The followed car ("ego") is in the right lane; the camera rigs follow it. Car positions come straight
from the simulation (positions on a 2.4 km loop, shown relative to the ego car).
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam
from factory.simulation_engine.physics import traffic as tr

SCENE = "traffic3d"
LANE_X = (1.8, -1.8)          # right, left
BRAKE_ACC = -0.7              # m/s^2: brake lights on below this deceleration
BRAKE_OFF = -0.3              # ...and off again only above this (hysteresis: no one-frame blinking)
BRAKE_MIN_ON = 12             # frames (0.4 s): a brake light that comes on stays on at least this long
BRAKE_MIN_OFF = 4             # frames: and once off, stays off at least this long


def _brakes(a):
    """Brake-light state per frame and car from the simulated acceleration, with hysteresis and a minimum
    on-time. A plain threshold made lights chatter on and off for single frames (seen as flicker by
    factory/qa/frames.py in the 2026-11-19 render)."""
    import numpy as np
    a = np.asarray(a)
    on = np.zeros(a.shape, bool)
    state = np.zeros(a.shape[1], bool); held = np.full(a.shape[1], 10 ** 6)
    for k in range(a.shape[0]):
        start = ~state & (a[k] < BRAKE_ACC) & (held >= BRAKE_MIN_OFF)
        stop = state & (a[k] > BRAKE_OFF) & (held >= BRAKE_MIN_ON)
        state = (state | start) & ~stop
        held = np.where(start | stop, 0, held + 1)
        on[k] = state
    return on


def _rel_speed(R, Lr, k0, k1):
    """Ego-relative speed of the nearest other-lane car, for every right-lane car, frames k0..k1."""
    L = tr.LENGTH
    out = []
    for k in range(k0, k1, 5):
        d = ((Lr.x[k][None, :] % L) - (R.x[k][:, None] % L) + L / 2) % L - L / 2
        j = np.argmin(np.abs(d), axis=1)
        out.append(R.v[k] - Lr.v[k][j])
    return np.mean(out, axis=0)


def _pick_ego(R, Lr, a, b, c, d, offsets):
    """(ego, offset): the ego passes its neighbours in window [a,b] and is passed in [c,d]."""
    best, arg = -1e9, (0, 0)
    for o in offsets:
        if o + d >= R.v.shape[0]:
            break
        score = _rel_speed(R, Lr, o + a, o + b) - 1.5 * _rel_speed(R, Lr, o + c, o + d)
        e = int(np.argmax(score))
        if score[e] > best:
            best, arg = score[e], (e, o)
    return arg


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.85) * fps))
    T = np.arange(n) / fps
    split_r, split_l = tr.scenario("split")
    eq_r, eq_l = tr.scenario("equal")
    cut_eq = S("rehook") - 0.1            # hard cut to the second experiment (equal lanes, golden light)

    # split scenario: ego = a right-lane (slow lane) car that is crawling during the setup
    ego_s = int(np.argmin(split_r.v[: int(10 * fps)].mean(axis=0)))
    # equal scenario: ego flows during "watch" and crawls during "crawl"
    f = lambda t: int(round((t - cut_eq) * fps))
    ego_e, off_e = _pick_ego(eq_r, eq_l, f(S("watch")), f(E("watch")), f(S("crawl")), f(E("crawl")), range(0, 5200, 60))

    frames = {"right": [], "left": [], "rb": [], "lb": [], "ego": [], "scen": [], "scroll": [], "focal_pt": []}
    L = tr.LENGTH
    brakes = {id(r): _brakes(r.a) for r in (split_r, split_l, eq_r, eq_l)}
    for i, t in enumerate(T):
        if t < cut_eq:
            R, Lr, e, k = split_r, split_l, ego_s, min(i, split_r.x.shape[0] - 1)
            z0 = split_r.x[0, ego_s]
        else:
            R, Lr, e = eq_r, eq_l, ego_e
            k = min(off_e + i - int(round(cut_eq * fps)), eq_r.x.shape[0] - 1)
            z0 = eq_r.x[off_e, ego_e]
        xe = R.x[k, e]
        ze = -(xe - z0)                                    # ego world z (moves along -z)
        rel = lambda xs: ((xs - xe + L / 2) % L) - L / 2   # loop distance ahead of ego (m)
        # ego-relative world: the ego car sits at z=0, the road and scenery scroll past (keeps shadows
        # and the camera near the origin); z = -(distance ahead along the loop)
        frames["right"].append([round(float(-d), 2) for d in rel(R.x[k])])
        frames["left"].append([round(float(-d), 2) for d in rel(Lr.x[k])])
        frames["scroll"].append(round(float(-ze), 3))
        frames["rb"].append("".join("1" if b else "0" for b in brakes[id(R)][k]))
        frames["lb"].append("".join("1" if b else "0" for b in brakes[id(Lr)][k]))
        frames["ego"].append(e)
        frames["scen"].append(0 if t < cut_eq else 1)
        frames["focal_pt"].append([LANE_X[0], 0.7, 0.0])

    ego = lambda i: (LANE_X[0], 0.0, 0.0)
    shots = cam.chain([
        # 1. chase cam behind the ego car, the other lane rolling past
        cam.shot(0.0, S("dense") - 0.1, [(0.0, [-1.2, 3.0, 13.0], [-0.4, 0.8, -20], 40),
                                         (S("dense"), [-0.8, 3.3, 14.5], [-0.4, 0.8, -22], 40)], fps, "key", ego),
        # 2. crane up to a 3/4 aerial: the slow lane is packed, the fast lane spread out
        cam.shot(S("dense") - 0.1, S("share") - 0.05, [(S("dense"), [5.0, 8.0, 16.0], [-1.8, 0.0, -30], 42),
                                                       (S("share"), [8.0, 42.0, 40.0], [-1.8, 0.0, -90], 42)], fps, "key", ego),
        # 3. high "map" view far down both lanes: the packed lane against the spread one
        cam.shot(S("share") - 0.05, cut_eq, [(S("share"), [-1.8, 60.0, 62.0], [-1.8, 0.0, -50.0], 38),
                                             (cut_eq, [-1.8, 70.0, 58.0], [-1.8, 0.0, -66.0], 38)], fps, "key", ego),
        # 4. new experiment, golden light: highway centreline, symmetric, cars receding into haze
        cam.shot(cut_eq, S("watch") - 0.1, [(cut_eq, [0.0, 5.5, 14.0], [0.0, 1.0, -60], 38),
                                            (S("watch"), [0.0, 6.5, 18.0], [0.0, 1.0, -70], 38)], fps, "golden", ego),
        # 5. 3/4 tracking on the ego car (ring): it zips past, then crawls while the other lane drifts by
        cam.shot(S("watch") - 0.1, S("number") - 0.1, [(S("watch"), [-5.0, 9.0, 13.0], [-0.3, 0.6, -1.5], 44),
                                                       (S("crawl"), [-6.0, 9.5, 11.0], [-0.3, 0.6, -2.0], 44),
                                                       (S("number"), [-7.0, 10.0, 9.0], [-0.3, 0.6, -2.5], 44)], fps, "golden", ego),
        # 6. big picture: both lanes from high up, waves of brake lights travelling backwards
        cam.shot(S("number") - 0.1, S("view") - 0.1, [(S("number"), [18.0, 55.0, 40.0], [0.0, 0.0, -60.0], 40),
                                                      (S("view"), [22.0, 70.0, 30.0], [0.0, 0.0, -80.0], 40)], fps, "golden", ego),
        # 7. just above and behind the ego roof: cars that pass stay in view ahead
        cam.shot(S("view") - 0.1, S("outro") - 0.1, [(S("view"), [0.3, 3.6, 11.0], [-0.8, 0.0, -14], 46),
                                                     (S("outro"), [0.1, 3.3, 10.0], [-0.7, 0.0, -13], 46)], fps, "golden", ego),
        # 8. rise and pull back over the road (calm ending)
        cam.shot(S("outro") - 0.1, n / fps + 0.1, [(S("outro"), [3.0, 4.0, 14.0], [0.0, 0.5, -12.0], 40),
                                                   (n / fps, [8.0, 22.0, 34.0], [0.0, 0.0, -5.0], 40)], fps, "golden", ego),
    ])

    # wide shots are about the whole system: their focal point is where the camera looks
    for s_ in (shots[1], shots[2], shots[3], shots[5]):
        for k, lk in enumerate(s_["look"]):
            i = s_["i0"] + k
            if i < n:
                frames["focal_pt"][i] = [round(v, 2) for v in lk]

    sh = tr.share_in_slow_lane(); ov = tr.overtaken_fraction()
    cards = [
        {"start": S("share") + 2.6, "end": E("odds") + 0.3, "big": f"{sh['share'] * 100:.0f}%", "small": "of drivers are in the slow lane", "y": 0.17},
        {"start": S("number") + 1.2, "end": S("number") + 4.4, "big": f"{ov['passed_frac'] * 100:.0f}%", "small": "of the time being overtaken", "y": 0.17},
        {"start": S("number") + 4.6, "end": E("number") + 0.4, "big": f"{ov['passing_frac'] * 100:.0f}%", "small": "of the time overtaking", "y": 0.17},
    ]
    badges = [""] * n
    for i, t in enumerate(T):
        if S("dense") <= t < cut_eq:
            badges[i] = "SAME ROAD, TWO LANES"
        elif S("watch") <= t < S("number"):
            badges[i] = "EQUAL AVERAGE SPEED"
    frames["badge"] = badges
    frames["ring"] = [1 if S("watch") - 0.1 <= t < S("number") - 0.1 or (S("rehook") <= t < S("watch")) else 0 for t in T]

    timing = {"cut_eq": cut_eq, "reveals": [S("share") + 2.6], "cuts": [s["start"] for s in shots[1:]],
              "ego_split": ego_s, "ego_equal": ego_e, "offset_equal": off_e}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 5, "supersample": 1.25,
            "lanes": LANE_X, "n_right": max(split_r.x.shape[1], eq_r.x.shape[1]),
            "n_left": max(split_l.x.shape[1], eq_l.x.shape[1]),
            "shots": shots, "cards": cards, "frames": frames, "timing": timing, "wordmark": None,
            "facts": {"slow_lane_share_pct": sh["share"] * 100, "overtaken_pct": ov["passed_frac"] * 100,
                      "overtaking_pct": ov["passing_frac"] * 100}}


def sfx_events(plan: dict) -> list:
    t = plan["timing"]
    return [(c - 0.25, "swish", {"gain": 0.35}) for c in t["cuts"][2:4]]


def music(plan: dict) -> dict:
    return {"mutes": [], "swells": [plan["timing"]["reveals"][0]], "bpm": 100, "gain": 0.17}


def self_checks() -> dict:
    return tr.self_checks()
