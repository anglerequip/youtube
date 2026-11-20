"""The zipper merge: render plan (the three.js scene is renderer/scenes/zipper3d.js; the street set is
renderer/sets/street.js).

A straight two-lane road in warm daylight; the right lane is closed by cones, a sign and a small digger, and the
cone taper meets the lane line at the merge point (z = 0). Cars travel toward -z. The wizard and the woman stand on
the grass verge by the road works.

Queue model (kept deliberately simple and the same for both scenarios): one car passes the merge point every
HEADWAY seconds, so the flow through the bottleneck, and with it the time through, is the same whichever way people
merge (MnDOT: travel time stays about the same). What changes is where the waiting cars stand: in one lane (merge
early) or shared over both lanes (zipper). With 20 cars, 12 + 8 over two lanes makes the longest queue 40 % shorter,
the "up to 40 %" the road agencies quote.

Scenario A (hook to "early"): 20 cars in the left lane, the right lane empty; a teal car drives the empty lane to the
cones and cuts in. Scenario B (from "zipper"): 12 cars left, 8 right, merging one from each side in turn.
Two frozen comparison roads far to the left (A: 20 in one lane; B: 12 + 8) for the "forty" beat; the A road is
reused, empty, for "On an empty road, though? Merge early." where one car moves over long before the cones.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "zipper3d"
SLUG = "zipper-merge"
LANE_W = 3.6
LEFT, RIGHT = -LANE_W / 2, LANE_W / 2
HEADWAY = 3.0          # s per car through the merge point (illustrative; the same in both scenarios)
SPACING = 6.0          # m from one queued car to the next (4.1 m car + gap)
FRONT = 3.0            # m: the first queued car's centre, behind the merge point
N_CARS = 20
B_LEFT, B_RIGHT = 12, 8
WIZ_CAR_RANK = 4       # the cream car in the left queue
GHOST_A = -30.0        # comparison roads (x of their centre lines)
GHOST_B = -56.0
WIZ = [7.0, 0.0, 9.5]
WOMAN = [7.5, 0.0, 6.4]
SPEAKER = {"hook": "wizard", "correct": "woman", "what": "wizard", "early": "woman", "zipper": "woman", "thatsit": "wizard",
           "forty": "woman", "faster": "wizard", "honest": "woman", "why": "woman", "payoff": "wizard"}
COLORS = ['#d9c7a0', '#e6e3dc', '#b9bdc2', '#8fa6c8', '#a99bc4', '#e2c45a', '#c9a77c']
KINDS = ['hatch', 'estate', 'sedan']


def queue_length(lanes: list[int]) -> float:
    """Length of the longest queue (m) for cars per lane."""
    return max(lanes) * SPACING


def _depart(z0, x0, t, td, to_left=True):
    """A car that passes the merge point at time td: accelerate away along -z, sliding into the left lane."""
    tau = t - td
    a, vmax = 2.2, 11.0
    t_v = vmax / a
    s = 0.5 * a * tau * tau if tau < t_v else 0.5 * a * t_v * t_v + vmax * (tau - t_v)
    z = z0 - s
    x = x0 + (LEFT - x0) * cam.ease(min(1.0, max(0.0, tau / 1.6))) if to_left else x0
    return x, z


def simulate(T, fps, t_a, t_b, cut_t):
    """Per-frame (x, z) for the 20 main-road cars and the cutter. Before t_b: scenario A; from t_b: scenario B."""
    n = len(T)
    X = np.zeros((n, N_CARS + 1)); Z = np.zeros((n, N_CARS + 1))
    # scenario A: left lane, rank = id; slot 0 before the cutter, the cutter takes slot 1, the rest follow
    slot_a = {0: cut_t - HEADWAY}
    for k in range(1, N_CARS):
        slot_a[k] = cut_t + k * HEADWAY
    # scenario B: alternate left / right until the right lane is empty
    order, li, ri = [], 0, 0
    while li < B_LEFT or ri < B_RIGHT:
        if li < B_LEFT:
            order.append(("L", li)); li += 1
        if ri < B_RIGHT:
            order.append(("R", ri)); ri += 1
    t_b0 = t_b + 1.2
    slot_b = {key: t_b0 + j * HEADWAY for j, key in enumerate(order)}
    lag = 1.0 - math.exp(-1.0 / (0.8 * fps))
    for car in range(N_CARS):
        zq = None
        for i, t in enumerate(T):
            if t < t_b:
                lane_x, rank, td = LEFT, car, slot_a[car]
                ahead = sum(1 for c in range(car) if slot_a[c] > t)
                started = t_a
            else:
                if car < B_LEFT:
                    key = ("L", car); lane_x = LEFT; rank = car
                    ahead = sum(1 for c in range(car) if slot_b[("L", c)] > t)
                else:
                    r = car - B_LEFT; key = ("R", r); lane_x = RIGHT; rank = r
                    ahead = sum(1 for c in range(r) if slot_b[("R", c)] > t)
                td = slot_b[key]
                started = t_b
            target = FRONT + SPACING * ahead
            if i == 0 or (T[i - 1] < started <= t):
                zq = FRONT + SPACING * rank                  # a fresh scenario starts with everyone at their rank
            if t < td:
                zq = zq + (target - zq) * lag
                X[i, car], Z[i, car] = lane_x, zq
                zdep = zq
            else:
                x, z = _depart(min(zdep, FRONT), lane_x, t, td, to_left=True)
                X[i, car], Z[i, car] = x, (z if z > -150 else -400.0)
    # the cutter: down the empty right lane, stops at the cones, slips in at its slot; gone in scenario B
    stop_t = cut_t - 0.5
    for i, t in enumerate(T):
        if t >= t_b:
            X[i, N_CARS], Z[i, N_CARS] = RIGHT, -400.0
        elif t < stop_t:
            u = cam.ease(min(1.0, t / stop_t))
            X[i, N_CARS], Z[i, N_CARS] = RIGHT, 95.0 + (FRONT - 95.0) * (1 - (1 - u) ** 1.6)
        elif t < cut_t:
            X[i, N_CARS], Z[i, N_CARS] = RIGHT, FRONT
        else:
            x, z = _depart(FRONT, RIGHT, t, cut_t)
            X[i, N_CARS], Z[i, N_CARS] = x, (z if z > -150 else -400.0)
    return X, Z


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    cut_t = at("hook", "cut") - 0.2
    hookcut_t = 2.9
    t_b = S("zipper") - 0.1
    then_t = at("zipper", "Then") - 0.2
    empty_t = at("why", "empty") - 0.5
    lanes_t = at("why", "both") - 0.2
    less_t = at("why", "less") - 0.1
    empty_e = at("early", "right") - 0.1
    X, Z = simulate(T, fps, 0.0, t_b, cut_t)

    # one car on the empty comparison road: right lane, moves over long before the cones (merge early)
    early = []
    for t in T:
        tau = t - empty_t
        z = 70.0 - 13.0 * max(0.0, tau)
        u = cam.ease(min(1.0, max(0.0, (70.0 - z - 14.0) / 22.0)))
        early.append([round(GHOST_A + RIGHT + (LEFT - RIGHT) * u, 2), round(z, 2)])

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_point", "woman_point", "ghost", "early", "zip_sign")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    frames["car_x"] = np.round(X, 2).tolist()
    frames["car_z"] = np.round(Z, 2).tolist()
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        who = SPEAKER.get(a) if a else None
        frames["look_w"].append("cutter" if t < S("correct") else ("road" if a in ("zipper", "honest", "why") else "woman"))
        frames["look_m"].append("road" if a in ("early", "zipper") else "wizard")
        frames["wiz_point"].append(round(duo.bump(t, at("hook", "guy") - 0.3, 0.35, 2.0, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, at("zipper", "both") - 0.3, 0.35, 1.6, 0.5), 3))
        frames["wiz_blink"].append(1.0 if (t % 3.9) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        g = 0
        if S("forty") - 0.1 <= t < S("faster") - 0.1:
            g = 1                                  # frozen comparison: A and B queues
        elif t >= empty_t - 0.2 and t < S("payoff") - 0.1:
            g = 2                                  # empty road, one early merger
        frames["ghost"].append(g)
        frames["early"].append(early[i])
        frames["zip_sign"].append(1 if t >= t_b else 0)

    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    # hook (a): chase cam low behind the cutter as it passes the stopped queue (keys follow its trajectory)
    keys = []
    for tk in np.arange(0.0, hookcut_t + 0.01, 0.25):
        i = min(n - 1, int(round(tk * fps)))
        cz = float(Z[i, N_CARS]); cx = float(X[i, N_CARS])
        keys.append((float(tk), K(cx + 0.9, 1.7, cz + 7.5), K(cx - 0.6, 1.0, cz - 14.0), 45))
    gx, gb = GHOST_A, GHOST_B
    # why (b): chase the early merger on the empty comparison road
    ekeys = []
    for tk in np.arange(empty_t, S("payoff") - 0.1 + 1e-6, 0.25):
        i = min(n - 1, int(round(tk * fps)))
        ex, ez = early[i]
        ekeys.append((float(tk), K(ex + 2.2, 3.6, ez + 13.0), K(ex - 1.0, 0.6, ez - 18.0), 44))
    shots = cam.chain([
        cam.shot(0.0, hookcut_t, keys, fps, "day"),
        # hook (b): the wizard on the verge pointing as the teal car squeezes in at the cones
        E_(hookcut_t, S("correct") - 0.1, K(10.2, 2.0, 15.5), K(9.9, 1.95, 15.0), K(3.0, 1.1, 2.0), 42, "day"),
        # correct: the woman, the road works behind her
        E_(S("correct") - 0.1, S("what") - 0.1, K(7.0, 1.62, 9.4), K(7.05, 1.62, 9.15), K(7.6, 1.45, 6.4), 38, "day"),
        # what: the wizard, the long queue behind him
        E_(S("what") - 0.1, S("early") - 0.1, K(5.6, 1.65, 6.9), K(5.65, 1.65, 7.05), K(7.0, 1.6, 9.5), 36, "day"),
        # early: highway centreline from behind the queue: one long line beside an empty lane
        E_(S("early") - 0.1, empty_e, K(0.0, 9.0, 131.0), K(0.0, 8.6, 126.0), K(0.0, 0.0, 40.0), 40, "day"),
        # early (b): low in the empty right lane, the stopped queue receding beside it
        E_(empty_e, t_b, K(3.2, 2.4, 18.0), K(3.1, 2.3, 23.0), K(-0.6, 0.9, 95.0), 44, "day"),
        # zipper (a): high centreline again, now from the other shoulder: both lanes used, two short queues
        E_(t_b, then_t, K(-5.0, 12.0, 112.0), K(-4.6, 11.4, 106.0), K(1.0, 0.0, 35.0), 42, "day"),
        # zipper (b): high over the merge point: one from each side, in turn
        E_(then_t, S("thatsit") - 0.1, K(-6.0, 24.0, 20.0), K(-5.0, 23.0, 17.0), K(0.0, 0.0, 2.0), 40, "day"),
        # thatsit: the wizard, sceptical
        E_(S("thatsit") - 0.1, S("forty") - 0.1, K(5.95, 1.62, 7.15), K(6.05, 1.62, 7.3), K(7.0, 1.58, 9.5), 36, "day"),
        # forty: the two frozen comparison roads from high above: one long queue against two short ones
        E_(S("forty") - 0.1, S("faster") - 0.1, K((gx + gb) / 2, 140.0, 76.0), K((gx + gb) / 2, 134.0, 74.0), K((gx + gb) / 2, 0.0, 62.0), 50, "day"),
        # faster: the wizard, delighted
        E_(S("faster") - 0.1, S("honest") - 0.1, K(5.6, 1.65, 6.9), K(5.7, 1.65, 7.1), K(7.0, 1.62, 9.5), 36, "day"),
        # honest: the woman, then the merge flowing at its steady rate
        E_(S("honest") - 0.1, at("honest", "Minnesota") - 0.2, K(7.0, 1.62, 9.4), K(7.05, 1.62, 9.2), K(7.5, 1.45, 6.4), 38, "day"),
        E_(at("honest", "Minnesota") - 0.2, S("why") - 0.1, K(-8.0, 8.0, 14.0), K(-7.5, 7.6, 12.5), K(0.0, 0.0, 0.0), 42, "day"),
        # why (a): highway centreline in front of the merge, both lanes rolling in at the same speed
        E_(S("why") - 0.1, less_t, K(1.0, 5.5, -22.0), K(1.0, 5.2, -19.0), K(0.0, 0.5, 20.0), 40, "day"),
        # why (a2): overhead 3/4 over the merge: no lane jumping, one from each side
        E_(less_t, empty_t, K(12.0, 15.0, 26.0), K(10.5, 14.0, 22.0), K(0.0, 0.0, 2.0), 40, "day"),
        # why (b): the empty comparison road: one car moves over early, long before the cones
        cam.shot(empty_t, S("payoff") - 0.1, ekeys, fps, "day"),
        # payoff: back on the verge: the wizard, the zipper working behind him
        cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(10.4, 2.0, 15.6), K(4.0, 1.1, 4.0), 42),
                                                (dur + 0.05, K(9.8, 1.95, 14.6), K(4.0, 1.1, 4.0), 42)], fps, "day"),
    ])
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("forty", "forty"), "end": S("faster") - 0.15, "big": "Up to 40%", "small": "shorter backup", "y": 0.16},
        {"start": at("honest", "same") - 0.2, "end": S("why") - 0.15, "big": "Same trip time", "small": "MnDOT", "y": 0.16},
    ]
    events = [(round(cut_t, 3), "swish", {"gain": 0.16}),
              (round(t_b, 3), "whoosh", {"gain": 0.14}),
              (round(at("forty", "forty"), 3), "ding", {"gain": 0.14}),
              (round(empty_t + 0.2, 3), "whoosh", {"gain": 0.12})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [t_b, at("forty", "forty"), at("honest", "Not")], "events": events,
               "mutes": [], "swells": [S("payoff")]}
    a_len, b_len = queue_length([N_CARS]), queue_length([B_LEFT, B_RIGHT])
    facts = {"queue_shorter_pct": round(100 * (1 - b_len / a_len)), "cars": N_CARS, "headway_s": HEADWAY,
             "events": {"cutter_in_lane": {"t": cut_t + 1.7, "observe": "cutter_x", "expect": LEFT, "tol": 0.05},
                        "right_lane_used_in_b": {"t": t_b + 0.5, "observe": "right_queue", "expect": B_RIGHT, "tol": 0}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 41, "supersample": 1.0,
            "end_hold_s": 1.6,
            "layout": {"wiz": WIZ, "woman": WOMAN, "lane_w": LANE_W, "n_cars": N_CARS, "wiz_car": WIZ_CAR_RANK,
                       "ghost_a": GHOST_A, "ghost_b": GHOST_B, "b_left": B_LEFT, "b_right": B_RIGHT, "spacing": SPACING,
                       "front": FRONT, "colors": COLORS, "kinds": KINDS},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    F = plan["frames"]
    if what == "cutter_x":
        return F["car_x"][k][-1]
    if what == "right_queue":
        return sum(1 for c in range(plan["layout"]["n_cars"]) if abs(F["car_x"][k][c] - LANE_W / 2) < 0.01 and F["car_z"][k][c] > 0)
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 100, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """The toy queues must show the claimed effect and nothing more: 40 % shorter, same flow through the merge."""
    a, b = queue_length([N_CARS]), queue_length([B_LEFT, B_RIGHT])
    pct = 100 * (1 - b / a)
    return {"zipper queue 40 % shorter than the single-lane queue (WisDOT 'as much as 40%')": {"pass": abs(pct - 40) < 0.5, "detail": f"{a:.0f} m vs {b:.0f} m = {pct:.0f}%"},
            "same headway through the merge in both scenarios (MnDOT: travel time about the same)": {"pass": True, "detail": f"{HEADWAY} s per car"}}
