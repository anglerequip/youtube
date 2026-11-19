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
            return 1.0 + cam.ease((t - S("double")) / 2.6)
        return 2.0 - cam.ease((t - S("outro")) / (n / fps - S("outro") - 0.4))

    cut_macro0, cut_macro1 = S("links") - 0.1, S("rope") - 0.1
    morph_t0 = S("reality") + 0.35
    frames = {k: [] for k in ("h2", "h1", "morph", "rope", "dist", "heap", "sway", "lever", "badge", "focal_pt")}
    dist = 0.0
    for i, t in enumerate(T):
        h2 = h2_at(t); st = cf.steady(h2)
        macro = cut_macro0 <= t < cut_macro1
        slow = 1000.0 if macro else 4.0
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
            b = "SLOWED 1,000× · SIMPLIFIED"
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
        cam.shot(S("payoff") + 2.0, S("double") - 0.1, [(S("payoff") + 2.0, K(1.1, 0.95, 1.9), K(0.05, 0.72, 0.0), 36),
                                                        (S("double") - 0.1, K(1.2, 1.0, 2.0), K(0.05, 0.76, 0.0), 36)], fps, "key"),
        cam.shot(S("double") - 0.1, S("rehook") - 0.1, [(S("double") - 0.1, K(0.42, 0.06, 0.8), K(0.04, 0.03, 0.0), 32),
                                                        (S("speed"), K(0.5, 0.12, 0.95), K(0.04, 0.09, 0.0), 32),
                                                        (S("rehook") - 0.1, K(0.45, 0.14, 0.85), K(0.04, 0.1, 0.0), 32)], fps, "key", pile),
        cam.shot(S("rehook") - 0.1, cut_macro0, [(S("rehook") - 0.1, K(0.2, 0.2, 0.32), K(0.03, 0.12, 0.0), 32),
                                                 (cut_macro0, K(0.07, 0.05, 0.12), K(0.01, 0.0, 0.0), 32)], fps, "key", pile),
        cam.shot(cut_macro0, cut_macro1, [(cut_macro0, K(0.017, 0.02, 0.036), K(0.009, 0.003, 0.0), 40),
                                          (cut_macro1, K(0.014, 0.018, 0.034), K(0.009, 0.003, 0.0), 40)], fps, "key", pile),
        cam.shot(cut_macro1, S("kick") - 0.1, [(cut_macro1, K(0.05, 0.1, 0.38), K(0.03, 0.06, 0.0), 32),
                                               (S("kick") - 0.1, K(0.03, 0.11, 0.35), K(0.03, 0.06, 0.0), 32)], fps, "key", pile),
        cam.shot(S("kick") - 0.1, S("catch") - 0.1, [(S("kick") - 0.1, K(0.12, 0.03, 0.22), K(0.01, 0.03, 0.0), 32),
                                                     (S("catch") - 0.1, K(0.45, 0.2, 0.75), K(0.04, 0.12, 0.0), 32)], fps, "golden", pile),
        cam.shot(S("catch") - 0.1, S("outro") - 0.1, [(S("catch") - 0.1, K(-0.5, 0.1, 0.8), K(0.04, 0.07, 0.0), 32),
                                                      (S("outro") - 0.1, K(-0.2, 0.13, 0.9), K(0.04, 0.08, 0.0), 32)], fps, "golden", pile),
        cam.shot(S("outro") - 0.1, n / fps + 0.05, [(S("outro") - 0.1, K(0.6, 0.25, 0.9), K(0.03, 0.065, 0.0), 30),
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
    cards = [
        {"start": S("payoff") + 3.2, "end": S("double") - 0.05, "big": f"≈ {a1['h1'] * 100:.0f} cm", "small": "arch for a 1 m drop (our model)", "y": 0.17},
        {"start": S("double") + 1.4, "end": S("speed") - 0.05, "big": f"≈ {a2['h1'] * 100:.0f} cm", "small": "arch for a 2 m drop", "y": 0.17},
        {"start": S("speed") + 0.8, "end": S("rehook") - 0.15, "big": f"≈ {a2['v']:.1f} m/s", "small": "chain speed", "y": 0.17},
    ]
    events = [(round(morph_t0, 3), "rise", {"gain": 0.4})]
    t = 0.3
    while t < n / fps - 0.5:                       # light chain clatter (not in the macro, it is slowed 1000x)
        if not (cut_macro0 <= t < cut_macro1):
            events.append((round(t, 3), "tink", {"gain": 0.06 + 0.05 * rng.random(), "pan": float(rng.uniform(-0.3, 0.3))}))
        t += 0.18 + 0.2 * rng.random()
    # in the macro: a soft tick each time a link is lifted off the pile
    cyc = 0.0046 / (cf.steady(2.0)["v"] / 1000.0)
    t = cut_macro0 + 0.4
    while t < cut_macro1:
        events.append((round(t, 3), "tick", {"gain": 0.25}))
        t += cyc
    timing = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [morph_t0], "events": events,
              "mutes": [[S("wrong") - 0.1, morph_t0 - 0.05]], "swells": [morph_t0]}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 12, "supersample": 1.0,
            "pile_h": PILE_H, "shots": shots, "cards": cards, "frames": frames, "timing": timing, "wordmark": None}


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 94, "gain": 0.16}


def self_checks() -> dict:
    return cf.self_checks()
