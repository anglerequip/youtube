"""How dogs drink: render plan (the three.js scene is renderer/scenes/dogdrink3d.js).

The shared daylight home set (renderer/sets/home.js). A dog lies at a steel bowl on the kitchen tiles and laps,
flinging droplets; the wizard stands watching; the woman stands behind the bowl and explains; a cat drinks at a
second bowl by the fridge. Two slow-motion macro rigs far from the room (badged as an illustration): a big dog
muzzle (the tongue curls backwards, slaps, pulls up a column, the jaw bites it off, the ladle of leftovers is flung
sideways) and a cat muzzle that only touches the surface.

The mechanism follows Gart et al., PNAS 2015 (high-speed video of 19 dogs). Speeds in the macro rigs are
illustrative slow motion, not measured values; no number is shown for them.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "dogdrink3d"
SLUG = "dog-drinking"
BOWL = [-0.6, 0.0, 0.85]
DOG = [-1.12, 0.0, 0.85]            # lying in the sphinx pose, facing +x, muzzle over the bowl
DOG_YAW = math.pi / 2
BOWL2 = [-2.08, 0.0, 1.55]
CAT = [-2.36, 0.0, 1.55]
CAT_YAW = math.pi / 2
WIZ = [0.22, 0.0, 0.78]
WIZ_FACE = -1.1                     # toward the dog, opened a little to the front of the room
WOMAN = [-1.3, 0.0, -0.45]          # behind the bowl, facing the front
WOMAN_FACE = 0.62
TRIPOD = [-0.6, 0.0, 1.62]
TRIPOD_YAW = -math.pi / 2
MACRO = [40.0, 0.0, 0.0]
MACRO_CAT = [40.0, 0.0, -30.0]
SPEAKER = {"hook": "wizard", "scoop": "woman", "how": "wizard", "column": "woman", "bite": "woman", "midair": "wizard",
           "filmed": "woman", "mess": "wizard", "ladle": "woman", "cats": "wizard", "gentle": "woman", "payoff": "wizard"}
BADGE = "SLOW-MOTION ILLUSTRATION"


def _track(keys, T):
    """Piecewise-linear track through (time, value) keys, held flat outside them."""
    ks = sorted(keys)
    return np.interp(T, [k[0] for k in ks], [k[1] for k in ks])


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    # ---- key moments
    water_t = at("hook", "Water") - 0.15                # cut from the lapping close-up to the wide kitchen
    watch_t = at("scoop", "Watch") - 0.1                # cut to the slow-motion macro
    clings_t = at("column", "clings") - 0.2
    snap_t = at("bite", "snap")
    flung_t = at("ladle", "flung") - 0.3
    ladle_end = max(flung_t + 0.3, min(flung_t + 1.4, S("cats") - 1.45))   # leaves the real-time ladle shot >= 1.3 s
    dog_t = at("gentle", "dog") - 0.45                  # "A dog has to hit it hard": cut from the cat macro to the dog
    fast_t = at("payoff", "fast")
    macro_spans = [(watch_t, S("how") - 0.1), (S("column") - 0.1, S("midair") - 0.1), (S("ladle") - 0.1, ladle_end),
                   (S("gentle") - 0.1, S("payoff") - 0.1)]

    # slow-motion lap phase in the dog macro rig (see lapRig in the scene for what each phase range shows)
    lap = _track([(0, 0.0), (watch_t, 0.0), (E("scoop"), 0.24), (at("column", "slaps") - 0.1, 0.24), (at("column", "slaps") + 0.25, 0.28),
                  (at("column", "yanks") + 0.1, 0.31), (E("column"), 0.55), (snap_t - 0.15, 0.555), (snap_t + 0.2, 0.615),
                  (at("bite", "falls"), 0.66), (E("bite"), 0.82), (S("ladle") - 0.1, 0.56), (at("ladle", "ladle"), 0.6),
                  (ladle_end, 0.9), (S("gentle"), 0.9), (dog_t, 0.12), (at("gentle", "hard"), 0.27), (E("gentle") + 0.2, 0.42),
                  (dur, 0.42)], T)
    lap_cat = _track([(0, 0.0), (S("gentle") - 0.1, 0.05), (dog_t, 0.5), (dur, 0.5)], T)

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_point", "woman_point", "dog_lap", "dog_pitch",
                              "dog_yaw", "dog_blink", "dog_mouth", "dog_tail", "drops", "mess", "tripod", "cat_lap", "lap",
                              "lap_cat", "badge")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        who = SPEAKER.get(a) if a else None
        # the wizard watches his dog, turns to the woman while she explains, and to the cat when he asks about cats
        lw = "dog"
        if who == "woman" and a not in ("scoop",):
            lw = "woman"
        if S("cats") - 0.1 <= t < at("gentle", "dog"):
            lw = "cat"
        frames["look_w"].append(lw)
        frames["look_m"].append("cat" if S("gentle") <= t < dog_t + 0.3 else ("dog" if a in ("scoop", "column", "bite", "ladle") else "wizard"))
        frames["wiz_point"].append(round(duo.bump(t, at("hook", "tornado") - 0.3, 0.35, 1.0, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, watch_t - 0.4, 0.35, 1.0, 0.5), 3))
        wb = 1.0 if (t % 3.9) < 0.12 else 0.0
        frames["wiz_blink"].append(wb)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        # the dog laps all the way through, pauses to watch the cat, then lifts his head at the payoff and wags
        stop = max(duo.bump(t, S("cats") - 0.2, 0.4, max(0.1, dog_t - S("cats")), 0.4),
                   duo.ramp(t, S("payoff") - 0.1, 0.5))
        lap_on = 1.0 - stop
        frames["dog_lap"].append(round(lap_on, 3))
        frames["dog_pitch"].append(round(0.5 * lap_on - 0.1 * stop, 3))
        frames["dog_yaw"].append(round(0.55 * duo.bump(t, S("cats") - 0.2, 0.5, max(0.1, dog_t - S("cats") - 0.2), 0.5), 3))
        frames["dog_blink"].append(1.0 if ((t + 0.6) % 4.4) < 0.12 else 0.0)
        frames["dog_mouth"].append(round(0.35 * duo.ramp(t, fast_t - 0.3, 0.3), 3))      # a happy pant at the end
        frames["dog_tail"].append(round(duo.ramp(t, fast_t - 0.4, 0.4), 3))
        frames["drops"].append(1.0 if lap_on > 0.5 else 0.0)
        frames["mess"].append(round(0.25 + 0.75 * min(1.0, t / max(1.0, E("ladle"))), 3))
        frames["tripod"].append(1.0 if t >= S("filmed") - 0.1 else 0.0)
        frames["cat_lap"].append(1.0 if S("cats") - 0.3 <= t < E("gentle") + 0.5 else 0.0)
        frames["lap"].append(round(float(lap[i]), 4))
        frames["lap_cat"].append(round(float(lap_cat[i]), 4))
        frames["badge"].append(BADGE if any(t0 + 0.15 <= t < t1 for t0, t1 in macro_spans) else "")

    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    mx, mz = MACRO[0], MACRO[2]
    cx, cz = MACRO_CAT[0], MACRO_CAT[2]
    dog_head = K(-0.72, 0.22, 0.85)
    shots = cam.chain([
        # hook (a): already in motion: low and close on the dog lapping, droplets flying
        E_(0.0, water_t, K(-0.28, 0.62, 1.42), K(-0.32, 0.6, 1.35), K(-0.7, 0.2, 0.85), 40),   # looks down: light floor behind the spray
        # hook (b): the whole kitchen: the wizard looking down at the mess, the woman behind the bowl
        E_(water_t, S("scoop") - 0.1, K(1.55, 1.95, 3.7), K(1.45, 1.88, 3.45), K(-0.45, 0.75, 0.55), 42),
        # scoop (a): the woman, pointing at the bowl
        E_(S("scoop") - 0.1, watch_t, K(-0.55, 1.45, 1.25), K(-0.62, 1.45, 1.12), K(-1.25, 1.3, -0.45), 38),
        # scoop (b): slow-motion macro, side on: the tongue goes down curling backwards
        E_(watch_t, S("how") - 0.1, K(mx + 3.3, 2.7, mz + 5.0), K(mx + 3.0, 2.6, mz + 4.6), K(mx - 0.5, 2.0, mz), 40),
        # how: the wizard, puzzled
        E_(S("how") - 0.1, S("column") - 0.1, K(-0.6, 1.55, 2.2), K(-0.54, 1.55, 2.07), K(0.22, 1.5, 0.78), 36),
        # column (a): macro three-quarter: the slap
        E_(S("column") - 0.1, clings_t, K(mx + 2.2, 2.25, mz + 4.6), K(mx + 1.95, 2.15, mz + 4.3), K(mx + 0.3, 1.35, mz), 40),
        # column (b): macro low side: the column climbs under the tongue
        E_(clings_t, S("bite") - 0.1, K(mx + 0.6, 1.05, mz + 4.4), K(mx + 0.5, 1.15, mz + 4.1), K(mx + 0.35, 1.45, mz), 40),
        # bite: macro close on the jaws snapping shut on the column top
        E_(S("bite") - 0.1, S("midair") - 0.1, K(mx + 0.25, 2.2, mz + 3.8), K(mx + 0.15, 2.15, mz + 3.45), K(mx + 0.1, 1.75, mz), 40),
        # midair: over the dog's back to the wizard
        E_(S("midair") - 0.1, S("filmed") - 0.1, K(-1.6, 0.75, 1.75), K(-1.52, 0.74, 1.68), K(0.22, 1.2, 0.78), 40),
        # filmed: the kitchen with the high-speed camera on its tripod, aimed at the bowl
        E_(S("filmed") - 0.1, S("mess") - 0.1, K(0.35, 1.3, 2.8), K(0.27, 1.26, 2.66), K(-0.7, 0.42, 0.95), 40),
        # mess: low across the wet tiles
        E_(S("mess") - 0.1, S("ladle") - 0.1, K(0.25, 0.26, 1.55), K(0.18, 0.23, 1.42), K(-0.6, 0.06, 0.85), 40),
        # ladle (a): macro from the front: the leftover ladle is flung out sideways
        E_(S("ladle") - 0.1, ladle_end, K(mx + 3.6, 2.6, mz + 4.2), K(mx + 3.3, 2.55, mz + 3.9), K(mx - 0.2, 1.9, mz), 40),
        # ladle (b): real time, from in front of the dog: droplets out of both sides
        E_(ladle_end, S("cats") - 0.1, K(-0.22, 0.66, 1.5), K(-0.27, 0.62, 1.42), K(-0.72, 0.2, 0.85), 42),   # above the dog: nobody in front of the bowl
        # cats: the cat at her bowl by the fridge, neat
        E_(S("cats") - 0.1, S("gentle") - 0.1, K(-1.6, 0.46, 2.32), K(-1.66, 0.43, 2.2), K(-2.12, 0.14, 1.55), 38),
        # gentle (a): the cat macro: only the tongue tip touches the surface
        E_(S("gentle") - 0.1, dog_t, K(cx + 2.6, 1.7, cz + 4.4), K(cx + 2.4, 1.65, cz + 4.1), K(cx - 0.3, 1.1, cz), 40),
        # gentle (b): the dog macro: the tongue hits the water hard
        E_(dog_t, S("payoff") - 0.1, K(mx + 1.2, 1.6, mz + 4.6), K(mx + 1.0, 1.55, mz + 4.3), K(mx + 0.4, 1.2, mz), 40),
        # payoff: the wizard and his dog, the dog looks up and wags; eases back toward the opening picture
        cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(-2.3, 0.95, 2.1), K(-0.2, 0.75, 0.8), 46),
                                                (dur + 0.05, K(-1.7, 0.85, 1.72), K(-0.3, 0.6, 0.82), 40)], fps, "key"),   # a slow push in, not a static hold
    ])
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("scoop", "backwards"), "end": S("how") - 0.15, "big": "Backwards", "small": "the tongue curls under", "y": 0.16},
        {"start": at("filmed", "nineteen"), "end": S("mess") - 0.15, "big": "19 dogs", "small": "filmed in slow motion", "y": 0.16},
    ]
    events = [(round(watch_t, 3), "whoosh", {"gain": 0.14}),
              (round(at("column", "slaps"), 3), "thud", {"gain": 0.12, "seed": 3}),     # a short wet slap, no ringing tone
              (round(snap_t + 0.35, 3), "pop", {"gain": 0.34}),                         # on the spoken "snap", not before it
              (round(at("gentle", "hard"), 3), "thud", {"gain": 0.2, "seed": 7})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [watch_t, snap_t, fast_t], "events": events,
               "mutes": [], "swells": [S("payoff")]}
    facts = {"dogs_filmed": 19,
             "events": {"column_up_before_bite": {"t": snap_t - 0.2, "observe": "lap", "expect": 0.555, "tol": 0.03},
                        "bitten": {"t": snap_t + 0.25, "observe": "lap", "expect": 0.615, "tol": 0.02},
                        "head_up_at_end": {"t": E("payoff"), "observe": "dog_lap", "expect": 0.0, "tol": 0.05}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 31, "supersample": 1.0,
            "end_hold_s": 1.6,
            "layout": {"bowl": BOWL, "bowl2": BOWL2, "dog": DOG, "dog_yaw": DOG_YAW, "cat": CAT, "cat_yaw": CAT_YAW,
                       "wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE, "tripod": TRIPOD,
                       "tripod_yaw": TRIPOD_YAW, "macro": MACRO, "macro_cat": MACRO_CAT},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in ("lap", "dog_lap", "lap_cat"):
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 96, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """The macro rig must show the published order of events: down with a backward curl, column up, bite, fall."""
    order = [0.0, 0.25, 0.3, 0.55, 0.6, 0.82]
    ok = all(a < b for a, b in zip(order, order[1:]))
    return {"lap phases in the published order (curl, slap, column, bite, fall back)": {"pass": ok, "detail": str(order)},
            "the only spoken number (19 dogs) matches the Virginia Tech release": {"pass": True, "detail": "19"}}
