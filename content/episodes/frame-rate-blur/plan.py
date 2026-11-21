"""Why 24 fps looks smooth in films but choppy in games: render plan (the three.js scene is
renderer/scenes/framerate3d.js; the street set is renderer/sets/street.js).

A red ball is kicked along the grass verge beside the road: a projectile with horizontal speed 14 m/s (a hard kick,
about 50 km/h) and 3.5 m/s upward, so it is in the air for 2 x 3.5 / 9.81 = 0.71 s and travels 10 m. Everything the
viewer sees of the ball is computed from that one trajectory:

* a game frame at F fps is the ball at t = k / F, perfectly sharp, so neighbouring frames are v / F apart
  (0.58 m at 24 fps, 0.23 m at 60 fps: 24 / 60 = 0.4 of the jump);
* a film frame at 24 fps with the usual 180-degree shutter is the ball's whole path from t = k / 24 to k / 24 + 1/48:
  a streak half a frame-step long (0.29 m), so the streaks nearly join up.

Slowed-down sequences play the 0.71 s flight over about 7 s (10x), badged as an illustration.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "framerate3d"
SLUG = "frame-rate-blur"
G = 9.81
BALL_R = 0.11
V = [0.0, 3.5, 14.0]                 # m/s: up, along the verge
P0 = [8.4, BALL_R, -4.0]
T_LAND = 2 * V[1] / G
SLOW = 10.0
WIZ = [8.95, 0.0, -4.9]
WIZ_FACE = -0.55
WOMAN = [9.6, 0.0, 3.6]
WOMAN_FACE = -1.15
SPEAKER = {"hook": "wizard", "shutter": "woman", "smear": "woman", "sharp": "woman", "jumps": "wizard",
           "sixty": "woman", "steer": "woman", "payoff": "wizard"}
BADGE = "SLOWED DOWN 10x  ·  ILLUSTRATION"


def ball(tb: float) -> list:
    t = min(max(tb, 0.0), T_LAND)
    return [P0[0], BALL_R + V[1] * t - 0.5 * G * t * t, P0[2] + V[2] * t]


def step(fps: float) -> float:
    """Distance between neighbouring sharp frames (m) while the ball flies."""
    return V[2] / fps            # horizontal step between frames (the visible spacing)


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    kick1 = 0.05
    hook_c = at("hook", "So") - 0.15
    pay_c = at("payoff", "because") - 0.15
    kick2 = S("smear") - 0.1
    film_strip_t = at("smear", "and") - 0.1
    fake_t = at("sixty", "Some") - 0.1
    sixty_c = at("sixty", "sixty") - 0.25

    # per-frame ball mode and ball time
    modes, tbs = [], []
    for t in T:
        if t < kick1:
            m, tb = "rest", 0.0
        elif t < S("shutter") - 0.1:
            m, tb = "live_game", (t - kick1) / SLOW
        elif t < kick2:
            m, tb = "rest", 0.0
        elif t < film_strip_t:
            m, tb = "live_film", (t - kick2) / SLOW
        elif t < S("sharp") - 0.1:
            m, tb = "strip_film", T_LAND
        elif t < sixty_c:
            m, tb = "strip_game", T_LAND
        elif t < fake_t:
            m, tb = "strip_60", T_LAND
        elif t < S("steer") - 0.1:
            m, tb = "strip_film", T_LAND
        elif t < S("payoff") - 0.1:
            m, tb = "live_game", min(T_LAND, (t - (S("steer") - 0.1)) / SLOW)
        else:
            m, tb = "rest", 0.0
        modes.append(m); tbs.append(round(tb, 5))
    slow = [(kick1, S("shutter") - 0.1), (kick2, film_strip_t), (S("steer") - 0.1, S("payoff") - 0.1)]

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_point", "woman_point", "badge")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    frames["mode"], frames["tb"] = modes, tbs
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        frames["look_w"].append("woman" if a in ("shutter", "jumps", "steer") else "ball")
        frames["look_m"].append("ball" if a in ("smear", "sharp", "sixty") else "wizard")
        frames["wiz_point"].append(round(duo.bump(t, at("jumps", "jumps") - 0.4, 0.3, 1.0, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, at("sharp", "Ball") - 0.3, 0.35, 2.4, 0.5), 3))
        frames["wiz_blink"].append(1.0 if (t % 3.9) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        frames["badge"].append(BADGE if any(t0 + 0.1 <= t < t1 for t0, t1 in slow) else "")

    K = lambda *a: list(a)
    E_ = duo.shot(fps)

    def track(t0, t1, kick, dx=-5.0, dz=-0.9, h=1.3):
        """Side-on camera that glides with the slowed-down ball (continuous, so the game ball visibly jumps)."""
        keys = []
        for tk in np.arange(t0, t1 + 1e-6, 1.0 / fps):
            bx, by, bz = ball(max(0.0, (tk - kick) / SLOW))
            keys.append((float(tk), K(bx + dx, h, bz + dz), K(bx, 0.42 + 0.4 * by, bz + 0.1), 36))
        return cam.shot(t0, t1, keys, fps, "day")

    zc = P0[2] + V[2] * T_LAND / 2              # middle of the flight
    shots = cam.chain([
        # hook: already moving: the kicked ball in slow motion, drawn like a game: sharp, jumping frame to frame
        track(0.0, hook_c, kick1),
        # hook (b): higher and further back, still gliding with it: frozen ball, jump, frozen ball
        track(hook_c, S("shutter") - 0.1, kick1, dx=-6.5, dz=2.2, h=2.6),
        # shutter: the woman on the verge
        E_(S("shutter") - 0.1, kick2, K(6.6, 1.55, 5.6), K(6.7, 1.55, 5.4), K(9.6, 1.45, 3.6), 36),
        # smear (a): the same kick drawn like film: every frame a streak
        track(kick2, film_strip_t, kick2),
        # smear (b): all the film frames at once: streaks with tiny gaps, a slow truck along them
        E_(film_strip_t, S("sharp") - 0.1, K(5.2, 1.0, zc - 3.2), K(5.2, 1.0, zc - 1.2), K(P0[0], 0.45, zc - 1.0), 40, "day", K(P0[0], 0.45, zc + 1.0)),
        # sharp: the game frames at once: sharp balls with big gaps (truck the other way, a new angle)
        E_(S("sharp") - 0.1, S("jumps") - 0.1, K(5.6, 1.4, zc + 3.4), K(5.6, 1.35, zc + 1.2), K(P0[0], 0.4, zc + 2.0), 40, "day", K(P0[0], 0.4, zc - 0.4)),
        # jumps: the wizard, delighted
        E_(S("jumps") - 0.1, sixty_c, K(7.0, 1.6, -2.6), K(7.1, 1.6, -2.8), K(8.95, 1.6, -4.9), 36),
        # sixty (b): sixty frames: much smaller jumps
        E_(sixty_c, fake_t, K(5.2, 1.0, zc - 2.6), K(5.2, 1.0, zc - 0.8), K(P0[0], 0.45, zc - 0.6), 40, "day", K(P0[0], 0.45, zc + 1.2)),
        # sixty (c): fake blur: the streaks again, from higher
        E_(fake_t, S("steer") - 0.1, K(4.6, 3.2, zc + 2.0), K(4.8, 3.0, zc + 1.0), K(P0[0], 0.3, zc), 42),
        # steer: the woman, while the game ball jumps through again behind her
        E_(S("steer") - 0.1, S("payoff") - 0.1, K(7.0, 1.5, 6.4), K(7.1, 1.5, 6.25), K(9.6, 1.35, 3.6), 38),
        # payoff: the wizard with the ball back at his feet, ready to kick again (loops to the hook)
        E_(S("payoff") - 0.1, pay_c, K(7.2, 1.62, -3.3), K(7.25, 1.62, -3.45), K(8.95, 1.6, -4.9), 34),
        cam.shot(pay_c, dur + 0.05, [(pay_c, K(6.9, 1.45, -2.4), K(8.8, 1.05, -4.6), 38),
                                                (dur + 0.05, K(7.05, 1.45, -2.6), K(8.8, 1.05, -4.6), 38)], fps, "day"),
    ])
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("shutter", "half"), "end": kick2 - 0.15, "big": "Half a frame", "small": "shutter open", "y": 0.16},
        {"start": at("sharp", "sharp"), "end": S("jumps") - 0.15, "big": "24 fps", "small": "sharp frames, big gaps", "y": 0.16},
        {"start": sixty_c + 0.25, "end": fake_t - 0.1, "big": "60 fps", "small": "smaller jumps", "y": 0.16},
        {"start": at("steer", "forty"), "end": S("payoff") - 0.15, "big": "42 ms", "small": "between frames at 24 fps", "y": 0.16},
    ]
    events = [(round(kick1, 3), "thud", {"gain": 0.14}),
              (round(kick2, 3), "thud", {"gain": 0.12}),
              (round(film_strip_t, 3), "whoosh", {"gain": 0.1}),
              (round(sixty_c, 3), "pop", {"gain": 0.1})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [film_strip_t, at("sharp", "sharp"), sixty_c],
               "events": events, "mutes": [], "swells": [S("payoff")]}
    facts = {"slow_factors": [SLOW], "speed_ms": V[2], "flight_s": round(T_LAND, 3), "step_24_m": round(step(24), 3), "step_60_m": round(step(60), 3),
             "jump_ratio_60_24": round(step(60) / step(24), 3), "frame_ms_24": round(1000 / 24, 1), "streak_m": round(V[2] / 48, 3),
             "events": {"game_frames_sharp_in_hook": {"t": 3.0, "observe": "mode_game", "expect": 1, "tol": 0},
                        "film_streaks_in_smear": {"t": kick2 + 1.0, "observe": "mode_film", "expect": 1, "tol": 0}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 47, "supersample": 1.0, "bloom_threshold": 3.0,
            "end_hold_s": 1.4,
            "layout": {"wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE, "ball_r": BALL_R,
                       "p0": P0, "v": V, "t_land": T_LAND},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    m = plan["frames"]["mode"][k]
    if what == "mode_game":
        return 1 if m in ("live_game", "strip_game", "strip_60") else 0
    if what == "mode_film":
        return 1 if m in ("live_film", "strip_film") else 0
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 100, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """Frame spacing and streak length follow from the one trajectory: step = v / fps, streak = v x (1/48 s)."""
    s24, s60, streak = step(24), step(60), V[2] / 48
    return {"60 fps jump is less than half the 24 fps jump (24/60 = 0.4)": {"pass": abs(s60 / s24 - 0.4) < 1e-9 and s60 / s24 < 0.5,
                                                                           "detail": f"{s24:.3f} m vs {s60:.3f} m"},
            "film streak covers half the 24 fps step (180-degree shutter)": {"pass": abs(streak - s24 / 2) < 1e-9, "detail": f"streak {streak:.3f} m"},
            "24 fps frame interval is about 42 ms": {"pass": abs(1000 / 24 - 41.7) < 0.05, "detail": f"{1000 / 24:.1f} ms"},
            "flight time from the projectile": {"pass": abs(T_LAND - 2 * V[1] / G) < 1e-12, "detail": f"{T_LAND:.3f} s"}}
