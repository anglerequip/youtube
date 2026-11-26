"""Captain Finn tries Lure Finder: render plan for the Blender renderer (tools/blender/render_episode.py).

HOST style (docs/styles/HOST.md): Finn on a weathered jetty at a misty autumn dawn, the low sun behind him over the
lake (warm rim/key, cool sky fill). Shots are timed from the narration; mix aimed at the measured reference
grammar (medium ~38 %, close ~26 %, wide ~21 %, insert ~14 %), average shot ~2-3 s, hard cuts.

World (Blender, z up): the jetty runs along +y out over the lake, deck top z = DECK_Z. Finn stands at FINN facing -y
(toward the bank and the camera), so every reverse angle has the lake, the mist and the sun behind him.
The phone screen shows a recreation of the REAL Lure Finder result captured on 2026-11-26 (ref/tool_output.md).
This file only decides positions and timing; render_episode.py draws.
"""
from __future__ import annotations

import math

import numpy as np

SLUG = "finn-lure-finder"
SCENE = "finn_dock"
DECK_Z = 0.55
FINN = [0.0, 2.2, DECK_Z]          # feet
FINN_YAW = 0.0                     # 0 = facing -y
EYE = [0.0, 2.2, DECK_Z + 1.72]    # roughly his eye line
CHEST = [0.0, 2.2, DECK_Z + 1.35]
BOX = [0.45, 1.75, DECK_Z]         # open tackle box on the deck, front right of him
PIKE = [1.7, 3.4, 0.0]             # where the pike surfaces, off the jetty's right side

facts = {"models": 756, "colourways": 4627, "match": "9/10", "top_pick": "Rapala Jointed J11",
         "colour_call": "Firetiger", "inputs": "Northern pike, shore, dawn/dusk, autumn, overcast, calm, murky"}


