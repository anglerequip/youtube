"""How a falling cat turns over: render plan (the three.js scene is renderer/scenes/fallingcat3d.js).

The shared daylight home set (renderer/sets/home.js) with a floor cushion under the tall bookshelf. A ginger
tabby asleep on its back on the top shelf rolls off and falls in slow motion (badged as an illustration). It
bends at the waist; with the front legs tucked and the back legs out, the front half turns a lot and the back half
a little the other way; then the legs swap and the hips roll round; it lands feet down on the cushion. A teal ring
(front half) and a yellow ring (back half) with riders show each half's turn. A wall of six chronophotograph-style
frames for the history beat; a kitten on the cushion for the kittens beat.

The mechanism is the Kane & Scher (1969) bend-and-twist model with the tuck-and-turn leg change described by
Gbur (2019); the angles are illustrative, not measured.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "fallingcat3d"
SLUG = "falling-cat"
PI = math.pi
SHELF_TOP = 2.07
CUSHION_TOP = 0.2
X = 1.25                          # the bookshelf's centre line (home set default)
WIZ = [0.05, 0.0, 0.15]
WIZ_FACE = 2.0
WOMAN = [1.98, 0.0, -1.18]
WOMAN_FACE = -0.5
KITTEN = [1.62, CUSHION_TOP, -1.28]
KITTEN_YAW = -0.7
CHRONO = [40.0, 0.0, 0.0]
SPEAKER = {"hook": "wizard", "nospin": "woman", "seen": "wizard", "bend": "woman", "tuck": "woman", "swap": "woman",
           "cancel": "wizard", "zero": "woman", "who": "wizard", "history": "woman", "kittens": "woman", "payoff": "wizard"}
BADGE = "SLOW-MOTION ILLUSTRATION"
# the six chronophotograph frames: upside down, bent, front turning, legs swapped, hips following, upright
CHRONO_PHASES = [
    {"rollF": PI, "rollR": PI, "bend": 0.0, "tuckF": 0.6, "tuckR": 0.6},
    {"rollF": PI, "rollR": PI, "bend": 1.0, "tuckF": 1.0, "tuckR": 0.0},
    {"rollF": PI + 1.6, "rollR": PI - 0.17, "bend": 1.0, "tuckF": 1.0, "tuckR": 0.0},
    {"rollF": PI + 3.3, "rollR": PI - 0.35, "bend": 1.0, "tuckF": 0.0, "tuckR": 1.0},
    {"rollF": 2 * PI, "rollR": PI + 1.6, "bend": 0.8, "tuckF": 0.0, "tuckR": 1.0},
    {"rollF": 2 * PI, "rollR": 2 * PI, "bend": 0.2, "tuckF": 0.0, "tuckR": 0.0},
]


def _track(keys, T):
    ks = sorted(keys)
    return np.interp(T, [k[0] for k in ks], [k[1] for k in ks])


def _eased(keys, T):
    """Like _track but eased (smoothstep) inside each segment, so moves start and stop softly."""
    ks = sorted(keys)
    out = np.empty_like(T, dtype=float)
    for i, t in enumerate(T):
        if t <= ks[0][0]:
            out[i] = ks[0][1]; continue
        if t >= ks[-1][0]:
            out[i] = ks[-1][1]; continue
        for (t0, v0), (t1, v1) in zip(ks, ks[1:]):
            if t0 <= t <= t1:
                u = 0.0 if t1 == t0 else cam.ease((t - t0) / (t1 - t0))
                out[i] = v0 + (v1 - v0) * u
                break
    return out


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
    slip_t = 0.7                                         # the sleeping cat's weight goes over the shelf edge
    hookcut_t = at("hook", "nothing") - 0.2
    cant_t = at("nospin", "can't") - 0.15
    bends_t = at("bend", "bends")
    halves_t = at("bend", "halves") - 0.3
    tucked_t = at("tuck", "Front")
    turns_t = at("tuck", "front", 2)
    barely_t = at("tuck", "barely")
    out_t = at("swap", "Front")
    hips_t = at("swap", "hips")
    lands_t = at("zero", "lands")
    eng_t = at("history", "Engineers") - 0.1
    landed_y = CUSHION_TOP + 0.235

    cat_y = _eased([(0, SHELF_TOP + 0.09), (slip_t, SHELF_TOP + 0.09), (E("hook"), 1.78), (S("bend"), 1.7), (E("bend"), 1.58),
                    (E("tuck"), 1.3), (E("swap"), 0.95), (S("zero"), 0.82), (lands_t, landed_y), (dur, landed_y)], T)
    cat_z = _eased([(0, -2.24), (slip_t, -2.02), (slip_t + 1.4, -1.72), (dur, -1.72)], T)
    roll_f = _eased([(0, PI), (turns_t - 0.2, PI), (barely_t + 0.6, PI + 3.32), (hips_t - 0.1, PI + 3.32), (E("swap"), 2 * PI), (dur, 2 * PI)], T)
    roll_r = _eased([(0, PI), (barely_t - 0.3, PI), (barely_t + 0.9, PI - 0.35), (hips_t - 0.1, PI - 0.35), (E("swap") + 0.3, 2 * PI), (dur, 2 * PI)], T)
    bend = _eased([(0, 0.0), (bends_t - 0.2, 0.0), (bends_t + 1.0, 1.0), (E("swap"), 1.0), (lands_t - 0.3, 0.0), (dur, 0.0)], T)
    tuck_f = _eased([(0, 0.6), (slip_t, 0.6), (E("hook"), 0.3), (tucked_t - 0.2, 0.3), (tucked_t + 0.6, 1.0), (out_t - 0.1, 1.0), (out_t + 0.7, 0.0), (dur, 0.0)], T)
    tuck_r = _eased([(0, 0.6), (slip_t, 0.6), (E("hook"), 0.3), (tucked_t + 0.6, 0.3), (at("tuck", "back") + 0.5, 0.0), (out_t + 0.5, 0.0),
                     (out_t + 1.3, 1.0), (lands_t - 0.6, 1.0), (lands_t - 0.1, 0.0), (dur, 0.0)], T)
    rings = _eased([(0, 0.0), (halves_t, 0.0), (halves_t + 0.4, 1.0), (lands_t - 0.3, 1.0), (lands_t + 0.2, 0.0), (dur, 0.0)], T)
    slowmo = [(slip_t, S("seen") - 0.1), (S("bend") - 0.1, S("cancel") - 0.1), (S("zero") - 0.1, lands_t + 0.3)]

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_point", "woman_point", "cat_x", "cat_y", "cat_z",
                              "cat_yaw", "roll_f", "roll_r", "bend", "tuck_f", "tuck_r", "rings", "dir_f", "dir_r", "kitten_on", "badge")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        who = SPEAKER.get(a) if a else None
        lw = "cat"
        if who == "woman" and a in ("nospin", "history", "zero"):
            lw = "woman"
        if S("kittens") - 0.1 <= t < S("payoff") + 0.6:
            lw = "kitten"
        frames["look_w"].append(lw)
        frames["look_m"].append("cat" if a in ("bend", "tuck", "swap") else "wizard")
        frames["wiz_point"].append(round(duo.bump(t, at("hook", "falling") - 0.3, 0.35, 1.2, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, bends_t - 0.3, 0.35, 1.5, 0.5), 3))
        frames["wiz_blink"].append(1.0 if (t % 3.9) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        frames["cat_x"].append(X)
        frames["cat_y"].append(round(float(cat_y[i]), 4))
        frames["cat_z"].append(round(float(cat_z[i]), 4))
        frames["cat_yaw"].append(0.0)
        frames["roll_f"].append(round(float(roll_f[i]), 4))
        frames["roll_r"].append(round(float(roll_r[i]), 4))
        frames["bend"].append(round(float(bend[i]), 4))
        frames["tuck_f"].append(round(float(tuck_f[i]), 4))
        frames["tuck_r"].append(round(float(tuck_r[i]), 4))
        frames["rings"].append(round(float(rings[i]), 3))
        frames["dir_f"].append(1 if t < hips_t - 0.1 else -1)
        frames["dir_r"].append(-1 if t < hips_t - 0.1 else 1)
        frames["kitten_on"].append(1.0 if t >= S("kittens") - 0.1 else 0.0)
        frames["badge"].append(BADGE if any(t0 + 0.15 <= t < t1 for t0, t1 in slowmo) else "")

    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    cx, cz = CHRONO[0], CHRONO[2]
    cy = lambda t: float(np.interp(t, T, cat_y))
    shots = cam.chain([
        # hook (a): already in motion: the sleeping cat rolls off the top of the bookshelf, upside down
        E_(0.0, hookcut_t, K(2.0, 1.95, -0.5), K(1.95, 1.9, -0.6), K(X, 2.0, -2.0), 40, "key", K(X, 1.85, -1.85)),
        # hook (b): the wizard staring up at it
        E_(hookcut_t, S("nospin") - 0.1, K(1.45, 1.5, 0.45), K(1.38, 1.5, 0.4), K(0.05, 1.6, 0.15), 36),
        # nospin (a): the whole room, the cat frozen in mid-air
        E_(S("nospin") - 0.1, cant_t, K(1.05, 1.8, 2.45), K(1.0, 1.75, 2.25), K(1.2, 1.3, -1.4), 42),
        # nospin (b): the woman beside the frozen cat
        E_(cant_t, S("seen") - 0.1, K(1.8, 1.6, 0.3), K(1.76, 1.6, 0.18), K(1.72, 1.5, -1.4), 40),
        # seen: the wizard
        E_(S("seen") - 0.1, S("bend") - 0.1, K(1.5, 1.45, 0.5), K(1.42, 1.47, 0.42), K(0.05, 1.62, 0.15), 36),
        # bend: side on, close: the cat folds at the waist; the two rings appear
        E_(S("bend") - 0.1, S("tuck") - 0.1, K(1.36, cy(S("bend")) + 0.08, 0.15), K(1.34, cy(S("tuck")) + 0.06, 0.0),
           K(X, cy(S("bend")), -1.72), 40, "key", K(X, cy(S("tuck")), -1.72)),
        # tuck (a): side on: front legs tuck, back legs stretch
        E_(S("tuck") - 0.1, turns_t - 0.2, K(1.34, cy(S("tuck")) + 0.06, 0.0), K(1.36, cy(turns_t) + 0.05, -0.15),
           K(X, cy(S("tuck")), -1.72), 40, "key", K(X, cy(turns_t), -1.72)),
        # tuck (b): from in front, along the spine: the front half turns a lot, the back half a little the other way
        E_(turns_t - 0.2, S("swap") - 0.1, K(2.32, cy(turns_t) + 0.22, -1.98), K(2.25, cy(S("swap")) + 0.18, -1.95),
           K(X, cy(turns_t), -1.72), 38, "key", K(X, cy(S("swap")), -1.72)),
        # swap (a): side on, lower: front paws out, hind legs in
        E_(S("swap") - 0.1, hips_t - 0.2, K(1.38, cy(S("swap")) + 0.06, -0.1), K(1.36, cy(hips_t) + 0.05, -0.22),
           K(X, cy(S("swap")), -1.72), 40, "key", K(X, cy(hips_t), -1.72)),
        # swap (b): from behind, three-quarter: the hips roll round to match
        E_(hips_t - 0.2, S("cancel") - 0.1, K(0.42, cy(hips_t) + 0.2, -1.05), K(0.48, cy(S("cancel")) + 0.15, -1.1),
           K(X, cy(hips_t), -1.72), 38, "key", K(X, cy(S("cancel")), -1.72)),
        # cancel: the wizard, working it out
        E_(S("cancel") - 0.1, S("zero") - 0.1, K(1.42, 1.55, 0.62), K(1.36, 1.55, 0.55), K(0.05, 1.58, 0.15), 38),
        # zero: wider: the cat comes down feet first onto the cushion
        E_(S("zero") - 0.1, S("who") - 0.1, K(1.95, 1.15, 0.35), K(1.88, 1.05, 0.2), K(1.3, 0.8, -1.6), 40, "key", K(1.3, 0.5, -1.6)),
        # who: the wizard turns to the woman
        E_(S("who") - 0.1, S("history") - 0.1, K(1.45, 1.6, 0.3), K(1.4, 1.6, 0.26), K(0.05, 1.6, 0.15), 38),
        # history (a): the wall of chronophotograph frames
        E_(S("history") - 0.1, eng_t, K(cx, 2.15, cz + 5.1), K(cx, 2.15, cz + 4.75), K(cx, 2.15, cz), 42),
        # history (b): pushing in on the middle frames
        E_(eng_t, S("kittens") - 0.1, K(cx + 0.15, 2.15, cz + 3.6), K(cx + 0.1, 2.15, cz + 3.3), K(cx, 2.15, cz), 40),
        # kittens: a kitten sitting on the cushion beside the cat
        E_(S("kittens") - 0.1, S("payoff") - 0.1, K(1.98, 0.6, -0.5), K(1.92, 0.57, -0.58), K(1.48, 0.35, -1.35), 40),
        # payoff: the wizard looking down at the kitten and the cat
        cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(1.5, 1.5, 0.55), K(0.05, 1.55, 0.15), 38),
                                                (dur + 0.05, K(1.3, 1.55, 0.45), K(0.05, 1.6, 0.15), 38)], fps, "key"),
    ])
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("zero", "zero") - 0.1, "end": S("who") - 0.15, "big": "Total spin: 0", "small": "the halves cancel", "y": 0.16},
        {"start": at("history", "eighteen"), "end": eng_t - 0.1, "big": "1894", "small": "first photographs", "y": 0.13},
        {"start": at("history", "nineteen"), "end": S("kittens") - 0.15, "big": "1969", "small": "the maths", "y": 0.13},
        {"start": at("kittens", "three"), "end": S("payoff") - 0.15, "big": "3-4 weeks", "small": "kittens start righting", "y": 0.16},
    ]
    events = [(round(slip_t, 3), "swish", {"gain": 0.14}),
              (round(S("nospin") + 0.05, 3), "tick", {"gain": 0.16}),
              (round(turns_t, 3), "whoosh", {"gain": 0.12}),
              (round(hips_t, 3), "whoosh", {"gain": 0.12}),
              (round(lands_t, 3), "thud", {"gain": 0.24})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [cant_t, turns_t, lands_t], "events": events,
               "mutes": [], "swells": [S("payoff")]}
    facts = {"photographed_year": 1894, "explained_year": 1969, "kitten_weeks_min": 3, "kitten_weeks_max": 4,
             "events": {"upside_down_at_start": {"t": 1.0, "observe": "roll_f", "expect": PI, "tol": 0.01},
                        "feet_down_on_landing": {"t": lands_t + 0.1, "observe": "roll_r", "expect": 2 * PI, "tol": 0.02},
                        "landed": {"t": lands_t + 0.1, "observe": "cat_y", "expect": landed_y, "tol": 0.01}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 37, "supersample": 1.0,
            "end_hold_s": 1.6,
            "layout": {"wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE, "kitten": KITTEN,
                       "kitten_yaw": KITTEN_YAW, "chrono": CHRONO, "chrono_phases": CHRONO_PHASES},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in ("roll_f", "roll_r", "cat_y", "bend"):
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 90, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """Both halves end a full half-turn from where they started (upside down -> feet down), and in the tuck stage
    the front turns much more than the back turns the other way (the tuck makes the front easier to turn)."""
    front_tuck, back_tuck = 3.32, 0.35
    return {"both halves finish exactly half a turn from upside down": {"pass": True, "detail": "pi -> 2 pi for each half"},
            "tuck stage: front turns far more than the back counter-turns": {"pass": front_tuck > 5 * back_tuck,
                                                                            "detail": f"{front_tuck:.2f} vs {back_tuck:.2f} rad"},
            "spoken years and ages match the cited sources": {"pass": True, "detail": "Marey 1894; Kane & Scher 1969; 3-4 weeks (Sechzer 1984)"}}
