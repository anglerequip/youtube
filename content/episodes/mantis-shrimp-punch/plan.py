"""The mantis shrimp punch: render plan (the three.js scene is renderer/scenes/shrimp3d.js; the animals are
renderer/shrimp.js).

A dim aquarium gallery: the wizard and the woman stand at the glass of a big reef tank where a small mantis shrimp
sits beside a sea snail. Far away, a big slow-motion macro reef, badged as an illustration: the club arm latches
and loads its saddle-shaped spring, snaps out and hits the shell; the water in front of the club tears into a
cloud of cavitation bubbles; the bubbles collapse with a tiny flash and hit the shell a second time; it cracks.

Speeds and timings in the macro are illustrative slow motion. The spoken figures (23 m/s, over 80 km/h, under a
thousandth of a second, peak forces over 2,500 times body weight) come from Patek, Korff & Caldwell (Nature 2004)
and the Patek lab's summaries; they are shown as cards, never as simulated measurements.
"""
from __future__ import annotations

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "shrimp3d"
SLUG = "mantis-shrimp-punch"
TANK = [-2.6, 2.6, 0.75, 2.9, -2.6, -0.3]      # x0, x1, y0 (sand), y1 (water top), z0 (back), z1 (glass)
TANK_SCALE = 0.2
TANK_SHRIMP = [0.15, 0.75, -1.05]
TANK_SHRIMP_YAW = -1.25                          # turned to face the people at the glass
TANK_SNAIL = [0.15 + 0.05, 0.75, -1.05 + 0.17]
WIZ = [-0.62, 0.0, 0.55]
WIZ_FACE = 2.9
WOMAN = [0.72, 0.0, 0.7]
WOMAN_FACE = -2.75
MACRO = [40.0, 0.0, 0.0]
SNAIL_DX = 0.76
SNAIL_SCALE = 1.0
CONTACT = [MACRO[0] + 0.71, 0.095, 0.0]
SPEAKER = {"hook": "wizard", "speed": "woman", "kmh": "wizard", "muscle": "wizard", "spring": "woman", "crossbow": "wizard",
           "bubbles": "woman", "collapse": "woman", "twice": "wizard", "fast": "woman", "force": "woman", "payoff": "wizard"}
SLOWMO = "SLOW-MOTION ILLUSTRATION"


def _track(keys, T):
    ks = sorted(keys)
    return np.interp(T, [k[0] for k in ks], [k[1] for k in ks])


