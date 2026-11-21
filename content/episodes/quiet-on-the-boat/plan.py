"""Shouting barely reaches fish, a dropped tackle box does: render plan (scene renderer/scenes/quietboat3d.js).

The shared lake set. A rowing boat out on the lake, the wizard on the bow seat and the woman on the stern seat,
a trout under the boat. Sound is drawn as wavefront rings on a vertical sheet through the boat's long axis.

Physics (all computed here):
  * specific acoustic impedance Z = rho c: air 1.204 kg/m3 x 343 m/s = 413 rayl, fresh water 1000 x 1482 =
    1.48 million rayl, ratio about 3,590;
  * intensity transmitted through the surface at normal incidence T = 4 Z1 Z2 / (Z1 + Z2)^2 = 0.11 %;
  * sound speed in water / air = 1482 / 343 = 4.3.
Rings in the air bounce off the surface (drawn as the mirror-image ring, the image-source picture of a reflection)
and the ring that gets into the water is drawn at T relative strength (scaled up a little so it is visible at all,
and still the faintest thing on screen). Rings in water expand 4.3 times faster than rings in air. The drawing is
slowed down about 620 times (0.55 m/s for air) so the eye can follow it; the ratio of the speeds is real.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "quietboat3d"
SLUG = "quiet-on-the-boat"
RHO_AIR, C_AIR = 1.204, 343.0
RHO_WATER, C_WATER = 1000.0, 1482.0
Z_AIR, Z_WATER = RHO_AIR * C_AIR, RHO_WATER * C_WATER
T_NORMAL = 4 * Z_AIR * Z_WATER / (Z_AIR + Z_WATER) ** 2
SPEED_RATIO = C_WATER / C_AIR
V_AIR = 0.55                                        # drawn speed of sound in air, m/s (slowed ~620x)
V_WATER = V_AIR * SPEED_RATIO
G = 9.81

BOAT = [0.0, 0.0, -3.2]
SEAT_X = 0.47
FLOOR_Y = 0.12 - 0.5 + 0.015                        # top of the floor board (lake.js rowboat)
SIT_ROOT_Y = -0.33                                  # presenter root height so the sit pose rests on the thwart
WIZ = [BOAT[0] - SEAT_X, SIT_ROOT_Y, BOAT[2]]
WIZ_FACE = math.pi / 2                              # faces +x (toward the woman)
WOMAN = [BOAT[0] + SEAT_X, SIT_ROOT_Y, BOAT[2]]
WOMAN_FACE = -math.pi / 2
FISH = [BOAT[0] + 0.25, -1.25, BOAT[2] - 0.3]
FISH_LEN = 0.45
BOX_REST = [BOAT[0] + 0.22, 0.19, BOAT[2] - 0.46]   # on the gunwale beside the woman
BOX_FLOOR = [BOAT[0] + 0.18, FLOOR_Y, BOAT[2] - 0.12]
HULL_BOTTOM = [BOAT[0] + 0.18, -0.5]                # under the impact, in the sheet's (x, y)

SPEAKER = {"hook": "woman", "why": "wizard", "push": "woman", "bounce": "woman", "sing": "wizard", "drop": "woman",
           "hull": "woman", "gone": "wizard", "payoff": "wizard"}


def box_track(t: float, t_drop: float) -> tuple[list, float]:
    """Tackle box: resting on the gunwale, tipped off at t_drop, free fall to the floor, one small bounce."""
    fall_h = BOX_REST[1] - BOX_FLOOR[1]
    t_fall = math.sqrt(2 * fall_h / G)
    if t < t_drop:
        return list(BOX_REST) + [0.0], 0.0
    u = t - t_drop
    if u < t_fall:
        f = u / t_fall
        y = BOX_REST[1] - 0.5 * G * u * u
        x = BOX_REST[0] + (BOX_FLOOR[0] - BOX_REST[0]) * f
        z = BOX_REST[2] + (BOX_FLOOR[2] - BOX_REST[2]) * f
        return [x, y, z, -0.9 * f], 0.0
    u -= t_fall
    vb = 0.25 * G * t_fall                         # bounce with a quarter of the impact speed
    tb = 2 * vb / G
    if u < tb:
        return [BOX_FLOOR[0], BOX_FLOOR[1] + vb * u - 0.5 * G * u * u, BOX_FLOOR[2], -0.9 + 0.9 * u / tb], 0.0
    return list(BOX_FLOOR) + [0.0], 0.0


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    bx, _, bz = BOAT
    fx, fy, fz = FISH
    t_drop = E("drop") - 0.55
    t_fall = math.sqrt(2 * (BOX_REST[1] - BOX_FLOOR[1]) / G)
    t_imp = t_drop + t_fall
    t_bounce2 = t_imp + 2 * (0.25 * G * t_fall) / G
    t_hit = t_imp + math.hypot(fx - HULL_BOTTOM[0], fy - HULL_BOTTOM[1]) / V_WATER   # first ring reaches the fish
    t_race = at("hull", "underwater") - 0.15
    t_bolt = at("gone", "goes") - 0.1
    hook_c = max(2.4, at("hook", "Almost") - 0.15)
    bounce_c = at("bounce", "Only") - 0.15
    hull_c = at("hull", "That") - 0.1

    E_ = duo.shot(fps)
    K = lambda *a: list(a)
    UL = "underlake"
    shots_spec = [
        # hook (a): side view of the boat with the water see-through: the woman calls out, rings bounce off
        ("xray", E_(0.0, hook_c, K(bx - 0.2, 0.4, bz - 3.7), K(bx - 0.1, 0.4, bz - 3.3), K(bx + 0.1, -0.25, bz), 50)),
        # hook (b): under the boat next to the trout, calm; a faint ring above
        ("under", E_(hook_c, S("why") - 0.1, K(fx + 0.95, fy + 0.05, fz - 0.95), K(fx + 0.8, fy + 0.1, fz - 0.8), K(fx, fy + 0.1, fz), 44, UL)),
        # why: over the woman's shoulder onto the wizard
        ("out", E_(S("why") - 0.1, S("push") - 0.1, K(bx + 1.55, 1.12, bz - 0.55), K(bx + 1.45, 1.1, bz - 0.45), K(bx - 0.6, 0.82, bz), 36)),
        # push: reverse, over the wizard's shoulder onto the woman
        ("out", E_(S("push") - 0.1, S("bounce") - 0.1, K(bx - 1.55, 1.12, bz - 0.55), K(bx - 1.45, 1.1, bz - 0.45), K(bx + 0.6, 0.78, bz), 36)),
        # bounce (a): the diagram, side view: rings from her voice hit the surface and come back up
        ("xray", E_(S("bounce") - 0.1, bounce_c, K(bx + 0.2, 0.55, bz - 3.3), K(bx + 0.1, 0.5, bz - 2.9), K(bx, 0.05, bz), 46)),
        # bounce (b): at the waterline: the echo above, the faint ring that gets in below
        ("xray", E_(bounce_c, S("sing") - 0.1, K(bx + 0.5, 0.05, bz - 3.2), K(bx + 0.4, 0.05, bz - 2.9), K(bx + 0.1, -0.1, bz), 52)),
        # sing: the wizard sings, arms out; a front three-quarter of both in the boat
        ("out", E_(S("sing") - 0.1, S("drop") - 0.1, K(bx - 0.6, 1.25, bz - 2.4), K(bx - 0.5, 1.2, bz - 2.15), K(bx - 0.2, 0.6, bz), 40)),
        # drop: close on the tackle box on the gunwale; it tips and falls to the floor
        ("out", E_(S("drop") - 0.1, t_imp + 0.2, K(bx + 0.95, 0.75, bz - 1.35), K(bx + 0.9, 0.7, bz - 1.2), K(BOX_REST[0], 0.0, BOX_REST[2] + 0.15), 40)),
        # hull (a): under water, side-on: strong rings from the hull reach the trout
        ("xray", E_(t_imp + 0.2, hull_c, K(fx + 0.9, -1.0, fz - 1.9), K(fx + 0.75, -1.05, fz - 1.65), K(fx - 0.1, -0.95, fz), 50, UL)),
        # hull (b): the race at the waterline: one knock, the water ring 4.3 times bigger than the air ring
        ("xray", E_(hull_c, S("gone") - 0.1, K(bx + 0.3, 0.25, bz - 5.2), K(bx + 0.25, 0.2, bz - 4.6), K(bx + 0.2, -0.45, bz), 52)),
        # gone: under water by the trout, which bolts away
        ("under", E_(S("gone") - 0.1, S("payoff") - 0.1, K(fx + 1.0, fy + 0.15, fz - 1.1), K(fx + 0.9, fy + 0.15, fz - 1.0), K(fx, fy, fz - 0.3), 46, UL)),
        # payoff: both in the boat, the wizard sings softly, then wags a finger at the box
        ("out", cam.shot(S("payoff") - 0.1, dur + 0.05, [(S("payoff") - 0.1, K(bx + 0.2, 1.15, bz - 2.9), K(bx, 0.55, bz), 44),
                                                         (dur + 0.05, K(bx + 0.18, 1.1, bz - 2.55), K(bx, 0.55, bz), 44)], fps, "key")),
    ]
    shots = cam.chain([s for _, s in shots_spec])
    kinds = [kd for kd, _ in shots_spec]
    for kd, s_ in zip(kinds, shots):
        if kd == "xray":
            s_["dof"] = 0                              # diagram shots stay fully sharp

    def kind_at(t):
        for kd, s_ in zip(kinds, shots):
            if s_["start"] <= t < s_["end"]:
                return kd
        return kinds[-1]

    # rings: every 0.42 s while someone is talking (their voice), stronger for the call and the song; the knock
    leak = min(1.0, T_NORMAL * 60)                 # 0.11 % drawn at 6.6 % of the echo's strength: visible, faintest
    rings = []
    last = {"wizard": -9.0, "woman": -9.0}
    for i, t in enumerate(T):
        ln = tl.active(t)
        if not ln or ln.id in ("hull", "gone") or t > t_drop - 0.3 and t < t_race + 3.0:
            continue
        who = SPEAKER[ln.id]
        talk = tw[i] if who == "wizard" else tm[i]
        if talk > 0.25 and t - last[who] >= 0.42:
            loud = 1.0 if ln.id in ("hook", "sing") else 0.6
            rings.append({"t0": round(float(t), 3), "src": who, "kind": "air", "v": V_AIR, "a": round(0.85 * loud, 3),
                          "leak": round(leak, 4), "life": 3.6})
            last[who] = t
    for k, (t0, a) in enumerate([(t_imp, 1.0), (t_imp + 0.12, 0.7), (t_bounce2, 0.55), (t_bounce2 + 0.12, 0.35)]):
        rings.append({"t0": round(t0, 3), "src": "hull", "at": HULL_BOTTOM, "kind": "water", "v": V_WATER, "a": a, "life": 2.6})
    for k in range(3):                               # the race: the same knock into the air and into the water
        t0 = t_race + 0.9 * k
        rings.append({"t0": round(t0, 3), "src": "hull", "at": [HULL_BOTTOM[0], 0.0], "kind": "race_air", "v": V_AIR, "a": 0.95, "life": 1.7})
        rings.append({"t0": round(t0, 3), "src": "hull", "at": [HULL_BOTTOM[0], 0.0], "kind": "water", "v": V_WATER, "a": 0.95, "life": 1.7})

    frames = {k: [] for k in ("wiz_blink", "woman_blink", "look_w", "look_m", "wiz_wave", "wiz_point", "woman_point", "xray",
                              "jolt", "rings_on", "box", "fish", "fish_yaw", "fish_swim", "fish_turn")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        kd = kind_at(t)
        frames["xray"].append(1 if kd == "xray" else 0)
        frames["rings_on"].append(1 if kd in ("xray", "under") or a in ("sing",) else 0)
        b, _ = box_track(t, t_drop)
        frames["box"].append([round(v, 4) for v in b])
        frames["jolt"].append(round(duo.bump(t, t_imp, 0.03, 0.02, 0.35) + 0.4 * duo.bump(t, t_bounce2, 0.03, 0.0, 0.25), 3))
        # trout: hovers calmly; startles when the first hull ring reaches it, bolts away on "there goes the fish"
        st = duo.bump(t, t_hit, 0.06, 0.15, 0.6)
        bolt = duo.ramp(t, t_bolt, 1.6)
        drift = 0.05 * math.sin(t * 0.6)
        x = fx + drift + 0.06 * st - 3.2 * bolt ** 1.6
        z = fz + 0.12 * st + 1.4 * bolt ** 1.6
        frames["fish"].append([round(x, 4), round(fy + 0.02 * math.sin(t * 1.1) + 0.05 * st, 4), round(z, 4)])
        frames["fish_yaw"].append(round(0.0 + 0.5 * st + (math.pi - 0.42) * duo.ramp(t, t_bolt - 0.25, 0.3), 3))
        frames["fish_swim"].append(round(0.22 + 0.5 * st + 0.78 * duo.ramp(t, t_bolt - 0.25, 0.2), 3))
        frames["fish_turn"].append(round(0.6 * duo.bump(t, t_hit, 0.05, 0.08, 0.25), 3))
        frames["look_w"].append("box" if a in ("drop",) or (a == "payoff" and t > at("payoff", "Stomping") - 0.2)
                                else ("fish" if a in ("gone",) else ("water" if a in ("sing",) else "woman")))
        frames["look_m"].append("box" if a in ("drop",) else ("water" if a in ("hook", "bounce", "hull") else "wizard"))
        frames["wiz_wave"].append(round(duo.bump(t, S("sing") - 0.05, 0.25, max(0.3, E("sing") - S("sing") - 0.3), 0.35) * 0.8
                                        + duo.bump(t, S("payoff") + 0.1, 0.3, 0.6, 0.4) * 0.35, 3))
        frames["wiz_point"].append(round(duo.bump(t, at("payoff", "Stomping") - 0.1, 0.3, 1.2, 0.5), 3))
        frames["woman_point"].append(round(duo.bump(t, S("drop") + 0.2, 0.3, 0.9, 0.4) + duo.bump(t, S("hook") + 0.2, 0.3, 1.0, 0.4) * 0.6, 3))
        frames["wiz_blink"].append(1.0 if (t % 3.7) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.1) % 3.3) < 0.12 else 0.0)
    frames["focal_pt"] = duo.focal_track(shots, n)

    cards = [
        {"start": at("bounce", "tenth") - 0.1, "end": S("sing") - 0.15, "big": "≈ 0.1 %", "small": "of the sound gets in", "y": 0.16},
        {"start": at("hull", "four") - 0.1, "end": S("gone") - 0.15, "big": "4.3×", "small": "faster in water", "y": 0.16},
    ]
    events = [(round(hook_c, 3), "whoosh", {"gain": 0.07}),
              (round(t_imp, 3), "thud", {"gain": 0.2}),
              (round(t_bounce2, 3), "thud", {"gain": 0.09}),
              (round(t_bolt, 3), "whoosh", {"gain": 0.09})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [hook_c, at("bounce", "tenth"), t_imp],
               "events": events, "mutes": [], "swells": [S("payoff")]}
    facts = {"impedance_ratio": round(Z_WATER / Z_AIR, 1), "transmitted_pct": round(100 * T_NORMAL, 3),
             "speed_ratio": round(SPEED_RATIO, 2),
             "events": {"box_lands": {"t": t_imp + 0.6, "observe": "box_on_floor", "expect": 1, "tol": 0},
                        "fish_bolts": {"t": dur - 0.3, "observe": "fish_gone", "expect": 1, "tol": 0}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 53, "supersample": 1.0, "bloom_threshold": 3.5,
            "end_hold_s": 1.4,
            "layout": {"boat": BOAT, "clip_y": 0.12 - 0.5 + 0.02, "wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": WOMAN_FACE,
                       "fish_len": FISH_LEN},
            "rings": rings, "speed_ratio": round(SPEED_RATIO, 4),
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    F = plan["frames"]
    if what == "box_on_floor":
        return 1 if abs(F["box"][k][1] - FLOOR_Y) < 0.01 else 0
    if what == "fish_gone":
        return 1 if math.hypot(F["fish"][k][0] - FISH[0], F["fish"][k][2] - FISH[2]) > 2.0 else 0
    if what in F:
        return F[what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 92, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """The impedance ratio, the 0.1 % transmission, the 4.3x speed ratio and the drawn speeds keeping that ratio,
    and the tackle box falling in free fall time."""
    fall_h = BOX_REST[1] - BOX_FLOOR[1]
    return {"water is about 3,600 times harder to push than air": {"pass": 3400 < Z_WATER / Z_AIR < 3800, "detail": f"{Z_WATER / Z_AIR:.0f}x"},
            "about 0.1 % of the sound energy crosses the surface": {"pass": 0.0009 < T_NORMAL < 0.0013, "detail": f"{100 * T_NORMAL:.3f} %"},
            "sound is more than four times faster in water": {"pass": SPEED_RATIO > 4.0, "detail": f"{SPEED_RATIO:.2f}x"},
            "drawn rings keep the real speed ratio": {"pass": abs(V_WATER / V_AIR - SPEED_RATIO) < 1e-9, "detail": f"{V_WATER:.2f} vs {V_AIR:.2f} m/s"},
            "the tackle box falls in free-fall time": {"pass": abs(math.sqrt(2 * fall_h / G) - 0.33) < 0.05, "detail": f"{math.sqrt(2 * fall_h / G):.2f} s for {fall_h:.2f} m"}}
