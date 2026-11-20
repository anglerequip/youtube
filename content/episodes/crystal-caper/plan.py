"""We cooked crystals (rock candy): render plan for the comedy caper (scene renderer/scenes/crystal3d.js).

One diorama world, five sets: the house at night (hook and the loop ending), the kitchen (the syrup, the jar,
the finished candy), the road (the chase at sunset) and the roadside stop at night (the reveal and the
sparks). The dialogue is pre-recorded (storyboard beats carry `audio:`), and each character's mouth follows
the loudness of their own recorded lines, so lip movement is in sync with the voice.

Science on screen comes from factory/simulation_engine/physics/crystal.py: the two solubility cards (CRC
table) and the crystal growth on the string (our model, labelled time-lapse).
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import yaml

from factory import camera as cam
from factory.simulation_engine.physics import crystal as cx

SCENE = "crystal3d"
HERE = Path(__file__).resolve().parent
HOUSE = {"nyx": [0.2, 0.0, 2.6], "car": [1.6, 0.0, -0.1], "wizard": [-1.55, 0.0, 0.2], "cop": [-2.35, 0.0, 0.55]}
KITCHEN = {"island": [40.0, 0.0, 0.0], "pot": [39.85, 0.0, 0.0], "jar": [40.5, 0.0, 0.15],
           "wizard": [39.85, 0.0, -0.72], "nyx": [40.98, 0.0, 0.66], "candy": [40.5, 0.0, 0.1]}
TOP = 0.92                        # island worktop height
ROAD_X = 100.0
STOP = {"car": [102.0, 0.0, -306.0], "cop_car": [102.0, 0.0, -292.0], "wizard": [103.7, 0.0, -300.2],
        "nyx": [103.6, 0.0, -299.3], "cop": [103.3, 0.0, -298.3]}
COP_YAW, WIZ_YAW, NYX_YAW = -math.pi / 2 - 0.5, -math.pi / 2 + 0.4, -math.pi / 2 + 0.3
DARK = [300.0, 0.0, 0.0]            # a dark table for the triboluminescence close-up (a really dark room)
SPEED = 15.0                      # chase speed, m/s


def _front(p, yaw, dist, h, side=0.0):
    """A camera point `dist` in front of a figure at p facing `yaw` (three.js: facing (sin yaw, cos yaw)), shifted sideways."""
    fx, fz = math.sin(yaw), math.cos(yaw)
    return [round(p[0] + fx * dist - fz * side, 3), h, round(p[2] + fz * dist + fx * side, 3)]


def _speakers() -> dict:
    sb = yaml.safe_load((HERE / "storyboard.yaml").read_text(encoding="utf-8"))
    return {b["id"]: (b.get("speaker"), b.get("audio")) for b in sb["beats"]}


def _envelope(path: Path, fps: int) -> np.ndarray:
    """Mouth opening per video frame from a recorded line (trimmed the same way narrate() trims it)."""
    sr = 24000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    idx = np.nonzero(np.abs(x) > 0.01)[0]
    if len(idx):
        x = x[max(0, idx[0] - int(0.03 * sr)): idx[-1] + int(0.03 * sr)]
    hop = sr // fps
    rms = np.array([float(np.sqrt(np.mean(x[i:i + hop] ** 2))) for i in range(0, max(1, len(x) - hop), hop)])
    if rms.max() <= 0:
        return rms
    v = np.clip(rms / (0.55 * rms.max()), 0, 1) ** 0.7
    return np.convolve(v, [0.25, 0.5, 0.25], mode="same")


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    S, E = tl.start, tl.end
    n = int(math.ceil((tl.duration + 0.05) * fps))
    T = np.arange(n) / fps
    f = cx.facts()

    # ---- lip sync: each speaker's mouth follows their own recorded lines
    talk = {k: np.zeros(n) for k in ("wizard", "nyx", "cop")}
    for bid, (who, audio) in _speakers().items():
        if who in talk and audio and (HERE / audio).exists():
            env = _envelope(HERE / audio, fps)
            i0 = int(round(S(bid) * fps))
            m = min(len(env), n - i0)
            if m > 0:
                talk[who][i0:i0 + m] = np.maximum(talk[who][i0:i0 + m], env[:m])
    rng = np.random.default_rng(4)
    blinks = {k: sorted(rng.uniform(0, tl.duration, int(tl.duration / 3.1))) for k in talk}

    # ---- story moments
    grow0, grow1 = S("howlong") - 0.2, E("week") + 0.6          # time-lapse growth on the string
    heat_off = S("cool") + 0.2                                  # the pot comes off the heat
    crunch = S("spark") - 0.05                                   # the cop bites the candy
    spark_ev = [round(crunch + d, 3) for d in (0.0, 0.07, 0.19, 0.33, 0.52, 0.9, 1.35, 1.6, 2.1)]
    t_tribo2 = round(S("tribo") + 1.6, 3)                       # cut to the dark close-up after "Triboluminescence."
    crack2 = round(S("tribo") + 1.95, 3)                        # on "Crack": the crystal splits
    tribo_sparks = [round(crack2 + d, 3) for d in (0.0, 0.3, 1.3, 1.85, 2.6, 4.7)]   # at most ~3 per second, no strobe
    frames = {k: [] for k in ("talk_w", "talk_n", "talk_c", "blink_w", "blink_n", "blink_c", "grow", "steam",
                               "set", "badge", "bite", "split")}
    sets = [("house", 0.0), ("kitchen", S("rule") - 0.1), ("road", S("run") - 0.1), ("stop", S("candy") - 0.1),
            ("dark", t_tribo2), ("stop", S("makeme") - 0.1), ("house", S("end") - 0.1)]
    for k, t in enumerate(T):
        frames["talk_w"].append(round(float(talk["wizard"][k]), 3))
        frames["talk_n"].append(round(float(talk["nyx"][k]), 3))
        frames["talk_c"].append(round(float(talk["cop"][k]), 3))
        for who, key in (("wizard", "blink_w"), ("nyx", "blink_n"), ("cop", "blink_c")):
            b = min((abs(t - x) for x in blinks[who]), default=9)
            frames[key].append(1.0 if b < 0.06 else 0.0)
        days = cx.WEEK_DAYS * cam.ease((t - grow0) / (grow1 - grow0)) if t > grow0 else 0.0
        frames["grow"].append(round(cx.crystal_scale(days) if days > 0 else 0.0, 4))
        frames["steam"].append(1.0 if t < heat_off else round(max(0.0, 1 - (t - heat_off) / 2.5), 3))
        frames["set"].append([s for s, t0 in sets if t >= t0][-1])
        frames["bite"].append(round(min(1.0, max(0.0, (t - crunch + 0.25) / 0.25)), 3) if t < crunch + 0.6 else
                              round(max(0.0, 1 - (t - crunch - 0.6) / 0.3), 3))
        frames["split"].append(round(min(1.0, max(0.0, (t - crack2) / 0.25)), 3))
        b = ""
        if S("rule") - 0.1 <= t < S("hot") - 0.1:
            b = "8 DAYS EARLIER"
        elif grow0 <= t < S("week") - 0.1:
            b = "TIME-LAPSE, ONE WEEK"
        elif S("faces") - 0.1 <= t < S("faces") + 2.4:
            b = "1 WEEK LATER"
        elif S("spark") - 0.1 <= t < S("makeme") - 0.1:
            b = "FLASHES DRAWN BRIGHTER"
        frames["badge"].append(b)

    K = lambda *a: list(a)
    hx, hz = HOUSE["nyx"][0], HOUSE["nyx"][2]
    kx, kz = KITCHEN["island"][0], KITCHEN["island"][2]
    px, pz = KITCHEN["pot"][0], KITCHEN["pot"][2]
    jx, jz = KITCHEN["jar"][0], KITCHEN["jar"][2]
    wx, wz = KITCHEN["wizard"][0], KITCHEN["wizard"][2]
    nx, nz = KITCHEN["nyx"][0], KITCHEN["nyx"][2]
    sx, sz = STOP["wizard"][0], STOP["wizard"][2]
    cx_, cz_ = STOP["cop"][0], STOP["cop"][2]
    end_t = n / fps + 0.05
    t_run = S("run") - 0.1
    t_faces2 = round(S("faces") + 0.45 * (E("faces") - S("faces")), 3)
    z_car = lambda t: -40.0 - SPEED * (t - t_run)       # their car, driving towards -z
    road_subject = lambda i: [0.0, 0.0, z_car(i / fps)]  # road shots ride along with the cars (no easing lag)
    shots = cam.chain([
        # hook: night, Nyx in the front yard, the police car's lights sweeping the house; slow push in
        cam.shot(0.0, S("rule") - 0.1, [(0.0, K(hx + 0.75, 1.62, hz + 3.6), K(hx + 0.6, 1.3, hz - 0.4), 46),
                                        (S("rule") - 0.1, K(hx + 0.65, 1.6, hz + 2.9), K(hx + 0.55, 1.32, hz - 0.4), 46)], fps, "night"),
        # rule + sugar: the kitchen in daylight, wizard over the pot, Nyx leaning on the island
        cam.shot(S("rule") - 0.1, S("hot") - 0.1, [(S("rule") - 0.1, K(kx + 0.35, 1.7, kz + 4.4), K(kx + 0.42, 1.2, kz - 0.1), 40),
                                                   (S("hot") - 0.1, K(kx + 0.55, 1.68, kz + 4.0), K(kx + 0.45, 1.2, kz - 0.1), 40)], fps, "key"),
        # hot: close on the steaming pot and the sugar bag
        cam.shot(S("hot") - 0.1, S("cool") - 0.1, [(S("hot") - 0.1, K(px + 0.55, TOP + 0.55, pz + 0.95), K(px + 0.05, TOP + 0.12, pz), 40),
                                                   (S("cool") - 0.1, K(px + 0.35, TOP + 0.5, pz + 0.8), K(px + 0.02, TOP + 0.12, pz), 40)], fps, "key"),
        # cool: the pot off the heat, steam dying away
        cam.shot(S("cool") - 0.1, S("stressed") - 0.1, [(S("cool") - 0.1, K(px - 0.6, TOP + 0.6, pz + 0.85), K(px + 0.05, TOP + 0.1, pz), 40),
                                                        (S("stressed") - 0.1, K(px - 0.45, TOP + 0.52, pz + 0.75), K(px + 0.05, TOP + 0.1, pz), 40)], fps, "key"),
        # stressed + super: the two of them, a tighter two-shot
        cam.shot(S("stressed") - 0.1, S("string") - 0.1, [(S("stressed") - 0.1, K(kx + 0.7, 1.62, kz + 3.5), K(kx + 0.45, 1.42, kz - 0.05), 40),
                                                          (S("string") - 0.1, K(kx + 0.55, 1.62, kz + 3.2), K(kx + 0.45, 1.44, kz - 0.05), 40)], fps, "key"),
        # string + howlong: macro on the jar, the string hanging in the syrup; growth starts (time-lapse)
        cam.shot(S("string") - 0.1, S("week") - 0.1, [(S("string") - 0.1, K(jx + 0.32, TOP + 0.24, jz + 0.42), K(jx, TOP + 0.12, jz), 40),
                                                      (S("week") - 0.1, K(jx + 0.2, TOP + 0.22, jz + 0.34), K(jx, TOP + 0.11, jz), 40)], fps, "key"),
        # week: Nyx, close, staring into the camera
        cam.shot(S("week") - 0.1, S("faces") - 0.1, [(S("week") - 0.1, K(nx - 0.25, 1.52, nz + 1.15), K(nx - 0.05, 1.5, nz), 36),
                                                     (S("faces") - 0.1, K(nx - 0.22, 1.52, nz + 1.0), K(nx - 0.05, 1.5, nz), 36)], fps, "key"),
        # faces: the finished rock candy, flat shiny faces, slow orbit
        cam.shot(S("faces") - 0.1, t_faces2, [(S("faces") - 0.1, K(kx + 0.85, TOP + 0.3, kz + 0.72), K(kx + 0.5, TOP + 0.13, kz + 0.1), 36),
                                              (t_faces2, K(kx + 0.55, TOP + 0.31, kz + 0.78), K(kx + 0.5, TOP + 0.13, kz + 0.1), 36)], fps, "golden"),
        # faces, second half: macro on the flat faces as the wizard explains the stacking
        cam.shot(t_faces2, S("run") - 0.1, [(t_faces2, K(kx + 0.42, TOP + 0.2, kz + 0.4), K(kx + 0.5, TOP + 0.14, kz + 0.1), 34),
                                            (S("run") - 0.1, K(kx + 0.6, TOP + 0.21, kz + 0.38), K(kx + 0.5, TOP + 0.14, kz + 0.1), 34)], fps, "golden"),
        # run + habit: chase cam behind the police car, their little car ahead, sunset
        cam.shot(t_run, S("pull") - 0.1, [(t_run, K(ROAD_X + 1.9, 3.2, 24.0), K(ROAD_X + 1.8, 0.9, -2), 40),
                                          (S("pull") - 0.1, K(ROAD_X + 1.9, 3.0, 22.5), K(ROAD_X + 1.8, 0.9, -2), 40)], fps, "sunset",
                 subject=road_subject),
        # pull: low, ahead of the police car, looking back at its lights (moves with the cars)
        cam.shot(S("pull") - 0.1, S("candy") - 0.1, [(S("pull") - 0.1, K(ROAD_X + 1.1, 1.15, 2.6), K(ROAD_X + 1.8, 1.0, 12.0), 40),
                                                     (S("candy") - 0.1, K(ROAD_X + 1.1, 1.15, 3.2), K(ROAD_X + 1.8, 1.0, 12.0), 40)], fps, "sunset",
                 subject=road_subject),
        # candy + told: roadside at night, the cop holds up one pink stick in his torch beam
        cam.shot(S("candy") - 0.1, S("spark") - 0.1, [(S("candy") - 0.1, K(*_front(STOP["cop"], COP_YAW, 1.9, 1.5, -0.05)), K(*_front(STOP["cop"], COP_YAW, 0.0, 1.4, -0.2)), 40),
                                                      (S("spark") - 0.1, K(*_front(STOP["cop"], COP_YAW, 1.65, 1.48, -0.05)), K(*_front(STOP["cop"], COP_YAW, 0.0, 1.4, -0.2)), 40)], fps, "night"),
        # spark: close on the cop biting the candy in the dark
        cam.shot(S("spark") - 0.1, S("tribo") - 0.1, [(S("spark") - 0.1, K(*_front(STOP["cop"], COP_YAW, 0.8, 1.7, 0.08)), K(cx_, 1.66, cz_), 38),
                                                      (S("tribo") - 0.1, K(*_front(STOP["cop"], COP_YAW, 0.68, 1.69, 0.06)), K(cx_, 1.66, cz_), 38)], fps, "night"),
        # tribo: the wizard explains, lit by the police lights
        cam.shot(S("tribo") - 0.1, t_tribo2, [(S("tribo") - 0.1, K(*_front(STOP["wizard"], WIZ_YAW, 1.5, 1.78, -0.25)), K(sx, 1.58, sz), 38),
                                              (t_tribo2, K(*_front(STOP["wizard"], WIZ_YAW, 1.35, 1.77, -0.22)), K(sx, 1.58, sz), 38)], fps, "night"),
        # tribo, the payoff: a sugar crystal cracking in a dark room, a spark jumping the gap (macro)
        cam.shot(t_tribo2, S("makeme") - 0.1, [(t_tribo2, K(DARK[0] + 0.06, 1.02, DARK[2] + 0.5), K(DARK[0], 0.93, DARK[2]), 32),
                                               (S("makeme") - 0.1, K(DARK[0] + 0.03, 1.0, DARK[2] + 0.4), K(DARK[0], 0.93, DARK[2]), 32)], fps, "night"),
        # makeme: the cop, sheepish
        cam.shot(S("makeme") - 0.1, S("end") - 0.1, [(S("makeme") - 0.1, K(*_front(STOP["cop"], COP_YAW, 1.15, 1.68, 0.15)), K(cx_, 1.6, cz_), 38),
                                                     (S("end") - 0.1, K(*_front(STOP["cop"], COP_YAW, 1.0, 1.67, 0.12)), K(cx_, 1.6, cz_), 38)], fps, "night"),
        # end: back at the house, the same frame as the hook (the loop); the cop and the wizard by the door
        cam.shot(S("end") - 0.1, end_t, [(S("end") - 0.1, K(hx + 0.65, 1.6, hz + 2.9), K(hx + 0.55, 1.32, hz - 0.4), 46),
                                         (end_t, K(hx + 0.75, 1.62, hz + 3.6), K(hx + 0.6, 1.3, hz - 0.4), 46)], fps, "night"),
    ])
    # the focal point per frame (who or what the shot is about), for QC and the near plane
    focus = [
        (S("rule") - 0.1, [hx, 1.45, hz]),
        (S("hot") - 0.1, [kx + 0.5, 1.3, kz - 0.2]),
        (S("cool") - 0.1, [px, TOP + 0.12, pz]),
        (S("stressed") - 0.1, [px, TOP + 0.1, pz]),
        (S("string") - 0.1, [kx + 0.5, 1.42, kz - 0.2]),
        (S("week") - 0.1, [jx, TOP + 0.12, jz]),
        (S("faces") - 0.1, [nx - 0.05, 1.5, nz]),
        (t_faces2, [kx + 0.5, TOP + 0.13, kz + 0.1]),
        (t_run, [kx + 0.5, TOP + 0.14, kz + 0.1]),
        (S("candy") - 0.1, None),                       # road: follows the cars
        (S("spark") - 0.1, [cx_, 1.4, cz_]),
        (S("tribo") - 0.1, [cx_, 1.66, cz_]),
        (t_tribo2, [sx, 1.58, sz]),
        (S("makeme") - 0.1, [DARK[0], 0.93, DARK[2]]),
        (S("end") - 0.1, [cx_, 1.6, cz_]),
        (1e9, [hx, 1.45, hz]),
    ]
    fp = []
    for t in T:
        p = next(v for t1, v in focus if t < t1)
        fp.append(p if p is not None else [ROAD_X + 1.8, 1.0, round(z_car(t) + 6.0, 3)])
    frames["focal_pt"] = fp

    cards = [
        {"start": S("hot") + 2.2, "end": S("cool") - 0.15, "big": "≈ 4.9 ×", "small": "its weight in sugar, 100 °C", "y": 0.17},
        {"start": S("cool") + 1.2, "end": S("stressed") - 0.15, "big": "≈ 2 ×", "small": "at 20 °C: the rest is extra", "y": 0.17},
    ]
    events = [(0.05, "siren", {"gain": 0.09, "dur": round(S("rule") - 0.3, 2), "near": 0.15}),
              (round(t_run, 3), "siren", {"gain": 0.07, "dur": round(S("candy") - 0.4 - t_run, 2), "near": 0.35, "seed": 23}),
              (round(S("end") - 0.05, 3), "siren", {"gain": 0.08, "dur": round(E("end") - S("end") + 1.0, 2), "near": 0.15, "seed": 29}),
              (round(S("rule") - 0.1, 3), "swish", {"gain": 0.18}),
              (round(grow0 + 0.3, 3), "rise", {"gain": 0.22, "dur": 1.6}),
              (round(S("faces") - 0.05, 3), "ding", {"gain": 0.2}),
              (round(t_run, 3), "swish", {"gain": 0.16}),
              (round(S("candy") - 0.25, 3), "impact", {"gain": 0.25, "speed": 1.2}),
              (round(crunch, 3), "crack", {"gain": 0.2, "size": 0.6, "seed": 31}),
              (crack2, "crack", {"gain": 0.3, "size": 1.0, "seed": 37})]
    timing = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [S("candy"), crunch], "events": events,
              "mutes": [(S("candy") - 0.2, S("candy") + 1.4)], "swells": [S("run"), S("end")],
              "sparks": spark_ev, "tribo_sparks": tribo_sparks, "crack2": crack2, "t_run": t_run, "speed": SPEED, "z0": -40.0, "crunch": crunch}
    facts = dict(f)
    facts.update({"slow_factors": [], "days_card": 8.0,
                  "events": {"crystals_grown": {"t": round(grow1 + 0.2, 2), "observe": "grow", "expect": 1.0, "tol": 0.02}}})
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 23, "supersample": 1.0,
            "bloom_threshold": 3.2, "end_hold_s": 1.2,
            "layout": {"yaw": {"cop": COP_YAW, "wizard": WIZ_YAW, "nyx": NYX_YAW}, "house": HOUSE, "kitchen": KITCHEN, "top": TOP, "road_x": ROAD_X, "stop": STOP, "dark": DARK},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what == "grow":
        return plan["frames"]["grow"][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 104, "gain": 0.09}


def self_checks() -> dict:
    return cx.self_checks()
