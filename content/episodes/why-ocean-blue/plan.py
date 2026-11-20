"""Why the ocean is blue: render plan from the water-colour model
(factory/simulation_engine/physics/water_color.py; the three.js scene is renderer/scenes/ocean3d.js).

Every water colour on screen is computed here from Pope & Fry's absorption data: the sea seen from above,
the glass (8 cm of water) and the long tank (4 m), the underwater haze at each depth, the light beams'
brightness metre by metre, the red ball as it sinks, and the fish in the deep. The scene only draws them.
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam
from factory.simulation_engine.physics import water_color as wc

SCENE = "ocean3d"
ROPE = [0.0, 0.0, 0.0]          # rope from the boat at the pier's end; depth is -y
PIER_Z = 6.0                    # pier runs from the beach (z = 40) to here
GLASS = [1.25, 1.25, 9.0]       # on a pier post
TANK = [4.0, 0.25, 30.0]        # a tall clear column of water standing on the beach (bottom of the water)
TANK_L = 4.0
MOLE = [4.0, -3.0, -3.0]
BEAMS_X = [-2.4, -1.2, 0.0]     # red, green, blue beams (x), at z = -4
FISH = [30.0, -60.0, -30.0]
BALL_DEPTH = 10.0


def _hex(lin, gain=1.0):
    return wc.hexcol(lin, gain)


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.05) * fps))
    T = np.arange(n) / fps
    f = wc.facts()
    at = lambda b, w: timing.word_time(tl, b, w)

    # ---- colours from the model
    deep = wc.deep_sea_rgb(); deep = deep / deep.max()
    sky = np.array([0.80, 0.84, 0.88])                    # hazy sky reflected at the surface (display mix)
    sea = deep * 0.14 + sky * 0.02                        # seen from above: dark water-leaving blue + a little sky (display mix)
    colours = {
        "sea": _hex(sea),
        "glass": _hex(wc.through(0.08)),                   # through an 8 cm glass
        "tank": _hex(wc.through(2 * TANK_L)),              # its white floor seen from the top: 4 m down and 4 m back up
        "tank_side": _hex(wc.through(0.5)),
        "underside": _hex(wc.through(3.0), 0.95),
        "beam_cols": ["#ff3b30", "#5fd36a", "#3d7bff"],
        "ball_surface": _hex(wc.through(0.0, wc.red_paint())),
        "fish_lamp": _hex(wc.through(1.0, wc.red_paint())),                      # lit by a lamp 0.5 m away
        "fish_dark": _hex(wc.through(150.0, wc.red_paint()) + 0.02 * wc.through(150.0), 1.0),
        "deep_fog": _hex(wc.through(100.0) * 0.08),
    }
    # beam brightness per metre (0..15 m) for 700, 550, 450 nm
    beams = [[round(math.exp(-wc.a(wl) * d), 4) for d in range(16)] for wl in (700.0, 550.0, 450.0)]

    dive0, dive1 = S("dive") + 0.1, max(S("dive") + 1.6, at("dive", "gone") + 0.2)
    lamp_off = at("red", "Down") - 0.1
    frames = {k: [] for k in ("depth", "ball_y", "ball_col", "fog", "fog_far", "wob", "badge", "set", "lamp", "fish_col", "beams_on", "light")}
    for t in T:
        # the red ball sinks from just under the surface to 10 m during the dive beat
        u = min(1.0, max(0.0, (t - dive0) / (dive1 - dive0)))
        d = 0.5 + (BALL_DEPTH - 0.5) * cam.ease(u) if t >= S("dive") - 0.1 else 0.5
        if t >= S("back"):
            d = BALL_DEPTH
        frames["depth"].append(round(d if t >= S("dive") - 0.1 else 0.0, 3))
        frames["ball_y"].append(round(-d, 3))
        # its colour: sunlight down d metres, off red paint, then ~2.5 m to the camera
        frames["ball_col"].append(_hex(wc.through(d + 2.5, wc.red_paint()), 1.15))
        # underwater haze colour at the camera's depth (scene decides when the camera is underwater)
        if t >= S("red") - 0.1:
            frames["fog"].append(colours["deep_fog"]); frames["fog_far"].append(14.0); frames["light"].append(0.12)
        else:
            dc = {"absorb": 3.0, "metres": 6.0}.get(next((b for b in ("absorb", "metres") if S(b) - 0.1 <= t < E(b) + 0.15), ""), d)
            frames["fog"].append(_hex(wc.through(dc + 4.0), 0.75)); frames["fog_far"].append(26.0 if dc > 4 else 30.0)
            frames["light"].append(round(float(np.mean(wc.through(dc))), 3))
        frames["wob"].append(round(math.sin(t * 2 * math.pi * 1.6), 4))
        frames["beams_on"].append(1 if S("metres") - 0.1 <= t < S("dive") - 0.1 else 0)
        lamp = 1 if t < lamp_off else 0
        frames["lamp"].append(lamp)
        frames["fish_col"].append(colours["fish_lamp"] if lamp else colours["fish_dark"])
        b = ""
        if S("absorb") - 0.1 <= t < S("metres") - 0.1:
            b = "NOT TO SCALE"
        frames["badge"].append(b)

    K = lambda *a: list(a)
    bx = BEAMS_X[1]
    gx, gy, gz = GLASS
    tx, ty, tz = TANK
    mx, my, mz = MOLE
    fx, fy, fz = FISH
    end_t = n / fps + 0.05
    shots = cam.chain([
        # hook: aerial 3/4 over the pier and the sea, drifting
        cam.shot(0.0, S("glass") - 0.1, [(0.0, K(13.0, 6.5, 19.0), K(0.0, 0.3, 3.0), 44),
                                         (S("glass") - 0.1, K(11.0, 5.8, 16.5), K(0.0, 0.3, 3.0), 44)], fps, "key"),
        # glass: close on the glass, the long tank behind it
        cam.shot(S("glass") - 0.1, at("glass", "You") - 0.1, [(S("glass") - 0.1, K(gx + 0.28, gy + 0.14, gz + 0.62), K(gx, gy + 0.07, gz), 38),
                                                              (at("glass", "You") - 0.1, K(gx + 0.24, gy + 0.13, gz + 0.55), K(gx, gy + 0.07, gz), 38)], fps, "golden"),
        # glass 2: down the length of the tank: 4 m of water looks blue
        cam.shot(at("glass", "You") - 0.1, S("absorb") - 0.1, [(at("glass", "You") - 0.1, K(tx + 0.9, ty + TANK_L + 1.2, tz + 1.6), K(tx, ty + TANK_L * 0.45, tz), 40),
                                                                 (S("absorb") - 0.1, K(tx + 0.6, ty + TANK_L + 1.0, tz + 1.1), K(tx, ty + TANK_L * 0.4, tz), 40)], fps, "golden"),
        # absorb: underwater, a water molecule wobbling in a red beam
        cam.shot(S("absorb") - 0.1, S("metres") - 0.1, [(S("absorb") - 0.1, K(mx + 2.0, my + 0.4, mz + 3.6), K(mx, my - 0.3, mz), 40),
                                                        (S("metres") - 0.1, K(mx + 1.6, my + 0.3, mz + 3.2), K(mx, my - 0.3, mz), 40)], fps, "key"),
        # metres: underwater, the three beams going down, red fading first
        cam.shot(S("metres") - 0.1, S("dive") - 0.1, [(S("metres") - 0.1, K(bx + 5.0, -3.0, 7.0), K(bx, -5.0, -4.0), 46),
                                                      (S("dive") - 0.1, K(bx + 4.4, -4.0, 6.4), K(bx, -5.5, -4.0), 46)], fps, "key"),
        # dive: follow the red ball down the rope
        cam.shot(S("dive") - 0.1, S("back") - 0.1, [(S("dive") - 0.1, K(1.4, 0.4, 2.4), K(0.0, -0.1, 0.0), 42),
                                                    (S("back") - 0.1, K(1.2, 0.3, 2.2), K(0.0, 0.0, 0.0), 42)], fps, "key",
                 subject=lambda i: (0.0, frames["ball_y"][min(i, n - 1)], 0.0)),
        # back: high aerial, the sea from above
        cam.shot(S("back") - 0.1, S("red") - 0.1, [(S("back") - 0.1, K(-14.0, 30.0, 26.0), K(0.0, 0.0, -4.0), 44),
                                                   (S("red") - 0.1, K(-11.0, 26.0, 23.0), K(0.0, 0.0, -4.0), 44)], fps, "key"),
        # red: the deep: a red fish in a lamp beam, then the lamp goes off
        cam.shot(S("red") - 0.1, end_t, [(S("red") - 0.1, K(fx + 1.3, fy + 0.35, fz + 2.6), K(fx, fy, fz), 40),
                                         (end_t, K(fx + 1.0, fy + 0.3, fz + 2.3), K(fx, fy, fz), 40)], fps, "key"),
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
        {"start": at("metres", "almost"), "end": at("metres", "Blue") - 0.05, "big": "46%", "small": "of the deepest red lost per metre", "y": 0.17},
        {"start": at("metres", "about"), "end": S("dive") - 0.15, "big": "≈ 0.9%", "small": "of the blue lost per metre", "y": 0.17},
        {"start": at("dive", "gone"), "end": S("back") - 0.15, "big": "≈ 0.2%", "small": "of the deepest red left", "y": 0.17},
    ]
    events = [(round(dive0 + 0.05, 3), "whoosh", {"gain": 0.14}),
              (round(lamp_off, 3), "tick", {"gain": 0.18, "seed": 5})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [dive0, lamp_off], "events": events,
               "mutes": [], "swells": [S("back")], "lamp_off": lamp_off, "dive": [dive0, dive1]}
    facts = dict(f)
    facts.update({"slow_factors": [], "red_loss_card": 100 * f["red_loss_per_m"],
                  "events": {"ball_10m": {"t": dive1 + 0.1, "observe": "depth", "expect": BALL_DEPTH, "tol": 0.01}}})
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 41, "supersample": 1.0,
            "bloom_threshold": 3.0, "end_hold_s": 1.0,
            "layout": {"rope": ROPE, "pier_z": PIER_Z, "glass": GLASS, "tank": TANK, "tank_l": TANK_L, "mole": MOLE,
                       "beams_x": BEAMS_X, "fish": FISH},
            "colours": colours, "beams": beams,
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what == "depth":
        return plan["frames"]["depth"][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 80, "gain": 0.14}


def self_checks() -> dict:
    return wc.self_checks()
