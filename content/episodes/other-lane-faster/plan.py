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


def _crossings(R, Lr, k0, k1):
    """Per right-lane car: (other-lane cars it overtakes, other-lane cars that overtake it) in frames k0..k1.
    Positions are loop distances; a crossing counts only near the car (|gap| < 25 m), not across the loop."""
    L = tr.LENGTH
    d0 = ((Lr.x[k0][None, :] % L) - (R.x[k0][:, None] % L) + L / 2) % L - L / 2
    d1 = ((Lr.x[k1][None, :] % L) - (R.x[k1][:, None] % L) + L / 2) % L - L / 2
    near = (np.abs(d0) < 60) & (np.abs(d1) < 60)
    passes = ((d0 > 0) & (d1 < 0) & near).sum(axis=1)
    passed = ((d0 < 0) & (d1 > 0) & near).sum(axis=1)
    return passes, passed


def _flow_past(R, Lr, k0, k1, back=15.0, ahead=90.0, dv=2.5):
    """Per right-lane car: mean number of other-lane cars on screen beside/ahead of it (-back..ahead m) that
    move at least `dv` m/s faster, frames k0..k1. Reviewer, round 3: during "the other lane drifts past" the
    other lane looked almost empty; crossings alone (at most one in 4.5 s) did not reward a busy other lane."""
    L = tr.LENGTH
    acc, n = np.zeros(R.x.shape[1]), 0
    for k in range(k0, k1, 6):
        d = ((Lr.x[k][None, :] % L) - (R.x[k][:, None] % L) + L / 2) % L - L / 2
        fast = Lr.v[k][None, :] > R.v[k][:, None] + dv
        acc += ((d > -back) & (d < ahead) & fast).sum(axis=1); n += 1
    return acc / max(n, 1)


def _pick_ego_visible(R, Lr, w, c, v, offsets):
    """(ego, offset) whose story is visible on screen (reviewer, round 2): during `w` (watch) it overtakes
    several other-lane cars without braking, during `c` (crawl) and `v` (view) other-lane cars overtake it."""
    best, arg = -1e9, (0, 0)
    brk = _brakes(R.a)
    for o in offsets:
        if o + v[1] >= R.v.shape[0]:
            break
        pw, _ = _crossings(R, Lr, o + w[0], o + w[1])
        _, qc = _crossings(R, Lr, o + c[0], o + c[1])
        _, qv = _crossings(R, Lr, o + v[0], o + v[1])
        pc, _ = _crossings(R, Lr, o + c[0], o + c[1])
        score = 2.0 * np.minimum(pw, 4) + np.minimum(qc, 5) + 1.5 * np.minimum(qv, 2) - 3.0 * pc \
            - 12.0 * brk[o + w[0]: o + w[1]].mean(axis=0)
        e = int(np.argmax(score))
        if score[e] > best:
            best, arg = score[e], (e, o)
    return arg


def _jams(z, v, slow=5.0, pad=3.0, max_n=8):
    """Stretches of the right lane where cars crawl (< `slow` m/s), as [z_front, z_back] in world z. The red
    wash marks these jams only, moving with them (reviewer, round 2: painting the whole lane red said
    'this lane is slow' instead of 'jams hold more cars')."""
    idx = np.argsort(z)
    segs = []
    for j in idx:
        if v[j] < slow and -260 < z[j] < 150:
            a, b = z[j] - pad - 2.1, z[j] + pad + 2.1
            if segs and a <= segs[-1][1] + 6.0:
                segs[-1][1] = max(segs[-1][1], b)
            else:
                segs.append([a, b])
    segs = [sg for sg in segs if sg[1] - sg[0] > 14.0]          # a jam is several cars, not one slow car
    return [[round(a, 1), round(b, 1)] for a, b in segs[:max_n]]