def _shot(t0, t1, kind, cam0, cam1, tgt0, tgt1, lens, focus=None, fstop=2.8, roll=0.0, note="", track=None, dist=None):
    d = {"start": round(t0, 3), "end": round(t1, 3), "kind": kind, "cam0": cam0, "cam1": cam1, "tgt0": tgt0,
         "tgt1": tgt1, "lens": lens, "focus": focus or tgt1, "fstop": fstop, "roll": roll, "note": note}
    if track:
        d["track"] = track
    if dist:
        d["dist"] = dist          # phone_screen: camera distance in front of the screen          # the renderer keeps the camera's offset from this prop's real position
    return d


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory import duo
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)

    fx, fy, fz = FINN
    ex, ey, ez = EYE
    face = [ex, ey - 0.02, ez - 0.05]
    shots = []
    add = lambda *a, **k: shots.append(_shot(*a, **k))
    # hook: low MCU, he holds a chartreuse lure up beside his face, already talking; slow push in
    t_guess = at("hook", "guesses") - 0.05
    add(0.0, t_guess, "medium", [0.1, ey - 1.6, ez - 0.35], [0.08, ey - 1.35, ez - 0.32], [-0.06, ey, ez - 0.22], [-0.06, ey, ez - 0.2], 40,
        focus=face, note="hold-up lure, talk")
    # punch-in close-up on the vow
    add(t_guess, S("enemy") - 0.05, "close", [0.12, ey - 1.0, ez - 0.02], [0.1, ey - 0.9, ez - 0.02], [face[0], face[1], face[2] - 0.04], [face[0], face[1], face[2] - 0.04], 55, focus=face, fstop=2.0,
        note="shout on 'ever'")
    # enemy: wide, him and the open tackle box on the jetty, mist and the sun behind; slow dolly
    t_every = at("enemy", "Every") - 0.05
    add(S("enemy") - 0.05, t_every, "wide", [1.3, fy - 4.6, fz + 1.25], [1.0, fy - 4.2, fz + 1.2], [0.2, fy, fz + 0.9], [0.2, fy, fz + 0.95], 28,
        focus=[0.2, fy, fz + 1.0], fstop=5.6, note="box opens")
    # insert: top-down POV over the trays of lures, his gloved hand sweeping across
    t_pick = at("enemy", "pick") - 0.05
    bx, by, bz = BOX
    add(t_every, t_pick, "insert", [bx + 0.05, by - 0.15, bz + 0.95], [bx + 0.02, by - 0.1, bz + 0.85], [bx, by, bz + 0.05], [bx, by, bz + 0.05], 35,
        focus=[bx, by, bz + 0.08], fstop=2.8, note="hand over trays")
    # medium side: he casts, then waits holding the rod, deadpan (the 0.6 s pause)
    t_pike = at("enemy", "wait") - 0.15     # the pike reaction gets at least 1.2 s (the held pause after "wait")
    add(t_pick, t_pike, "medium", [-1.7, fy - 1.7, fz + 1.35], [-1.55, fy - 1.55, fz + 1.32], [0.0, fy, fz + 1.15], [0.0, fy, fz + 1.12], 35,
        focus=CHEST, note="rod, waiting")
    # reaction cutaway: a pike's head breaks the surface beside the jetty, looks, sinks (bloop)
    px, py, pz = PIKE
    add(t_pike, S("nottoday") - 0.05, "close", [px - 0.62, py - 0.62, 0.3], [px - 0.55, py - 0.55, 0.27], [px, py, 0.08], [px, py, 0.06], 60,
        focus=[px, py, 0.08], fstop=2.0, note="pike surfaces")
    # 'Not today.' close-up with a slight Dutch tilt, smirk
    add(S("nottoday") - 0.05, S("weapon") - 0.05, "close", [-0.18, ey - 0.8, ez - 0.08], [-0.16, ey - 0.75, ez - 0.07], face, face, 65, focus=face,
        fstop=2.0, roll=-6, note="smirk")
    # weapon: low medium, he raises the phone, its glow on his face
    t_tell = at("weapon", "Tell") - 0.05
    add(S("weapon") - 0.05, t_tell, "medium", [0.5, ey - 1.6, ez - 0.75], [0.45, ey - 1.45, ez - 0.7], [0.0, ey, ez - 0.3], [0.0, ey, ez - 0.25], 35,
        focus=face, note="raise phone")
    # insert: over the shoulder onto the phone, thumb taps pike / murky / dawn
    phone = [0.12, ey - 0.42, ez - 0.42]
    add(t_tell, S("models") - 0.05, "insert", [phone[0] + 0.12, phone[1] + 0.34, phone[2] + 0.3], [phone[0] + 0.1, phone[1] + 0.3, phone[2] + 0.27],
        phone, phone, 30, focus=phone, fstop=2.8, note="taps", track="phone_screen", dist=0.17)
    # models: insert on the result card (top pick 9/10, '756 real models'), then his face as it lands
    t_real = at("models", "real") - 0.05
    add(t_real, S("colour") - 0.05, "close", [-0.12, ey - 0.85, ez - 0.05], [-0.11, ey - 0.8, ez - 0.05], face, face, 62, focus=face,
        fstop=2.0, note="impressed")
    # the result card, then a hard-cut punch-in on the number (HOST: punch-ins are cuts, no shot over ~3 s)
    m_res = (S("models") - 0.05 + t_real) / 2
    add(S("models") - 0.05, m_res, "insert", [0.15, ey - 0.85, ez - 0.35], [0.14, ey - 0.78, ez - 0.36], phone, phone, 32,
        focus=phone, fstop=2.8, note="result card", track="phone_screen", dist=0.17)
    add(m_res, t_real, "insert", [0.15, ey - 0.85, ez - 0.35], [0.14, ey - 0.78, ez - 0.36], phone, phone, 32,
        focus=phone, fstop=2.8, note="756 punch-in", track="phone_screen", dist=0.12)
    # colour: medium, he turns the phone to the lens (present), the Firetiger colour call
    t_out = at("colour", "Out") - 0.05
    m_col = (t_out + S("box") - 0.05) / 2
    add(t_out, m_col, "insert", [0.15, ey - 0.85, ez - 0.35], [0.14, ey - 0.78, ez - 0.36], phone, phone, 60,
        focus=phone, fstop=2.4, note="colour card", track="phone_screen", dist=0.3)
    add(m_col, S("box") - 0.05, "insert", [0.15, ey - 0.85, ez - 0.35], [0.14, ey - 0.78, ez - 0.36], phone, phone, 60,
        focus=phone, fstop=2.4, note="4,627 punch-in", track="phone_screen", dist=0.21)
    add(S("colour") - 0.05, t_out, "medium", [0.2, ey - 1.5, ez - 0.45], [0.18, ey - 1.35, ez - 0.43], [0.0, ey, ez - 0.35], [0.0, ey, ez - 0.32], 38,
        focus=face, note="present phone")
    # box: wide-ish, he holds the box out over the water... then hugs it
    add(S("box") - 0.05, S("free") - 0.05, "wide", [-1.8, fy - 3.2, fz + 1.0], [-1.6, fy - 2.9, fz + 1.0], [0.3, fy + 0.2, fz + 1.1], [0.3, fy + 0.2, fz + 1.1], 30,
        focus=CHEST, fstop=4.0, note="box over water, hug")
    # free + CTA: medium close-up, smirk, then the finger points down
    add(S("free") - 0.05, S("cta") - 0.05, "close", [0.1, ey - 0.95, ez - 0.1], [0.09, ey - 0.88, ez - 0.1], face, face, 60, focus=face,
        fstop=2.0, note="smirk")
    add(S("cta") - 0.05, dur + 0.01, "medium", [0.3, ey - 1.7, ez - 0.4], [0.28, ey - 1.55, ez - 0.38], [0.0, ey, ez - 0.45], [0.0, ey, ez - 0.42], 36,
        focus=face, note="point down")
    shots.sort(key=lambda s: s["start"])
    shots[0]["start"] = 0.0

    # Finn's acting: pose keys (the renderer blends between neighbouring keys over `blend` seconds)
    keys = [
        (0.0, "hold_up", {"mouth": "talk"}),
        (at("hook", "ever") - 0.1, "hold_up", {"mouth": "shout", "brow": 1.0}),
        (S("enemy"), "present", {"mouth": "talk", "brow": 0.3}),
        (t_pick, "rod", {"mouth": "talk"}),
        (E("enemy"), "rod", {"mouth": "closed", "brow": -0.6}),
        (S("nottoday"), "neutral", {"mouth": "smirk", "brow": 0.6, "head_yaw": 0.15}),
        (S("weapon"), "phone_up", {"mouth": "talk"}),
        (S("models"), "phone_up", {"mouth": "talk"}),
        (S("colour"), "phone_present", {"mouth": "talk", "brow": 0.8}),
        (S("box") - 0.05, "box_out", {"mouth": "talk", "brow": -0.3, "snap": True}),   # on the cut: no hands passing through the box
        (at("box", "keeping") - 0.1, "box_hug", {"mouth": "smirk", "brow": 0.4}),
        (S("free"), "neutral", {"mouth": "smirk", "brow": 0.6}),
        (S("cta"), "point_down", {"mouth": "talk", "brow": 0.4}),
    ]
    keys = [{"t": round(t, 3), "pose": p, **x} for t, p, x in keys]
    blinks = [round(t, 2) for t in np.arange(1.3, dur, 3.1)]
    talk = [round(float(v), 3) for v in env]
    # props: which is in his hand when (the renderer parents them to his hand bones)
    props = {
        "lure_hand": [[0.0, S("enemy")]],
        "rod": [[t_pick - 0.3, E("enemy") + 0.25]],
        "phone": [[S("weapon") - 0.05, S("box") - 0.05]],     # appears on the cut, never mid-shot
        "box_open": [[S("enemy") - 0.05, dur]],
        "box_in_hands": [[S("box") - 0.05, S("free") - 0.05]],
        "pike": [t_pike, S("nottoday") - 0.05],
    }
    screen = [   # what the phone shows, by time (textures made by render_episode.py from ref/tool_output.md)
        {"t": S("weapon"), "page": "conditions", "taps": ["Northern pike", "Murky", "Dawn / dusk", "Overcast"],
         "tap_times": [round(at("weapon", "fish"), 2), round(at("weapon", "water"), 2), round(at("weapon", "light"), 2), round(E("weapon"), 2)]},
        {"t": S("models"), "page": "result", "big": "756", "small": "real models"},
        {"t": S("colour"), "page": "colour", "big": "4,627", "small": "factory colours", "colour": "Firetiger"},
    ]
    return {"scene": SCENE, "renderer": "blender", "fps": fps, "W": W, "H": H, "n_frames": n, "duration": round(dur, 3),
            "deck_z": DECK_Z, "finn": {"pos": FINN, "yaw": FINN_YAW}, "box": BOX, "pike_at": PIKE,
            "shots": shots, "keys": keys, "blinks": blinks, "talk": talk, "props": props, "screen": screen, "facts": facts,
            "ambience": "lake"}


def sfx_events(plan: dict) -> list:
    out = []
    t_pike = plan["props"]["pike"][0]
    out.append((t_pike + 0.25, "pop"))      # the pike breaks the surface
    for k in plan["screen"][0]["tap_times"]:
        out.append((k, "tick"))
    return out


def self_checks() -> list:
    return [("facts match ref/tool_output.md", facts["models"] == 756 and facts["colourways"] == 4627, "756 / 4,627")]
