"""Chain fountain, retention demo: the chain-fountain plan plus what the retention toolkit needs.

Everything physical comes from ../chain-fountain/plan.py and the steady-state model. This file adds:
  * hud_anchors(): the tracked 3D points the HUD measures (pile level and arch top, the push point)
  * frames['alpha_pct']: the model's pile push, which the "no push" sequence in the catch beat switches
    off and back on. The arch is recomputed from the model at every frame (alpha 0 -> no arch, it drapes
    like the rope), so the picture, the meter and the narration all come from the same numbers.
  * a tighter opening shot (hook): the arch fills the middle of the frame and the camera pulls back.
The label cards for the two arch heights are dropped: the live measuring line shows the same values.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

from factory import camera as cam
from factory.simulation_engine.physics import chain_fountain as cf

_spec = importlib.util.spec_from_file_location("chain_fountain_base_plan", Path(__file__).parent.parent / "chain-fountain" / "plan.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

SCENE = base.SCENE
XR, XF, JR = 0.006, 0.045 + 0.032, 0.045      # pick-up x, falling-leg x, jar radius (renderer/scenes/chain3d.js)
DIM_X = (XR + XF) / 2                           # the measuring line runs up the middle of the arch, between its legs


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    plan = base.build_plan(tl, fps, W, H)
    S, E = tl.start, tl.end
    from factory.retention import timing
    F, n = plan["frames"], plan["n_frames"]
    # ---- no-push experiment (catch beat): alpha 12% -> 0 at "no push", back to 12% when the outro starts
    t_off = timing.word_time(tl, "catch", "no")
    t_on = S("outro")
    alpha = []
    for i in range(n):
        t = i / fps
        a = cf.ALPHA
        if t >= t_off:
            a = cf.ALPHA * (1 - cam.ease((t - t_off) / 1.3))
        if t >= t_on:
            a = cf.ALPHA * cam.ease((t - t_on) / 1.2)
        alpha.append(a)
        if t >= t_off:
            h2 = F["h2"][i]
            F["h1"][i] = round(cf.steady(h2, a)["h1"], 5)
            F["morph"][i] = round(a / cf.ALPHA, 4)      # no push: the path blends to the rope's drape over the rim
    F["alpha_pct"] = [round(100 * a, 3) for a in alpha]
    # ---- hook: open close on the arch (it fills the middle of the frame), then pull back to the old framing
    s0 = plan["shots"][0]
    pile = lambda i: (0.0, F["h2"][min(i, n - 1)], 0.0)
    K = lambda *a: list(a)
    new0 = cam.shot(0.0, s0["end"], [(0.0, K(0.15, 0.115, 0.24), K(0.035, 0.085, 0.0), 30),
                                     (S("hook") + 2.4, K(0.27, 0.125, 0.42), K(0.032, 0.07, 0.0), 30),
                                     (s0["end"], K(0.29, 0.13, 0.46), K(0.03, 0.065, 0.0), 30)], fps, "key", pile)
    new0["end"] = s0["end"]
    plan["shots"][0] = new0
    # ---- the two arch-height cards are replaced by the live measuring line (same values, from the same frames)
    plan["cards"] = [c for c in plan["cards"] if "arch" not in c.get("small", "")]
    plan["facts"]["alpha_pct"] = cf.ALPHA * 100
    plan["timing"]["mutes"] = [m for m in plan["timing"]["mutes"]]
    return plan


def hud_anchors(plan: dict) -> dict:
    F = plan["frames"]
    n = plan["n_frames"]
    base_, top, push = [], [], []
    for i in range(n):
        h2, h1 = F["h2"][i], F["h1"][i]
        base_.append([DIM_X, round(h2, 5), 0.0])                 # pile level (where links are picked up)
        top.append([DIM_X, round(h2 + h1, 5), 0.0])              # top of the arch
        push.append([XR + 0.0017, round(h2 - 0.0011, 5), 0.0])  # far end of the tipped link (scene: xr2 = xr + BEAD cos 1.2)
    return {"arch_base": base_, "arch_top": top, "push_point": push}


observe = base.observe
sfx_events = base.sfx_events
music = base.music
self_checks = base.self_checks