def _pick_story(R, Lr, w, c, v, offsets):
    """One followed car, three moments of its own simulated life (hard cuts between them): `w` where its
    lane flows and it overtakes other-lane cars without braking, `c` where it crawls in a jam while the
    other lane passes it, `v` where cars both pass it and get passed. A single continuous window with all
    three does not exist in this simulation (searched 2026-11-19), so the edit jumps forward in time at the
    cuts, like any documentary. Returns (ego, [offset_w, offset_c, offset_v])."""
    brk = _brakes(R.a)
    n = R.x.shape[1]
    bw, bc, bv = np.full(n, -1e9), np.full(n, -1e9), np.full(n, -1e9)
    ow, oc, ov = np.zeros(n, int), np.zeros(n, int), np.zeros(n, int)
    for o in offsets:
        if o + max(w[1], c[1], v[1]) >= R.v.shape[0]:
            break
        pw, qw = _crossings(R, Lr, o + w[0], o + w[1])
        sw = 2.0 * np.minimum(pw, 4) - 2.0 * qw - 12.0 * brk[o + w[0]: o + w[1]].mean(axis=0)
        pc, qc = _crossings(R, Lr, o + c[0], o + c[1])
        km = o + (c[0] + c[1]) // 2                     # a visible queue ahead: cars within 45 m in its own lane
        dq = ((R.x[km][None, :] % tr.LENGTH) - (R.x[km][:, None] % tr.LENGTH)) % tr.LENGTH
        ahead = ((dq > 0) & (dq < 45)).sum(axis=1)
        flow = _flow_past(R, Lr, o + c[0], o + c[1])
        vc = R.v[o + c[0]: o + c[1]]
        sc = 2.0 * np.minimum(qc, 3) - 3.0 * pc - 1.5 * vc.mean(axis=0) - 1.0 * vc.max(axis=0) \
            + 0.6 * np.minimum(ahead, 6) + 3.0 * np.minimum(flow, 3)      # crawling means really slow (round 4)
        pv, qv = _crossings(R, Lr, o + v[0], o + v[1])
        sv = np.minimum(qv, 2) + np.minimum(pv, 2) + 0.5 * ((qv > 0) & (pv > 0))
        for s_, b_, o_ in ((sw, bw, ow), (sc, bc, oc), (sv, bv, ov)):
            better = s_ > b_
            b_[better] = s_[better]; o_[better] = o
    e = int(np.argmax(bw + bc + bv))
    return e, [int(ow[e]), int(oc[e]), int(ov[e])]


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
    ego_e, offs = _pick_story(eq_r, eq_l, (f(S("watch")), f(E("watch"))), (f(S("crawl")), f(E("crawl"))),
                              (f(S("view")), f(E("view"))), range(0, 5200, 15))
    seg_off = lambda t: offs[0] if t < S("crawl") - 0.1 else offs[1] if t < S("view") - 0.1 else offs[2]
    off_e = offs[0]

    frames = {"right": [], "left": [], "rb": [], "lb": [], "ego": [], "scen": [], "scroll": [], "focal_pt": [], "jams": []}
    L = tr.LENGTH
    brakes = {id(r): _brakes(r.a) for r in (split_r, split_l, eq_r, eq_l)}
    for i, t in enumerate(T):
        if t < cut_eq:
            R, Lr, e, k = split_r, split_l, ego_s, min(i, split_r.x.shape[0] - 1)
            z0 = split_r.x[0, ego_s]
        else:
            R, Lr, e = eq_r, eq_l, ego_e
            k = min(seg_off(t) + i - int(round(cut_eq * fps)), eq_r.x.shape[0] - 1)
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
        frames["jams"].append(_jams(-rel(R.x[k]), R.v[k]) if t < cut_eq else [])

    ego = lambda i: (LANE_X[0], 0.0, 0.0)
    # Cuts every 2.5-6 s (house style: a new angle for most beats, no shot over ~6 s)
    shots = cam.chain([
        # 1. chase cam behind the ego car, the other lane rolling past
        cam.shot(0.0, S("setup") - 0.1, [(0.0, [-1.2, 3.0, 13.0], [-0.4, 0.8, -20], 40),
                                         (S("setup"), [-1.0, 3.15, 13.8], [-0.4, 0.8, -21], 40)], fps, "key", ego),
        # 2. low over the shoulder of the ego car, looking across at the next lane as it slides past
        # (picture review, round 4: the fence shot did not show the other lane moving)
        cam.shot(S("setup") - 0.1, S("setup") + 3.0, [(S("setup"), [0.6, 4.2, 9.0], [-3.2, 0.5, -12], 42),
                                                      (S("setup") + 3.0, [0.5, 4.3, 8.5], [-3.2, 0.5, -13], 42)], fps, "key", ego),
        # 2b. high behind the ego car, looking forward along its queue (round 4: the old look-back shot
        # mirrored the lanes and made the car seem to change lanes)
        cam.shot(S("setup") + 3.0, S("dense") - 0.1, [(S("setup") + 3.0, [3.2, 7.0, 13.0], [0.6, 0.6, -22.0], 42),
                                                      (S("dense"), [3.0, 7.6, 12.0], [0.6, 0.6, -24.0], 42)], fps, "key", ego),
        # 3. crane up to a 3/4 aerial: the slow lane is packed, the fast lane spread out
        cam.shot(S("dense") - 0.1, S("gaps") - 0.1, [(S("dense"), [5.0, 8.0, 16.0], [-1.8, 0.0, -30], 42),
                                                     (S("gaps"), [6.0, 15.0, 22.0], [-1.8, 0.0, -42], 42)], fps, "key", ego),
        # 4. 3/4 aerial from the other side: the gaps in the fast lane
        cam.shot(S("gaps") - 0.1, S("gaps") + 3.0, [(S("gaps"), [-11.0, 16.0, 12.0], [-1.0, 0.0, -30], 42),
                                                    (S("gaps") + 3.0, [-10.5, 17.0, 10.0], [-1.0, 0.0, -34], 42)], fps, "key", ego),
        # 4b. lower along the fast lane: long empty gaps between its cars
        cam.shot(S("gaps") + 3.0, S("share") - 0.05, [(S("gaps") + 3.0, [-5.5, 6.0, 10.0], [-1.8, 0.5, -60], 40),
                                                      (S("share"), [-5.0, 6.5, 12.0], [-1.8, 0.5, -66], 40)], fps, "key", ego),
        # 5. 3/4 aerial from behind the jam, looking forward along it (round 4: the old map view lost the
        # jam while the 62% card was up). The followed car leaves the jam's front at ~26 s and the jam drifts
        # backwards, so these shots frame the jam (z +30..+150 behind the car), not the car.
        cam.shot(S("share") - 0.05, S("odds") - 0.1, [(S("share"), [9.0, 26.0, 118.0], [0.0, 0.0, 35.0], 42),
                                                      (S("odds"), [10.0, 27.0, 126.0], [0.0, 0.0, 48.0], 42)], fps, "key", ego),
        # 6. the same jam from the fast-lane side, a little lower
        cam.shot(S("odds") - 0.1, cut_eq, [(S("odds"), [-12.0, 18.0, 140.0], [0.5, 0.0, 62.0], 42),
                                           (cut_eq, [-13.0, 19.0, 146.0], [0.5, 0.0, 72.0], 42)], fps, "key", ego),
        # 7. new experiment, golden light: highway centreline, symmetric, cars receding into haze
        cam.shot(cut_eq, S("rehook") + 3.0, [(cut_eq, [0.0, 5.5, 14.0], [0.0, 1.0, -60], 38),
                                             (S("rehook") + 3.0, [0.0, 6.0, 16.0], [0.0, 1.0, -66], 38)], fps, "golden", ego),
        # 7b. high behind the ego car (ring): the car we follow
        cam.shot(S("rehook") + 3.0, S("watch") - 0.1, [(S("rehook") + 3.0, [-3.0, 12.0, 18.0], [-0.3, 0.5, -6.0], 42),
                                                       (S("watch"), [-3.5, 11.0, 15.0], [-0.3, 0.5, -6.0], 42)], fps, "golden", ego),
        # 8. 3/4 tracking on the ego car (ring): it zips past the other lane
        cam.shot(S("watch") - 0.1, S("crawl") - 0.1, [(S("watch"), [-0.6, 7.0, 15.0], [-0.2, 0.4, -4.0], 46),
                                                      (S("crawl"), [-0.8, 7.4, 14.0], [-0.2, 0.4, -4.5], 46)], fps, "golden", ego),
        # 9. behind and above the ego, looking far down both lanes: it waits in its queue while the other
        # lane keeps arriving from behind and drifting ahead (round 4)
        cam.shot(S("crawl") - 0.1, S("number") - 0.1, [(S("crawl"), [-1.2, 6.0, 16.0], [-0.7, 0.4, -4.0], 46),
                                                       (S("number"), [-1.4, 6.3, 15.0], [-0.7, 0.4, -4.5], 46)], fps, "golden", ego),
        # 10. the numbers, still on the ringed driver (round 4: they used to sit over a generic aerial)
        cam.shot(S("number") - 0.1, S("number") + 3.9, [(S("number"), [5.0, 9.0, 13.0], [0.0, 1.0, -0.3], 44),
                                                        (S("number") + 3.9, [6.0, 9.5, 11.0], [0.0, 1.0, -0.3], 44)], fps, "golden", ego),
        cam.shot(S("number") + 3.9, S("view") - 0.1, [(S("number") + 3.9, [-6.5, 9.5, 12.0], [0.0, 1.0, -0.3], 44),
                                                      (S("view"), [-7.5, 10.0, 10.0], [0.0, 1.0, -0.3], 44)], fps, "golden", ego),
        # 11. just above and behind the ego roof: cars that pass stay in view ahead
        cam.shot(S("view") - 0.1, S("outro") - 0.1, [(S("view"), [-1.0, 6.5, 14.0], [-0.9, 0.0, -18], 46),
                                                     (S("outro"), [-1.2, 6.2, 13.0], [-0.9, 0.0, -17], 46)], fps, "golden", ego),
        # 12. centreline again, low: the same road for everyone
        cam.shot(S("outro") - 0.1, S("outro") + 2.6, [(S("outro"), [0.0, 4.5, 12.0], [0.0, 1.0, -60], 38),
                                                      (S("outro") + 2.6, [0.0, 5.0, 14.0], [0.0, 1.0, -62], 38)], fps, "golden", ego),
        # 13. rise and pull back over the road (calm ending)
        cam.shot(S("outro") + 2.6, n / fps + 0.1, [(S("outro") + 2.6, [3.0, 6.0, 16.0], [0.0, 0.5, -12.0], 40),
                                                   (n / fps, [8.0, 22.0, 34.0], [0.0, 0.0, -5.0], 40)], fps, "golden", ego),
    ])

    # wide shots are about the whole system: their focal point is where the camera looks
    for k_ in (3, 4, 5, 6, 7, 8, 15):
        s_ = shots[k_]
        for k, lk in enumerate(s_["look"]):
            i = s_["i0"] + k
            if i < n:
                frames["focal_pt"][i] = [round(v, 2) for v in lk]

    sh = tr.share_in_slow_lane(); ov = tr.overtaken_fraction()

    def at(bid, phrase):
        """Approximate time a phrase is spoken: its character position within the beat's narration."""
        txt = next(ln.text for ln in tl.lines if ln.id == bid).replace("*", "")
        return S(bid) + (E(bid) - S(bid)) * max(txt.find(phrase), 0) / max(len(txt), 1)
    # the rest of the time neither car is faster (within 0.5 m/s): shown as the remainder of the two rounded
    # numbers so the three cards add up to 100 (reviewer, round 3: "the remaining 10% is unexplained")
    level_pct = 100 - round(ov["passed_frac"] * 100) - round(ov["passing_frac"] * 100)
    cards = [
        {"start": S("share") + 2.6, "end": E("odds") + 0.3, "big": f"{sh['share'] * 100:.0f}%", "small": "of drivers are in the slow lane", "y": 0.17},
        {"start": at("number", "forty-eight") - 0.3, "end": at("number", "forty-two") - 0.45, "big": f"{ov['passed_frac'] * 100:.0f}%", "small": "of the time being overtaken", "y": 0.17},
        {"start": at("number", "forty-two") - 0.3, "end": at("number", "The rest") - 0.45, "big": f"{ov['passing_frac'] * 100:.0f}%", "small": "of the time overtaking", "y": 0.17},
        {"start": at("number", "The rest") - 0.3, "end": E("number") + 0.4, "big": f"≈ {level_pct:.0f}%", "small": "roughly level", "y": 0.17},
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
    frames["ring"] = [1 if S("watch") - 0.1 <= t < S("view") - 0.1 or (S("rehook") <= t < S("watch")) else 0 for t in T]

    timing = {"cut_eq": cut_eq, "reveals": [S("share") + 2.6], "cuts": [s["start"] for s in shots[1:]],
              "ego_split": ego_s, "ego_equal": ego_e, "offset_equal": off_e, "offsets_equal": offs}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 5, "supersample": 1.25,
            "lanes": LANE_X, "n_right": max(split_r.x.shape[1], eq_r.x.shape[1]),
            "n_left": max(split_l.x.shape[1], eq_l.x.shape[1]),
            "shots": shots, "cards": cards, "frames": frames, "timing": timing, "wordmark": None,
            "facts": {"slow_lane_share_pct": sh["share"] * 100, "overtaken_pct": ov["passed_frac"] * 100,
                      "overtaking_pct": ov["passing_frac"] * 100,
                      "level_pct": (1 - ov["passed_frac"] - ov["passing_frac"]) * 100}}


def sfx_events(plan: dict) -> list:
    t = plan["timing"]
    return [(c - 0.08, "swish", {"gain": 0.35}) for c in t["cuts"][2:4]]     # lands on the cut (sound review, round 3)


def music(plan: dict) -> dict:
    return {"mutes": [], "swells": [plan["timing"]["reveals"][0]], "bpm": 100, "gain": 0.17}


def self_checks() -> dict:
    return tr.self_checks()
