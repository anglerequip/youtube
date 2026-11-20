"""Your banana is radioactive: render plan from the potassium-40 model
(factory/simulation_engine/physics/potassium.py; the three.js scene is renderer/scenes/banana3d.js).

A banana on a wooden picnic table in a garden, a wooden toy figure beside it, and (not to scale) a cluster of
potassium atoms floating above the table. The flashes on the banana are a Poisson sample at the banana's real
activity, so the "decays counted" counter and the flashes agree frame by frame. In the body only one decay in
SHOW_EVERY is drawn (badge says so), while the card carries the real total.
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam
from factory.simulation_engine.physics import potassium as k40

SCENE = "banana3d"
TABLE = [0.0, 0.76, 0.0]         # table top centre (y = top surface)
BANANA = [0.0, 0.80, 0.0]        # banana centre on the table
FIG = [0.85, 0.0, -0.35]         # figure stands beside the table
ATOMS = [-0.6, 1.25, -0.2]       # the floating atom cluster (not to scale)
SHOW_EVERY = 25                  # body: draw one decay in 25


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.05) * fps))
    T = np.arange(n) / fps
    f = k40.facts()
    at = lambda b, w: timing.word_time(tl, b, w)
    dur = n / fps

    # ---- decays: the banana at its real rate the whole video; the body from the 'you' beat
    rng = np.random.default_rng(11)
    bt = k40.decay_times(f["banana_bq"], 0.0, dur, seed=5)
    banana_ev = [[t, round(float(rng.uniform(0.06, 0.94)), 3), round(float(rng.uniform(0, 2 * math.pi)), 3),
                  "beta" if rng.random() < k40.BETA_SHARE else "gamma"] for t in bt]
    body_t = k40.decay_times(f["body_bq"] / SHOW_EVERY, S("you") - 0.1, dur, seed=9)
    body_ev = [[t, round(float(rng.uniform(0.08, 1.68)), 3), round(float(rng.uniform(-1, 1)), 3), round(float(rng.uniform(-1, 1)), 3)] for t in body_t]
    count0 = S("hook") + 0.2
    eat0, eat1 = S("eat") + 0.3, S("eat") + 1.4               # banana goes to the figure
    decay_t = at("what", "fires") - 0.05                      # the highlighted atom decays

    frames = {k: [] for k in ("count", "body_k", "banana_on", "eaten", "atom", "badge", "body_on")}
    for t in T:
        frames["count"].append(sum(1 for x in bt if count0 <= x <= t))
        # body potassium: the banana's 0.45 g arrives, the kidneys remove it over a few hours (time-lapse)
        if t < eat1:
            kb = k40.BODY_K_G
        else:
            u = (t - eat1) / max(0.5, E("eat") - eat1 - 0.2)
            kb = k40.BODY_K_G + k40.BANANA_K_G * min(1.0, (t - eat1) / 0.6) * math.exp(-2.5 * max(0.0, u))
        frames["body_k"].append(round(kb, 3))
        frames["banana_on"].append(0 if t >= eat1 else 1)
        frames["eaten"].append(round(cam.ease((t - eat0) / (eat1 - eat0)) if t >= eat0 else 0.0, 3))
        frames["atom"].append(round(min(1.0, max(0.0, (t - decay_t) / 0.6)), 3) if t >= decay_t else 0.0)
        frames["body_on"].append(1 if t >= S("you") - 0.1 else 0)
        b = ""
        if S("why") - 0.1 <= t < S("you") - 0.1:
            b = "NOT TO SCALE"
        elif S("you") - 0.1 <= t < S("eat") - 0.1:
            b = "ONLY SOME DECAYS DRAWN"
        elif t >= eat1:
            b = "TIME-LAPSE, HOURS"
        frames["badge"].append(b)

    K = lambda *a: list(a)
    bx, by, bz = BANANA
    ax, ay, az = ATOMS
    fx, fy, fz = FIG
    end_t = dur + 0.05
    shots = cam.chain([
        # hook: low and close on the banana, flashes already popping, slow push
        cam.shot(0.0, S("why") - 0.1, [(0.0, K(bx + 0.30, by + 0.16, bz + 0.42), K(bx, by + 0.02, bz), 40),
                                       (S("why") - 0.1, K(bx + 0.24, by + 0.14, bz + 0.36), K(bx, by + 0.02, bz), 40)], fps, "key"),
        # why: the atom cluster above the table (not to scale), one potassium-40 highlighted
        cam.shot(S("why") - 0.1, S("slow") - 0.1, [(S("why") - 0.1, K(ax + 0.55, ay + 0.15, az + 0.85), K(ax, ay, az), 40),
                                                   (S("slow") - 0.1, K(ax + 0.42, ay + 0.12, az + 0.72), K(ax, ay, az), 40)], fps, "golden"),
        # slow: orbit closer around the waiting atom
        cam.shot(S("slow") - 0.1, S("what") - 0.1, [(S("slow") - 0.1, K(ax - 0.35, ay + 0.1, az + 0.55), K(ax, ay, az), 40),
                                                    (S("what") - 0.1, K(ax - 0.45, ay + 0.12, az + 0.45), K(ax, ay, az), 40)], fps, "golden"),
        # what: the decay: an electron streaks away, the atom turns white (calcium)
        cam.shot(S("what") - 0.1, S("you") - 0.1, [(S("what") - 0.1, K(ax + 0.2, ay + 0.06, az + 0.62), K(ax + 0.05, ay, az), 42),
                                                   (S("you") - 0.1, K(ax + 0.28, ay + 0.08, az + 0.7), K(ax + 0.08, ay, az), 42)], fps, "key"),
        # you: the figure beside the table, flickering
        cam.shot(S("you") - 0.1, S("eat") - 0.1, [(S("you") - 0.1, K(fx - 1.6, 1.3, fz + 3.4), K(fx - 0.25, 0.9, fz), 40),
                                                  (S("eat") - 0.1, K(fx - 1.3, 1.25, fz + 3.0), K(fx - 0.25, 0.9, fz), 40)], fps, "key"),
        # eat: the banana goes to the figure; the potassium counter barely moves and settles back
        cam.shot(S("eat") - 0.1, end_t, [(S("eat") - 0.1, K(fx + 1.8, 1.4, fz + 3.0), K(fx - 0.2, 0.95, fz), 40),
                                         (end_t, K(fx + 1.5, 1.35, fz + 2.6), K(fx - 0.2, 0.95, fz), 40)], fps, "golden"),
    ])
    focal = []
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            if len(focal) < n and s_["i0"] + k == len(focal):
                focal.append(lk)
    while len(focal) < n:
        focal.append(focal[-1])
    frames["focal_pt"] = focal[:n]

    cards = [
        {"start": at("why", "unstable") - 0.3, "end": S("slow") - 0.15, "big": "potassium-40", "small": "about 1 atom in 8,500", "y": 0.17},
        {"start": at("slow", "Half"), "end": S("what") - 0.15, "big": "half-life", "small": "over a billion years", "y": 0.17},
        {"start": at("what", "calcium") - 0.1, "end": S("you") - 0.15, "big": "calcium-40", "small": "what it becomes", "y": 0.17},
        {"start": at("you", "four"), "end": S("eat") - 0.15, "big": "≈ 4,400", "small": "decays a second in you", "y": 0.17},
    ]
    events = [(round(decay_t + 0.02, 3), "pop", {"gain": 0.2, "seed": 6}),
              (round(eat0, 3), "whoosh", {"gain": 0.12})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [decay_t, eat1], "events": events,
               "mutes": [], "swells": [S("you")], "decay_t": decay_t, "eat": [eat0, eat1]}
    facts = dict(f)
    facts.update({"slow_factors": [], "one_in_card": 8500.0,
                  "events": {"atom_decayed": {"t": decay_t + 0.7, "observe": "atom", "expect": 1.0, "tol": 0.01}}})
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 51, "supersample": 1.0,
            "bloom_threshold": 3.0, "end_hold_s": 1.0,
            "layout": {"table": TABLE, "banana": BANANA, "fig": FIG, "atoms": ATOMS},
            "banana_events": banana_ev, "body_events": body_ev,
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what == "atom":
        return plan["frames"]["atom"][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 96, "gain": 0.14}


def self_checks() -> dict:
    return k40.self_checks()
