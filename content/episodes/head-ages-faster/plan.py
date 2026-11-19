"""Your head is older than your feet: render plan from gravitational time dilation
(factory/simulation_engine/physics/time_dilation.py; the three.js scene is renderer/scenes/clocks3d.js).

The real effect (about 1e-16 per metre) is invisible, so two things are kept strictly apart:
  * every NUMBER on screen is the real value from the physics module (counters, cards, claims);
  * the PICTURE exaggerates the rate difference (clock pulses and hands), always under an
    "EXAGGERATED" badge, and time-lapses carry a badge too.

One small diorama world holds every set: a wooden toy figure next to a post with a clock at head height and
one at its feet, a tall mast with clocks at four heights, two atomic clocks on tables (one is jacked up
33 cm, as at NIST in 2010), and a road with one car under a toy GPS satellite (not to scale).
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam
from factory.simulation_engine.physics import time_dilation as td

SCENE = "clocks3d"
# world layout (metres); the scene reads these from the plan, so plan and renderer agree
FIG = [0.0, 0.0, 0.0]
POST_X = 0.62
HEAD_CLK = [POST_X, 1.62, 0.16]
FEET_CLK = [POST_X, 0.17, 0.16]
TOWER = [-12.0, 0.0, -14.0]
TOWER_YS = [2.0, 9.0, 16.0, 23.0]
LAB = [7.0, 0.0, -4.0]                 # between the two tables
TABLE_DX = 0.48
TABLE_TOP = 0.76
ROAD_X = 18.0
SAT = [ROAD_X - 4.0, 19.0, -34.0]       # relative to the car (x absolute), toy scale
EXAG = 0.30                            # exaggerated visual rate difference for the 1.55 m head-feet gap


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    end_hold = 1.0
    n = int(math.ceil((tl.duration + 0.05) * fps))      # tl.duration already holds end_hold_s after the last word
    T = np.arange(n) / fps
    f = td.facts()
    at = lambda b, w: timing.word_time(tl, b, w)

    # ---- moments, all from the narration
    lift0, lift1 = at("proof", "raised"), at("proof", "raised") + 1.4          # the table jacks up 33 cm
    life0 = S("lifetime") + 0.4                                                # time-lapse: 0 -> 80 years
    life1 = max(life0 + 3.0, E("lifetime") - 0.3)
    day0 = S("drift") + 0.2                                                    # uncorrected GPS: 0 -> 24 hours
    day1 = max(day0 + 2.2, E("drift") + 0.2)
    exag_on = lambda t: (t < S("why")) or (S("feet") <= t < E("small"))        # figure clocks exaggerated

    frames = {k: [] for k in ("head", "feet", "tower", "lab", "lift", "car_z", "pin", "years", "ns", "hours",
                              "err_km", "badge", "focal_pt", "warm")}
    head = feet = 0.0
    tower = [0.0] * 4
    lab = [0.0, 0.0]
    car_z = 20.0
    for i, t in enumerate(T):
        dt = 1 / fps
        # figure clocks: seconds shown. Exaggerated: head 1.0x, feet (1 - EXAG)x. Time-lapse: hands race.
        if life0 <= t < life1 + 0.6:
            rate = 9.0 * (1 - cam.ease((t - life1) / 0.6)) if t >= life1 else 9.0 * cam.ease((t - life0) / 0.5)
            head += rate * 60 * dt; feet += rate * 60 * dt          # minute hands spin; difference far too small to draw
        else:
            k = 1.0 if exag_on(t) else 0.0
            head += dt; feet += dt * (1 - EXAG * k)
        frames["head"].append(round(head, 4)); frames["feet"].append(round(feet, 4))
        # mast clocks (why beat): exaggerated, rate rises with height
        for j, y in enumerate(TOWER_YS):
            tower[j] += dt * (0.55 + 0.6 * (y - TOWER_YS[0]) / (TOWER_YS[-1] - TOWER_YS[0]))
        frames["tower"].append([round(v, 4) for v in tower])
        # lab clocks: equal until the lift, then the raised one pulses faster (exaggerated)
        lift = 0.33 * cam.ease((t - lift0) / (lift1 - lift0)) if t >= lift0 else 0.0
        frames["lift"].append(round(lift, 4))
        lab[0] += dt * 1.1
        lab[1] += dt * 1.1 * (1 + 1.1 * lift)
        frames["lab"].append([round(v, 4) for v in lab])
        # time-lapse counters (real values)
        u_life = min(1.0, max(0.0, (t - life0) / (life1 - life0)))
        u_life = u_life * u_life * (3 - 2 * u_life) * 0.25 + u_life * 0.75
        yrs = td.LIFE_YEARS * u_life
        frames["years"].append(round(yrs, 3))
        frames["ns"].append(round(td.head_ahead(yrs * td.YEAR) * 1e9, 3))
        u_day = min(1.0, max(0.0, (t - day0) / (day1 - day0)))
        hrs = 24 * u_day
        frames["hours"].append(round(hrs, 3))
        frames["err_km"].append(round(f["gps_km_per_day"] * hrs / 24, 4))
        # car on the road (drives towards -z), the map pin drifts ahead of it (not to scale)
        car_z -= dt * 11.0
        frames["car_z"].append(round(car_z, 3))
        frames["pin"].append(round(30.0 * u_day, 3))
        # warm glow on the head clock / cool on the feet clock while the figure's clocks are exaggerated
        frames["warm"].append(1.0 if exag_on(t) else 0.0)
        # badges: the picture exaggerates or speeds up time; numbers never do
        if t < S("why") or S("feet") <= t < E("small") or S("why") <= t < S("feet") or \
                (lift0 <= t < E("proof")):
            b = "EXAGGERATED"
        elif life0 <= t < life1 + 0.6:
            b = "TIME-LAPSE"
        elif S("gps") <= t < day0:
            b = "NOT TO SCALE"
        elif t >= day0:
            b = "TIME-LAPSE, NOT TO SCALE"
        else:
            b = ""
        frames["badge"].append(b)

    # ---- shots (each beat its own angle; every shot moves a little)
    K = lambda *a: list(a)
    hx, hy, hz = HEAD_CLK
    tx, _, tz = TOWER
    lx, _, lz = LAB
    car = lambda i: (ROAD_X - 1.8, 0.0, frames["car_z"][min(i, n - 1)])
    shots = cam.chain([
        # hook: already moving, low and close, the figure and both clocks fill the middle third
        cam.shot(0.0, S("why") - 0.1, [(0.0, K(1.9, 1.05, 3.1), K(0.3, 0.9, 0.0), 40),
                                       (S("why") - 0.1, K(1.55, 1.0, 2.55), K(0.32, 0.9, 0.0), 40)], fps, "key"),
        # why: the mast, looking up its clocks; slow crane up
        cam.shot(S("why") - 0.1, S("feet") - 0.1, [(S("why") - 0.1, K(tx + 9.0, 3.5, tz + 27.0), K(tx, 12.6, tz), 46),
                                                   (S("feet") - 0.1, K(tx + 7.5, 5.0, tz + 25.0), K(tx, 12.8, tz), 46)], fps, "key"),
        # feet: crane down the figure from head clock to feet clock
        cam.shot(S("feet") - 0.1, S("small") - 0.1, [(S("feet") - 0.1, K(2.1, 1.7, 3.7), K(0.6, 1.15, 0.0), 40),
                                                     (S("small") - 0.1, K(2.0, 0.95, 3.4), K(0.62, 0.8, 0.0), 40)], fps, "key"),
        # small: close and low on the feet clock
        cam.shot(S("small") - 0.1, S("proof") - 0.1, [(S("small") - 0.1, K(1.25, 0.32, 1.25), K(POST_X - 0.1, 0.3, 0.1), 38),
                                                      (S("proof") - 0.1, K(1.1, 0.3, 1.05), K(POST_X - 0.1, 0.28, 0.1), 38)], fps, "golden"),
        # proof: the two atomic clocks; one table jacks up 33 cm
        cam.shot(S("proof") - 0.1, S("lifetime") - 0.1, [(S("proof") - 0.1, K(lx + 1.1, 1.65, lz + 4.8), K(lx - 0.1, 1.05, lz), 44),
                                                         (S("lifetime") - 0.1, K(lx + 0.6, 1.55, lz + 4.4), K(lx - 0.15, 1.1, lz), 44)], fps, "key"),
        # lifetime: wide 3/4 on the figure while 80 years pass
        cam.shot(S("lifetime") - 0.1, S("gps") - 0.1, [(S("lifetime") - 0.1, K(-2.4, 2.1, 3.6), K(0.2, 0.85, 0.0), 40),
                                                       (S("gps") - 0.1, K(-1.6, 1.8, 3.9), K(0.25, 0.85, 0.0), 40)], fps, "golden"),
        # gps: from behind the car, crane up to the satellite overhead
        cam.shot(S("gps") - 0.1, S("drift") - 0.1, [(S("gps") - 0.1, K(-1.4, 3.0, 14.0), K(0.0, 5.0, -20.0), 50),
                                                    (S("drift") - 0.1, K(-1.4, 3.2, 13.0), K(-1.0, 14.0, -30.0), 50)], fps, "key", car),
        # drift: high 3/4 aerial over the road, the map pin slides away from the car
        cam.shot(S("drift") - 0.1, n / fps + 0.05, [(S("drift") - 0.1, K(7.0, 13.0, 16.0), K(0.0, 0.0, -14.0), 44),
                                                    (n / fps, K(8.0, 17.0, 19.0), K(0.5, 0.0, -24.0), 44)], fps, "key", car),
    ])
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            i = s_["i0"] + k
            if 0 <= i < n and len(frames["focal_pt"]) <= i:
                frames["focal_pt"].append(lk)
    while len(frames["focal_pt"]) < n:
        frames["focal_pt"].append(frames["focal_pt"][-1])
    frames["focal_pt"] = frames["focal_pt"][:n]

    cards = [
        {"start": at("small", "about") , "end": S("proof") - 0.1, "big": "≈ 10⁻¹⁶", "small": "slower, per metre of height", "y": 0.17},
        {"start": at("proof", "faster") - 0.2, "end": S("lifetime") - 0.15, "big": "NIST, 2010",
         "small": "the higher clock ran faster", "y": 0.17},
        {"start": at("gps", "forty-five"), "end": S("drift") - 0.1, "big": "≈ +45 µs a day",
         "small": "GPS clocks, from gravity alone", "y": 0.17},
    ]
    events = [
        (round(lift1 - 0.05, 3), "thud", {"gain": 0.25, "speed": 0.7}),          # the jack stops: table up 33 cm
        (round(S("gps") - 0.35, 3), "swish", {"gain": 0.22, "seed": 17}),         # crane up to the sky
    ]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [lift0, life0, day0], "events": events,
               "mutes": [], "swells": [life0], "lifetime": [life0, life1], "day": [day0, day1], "lift": [lift0, lift1]}
    facts = dict(f)
    facts.update({"nist_cm": 33.0, "slow_factors": [],
                  "events": {"lift_33cm": {"t": lift1 + 0.1, "observe": "lift_cm", "expect": 33.0, "tol": 0.01},
                             "life_ns": {"t": life1 + 0.05, "observe": "ns", "expect": f["lifetime_ns"], "tol": 0.01}}})
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 21, "supersample": 1.0,
            "bloom_threshold": 50.0, "end_hold_s": end_hold,
            "layout": {"fig": FIG, "head_clk": HEAD_CLK, "feet_clk": FEET_CLK, "post_x": POST_X, "tower": TOWER,
                       "tower_ys": TOWER_YS, "lab": LAB, "table_dx": TABLE_DX, "table_top": TABLE_TOP,
                       "road_x": ROAD_X, "sat": SAT},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what == "lift_cm":
        return plan["frames"]["lift"][k] * 100
    if what == "ns":
        return plan["frames"]["ns"][k]
    raise KeyError(what)


def hud_anchors(plan: dict) -> dict:
    """World points the HUD measures: head clock / feet clock (1.7 m line beside the figure) and the
    two atomic clocks' tops (the 33 cm lift)."""
    F, n = plan["frames"], plan["n_frames"]
    lx, _, lz = LAB
    top = TABLE_TOP + 0.32
    return {
        "head_mark": [[POST_X + 0.32, 1.72, 0.1]] * n,
        "feet_mark": [[POST_X + 0.32, 0.06, 0.1]] * n,
        "lab_low": [[lx - TABLE_DX + 0.3, top, lz + 0.32]] * n,
        "lab_high": [[lx - TABLE_DX + 0.3, round(top + F["lift"][i], 4), lz + 0.32] for i in range(n)],
    }


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 88, "gain": 0.15}


def self_checks() -> dict:
    return td.self_checks()
