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
    brk = _brakes(R.a)            # "they zip past" must not show brake lights (reviewer 2026-11-19)
    for o in offsets:
        if o + d >= R.v.shape[0]:
            break
        score = (_rel_speed(R, Lr, o + a, o + b) - 1.5 * _rel_speed(R, Lr, o + c, o + d)
                 - 12.0 * brk[o + a: o + b].mean(axis=0))
        e = int(np.argmax(score))
        if score[e] > best:
            best, arg = score[e], (e, o)
    return arg


def _pick_dense_ego(R, Lr, k0, k1, k_setup, ahead=70.0):
    L = tr.LENGTH
    best, arg = -1e9, 0
    for e in range(R.x.shape[1]):
        c = []
        for k in range(k0, min(k1, R.x.shape[0]), 15):
            xe = R.x[k, e] % L
            dr = ((R.x[k] % L) - xe + L / 2) % L - L / 2
            dl = ((Lr.x[k] % L) - xe + L / 2) % L - L / 2
            c.append(((dr > -15) & (dr < ahead)).sum() - ((dl > -15) & (dl < ahead)).sum())
        score = float(np.mean(c)) - 0.4 * float(R.v[:k_setup, e].mean())
        if score > best:
            best, arg = score, e
    return arg


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.85) * fps))
    T = np.arange(n) / fps
    split_r, split_l = tr.scenario("split")
    eq_r, eq_l = tr.scenario("equal")
    cut_eq = S("rehook") - 0.1            # hard cut to the second experiment (equal lanes, golden light)

    # split scenario: ego = a slow-lane car that crawls during the setup AND sits in the densest stretch
    # while the narration says "slow traffic is packed tight" (reviewer 2026-11-19: both lanes looked
    # equally sparse around the old ego). Score: cars ahead in its lane minus cars ahead in the other.
    ego_s = _pick_dense_ego(split_r, split_l, int(round(S("dense") * fps)), int(round(cut_eq * fps)), int(10 * fps))
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
    # Cuts every 2.5-6 s (house style: a new angle for most beats, no shot over ~6 s)
    shots = cam.chain([
        # 1. chase cam behind the ego car, the other lane rolling past
        cam.shot(0.0, S("setup") - 0.1, [(0.0, [-1.2, 3.0, 13.0], [-0.4, 0.8, -20], 40),
                                         (S("setup"), [-1.0, 3.15, 13.8], [-0.4, 0.8, -21], 40)], fps, "key", ego),
        # 2. low beside the road: both lanes stretch ahead, the ego car in front of us
        cam.shot(S("setup") - 0.1, S("setup") + 3.0, [(S("setup"), [6.5, 1.7, 7.0], [-1.0, 0.8, -26], 40),
                                                      (S("setup") + 3.0, [6.3, 1.85, 5.0], [-1.0, 0.8, -27], 40)], fps, "key", ego),
        # 2b. over the slow lane's queue, looking back at the ego car and the cars behind it
        cam.shot(S("setup") + 3.0, S("dense") - 0.1, [(S("setup") + 3.0, [-2.5, 7.0, -14.0], [0.0, 0.6, 6.0], 42),
                                                      (S("dense"), [-2.8, 7.6, -12.0], [0.0, 0.6, 8.0], 42)], fps, "key", ego),
        # 3. crane up to a 3/4 aerial: the slow lane is packed, the fast lane spread out
        cam.shot(S("dense") - 0.1, S("gaps") - 0.1, [(S("dense"), [5.0, 8.0, 16.0], [-1.8, 0.0, -30], 42),
                                                     (S("gaps"), [7.0, 26.0, 30.0], [-1.8, 0.0, -65], 42)], fps, "key", ego),
        # 4. 3/4 aerial from the other side: the gaps in the fast lane
        cam.shot(S("gaps") - 0.1, S("gaps") + 3.0, [(S("gaps"), [-16.0, 30.0, 28.0], [-1.8, 0.0, -70], 40),
                                                    (S("gaps") + 3.0, [-14.5, 34.0, 31.0], [-1.8, 0.0, -79], 40)], fps, "key", ego),
        # 4b. lower along the fast lane: long empty gaps between its cars
        cam.shot(S("gaps") + 3.0, S("share") - 0.05, [(S("gaps") + 3.0, [-5.5, 6.0, 10.0], [-1.8, 0.5, -60], 40),
                                                      (S("share"), [-5.0, 6.5, 12.0], [-1.8, 0.5, -66], 40)], fps, "key", ego),
        # 5. high "map" view far down both lanes: the packed lane against the spread one
        cam.shot(S("share") - 0.05, S("odds") - 0.1, [(S("share"), [-1.8, 60.0, 62.0], [-1.8, 0.0, -50.0], 38),
                                                      (S("odds"), [-1.8, 66.0, 60.0], [-1.8, 0.0, -60.0], 38)], fps, "key", ego),
        # 6. almost straight down, slowly turning: the queue as a map
        cam.shot(S("odds") - 0.1, cut_eq, [(S("odds"), [2.0, 80.0, -22.0], [-1.8, 0.0, -48.0], 40),
                                           (cut_eq, [-5.0, 84.0, -24.0], [-1.8, 0.0, -50.0], 40)], fps, "key", ego),
        # 7. new experiment, golden light: highway centreline, symmetric, cars receding into haze
        cam.shot(cut_eq, S("rehook") + 3.0, [(cut_eq, [0.0, 5.5, 14.0], [0.0, 1.0, -60], 38),
                                             (S("rehook") + 3.0, [0.0, 6.0, 16.0], [0.0, 1.0, -66], 38)], fps, "golden", ego),
        # 7b. high behind the ego car (ring): the car we follow
        cam.shot(S("rehook") + 3.0, S("watch") - 0.1, [(S("rehook") + 3.0, [-3.0, 12.0, 18.0], [-0.3, 0.5, -6.0], 42),
                                                       (S("watch"), [-3.5, 11.0, 15.0], [-0.3, 0.5, -6.0], 42)], fps, "golden", ego),
        # 8. 3/4 tracking on the ego car (ring): it zips past the other lane
        cam.shot(S("watch") - 0.1, S("crawl") - 0.1, [(S("watch"), [-8.0, 12.0, 16.0], [0.4, 0.3, -5.0], 44),
                                                      (S("crawl"), [-8.5, 12.5, 14.0], [0.4, 0.3, -5.5], 44)], fps, "golden", ego),
        # 9. low on the far side: now it crawls while the other lane drifts by
        cam.shot(S("crawl") - 0.1, S("number") - 0.1, [(S("crawl"), [5.5, 5.0, 10.0], [-0.6, 0.4, -3.0], 42),
                                                       (S("number"), [5.0, 5.4, 8.5], [-0.6, 0.4, -3.5], 42)], fps, "golden", ego),
        # 10. big picture: both lanes from high up, waves of brake lights travelling backwards
        cam.shot(S("number") - 0.1, S("view") - 0.1, [(S("number"), [18.0, 55.0, 40.0], [0.0, 0.0, -60.0], 40),
                                                      (S("view"), [22.0, 70.0, 30.0], [0.0, 0.0, -80.0], 40)], fps, "golden", ego),
        # 11. just above and behind the ego roof: cars that pass stay in view ahead
        cam.shot(S("view") - 0.1, S("outro") - 0.1, [(S("view"), [0.3, 3.6, 11.0], [-0.8, 0.0, -14], 46),
                                                     (S("outro"), [0.1, 3.3, 10.0], [-0.7, 0.0, -13], 46)], fps, "golden", ego),
        # 12. centreline again, low: the same road for everyone
        cam.shot(S("outro") - 0.1, S("outro") + 2.6, [(S("outro"), [0.0, 4.5, 12.0], [0.0, 1.0, -60], 38),
                                                      (S("outro") + 2.6, [0.0, 5.0, 14.0], [0.0, 1.0, -62], 38)], fps, "golden", ego),
        # 13. rise and pull back over the road (calm ending)
        cam.shot(S("outro") + 2.6, n / fps + 0.1, [(S("outro") + 2.6, [3.0, 6.0, 16.0], [0.0, 0.5, -12.0], 40),
                                                   (n / fps, [8.0, 22.0, 34.0], [0.0, 0.0, -5.0], 40)], fps, "golden", ego),
    ])

    # wide shots are about the whole system: their focal point is where the camera looks
    for k_ in (3, 4, 5, 6, 7, 8, 12, 14):
        s_ = shots[k_]
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
        elif S("rehook") + 1.5 <= t < S("number"):
            badges[i] = "EQUAL AVERAGE SPEED"
    frames["badge"] = badges
    # slow-lane wash: fades in when the narration compares the lanes, out before the second experiment
    def _fade(t, a, b, r=0.5):
        return max(0.0, min(1.0, (t - a) / r, (b - t) / r))
    frames["lane_tint"] = [round(_fade(t, S("dense"), cut_eq - 0.2), 3) for t in T]
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