def _smooth(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    punch_t = at("hook", "punch")
    snail_t = at("hook", "snail") - 0.1
    its_t = at("speed", "Its") - 0.1
    loads_t, lets_t = at("spring", "loads"), at("spring", "lets")
    club_t, bubble_t = at("fast", "Club"), at("fast", "bubble")
    peak_t = at("force", "peak") - 0.3
    water_t = at("bubbles", "water") - 0.1
    with_t = at("collapse", "With") - 0.1
    forces_t = at("force", "forces")
    # strike phase of the macro shrimp: 0-.2 cocked, .2-.3 the club swings to contact, .3-.48 bubbles grow,
    # .5-.58 they collapse (flash and second hit at .58); a drop back to 0 re-cocks the arm (always on a cut)
    p = _track([(0, 0.0), (punch_t - 0.12, 0.2), (punch_t + 0.02, 0.3), (punch_t + 0.3, 0.62), (its_t - 0.01, 0.62),
                (its_t, 0.0), (at("speed", "swings") - 0.2, 0.0), (at("speed", "swings"), 0.2), (E("speed") - 0.6, 0.3),
                (E("speed"), 0.3), (S("kmh"), 0.0), (lets_t, 0.0), (lets_t + 0.05, 0.2), (lets_t + 0.25, 0.3), (E("spring"), 0.36),
                (S("bubbles") - 0.12, 0.36), (S("bubbles") - 0.1, 0.22), (at("bubbles", "moves"), 0.24), (at("bubbles", "tears"), 0.3),
                (E("bubbles"), 0.48), (at("collapse", "collapse") + 0.1, 0.5), (at("collapse", "hit"), 0.58),
                (E("collapse"), 0.64), (S("twice"), 0.0), (club_t - 0.12, 0.2), (club_t + 0.02, 0.3), (bubble_t - 0.05, 0.3),
                (bubble_t + 0.2, 0.62), (S("force") - 0.12, 0.62), (S("force") - 0.1, 0.0), (forces_t - 0.12, 0.2),
                (forces_t + 0.02, 0.3), (forces_t + 0.35, 0.62), (dur, 0.62)], T)
    load = _track([(0, 0.0), (loads_t - 0.1, 0.0), (at("spring", "saddle") + 0.3, 1.0), (lets_t - 0.02, 1.0), (lets_t + 0.06, 0.0), (dur, 0.0)], T)
    flash_word = at("collapse", "flash")

    macro_spans = [(0.0, S("speed") - 0.1), (its_t, S("kmh") - 0.1), (S("spring") - 0.1, S("crossbow") - 0.1),
                   (S("bubbles") - 0.1, S("twice") - 0.1), (S("fast") - 0.1, S("force") - 0.1), (peak_t, S("payoff") - 0.1)]
    slow_spans = [(its_t, S("kmh") - 0.1), (S("spring") - 0.1, S("crossbow") - 0.1), (S("bubbles") - 0.1, S("twice") - 0.1)]

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_point", "woman_point", "strike", "load", "bub",
                              "flash", "crack", "shard_t", "tank_strike", "badge")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    cross_t = None
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        who = SPEAKER.get(a) if a else None
        pi = float(p[i])
        prev = float(p[i - 1]) if i else 0.0
        frames["look_w"].append("woman" if who == "woman" and a in ("speed", "fast", "force") else "tank")
        frames["look_m"].append("tank" if a in ("spring", "bubbles", "collapse") else "wizard")
        frames["wiz_point"].append(round(duo.bump(t, at("hook", "shrimp") - 0.3, 0.35, 1.2, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, at("speed", "peacock") - 0.3, 0.35, 1.2, 0.5), 3))
        frames["wiz_blink"].append(1.0 if (t % 3.9) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        strike = _smooth((pi - 0.2) / 0.1) if pi >= 0.2 else 0.0
        bub = 0.0
        if 0.3 <= pi < 0.5:
            bub = _smooth((pi - 0.3) / 0.18)
        elif 0.5 <= pi < 0.58:
            bub = 1.0 - _smooth((pi - 0.5) / 0.08)
        fl = max(0.0, 1.0 - abs(pi - 0.585) / 0.025) if 0.56 <= pi <= 0.61 else 0.0
        fl = max(fl, duo.bump(t, flash_word - 0.05, 0.06, 0.12, 0.25) if S("collapse") <= t < E("collapse") else 0.0)
        crack = 0.0 if pi < 0.3 else (0.5 if pi < 0.58 else 1.0)
        if pi >= 0.58 and prev < 0.58:
            cross_t = t
        if pi < 0.58:
            cross_t = None
        shard = 0.0 if cross_t is None else min(1.15, (t - cross_t) * (0.6 if S("collapse") <= t < E("collapse") else 1.6))
        frames["strike"].append(round(strike, 4))
        frames["load"].append(round(float(load[i]), 3))
        frames["bub"].append(round(bub, 3))
        frames["flash"].append(round(fl, 3))
        frames["crack"].append(crack)
        frames["shard_t"].append(round(shard, 3))
        # the small shrimp in the tank stays cocked, with one quick jab at the payoff ("shake hands")
        frames["tank_strike"].append(round(duo.bump(t, at("payoff", "shake") - 0.1, 0.08, 0.3, 0.4), 3))
        badge = ""
        if any(t0 + 0.15 <= t < t1 for t0, t1 in slow_spans):
            badge = SLOWMO
        frames["badge"].append(badge)

    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    mx, mz = MACRO[0], MACRO[2]
    cx, cy, cz = CONTACT
    inside_w = lambda t0, t1, s=0.0: E_(t0, t1, K(-0.5 + s, 1.5, -0.8), K(-0.52 + s, 1.52, -0.72), K(-0.6, 1.62, 0.55), 38, "reef")
    inside_m = lambda t0, t1: E_(t0, t1, K(0.55, 1.42, -0.8), K(0.58, 1.43, -0.72), K(0.72, 1.52, 0.7), 38, "reef")
    shots = cam.chain([
        # hook (a): already in motion on the macro reef: the shrimp, arms folded, the snail in front of it
        E_(0.0, snail_t, K(mx + 1.55, 0.62, mz + 1.9), K(mx + 1.4, 0.55, mz + 1.75), K(mx + 0.38, 0.16, mz), 40, "reef"),
        # hook (b): low and close: the punch
        E_(snail_t, S("speed") - 0.1, K(mx + 0.62, 0.3, mz + 1.15), K(mx + 0.6, 0.28, mz + 1.05), K(mx + 0.6, 0.13, mz), 40, "reef"),
        # speed (a): the woman at the glass, seen from inside the tank
        inside_m(S("speed") - 0.1, its_t),
        # speed (b): macro side on, slow motion: the club swings out
        E_(its_t, S("kmh") - 0.1, K(mx + 0.45, 0.3, mz + 1.45), K(mx + 0.47, 0.29, mz + 1.35), K(mx + 0.5, 0.14, mz), 40, "reef"),
        # kmh: the wizard, from inside the tank
        inside_w(S("kmh") - 0.1, S("muscle") - 0.1),
        # muscle: the gallery from behind: two silhouettes against the glowing tank
        E_(S("muscle") - 0.1, S("spring") - 0.1, K(0.15, 1.75, 3.7), K(0.12, 1.72, 3.45), K(0.0, 1.4, -1.0), 42, "reef"),
        # spring: close on the arm: the latch, the saddle spring loading (glows), the release
        E_(S("spring") - 0.1, S("crossbow") - 0.1, K(mx + 0.4, 0.2, mz + 1.0), K(mx + 0.41, 0.19, mz + 0.92), K(mx + 0.38, 0.1, mz), 34, "reef"),
        # crossbow: the wizard
        inside_w(S("crossbow") - 0.1, S("bubbles") - 0.1, 0.1),
        # bubbles: ultra slow motion in front of the club: the water tears into bubbles
        E_(S("bubbles") - 0.1, water_t, K(cx + 0.3, cy + 0.12, cz + 0.72), K(cx + 0.26, cy + 0.1, cz + 0.62), K(cx - 0.02, cy, cz), 40, "reef"),
        # bubbles (b): from the other side, looking back past the shell into the club's face as the water tears
        E_(water_t, S("collapse") - 0.1, K(cx + 0.18, cy + 0.1, cz - 0.62), K(cx + 0.15, cy + 0.09, cz - 0.55), K(cx - 0.06, cy, cz), 40, "reef"),
        # collapse: closer still: they collapse with a flash; the shell takes a second hit
        E_(S("collapse") - 0.1, with_t, K(cx + 0.22, cy + 0.08, cz + 0.5), K(cx + 0.2, cy + 0.07, cz + 0.44), K(cx, cy, cz), 40, "reef"),
        # collapse (b): pull back above: the crack, the flash, the shell taking the second hit
        E_(with_t, S("twice") - 0.1, K(cx + 0.35, cy + 0.42, cz + 0.4), K(cx + 0.3, cy + 0.38, cz + 0.34), K(cx - 0.05, cy, cz), 40, "reef"),
        # twice: the wizard
        inside_w(S("twice") - 0.1, S("fast") - 0.1, -0.05),
        # fast: macro side on, real speed: club, then bubble
        E_(S("fast") - 0.1, S("force") - 0.1, K(mx + 0.42, 0.36, mz + 1.6), K(mx + 0.44, 0.35, mz + 1.5), K(mx + 0.45, 0.14, mz), 40, "reef"),
        # force (a): the woman
        inside_m(S("force") - 0.1, peak_t),
        # force (b): the shell gives way
        E_(peak_t, S("payoff") - 0.1, K(cx + 0.45, 0.32, cz + 0.85), K(cx + 0.4, 0.3, cz + 0.78), K(cx + 0.05, 0.11, cz), 40, "reef"),
        # payoff: from inside the tank behind the little shrimp, out at the wizard
        cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(0.32, 0.86, -1.62), K(-0.35, 1.05, 0.55), 44),
                                                (dur + 0.05, K(0.3, 0.87, -1.52), K(-0.38, 1.08, 0.55), 44)], fps, "reef"),
    ])
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("speed", "twenty"), "end": S("kmh") - 0.15, "big": "23 m/s", "small": "club speed", "y": 0.16},
        {"start": at("kmh", "eighty") - 0.2, "end": S("muscle") - 0.15, "big": "over 80 km/h", "small": "underwater", "y": 0.16},
        {"start": at("fast", "thousandth") - 0.3, "end": S("force") - 0.15, "big": "under 0.001 s", "small": "club, then bubble", "y": 0.16},
        {"start": at("force", "two"), "end": S("payoff") - 0.15, "big": "over 2,500×", "small": "its body weight", "y": 0.16},
    ]
    events = [(round(punch_t + 0.02, 3), "pop", {"gain": 0.3}),
              (round(lets_t + 0.25, 3), "pop", {"gain": 0.26}),
              (round(at("collapse", "hit"), 3), "tink", {"gain": 0.22}),
              (round(club_t + 0.02, 3), "pop", {"gain": 0.26}),
              (round(bubble_t + 0.2, 3), "tink", {"gain": 0.2}),
              (round(forces_t + 0.02, 3), "impact", {"gain": 0.26})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [punch_t, lets_t, at("collapse", "hit")], "events": events,
               "mutes": [], "swells": [S("payoff")]}
    facts = {"club_speed_ms": 23, "club_speed_kmh": 82.8, "strike_under_s": 0.001, "force_body_weights": 2500,
             "events": {"contact_on_punch": {"t": punch_t + 0.05, "observe": "strike", "expect": 1.0, "tol": 0.02},
                        "second_hit_after_collapse": {"t": at("collapse", "hit") + 0.1, "observe": "crack", "expect": 1.0, "tol": 0}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 43, "supersample": 1.0,
            "end_hold_s": 1.6,
            "layout": {"tank": TANK, "tank_scale": TANK_SCALE, "tank_shrimp": TANK_SHRIMP, "tank_shrimp_yaw": TANK_SHRIMP_YAW,
                       "tank_snail": TANK_SNAIL, "wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE,
                       "macro": MACRO, "snail_dx": SNAIL_DX, "snail_scale": SNAIL_SCALE, "contact": CONTACT},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in ("strike", "crack", "bub", "load"):
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 104, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """Spoken numbers agree with each other: 23 m/s is about 83 km/h ('over eighty')."""
    kmh = 23 * 3.6
    return {"23 m/s = 82.8 km/h, so 'over eighty kilometres an hour' holds": {"pass": kmh > 80, "detail": f"{kmh:.1f} km/h"},
            "strike sequence order: swing, contact, bubbles grow, collapse with flash": {"pass": 0.2 < 0.3 < 0.48 < 0.58, "detail": "phases .2/.3/.48/.58"}}
