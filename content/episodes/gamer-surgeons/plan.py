"""Surgeons who game make fewer mistakes: render plan (the three.js scene is renderer/scenes/gamersurgeons3d.js).

The shared daylight home set (renderer/sets/home.js). A keyhole-surgery practice box on the coffee table: two long
tools pivot about two small holes in its lid (each shaft is drawn as the straight line from its tip through its
hole, the way a real keyhole instrument moves), a ring is carried from peg to peg inside, and a small monitor
beside the box shows the inside from the same tip positions. A TV plays an original abstract game. The numbers on
the cards are the published results of Rosser et al. 2007 (Arch Surg 142:181-186); nothing in the scene measures
them.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "gamersurgeons3d"
SLUG = "gamer-surgeons"
TABLE = [1.3, 0.0, 0.85]
BOX_DX, MON_DX = -0.15, 0.33
TY = TABLE[1] + 0.445                       # table top
BOX = [TABLE[0] + BOX_DX, TY, TABLE[2]]
MON = [TABLE[0] + MON_DX, TY, TABLE[2] - 0.08]
TV = [0.38, 0.0, -2.0]
TV_YAW = 0.3
WIZ = [0.5, 0.0, 0.95]
WIZ_FACE = 0.7
WOMAN = [2.0, 0.0, 1.05]
WOMAN_FACE = -0.75
SPEAKER = {"hook": "woman", "what": "wizard", "keyhole": "woman", "flat": "woman", "gamer": "wizard",
           "study": "woman", "catch": "wizard", "honest": "woman", "payoff": "wizard"}
# published results (Rosser et al. 2007 abstract), shown on the cards and spoken
RESULTS = {"fewer_errors_pct": 37, "faster_pct": 27, "doctors": 33, "hours_per_week": 3}


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    hook_c = max(at("hook", "thirty") - 0.25, 2.6)
    watch_c = at("keyhole", "while") - 0.1
    up_c = at("flat", "eyes") - 0.15
    faster_c = at("study", "gamers") - 0.15

    bx, by, bz = BOX
    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    shots_spec = [
        # hook (a): already in motion: inside the practice box, the tool carries the red ring from peg to peg
        ("inner", E_(0.0, hook_c, K(bx + 0.04, by + 0.185, bz + 0.34), K(bx - 0.02, by + 0.18, bz + 0.3), K(bx, by + 0.085, bz), 48)),
        # hook (b): the woman beside the box, the claim
        ("out", E_(hook_c, S("what") - 0.1, K(1.3, 1.45, 2.4), K(1.34, 1.45, 2.28), K(2.0, 1.3, 1.0), 38)),
        # what: the wizard, astonished
        ("out", E_(S("what") - 0.1, S("keyhole") - 0.1, K(1.15, 1.5, 2.2), K(1.1, 1.5, 2.1), K(0.5, 1.55, 0.95), 36)),
        # keyhole (a): three-quarter on the box: two long tools through two tiny holes, moving
        ("live", E_(S("keyhole") - 0.1, watch_c, K(bx + 0.55, by + 0.55, bz + 0.75), K(bx + 0.45, by + 0.5, bz + 0.68), K(bx, by + 0.18, bz), 38)),
        # keyhole (b): the monitor: all the doctor sees
        ("live", E_(watch_c, S("flat") - 0.1, K(MON[0] + 0.05, MON[1] + 0.26, MON[2] + 0.62), K(MON[0] + 0.03, MON[1] + 0.25, MON[2] + 0.54), K(MON[0] - 0.02, MON[1] + 0.24, MON[2]), 36)),
        # flat (a): low on the handles: the hands work down here
        ("live", E_(S("flat") - 0.1, up_c, K(bx - 0.35, by + 0.32, bz + 0.55), K(bx - 0.3, by + 0.3, bz + 0.5), K(bx, by + 0.3, bz + 0.05), 38)),
        # flat (b): box and monitor together: the eyes are up there, and the picture is flat
        ("live", E_(up_c, S("gamer") - 0.1, K(bx + 0.15, by + 0.7, bz + 1.15), K(bx + 0.2, by + 0.68, bz + 1.05), K(bx + 0.25, by + 0.2, bz - 0.05), 40)),
        # gamer: the wizard points at the TV game behind him
        ("out", E_(S("gamer") - 0.1, S("study") - 0.1, K(1.15, 1.45, 2.3), K(1.08, 1.45, 2.2), K(0.35, 1.15, -0.6), 40)),
        # study (a): the whole room, both presenters, the box between them
        ("out", E_(S("study") - 0.1, faster_c, K(1.25, 2.2, 4.4), K(1.22, 2.15, 4.2), K(1.25, 0.85, 0.7), 44)),
        # study (b): closer on the woman with the box
        ("out", E_(faster_c, S("catch") - 0.1, K(1.85, 1.3, 2.05), K(1.8, 1.3, 1.95), K(1.7, 1.05, 0.9), 38)),
        # catch: the wizard, delighted
        ("out", E_(S("catch") - 0.1, S("honest") - 0.1, K(0.95, 1.55, 2.0), K(0.9, 1.55, 1.93), K(0.5, 1.6, 0.95), 36)),
        # honest: the woman, gentle correction
        ("out", E_(S("honest") - 0.1, S("payoff") - 0.1, K(1.38, 1.5, 2.15), K(1.42, 1.5, 2.05), K(2.06, 1.5, 1.0), 36)),
        # payoff: the wizard and the TV game; held to the end
        ("out", cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(1.1, 1.5, 2.4), K(0.32, 1.25, -0.4), 40),
                                                         (dur + 0.05, K(0.98, 1.5, 2.2), K(0.32, 1.25, -0.4), 40)], fps, "key")),
    ]
    shots = cam.chain([s for _, s in shots_spec])
    kinds = [kd for kd, _ in shots_spec]

    def kind_at(t):
        for kd, s_ in zip(kinds, shots):
            if s_["start"] <= t < s_["end"]:
                return kd
        return kinds[-1]

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_point", "woman_point", "tools_live", "cutaway")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        kd = kind_at(t)
        frames["tools_live"].append(1 if kd in ("inner", "live") else 0)
        frames["cutaway"].append(1 if kd == "inner" else 0)
        frames["look_w"].append("tv" if a in ("gamer", "payoff") else ("box" if a in ("keyhole", "flat") else "woman"))
        frames["look_m"].append("box" if a in ("keyhole", "flat", "study") else "wizard")
        frames["wiz_point"].append(round(duo.bump(t, at("gamer", "video") - 0.4, 0.35, 1.0, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, at("keyhole", "steer") - 0.3, 0.35, 1.6, 0.5), 3))
        frames["wiz_blink"].append(1.0 if (t % 3.9) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("hook", "thirty"), "end": S("what") - 0.15, "big": "37%", "small": "fewer mistakes", "y": 0.16},
        {"start": at("study", "thirty"), "end": faster_c - 0.05, "big": "33 doctors", "small": "in surgery drills", "y": 0.16},
        {"start": at("study", "twenty"), "end": S("catch") - 0.15, "big": "27%", "small": "faster", "y": 0.16},
        {"start": at("honest", "link"), "end": S("payoff") - 0.15, "big": "A link", "small": "not proof", "y": 0.16},
    ]
    events = [(round(at("hook", "thirty"), 3), "ding", {"gain": 0.1}),
              (round(S("keyhole") - 0.05, 3), "whoosh", {"gain": 0.1}),
              (round(at("study", "twenty"), 3), "pop", {"gain": 0.1})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [at("hook", "thirty"), at("study", "twenty"), at("honest", "link")],
               "events": events, "mutes": [], "swells": [S("payoff")]}
    facts = {**RESULTS,
             "events": {"tools_move_in_box_shot": {"t": 1.0, "observe": "tools_live", "expect": 1, "tol": 0},
                        "front_wall_back_after_hook": {"t": S("what") + 0.2, "observe": "cutaway", "expect": 0, "tol": 0}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 43, "supersample": 1.0, "bloom_threshold": 50.0,
            "end_hold_s": 1.4,
            "layout": {"wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE, "table": TABLE,
                       "box_dx": BOX_DX, "mon_dx": MON_DX, "tv": TV, "tv_yaw": TV_YAW},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in ("tools_live", "cutaway"):
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 96, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """The tools pivot about the holes (fulcrum): a tip moving right means the handle outside moves left, the way a
    real keyhole instrument behaves; and the spoken numbers match the cited abstract."""
    hole_x, tip0, tip1, out = -0.11, -0.07, 0.06, 0.3
    h0 = hole_x + (hole_x - tip0) * (out / 0.13)          # the handle sits on the far side of the hole from the tip
    h1 = hole_x + (hole_x - tip1) * (out / 0.13)
    return {"handle moves opposite to the tip (fulcrum at the hole)": {"pass": (tip1 - tip0) * (h1 - h0) < 0, "detail": f"tip +{tip1 - tip0:.2f} m, handle {h1 - h0:+.2f} m"},
            "spoken numbers match Rosser et al. 2007": {"pass": RESULTS == {"fewer_errors_pct": 37, "faster_pct": 27, "doctors": 33, "hours_per_week": 3},
                                                       "detail": "37% fewer errors, 27% faster, 33 doctors, >3 h/week"}}
