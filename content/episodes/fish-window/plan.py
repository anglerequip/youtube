"""A fish sees the whole sky through one small circle: render plan (scene renderer/scenes/fishwindow3d.js).

The shared lake set (renderer/sets/lake.js). The wizard and the woman stand on the bank; a trout hovers 1 m under
the calm surface just off the bank. Every light path drawn in the diagram shots is computed here with Snell's law
(n = 1.333): a sky ray arriving at incidence angle i enters the water where it bends to r = asin(sin i / n) and runs
on to the fish's eye. Rays from the horizon (i -> 90 deg) end at r = 48.6 deg, the edge of the 97-degree window.
The red ray is the one from the wizard's head, solved for the real geometry of the bank, so it lands near the
window's edge (and closer still when he sits down). Underwater shots show the window around the camera (the set's
mirror sheet). This file decides positions and timing; the scene only draws.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "fishwindow3d"
SLUG = "fish-window"
N = 1.333
CRIT = math.degrees(math.asin(1 / N))          # 48.6 deg
DEPTH = 1.0                                     # the fish's eye, metres under the surface
BANK_Y, SHORE = 0.3, 2.0
EYE = [0.4, -DEPTH, -2.2]                       # fish eye (world); the fish faces the bank (+z)
WIZ = [0.0, BANK_Y, 3.1]
WIZ_FACE = math.pi
WOMAN = [1.35, BANK_Y, 3.35]
WOMAN_FACE = math.pi + 0.45
WIZ_HEAD_STAND, WIZ_HEAD_SIT = 1.62, 1.18      # eye height above his feet, standing / sitting
SPEAKER = {"hook": "woman", "what": "wizard", "bend": "woman", "cone": "woman", "size": "woman", "outside": "wizard",
           "mirror": "woman", "tall": "wizard", "edge": "woman", "payoff": "wizard"}


def refract_deg(i_deg: float) -> float:
    """Angle from the vertical under water for a ray arriving at i_deg from the vertical above (Snell)."""
    return math.degrees(math.asin(math.sin(math.radians(i_deg)) / N))


def sky_ray(i_deg: float, az: float, above: float = 3.0) -> list:
    """Polyline [far sky point, entry point, eye] for a sky ray at incidence i_deg arriving from azimuth az (rad)."""
    r = math.radians(refract_deg(i_deg))
    d = DEPTH * math.tan(r)
    ex, ez = EYE[0] + d * math.sin(az), EYE[2] + d * math.cos(az)
    i = math.radians(i_deg)
    far = [ex + above * math.sin(i) * math.sin(az), above * math.cos(i), ez + above * math.sin(i) * math.cos(az)]
    return [[round(v, 4) for v in far], [round(ex, 4), 0.0, round(ez, 4)], [round(v, 4) for v in EYE]]


def head_ray(head: list) -> tuple[list, float, float]:
    """The ray from a point above the water (the wizard's eye) to the fish's eye: solve Snell's law for the entry
    point on the surface (1-D root find along the line between them). Returns (polyline, i_deg, r_deg)."""
    hx, hy, hz = head
    dx, dz = hx - EYE[0], hz - EYE[2]
    D = math.hypot(dx, dz)
    lo, hi = 0.0, D
    for _ in range(80):          # entry at horizontal distance s from the fish: n sin r = sin i must balance
        s = (lo + hi) / 2
        sin_r = s / math.hypot(s, DEPTH)
        sin_i = (D - s) / math.hypot(D - s, hy)
        if sin_i - N * sin_r > 0:
            lo = s
        else:
            hi = s
    s = (lo + hi) / 2
    ux, uz = dx / D, dz / D
    entry = [EYE[0] + ux * s, 0.0, EYE[2] + uz * s]
    i_deg = math.degrees(math.atan2(D - s, hy))
    r_deg = math.degrees(math.atan2(s, DEPTH))
    return [[round(v, 4) for v in head], [round(v, 4) for v in entry], [round(v, 4) for v in EYE]], i_deg, r_deg


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    ex, ey, ez = EYE
    R_WIN = DEPTH * math.tan(math.radians(CRIT))
    hook_c = max(at("hook", "squeezed") - 0.2, 2.4)
    keep_c = at("edge", "that's") - 0.1
    sit_t = at("payoff", "sitting") - 0.55

    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    shots_spec = [
        # hook (a): under water beside the trout, looking up: the bright circle of sky, mirror all around it
        ("under", E_(0.0, hook_c, K(ex + 0.2, ey - 0.75, ez - 0.95), K(ex + 0.15, ey - 0.7, ez - 0.8), K(ex - 0.05, -0.1, ez + 0.35), 64, "underlake")),
        # hook (b): above the lake, the two on the bank, the fish a shadow under the surface
        ("out", E_(hook_c, S("what") - 0.1, K(1.6, 1.25, -1.2), K(1.5, 1.3, -0.9), K(0.6, 1.25, 3.2), 40)),
        # what: the wizard, arms out at the big sky
        ("out", E_(S("what") - 0.1, S("bend") - 0.1, K(0.35, 1.95, 0.9), K(0.3, 1.95, 1.05), K(0.0, 1.85, 3.1), 38)),
        # bend: the diagram, side-on above the water: sky rays come down, bend at the surface, meet at the eye
        ("xray", E_(S("bend") - 0.1, at("bend", "Even") - 0.1, K(ex + 3.0, 0.6, ez + 0.3), K(ex + 2.8, 0.7, ez + 0.5), K(ex, 0.05, ez + 0.2), 54)),
        # bend (b): low at the surface where the flattest rays enter and kink steeply down to the eye
        ("xray", E_(at("bend", "Even") - 0.1, S("cone") - 0.1, K(ex + 1.6, 0.18, ez - 0.4), K(ex + 1.45, 0.16, ez - 0.25), K(ex - 0.2, -0.35, ez + 0.4), 50)),
        # cone: the rays become a cone; the window ring on the surface
        ("xray", E_(S("cone") - 0.1, S("size") - 0.1, K(ex + 2.3, 1.25, ez - 1.9), K(ex + 2.15, 1.35, ez - 1.6), K(ex, -0.4, ez), 44)),
        # size: higher, looking down on the ring; 1 m deep, 2.3 m across
        ("xray", E_(S("size") - 0.1, S("outside") - 0.1, K(ex + 0.4, 3.6, ez - 2.6), K(ex + 0.35, 3.8, ez - 2.3), K(ex, -0.2, ez), 40)),
        # outside: the wizard asks
        ("out", E_(S("outside") - 0.1, S("mirror") - 0.1, K(-0.45, 1.9, 1.0), K(-0.4, 1.9, 1.15), K(0.0, 1.85, 3.1), 36)),
        # mirror: under water again, looking up at a slant: the window, and the mirror reflecting the bed
        ("under", E_(S("mirror") - 0.1, S("tall") - 0.1, K(ex - 1.4, ey - 0.25, ez - 1.2), K(ex - 1.2, ey - 0.25, ez - 1.0), K(ex + 0.6, -0.1, ez + 0.6), 58, "underlake")),
        # tall: low from the water, the wizard stands tall on the bank
        ("out", E_(S("tall") - 0.1, S("edge") - 0.1, K(0.9, 0.55, 0.2), K(0.85, 0.5, 0.45), K(0.0, 1.55, 3.1), 40)),
        # edge (a): the diagram again: the red ray from his eye bends in near the window's edge
        ("xray", E_(S("edge") - 0.1, keep_c, K(ex + 1.3, 0.55, ez - 1.9), K(ex + 1.2, 0.6, ez - 1.6), K(0.0, 0.7, 2.6), 50)),
        # edge (b): the woman: careful anglers keep low
        ("out", E_(keep_c, S("payoff") - 0.1, K(1.0, 1.75, 1.35), K(0.98, 1.75, 1.5), K(1.35, 1.68, 3.35), 36)),
        # payoff: the wizard sits down with his rod; held to the end
        ("out", cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(0.6, 1.5, 0.3), K(0.05, 1.2, 3.1), 40),
                                                         (dur + 0.05, K(0.55, 1.4, 0.55), K(0.05, 1.0, 3.1), 40)], fps, "key")),
    ]
    shots = cam.chain([s for _, s in shots_spec])
    kinds = [kd for kd, _ in shots_spec]

    def kind_at(t):
        for kd, s_ in zip(kinds, shots):
            if s_["start"] <= t < s_["end"]:
                return kd
        return kinds[-1]

    # the light paths (all from Snell's law)
    fan_i = [0, 25, 45, 62, 75, 84, 89.5]
    fan = []
    for k, i_deg in enumerate(fan_i):
        for az in (math.pi * 0.5, -math.pi * 0.5):          # rays in the side-on plane through the eye (x-y)
            if i_deg == 0 and az < 0:
                continue
            fan.append({"pts": sky_ray(i_deg, az), "i": i_deg, "edge": i_deg >= 89})
    cone_rays = [sky_ray(89.9, a)[1:] for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    stand_ray, i_stand, r_stand = head_ray([WIZ[0], BANK_Y + WIZ_HEAD_STAND, WIZ[2]])
    sit_ray, i_sit, r_sit = head_ray([WIZ[0], BANK_Y + WIZ_HEAD_SIT, WIZ[2]])

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_wave", "woman_point", "xray",
                              "rays", "cone", "ring", "head_ray", "sit", "fish_swim")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        kd = kind_at(t)
        frames["xray"].append(1 if kd == "xray" else 0)
        frames["rays"].append(round(duo.ramp(t, S("bend") + 0.2, 2.4), 3) if t < S("cone") + 1.0 else
                              round(1.0 - duo.ramp(t, S("cone") + 1.0, 0.8), 3) if t < S("edge") else 0.0)
        frames["cone"].append(round(duo.ramp(t, S("cone") + 0.4, 1.0) * (1 - duo.ramp(t, S("outside") - 0.3, 0.3)), 3))
        frames["ring"].append(round(duo.ramp(t, at("bend", "surface") - 0.2, 0.6) * (1 - duo.ramp(t, S("outside") - 0.3, 0.3))
                                    + duo.ramp(t, S("edge") - 0.1, 0.5), 3))
        frames["head_ray"].append(round(duo.ramp(t, S("edge") + 0.2, 1.4), 3))
        frames["sit"].append(round(duo.ramp(t, sit_t, 1.0), 3))
        frames["fish_swim"].append(0.25)
        frames["look_w"].append("sky" if a in ("what",) else ("water" if a in ("bend", "cone", "size", "mirror", "payoff") else "woman"))
        frames["look_m"].append("wizard" if a in ("hook", "edge", "outside", "what", "tall", "payoff") else "water")
        frames["wiz_wave"].append(round(duo.bump(t, S("what") + 0.1, 0.4, 1.4, 0.5) * 0.55 + duo.bump(t, at("tall", "tall") - 0.4, 0.4, 0.9, 0.5) * 0.35, 3))
        frames["woman_point"].append(round(duo.bump(t, S("hook") + 0.3, 0.4, 1.6, 0.5), 3))
        frames["wiz_blink"].append(1.0 if (t % 3.9) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("cone", "ninety") - 0.1, "end": S("size") - 0.15, "big": "≈ 97°", "small": "of sky, all of it", "y": 0.16},
        {"start": at("size", "little"), "end": S("outside") - 0.15, "big": "≈ 2.3 m", "small": "across, 1 m deep", "y": 0.16},
    ]
    events = [(round(hook_c, 3), "whoosh", {"gain": 0.08}),
              (round(at("cone", "ninety") - 0.1, 3), "ding", {"gain": 0.1}),
              (round(S("mirror") - 0.05, 3), "whoosh", {"gain": 0.08}),
              (round(sit_t + 0.9, 3), "thud", {"gain": 0.08})]
    cuts_ = [s_["start"] for s_ in shots[1:]]
    # a reveal that lands just before a cut is shown by that cut: mark it there (QC no_cut_in_reveal)
    reveals_ = [next((c for c in cuts_ if -0.05 < c - r < 1.5), r) for r in [hook_c, at("cone", "ninety"), S("mirror")]]
    timing_ = {"cuts": cuts_, "reveals": reveals_,
               "events": events, "mutes": [], "swells": [S("payoff")]}
    facts = {"window_cone_deg": round(2 * CRIT, 2), "window_width_1m": round(2 * R_WIN, 3),
             "events": {"underwater_hook": {"t": 0.8, "observe": "underwater", "expect": 1, "tol": 0},
                        "wizard_sits_at_end": {"t": dur - 0.2, "observe": "sit", "expect": 1, "tol": 0.02}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 47, "supersample": 1.0, "bloom_threshold": 3.5,
            "end_hold_s": 1.4,
            "layout": {"wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE, "eye": EYE,
                       "r_win": R_WIN, "fan": fan, "cone_rays": cone_rays, "stand_ray": stand_ray, "sit_ray": sit_ray},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts,
            "_angles": {"i_stand": i_stand, "r_stand": r_stand, "i_sit": i_sit, "r_sit": r_sit}}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what == "underwater":
        t = i / plan["fps"]
        sh = next((s for s in plan["shots"] if s["start"] <= t < s["end"]), plan["shots"][-1])
        return 1 if sh["pos"][min(i - sh["i0"], len(sh["pos"]) - 1)][1] < 0 else 0
    if what in plan["frames"]:
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 88, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """Snell's law for every drawn ray, the 97-degree cone, the 2.3 m window at 1 m, and the wizard's ray landing
    inside the window but in its outer part (closer to the edge when he sits)."""
    worst = 0.0
    for i_deg in (0, 25, 45, 62, 75, 84, 89.5):
        pts = sky_ray(i_deg, math.pi / 2)
        far, entry, eye = (np.array(p) for p in pts)
        a_in = math.degrees(math.atan2(math.hypot(*(far - entry)[[0, 2]]), (far - entry)[1]))
        a_out = math.degrees(math.atan2(math.hypot(*(entry - eye)[[0, 2]]), (entry - eye)[1]))
        worst = max(worst, abs(math.sin(math.radians(a_in)) - N * math.sin(math.radians(a_out))))
    _, i_st, r_st = head_ray([WIZ[0], BANK_Y + WIZ_HEAD_STAND, WIZ[2]])
    _, i_si, r_si = head_ray([WIZ[0], BANK_Y + WIZ_HEAD_SIT, WIZ[2]])
    return {"every drawn ray obeys sin i = 1.333 sin r": {"pass": worst < 1e-3, "detail": f"worst mismatch {worst:.2e}"},
            "window cone is about 97 degrees": {"pass": abs(2 * CRIT - 97.2) < 0.3, "detail": f"{2 * CRIT:.1f} deg"},
            "window is a little over 2 m across at 1 m depth": {"pass": 2.0 < 2 * DEPTH * math.tan(math.radians(CRIT)) < 2.5,
                                                               "detail": f"{2 * DEPTH * math.tan(math.radians(CRIT)):.2f} m"},
            "the wizard appears in the outer part of the window, nearer the edge when sitting": {
                "pass": 0.6 * CRIT < r_st < CRIT and r_st < r_si < CRIT,
                "detail": f"standing r = {r_st:.1f} deg, sitting r = {r_si:.1f} deg, edge = {CRIT:.1f} deg"}}
