"""Your phone can't feel you press it: render plan from the 2D electrostatics model
(factory/simulation_engine/physics/capacitive.py; the three.js scene is renderer/scenes/touch3d.js).

The world is a diorama at 10x scale: 1 mm of the real phone is 1 cm of world. A phone lies face up on a
wooden deck. In the cutaway beats the glass turns see-through, revealing the electrode grid; at one
crossing we draw the field lines computed by the solver (drive strip -> sense strip), for a ladder of
fingertip heights, so the picture of the field bending into the finger IS the model's solution.
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam
from factory.simulation_engine.physics import capacitive as cap

SCENE = "touch3d"
SCALE = 0.01                      # world metres per real millimetre (10x diorama)
PHONE = [0.0, 0.0, 0.0]           # phone centre on the deck (x across, z along)
PHONE_W, PHONE_L, PHONE_T = 0.75, 1.55, 0.08
GLASS_TOP = PHONE_T               # world y of the glass surface
ELEC_Y = GLASS_TOP - cap.GLASS * SCALE
NODE = [0.0, GLASS_TOP, 0.18]     # the crossing we look at (world)
LADDER = [None, 14.0, 9.0, 6.0, 4.0, 3.0, 2.0, 1.4, 0.9, 0.5, cap.SKIN]   # finger heights with solved field lines
FAR = 40.0                        # "far away" height (mm)


def _fieldsets():
    sets = []
    for g in LADDER:
        sol = cap.solve(g, h=0.05)
        sets.append({"gap": 99.0 if g is None else g, "lines": cap.coupling_lines(sol)})
    sol = cap.solve(cap.GLOVE + cap.SKIN, glove=cap.GLOVE, h=0.05)
    glove = {"gap": cap.GLOVE + cap.SKIN, "lines": cap.coupling_lines(sol)}
    return sets, glove


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.05) * fps))
    T = np.arange(n) / fps
    f = cap.facts()
    at = lambda b, w: timing.word_time(tl, b, w)
    sets, glove_set = _fieldsets()

    # ---- moments from the narration
    tap1 = (0.25, 0.75, 1.35)                                  # hook: down, contact, up
    tap2 = (S("hook") + 1.9, S("hook") + 2.3, S("hook") + 2.8)
    cut0, cut1 = S("grid") + 0.1, S("grid") + 1.2              # glass turns see-through
    fin0, fin1 = at("finger", "Bring") - 0.1, at("finger", "away") + 0.1     # finger lowers to contact
    lift0 = S("glove") - 0.1                                    # finger leaves, glove arrives
    glv0, glv1 = S("glove") + 0.3, at("glove", "holds") + 0.2
    sau0, sau1 = at("sausage", "tapped") - 0.2, at("sausage", "sausages") + 0.25
    detect_on = fin1 + 0.05

    frames = {k: [] for k in ("obj", "gap", "glove", "cut", "scan", "node", "ring", "snow", "badge", "field", "ui_tap")}
    for t in T:
        # what touches the glass, and how high its lowest point is (real mm)
        obj, gap, gl = "finger", FAR, 0
        if t < S("grid"):
            for d, c, u in (tap1, tap2):
                if d <= t < u + 0.4:
                    if t < c:
                        gap = FAR * (1 - cam.ease((t - d) / (c - d))) + cap.SKIN
                    elif t < u:
                        gap = cap.SKIN
                    else:
                        gap = cap.SKIN + FAR * cam.ease((t - u) / 0.4)
        elif t < S("finger"):
            obj = None
        elif t < lift0:
            if t < fin0:
                gap = FAR
            elif t < fin1:
                gap = cap.SKIN + (FAR - cap.SKIN) * (1 - cam.ease((t - fin0) / (fin1 - fin0))) ** 1.6
            else:
                gap = cap.SKIN
        elif t < S("sausage"):
            if t < lift0 + 0.3:
                gap = cap.SKIN + FAR * cam.ease((t - lift0) / 0.3)          # bare finger lifts away
            else:
                obj, gl = "glove", 1
                u = min(1.0, max(0.0, (t - glv0) / (glv1 - glv0)))
                gap = cap.GLOVE + cap.SKIN + (FAR - cap.GLOVE) * (1 - cam.ease(u)) ** 1.6
        else:
            obj = "sausage"
            u = min(1.0, max(0.0, (t - sau0) / (sau1 - sau0)))
            gap = cap.SKIN + (FAR - cap.SKIN) * (1 - cam.ease(u)) ** 1.6
        frames["obj"].append(obj); frames["gap"].append(round(gap, 3)); frames["glove"].append(gl)
        # cutaway: glass becomes see-through from the grid beat to the end
        frames["cut"].append(round(cam.ease((t - cut0) / (cut1 - cut0)) if t >= cut0 else 0.0, 3))
        # scanning sweep (grid beat onwards): one row lit at a time, travelling down the phone
        frames["scan"].append(round(((t - cut0) * 9.0) % 31, 3) if t >= cut0 else -1)
        # the chip's verdict at the crossing: the model's dip above the threshold?
        if obj is None:
            drop = 0.0
        else:
            ladder = [glove_set] if gl else sets
            drop = _drop_at(gap, gl)
        touched = drop > f["threshold"]
        frames["node"].append(1.0 if (touched and t >= S("grid")) else 0.0)
        frames["ring"].append(1.0 if touched else 0.0)
        frames["snow"].append(1 if t >= S("sausage") - 0.1 else 0)
        frames["field"].append(1 if S("field") - 0.1 <= t else 0)
        frames["ui_tap"].append(1 if touched and t < S("grid") else 0)
        frames["badge"].append("NOT TO SCALE" if t >= S("grid") - 0.1 else "")

    # ---- shots (world metres; the node is the crossing we watch)
    K = lambda *a: list(a)
    nx, ny, nz = NODE
    end_t = n / fps + 0.05
    shots = cam.chain([
        # hook: low 3/4 over the phone; the fingertip taps an icon, a ring spreads
        cam.shot(0.0, S("grid") - 0.1, [(0.0, K(0.85, 0.80, 1.75), K(0.0, 0.10, 0.10), 40),
                                        (S("grid") - 0.1, K(0.72, 0.72, 1.58), K(0.0, 0.10, 0.12), 40)], fps, "key"),
        # grid: high over the phone while the glass turns see-through and the scan sweeps
        cam.shot(S("grid") - 0.1, S("field") - 0.1, [(S("grid") - 0.1, K(0.45, 1.55, 1.25), K(0.0, 0.0, 0.0), 42),
                                                     (S("field") - 0.1, K(0.30, 1.35, 1.05), K(0.0, 0.0, 0.05), 42)], fps, "key"),
        # field: macro, side-on to the crossing: arcs from one wire to the next
        cam.shot(S("field") - 0.1, S("finger") - 0.1, [(S("field") - 0.1, K(nx + 0.035, ny + 0.03, nz + 0.14), K(nx, ny + 0.004, nz), 40),
                                                       (S("finger") - 0.1, K(nx + 0.02, ny + 0.026, nz + 0.12), K(nx, ny + 0.005, nz), 40)], fps, "key"),
        # finger: slightly wider macro, the fingertip comes down into frame
        cam.shot(S("finger") - 0.1, S("detect") - 0.1, [(S("finger") - 0.1, K(nx + 0.16, ny + 0.06, nz + 0.46), K(nx, ny + 0.04, nz), 40),
                                                        (S("detect") - 0.1, K(nx + 0.12, ny + 0.045, nz + 0.38), K(nx, ny + 0.03, nz), 40)], fps, "key"),
        # detect: higher 3/4: the crossing glows red in the grid
        cam.shot(S("detect") - 0.1, S("glove") - 0.1, [(S("detect") - 0.1, K(nx + 0.30, ny + 0.42, nz + 0.50), K(nx, ny, nz), 40),
                                                       (S("glove") - 0.1, K(nx + 0.24, ny + 0.36, nz + 0.44), K(nx, ny, nz), 40)], fps, "golden"),
        # glove: side-on macro, the measuring line shows the 2 mm of wool
        cam.shot(S("glove") - 0.1, S("sausage") - 0.1, [(S("glove") - 0.1, K(nx + 0.15, ny + 0.07, nz + 0.50), K(nx + 0.02, ny + 0.05, nz), 40),
                                                        (S("sausage") - 0.1, K(nx + 0.12, ny + 0.06, nz + 0.44), K(nx + 0.02, ny + 0.045, nz), 40)], fps, "key"),
        # sausage: winter light, wide over the phone with snow falling
        cam.shot(S("sausage") - 0.1, sau0 - 0.1, [(S("sausage") - 0.1, K(nx + 0.75, ny + 0.65, nz + 1.25), K(nx, ny + 0.03, nz - 0.1), 40),
                                                  (sau0 - 0.1, K(nx + 0.62, ny + 0.56, nz + 1.08), K(nx, ny + 0.03, nz - 0.05), 40)], fps, "winter"),
        # sausage 2: closer 3/4, the sausage taps and the crossing lights red
        cam.shot(sau0 - 0.1, end_t, [(sau0 - 0.1, K(nx + 0.36, ny + 0.36, nz + 0.62), K(nx, ny + 0.03, nz), 40),
                                     (end_t, K(nx + 0.28, ny + 0.30, nz + 0.52), K(nx, ny + 0.03, nz), 40)], fps, "winter"),
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
        {"start": at("detect", "That's"), "end": S("glove") - 0.15, "big": "less charge", "small": "= a touch", "y": 0.17},
    ]
    contacts = [tap1[1], tap2[1], fin1, sau1]
    events = [(round(tap1[1], 3), "pop", {"gain": 0.22, "seed": 1}),
              (round(tap2[1], 3), "pop", {"gain": 0.2, "seed": 2}),
              (round(fin1, 3), "pop", {"gain": 0.24, "seed": 3}),
              (round(sau1, 3), "pop", {"gain": 0.24, "seed": 4}),
              (round(cut0, 3), "rise", {"gain": 0.14})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [cut0, fin1, sau1], "events": events,
               "mutes": [], "swells": [sau1], "contacts": contacts, "glove": [glv0, glv1]}
    facts = dict(f)
    facts.update({"slow_factors": [],
                  "events": {"finger_touch": {"t": fin1 + 0.1, "observe": "node", "expect": 1.0, "tol": 0.01},
                             "glove_no_touch": {"t": glv1 + 0.3, "observe": "node", "expect": 0.0, "tol": 0.01},
                             "sausage_touch": {"t": sau1 + 0.1, "observe": "node", "expect": 1.0, "tol": 0.01}}})
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 33, "supersample": 1.0,
            "bloom_threshold": 3.0, "end_hold_s": 1.0,
            "layout": {"phone": PHONE, "phone_w": PHONE_W, "phone_l": PHONE_L, "phone_t": PHONE_T, "glass_top": GLASS_TOP,
                       "elec_y": ELEC_Y, "node": NODE, "scale": SCALE, "pitch": 0.05, "finger_r": cap.FINGER_R * SCALE,
                       "glove_mm": cap.GLOVE, "skin_mm": cap.SKIN,
                       "strip": [cap.STRIP_W * SCALE, cap.STRIP_GAP * SCALE]},
            "fields": sets, "glove_field": glove_set,
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


_DROP_CACHE: dict = {}


def _drop_at(gap: float, glove: int) -> float:
    """The model's relative dip for a conductor whose lowest point is `gap` mm above the glass
    (interpolated in log-height from solved points, cached)."""
    key = "glove" if glove else "bare"
    if key not in _DROP_CACHE:
        if glove:
            hs = [cap.GLOVE + cap.SKIN, 3.0, 5.0, 10.0, 20.0, 40.0]
            ds = [cap.relative_drop(cap.GLOVE + cap.SKIN, glove=cap.GLOVE)] + [cap.relative_drop(h) for h in hs[1:]]
        else:
            hs = [cap.SKIN, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 40.0]
            ds = [cap.relative_drop(h) for h in hs]
        _DROP_CACHE[key] = (np.log(hs), np.array(ds))
    lh, ds = _DROP_CACHE[key]
    return float(np.interp(math.log(max(gap, 1e-3)), lh, ds))


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what == "node":
        return plan["frames"]["node"][k]
    raise KeyError(what)


def hud_anchors(plan: dict) -> dict:
    """The 2 mm measuring line: from the glass surface to the skin inside the glove, just beside the tip."""
    n, L = plan["n_frames"], plan["layout"]
    x, y, z = L["node"][0] + 0.05, L["glass_top"], L["node"][2] + 0.02
    return {"glass_mark": [[x, y, z]] * n,
            "skin_mark": [[x, round(y + L["glove_mm"] * L["scale"], 4), z]] * n}


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 92, "gain": 0.14}


def self_checks() -> dict:
    return cap.self_checks()
