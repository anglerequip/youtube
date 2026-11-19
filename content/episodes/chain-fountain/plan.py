"""Chain fountain: render plan from the steady-state model (factory/simulation_engine/physics/chain_fountain.py).

The arch height h1 and chain speed v follow from the drop h2 (pile to floor) at every frame. The stand's
height changes only between demonstrations and slowly, so the chain is treated as quasi-steady.
The chain is shown slowed down (badge), so the beads can be followed.
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam
from factory.simulation_engine.physics import chain_fountain as cf

SCENE = "chain3d"
PILE_H = 0.035          # pile top above the jar's base (m)


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.85) * fps))
    T = np.arange(n) / fps
    rng = np.random.default_rng(4)

    def h2_at(t):
        if t < S("double"):
            return 1.0
        if t < S("outro"):
            return 1.0 + cam.ease((t - S("double")) / 1.6)
        return 2.0 - cam.ease((t - S("outro")) / (n / fps - S("outro") - 0.4))

    cut_macro0, cut_macro1 = S("links") - 0.1, S("rope") - 0.1
    morph_t0 = S("reality") + 0.35
    frames = {k: [] for k in ("h2", "h1", "morph", "rope", "dist", "heap", "sway", "lever", "badge", "focal_pt")}
    dist = 0.0
    for i, t in enumerate(T):
        h2 = h2_at(t); st = cf.steady(h2)
        macro = cut_macro0 <= t < cut_macro1
        slow = 3000.0 if macro else 4.0       # macro: one link-lift every ~3 s, so each step can be followed
        if S("wrong") - 0.1 <= t < morph_t0:
            m = 0.0
        elif morph_t0 <= t < morph_t0 + 1.1:
            m = cam.ease((t - morph_t0) / 1.1)
        else:
            m = 1.0
        frames["h2"].append(round(h2, 5)); frames["h1"].append(round(st["h1"] * m, 5))
        frames["morph"].append(round(m, 4))
        frames["rope"].append(1.0 if S("rope") - 0.1 <= t < S("kick") - 0.1 else 0.0)
        dist += st["v"] / slow / fps
        frames["dist"].append(round(dist, 6))
        frames["heap"].append(round(0.25 + 0.65 * t / (n / fps), 4))
        frames["sway"].append(0.0015 if not macro else 0.0)
        frames["lever"].append({"glow": 1.0 if t >= S("push") - 0.1 else 0.0} if macro else None)
        if macro:
            b = "SLOWED 3,000× · SIMPLIFIED"
        elif S("wrong") - 0.1 <= t < morph_t0:
            b = "IF IT WERE A ROPE"
        elif S("rope") - 0.1 <= t < S("kick") - 0.1:
            b = "WHITE: A ROPE"
        else:
            b = "SLOWED 4×"
        frames["badge"].append(b)

    pile = lambda i: (0.0, frames["h2"][min(i, n - 1)], 0.0)
    K = lambda *a: list(a)
    shots = cam.chain([
        cam.shot(0.0, S("setup") + 1.2, [(0.0, K(0.33, 0.12, 0.5), K(0.03, 0.065, 0.0), 30),
                                         (S("setup") + 1.2, K(0.29, 0.13, 0.46), K(0.03, 0.065, 0.0), 30)], fps, "key", pile),
        cam.shot(S("setup") + 1.2, S("wrong") - 0.1, [(S("setup") + 1.2, K(0.6, 1.0, 1.2), K(0.08, 0.95, 0.0), 34),
                                                      (S("wrong") - 0.1, K(0.7, 0.4, 1.5), K(0.08, 0.15, 0.0), 34)], fps, "key"),
        cam.shot(S("wrong") - 0.1, S("payoff") + 2.0, [(S("wrong") - 0.1, K(0.02, 0.11, 0.36), K(0.03, 0.07, 0.0), 30),
                                                       (S("payoff") + 2.0, K(0.0, 0.12, 0.33), K(0.03, 0.07, 0.0), 30)], fps, "key", pile),
        cam.shot(S("payoff") + 2.0, S("double") - 0.1, [(S("payoff") + 2.0, K(0.75, 0.95, 1.35), K(0.05, 0.72, 0.0), 38),
                                                        (S("double") - 0.1, K(0.8, 1.0, 1.4), K(0.05, 0.76, 0.0), 38)], fps, "key"),
        cam.shot(S("double") - 0.1, S("rehook") - 0.1, [(S("double") - 0.1, K(0.42, 0.06, 0.8), K(0.04, 0.03, 0.0), 32),
                                                        (S("speed"), K(0.5, 0.12, 0.95), K(0.04, 0.09, 0.0), 32),
                                                        (S("rehook") - 0.1, K(0.45, 0.14, 0.85), K(0.04, 0.1, 0.0), 32)], fps, "key", pile),
        cam.shot(S("rehook") - 0.1, cut_macro0, [(S("rehook") - 0.1, K(0.2, 0.2, 0.32), K(0.03, 0.12, 0.0), 32),
                                                 (cut_macro0, K(0.07, 0.05, 0.12), K(0.01, 0.0, 0.0), 32)], fps, "key", pile),
        cam.shot(cut_macro0, S("push") - 0.1, [(cut_macro0, K(0.017, 0.02, 0.036), K(0.009, 0.003, 0.0), 40),
                                               (S("push"), K(0.015, 0.019, 0.035), K(0.009, 0.003, 0.0), 40)], fps, "key", pile),
        cam.shot(S("push") - 0.1, cut_macro1, [(S("push"), K(0.004, 0.012, 0.04), K(0.010, 0.002, 0.0), 40),
                                               (cut_macro1, K(0.002, 0.013, 0.038), K(0.010, 0.002, 0.0), 40)], fps, "key", pile),
        cam.shot(cut_macro1, S("kick") - 0.1, [(cut_macro1, K(0.05, 0.1, 0.38), K(0.03, 0.06, 0.0), 32),
                                               (S("kick") - 0.1, K(0.03, 0.11, 0.35), K(0.03, 0.06, 0.0), 32)], fps, "key", pile),
        cam.shot(S("kick") - 0.1, S("kick") + 4.3, [(S("kick") - 0.1, K(0.12, 0.03, 0.22), K(0.01, 0.03, 0.0), 32),
                                                    (S("kick") + 4.3, K(0.3, 0.12, 0.5), K(0.03, 0.08, 0.0), 32)], fps, "golden", pile),
        cam.shot(S("kick") + 4.3, S("catch") - 0.1, [(S("kick") + 4.3, K(0.0, 0.5, 0.7), K(0.03, 0.2, 0.0), 34),
                                                     (S("catch") - 0.1, K(-0.05, 0.55, 0.75), K(0.03, 0.22, 0.0), 34)], fps, "golden", pile),
        cam.shot(S("catch") - 0.1, S("catch") + 3.4, [(S("catch") - 0.1, K(-0.5, 0.1, 0.8), K(0.04, 0.07, 0.0), 32),
                                                      (S("catch") + 3.4, K(-0.35, 0.12, 0.85), K(0.04, 0.08, 0.0), 32)], fps, "golden", pile),
        cam.shot(S("catch") + 3.4, S("outro") - 0.1, [(S("catch") + 3.4, K(0.08, 0.16, 0.34), K(0.03, 0.09, 0.0), 30),
                                                      (S("outro") - 0.1, K(0.06, 0.17, 0.32), K(0.03, 0.09, 0.0), 30)], fps, "golden", pile),
        cam.shot(S("outro") - 0.1, S("outro") + 3.0, [(S("outro") - 0.1, K(0.6, 0.25, 0.9), K(0.03, 0.065, 0.0), 30),
                                                      (S("outro") + 3.0, K(0.5, 0.2, 0.75), K(0.03, 0.065, 0.0), 30)], fps, "key", pile),
        cam.shot(S("outro") + 3.0, n / fps + 0.05, [(S("outro") + 3.0, K(-0.3, 0.15, 0.55), K(0.03, 0.065, 0.0), 30),
                                                    (n / fps, K(0.33, 0.12, 0.5), K(0.03, 0.065, 0.0), 30)], fps, "key", pile),
    ])
    frames["focal_pt"] = [None] * n
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            i = s_["i0"] + k
            if 0 <= i < n:
                frames["focal_pt"][i] = lk
    for i in range(n):
        if frames["focal_pt"][i] is None:
            frames["focal_pt"][i] = frames["focal_pt"][i - 1] if i else [0, 1.05, 0]

    a1, a2 = cf.steady(1.0), cf.steady(2.0)

    def settled(t0, target):
        """First time after t0 at which the drawn arch is within 2% of the value its card will show
        (a card must never announce a height the arch on screen has not reached yet)."""
        for i in range(int(t0 * fps), n):
            if abs(frames["h1"][i] - target) <= 0.02 * target:
                return i / fps
        return t0
    show1 = max(S("payoff") + 3.2, settled(S("payoff"), a1["h1"]))
    show2 = max(S("double") + 1.2, settled(S("double"), a2["h1"]) + 0.1)
    cards = [
        {"start": show1, "end": S("double") - 0.05, "big": f"≈ {a1['h1'] * 100:.0f} cm", "small": "arch for a 1 m drop (our model)", "y": 0.17},
        {"start": show2, "end": S("speed") + 0.7, "big": f"≈ {a2['h1'] * 100:.0f} cm", "small": "arch for a 2 m drop", "y": 0.17},
        {"start": S("speed") + 0.8, "end": S("rehook") - 0.15, "big": f"≈ {a2['v']:.1f} m/s", "small": "chain speed", "y": 0.17},
    ]
    events = [(round(morph_t0, 3), "rise", {"gain": 0.4})]
    # Chain clatter. It used to be a bell-like 'tink' (one identical sample, 1.4 s ring) every 0.18-0.38 s
    # for the whole video: Caesar heard "ding ding ding" (2026-11-19). Now: short dry link clicks
    # ('coil', a new random sample each time, 40 ms), quiet, only while the chain is visibly running,
    # and kept off the narration's words (factory/qa/sound.py checks repetition, density, masking).
    t = 0.3
    while t < n / fps - 0.5:
        if not (cut_macro0 <= t < cut_macro1):
            events.append((round(t, 3), "coil", {"gain": 0.10 + 0.06 * rng.random(), "speed": 0.5,
                                                 "stack": float(rng.random()), "pan": float(rng.uniform(-0.3, 0.3))}))
        t += 0.22 + 0.25 * rng.random()
    # in the macro (slowed 1000x): a soft, varied tick each time a link is lifted off the pile
    cyc = 0.0046 / (cf.steady(2.0)["v"] / 3000.0)
    t, j = cut_macro0 + 0.4, 0
    while t < cut_macro1 and j < 4:          # the first few links only: the idea is clear, then let it breathe
        events.append((round(t, 3), "tick", {"gain": 0.18, "seed": 60 + j, "pitch": 0.9 + 0.08 * (j % 3), "ring": 0.25}))
        t += cyc * (0.85 + 0.3 * rng.random()); j += 1
    timing = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [morph_t0], "events": events,
              "mutes": [[S("wrong") - 0.1, morph_t0 - 0.05]], "swells": [morph_t0]}
    facts = {"drop_1m": 1.0, "drop_2m": 2.0, "arch_1m_cm": a1["h1"] * 100, "arch_2m_cm": a2["h1"] * 100,
             "arch_ratio_2m_1m": a2["h1"] / a1["h1"], "speed_2m": a2["v"], "alpha": cf.ALPHA,
             "slow_factors": [4, 3000],
             "events": {
                 "arch_1m": {"t": show1, "observe": "arch_cm", "expect": a1["h1"] * 100, "tol": 0.03},
                 "arch_2m": {"t": show2, "observe": "arch_cm", "expect": a2["h1"] * 100, "tol": 0.03}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 12, "supersample": 1.0, "bloom_threshold": 50.0,
            "pile_h": PILE_H, "shots": shots, "cards": cards, "frames": frames, "timing": timing, "wordmark": None,
            "facts": facts}


def observe(plan: dict, i: int, what: str):
    if what == "arch_cm":
        return plan["frames"]["h1"][min(i, plan["n_frames"] - 1)] * 100
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 94, "gain": 0.16}


def self_checks() -> dict:
    return cf.self_checks()
