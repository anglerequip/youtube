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
FEET_CLK = [POST_X, 0.27, 0.16]            # clear of the patio (picture review, round 1)
TOWER = [-12.0, 0.0, -14.0]
TOWER_YS = [2.0, 7.0, 12.0, 17.0]          # mast is 19 m (round 2: all four clocks clear of badge and captions)
LAB = [7.0, 0.0, -4.0]                 # between the two tables
TABLE_DX = 0.48
TABLE_TOP = 0.76
ROAD_X = 18.0
SAT = [ROAD_X - 1.0, 19.0, -34.0]       # relative to the car (x absolute), toy scale
EXAG = 0.5                             # exaggerated: the feet clock runs at half the head clock's rate
SPEEDUP = 8.0                          # exaggerated clocks also run fast, so the gap is visible within seconds
HEAD_LEAD = 9.0                        # the head clock starts ahead (frame 0 already shows the difference)


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
    close_nist = at("proof", "And") - 0.15                                     # cut to the two readouts
    life0 = S("lifetime") + 0.4                                                # time-lapse: 0 -> 80 years
    life1 = max(life0 + 3.0, E("lifetime") - 0.3)
    gps_close = at("gps", "their") - 0.1                                     # cut up to the satellite
    day0 = S("drift") + 0.2                                                    # uncorrected GPS: 0 -> 24 hours
    day1 = max(day0 + 2.2, E("drift") + 0.2)
    exag_on = lambda t: (t < S("why")) or (S("feet") <= t < E("small"))        # figure clocks exaggerated

    frames = {k: [] for k in ("head", "feet", "tower", "lab", "lift", "car_z", "pin", "years", "ns", "hours",
                              "err_km", "badge", "focal_pt", "warm", "set", "readout", "lab_readout", "sat_dx", "sat_clk", "sat_readout")}
    head, feet = HEAD_LEAD, 0.0
    tower = [0.0] * 4
    lab = [0.0, 0.0]
    gps_clk = [0.0, 0.0]                       # satellite, ground (exaggerated: the satellite clock runs 1.5x)
    car_z = 20.0
    for i, t in enumerate(T):
        dt = 1 / fps
        # figure clocks: seconds shown. Exaggerated: head 1.0x, feet (1 - EXAG)x. Time-lapse: hands race.
        if life0 <= t < life1 + 0.6:
            rate = 9.0 * (1 - cam.ease((t - life1) / 0.6)) if t >= life1 else 9.0 * cam.ease((t - life0) / 0.5)
            head += rate * 60 * dt; feet += rate * 60 * dt          # minute hands spin; difference far too small to draw
        else:
            k = 1.0 if exag_on(t) else 0.0
            head += dt * (SPEEDUP if k else 1.0); feet += dt * ((1 - EXAG) * SPEEDUP if k else 1.0)
        frames["head"].append(round(head, 4)); frames["feet"].append(round(feet, 4))
        # mast clocks (why beat): exaggerated, rate rises with height
        for j, y in enumerate(TOWER_YS):
            tower[j] += dt * (0.55 + 0.6 * (y - TOWER_YS[0]) / (TOWER_YS[-1] - TOWER_YS[0]))
        frames["tower"].append([round(v, 4) for v in tower])
        # lab clocks: equal until the lift, then the raised one pulses faster (exaggerated)
        lift = 0.33 * cam.ease((t - lift0) / (lift1 - lift0)) if t >= lift0 else 0.0
        frames["lift"].append(round(lift, 4))
        lab[0] += dt * 1.1 * (1 + 1.1 * lift)       # [0] is the LIFTED clock (left table): it runs faster
        lab[1] += dt * 1.1
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
        frames["err_km"].append(round(f["gps_km_per_day"] * hrs / 24, 4))   # net 38.6 µs/day x c (as narrated)
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
        # in-world readouts beside each pair of clocks (round 2 review: the gap must be readable at phone size)
        mmss = lambda x: f"{int(x // 60)}:{x % 60:04.1f}"
        frames["readout"].append([mmss(head), mmss(feet)] if exag_on(t) else None)
        frames["lab_readout"].append([mmss(lab[0]), mmss(lab[1])])
        if t >= S("gps"):
            gps_clk[0] += dt * 1.5 * 3; gps_clk[1] += dt * 3
        frames["sat_clk"].append([round(v, 4) for v in gps_clk])
        frames["sat_readout"].append([mmss(gps_clk[0]), mmss(gps_clk[1])] if S("gps") - 0.1 <= t < S("drift") - 0.1 else None)
        frames["sat_dx"].append(round(-3.0 + 2.2 * cam.ease((t - S("gps")) / max(1.0, E("gps") - S("gps"))), 3))

    # ---- shots (each beat its own angle; every shot moves a little)
    K = lambda *a: list(a)
    hx, hy, hz = HEAD_CLK
    tx, _, tz = TOWER
    lx, _, lz = LAB
    car = lambda i: (ROAD_X - 1.8, 0.0, frames["car_z"][min(i, n - 1)])
    shots = cam.chain([
        # hook: already moving; the whole figure and both clocks (with their readouts) above the caption band
        cam.shot(0.0, S("why") - 0.1, [(0.0, K(2.3, 1.55, 4.6), K(0.3, 0.62, 0.0), 40),
                                       (S("why") - 0.1, K(1.95, 1.5, 4.1), K(0.32, 0.64, 0.0), 40)], fps, "key"),
        # why: the mast, looking up its four clocks; slow crane up
        cam.shot(S("why") - 0.1, S("feet") - 0.1, [(S("why") - 0.1, K(tx + 9.0, 4.0, tz + 34.0), K(tx, 6.6, tz), 46),
                                                   (S("feet") - 0.1, K(tx + 7.5, 4.6, tz + 33.0), K(tx, 7.0, tz), 46)], fps, "key"),
        # feet: crane down the figure from head clock to feet clock, measuring line beside the post
        cam.shot(S("feet") - 0.1, S("small") - 0.1, [(S("feet") - 0.1, K(2.6, 1.85, 5.0), K(0.7, 0.85, 0.0), 40),
                                                     (S("small") - 0.1, K(2.6, 1.3, 4.9), K(0.8, 0.72, 0.0), 40)], fps, "key"),
        # small: low from the side of the post, both clocks and their readouts stacked
        cam.shot(S("small") - 0.1, S("proof") - 0.1, [(S("small") - 0.1, K(3.4, 1.0, 3.6), K(POST_X, 0.99, 0.1), 46),
                                                      (S("proof") - 0.1, K(3.25, 0.95, 3.8), K(POST_X, 1.0, 0.1), 46)], fps, "golden"),
        # proof 1: both atomic clocks on their tables; one table jacks up 33 cm
        cam.shot(S("proof") - 0.1, close_nist, [(S("proof") - 0.1, K(lx + 2.6, 2.4, lz + 4.0), K(lx - 0.1, 1.0, lz), 44),
                                                (close_nist, K(lx + 2.2, 2.2, lz + 3.7), K(lx - 0.15, 1.05, lz), 44)], fps, "key"),
        # proof 2: close on the two readouts, the raised one counting faster
        cam.shot(close_nist, S("lifetime") - 0.1, [(close_nist, K(lx - 0.1, 1.2, lz + 4.4), K(lx - 0.05, 1.15, lz), 40),
                                                   (S("lifetime") - 0.1, K(lx - 0.1, 1.22, lz + 4.1), K(lx - 0.05, 1.17, lz), 40)], fps, "key"),
        # lifetime: wide 3/4 on the figure while 80 years pass
        cam.shot(S("lifetime") - 0.1, S("gps") - 0.1, [(S("lifetime") - 0.1, K(-2.6, 1.9, 4.6), K(0.2, 0.75, 0.0), 40),
                                                       (S("gps") - 0.1, K(-1.8, 1.7, 4.8), K(0.25, 0.75, 0.0), 40)], fps, "golden"),
        # gps: from behind the car, crane up to the satellite (centred, drifting) and its clock
        cam.shot(S("gps") - 0.1, gps_close, [(S("gps") - 0.1, K(-1.4, 3.0, 15.0), K(-1.0, 8.0, -20.0), 52),
                                             (gps_close, K(-1.4, 3.2, 14.0), K(-1.2, 10.0, -26.0), 52)], fps, "key", car),
        # gps 2: up close to the satellite, its clock and readout racing ahead (round 3: near-static 8.5 s)
        cam.shot(gps_close, S("drift") - 0.1, [(gps_close, K(9.0, 15.0, 3.0), K(-1.0, 14.8, -34.0), 44),
                                               (S("drift") - 0.1, K(7.0, 14.5, 4.0), K(-1.0, 14.8, -34.0), 44)], fps, "key", car),
        # drift: high 3/4 aerial over the road, the map pin slides away from the car
        cam.shot(S("drift") - 0.1, n / fps + 0.05, [(S("drift") - 0.1, K(7.0, 13.0, 16.0), K(0.0, 0.0, -14.0), 44),
                                                    (n / fps, K(7.5, 16.0, 20.0), K(0.3, 0.0, -18.0), 44)], fps, "key", car),
    ])
    # which set is on screen (the scene hides the others: round 2, cropped stray objects at the frame edges)
    for i, t in enumerate(T):
        frames["set"].append("tower" if S("why") - 0.1 <= t < S("feet") - 0.1 else
                             "lab" if S("proof") - 0.1 <= t < S("lifetime") - 0.1 else
                             "road" if t >= S("gps") - 0.1 else "fig")
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
        {"start": at("gps", "thirty-eight"), "end": S("drift") - 0.1, "big": "≈ +38 µs a day",
         "small": "GPS clocks: gravity +46, speed −7", "y": 0.17},
    ]
    events = [(round(lift0 + 0.1, 3), "rise", {"gain": 0.16})]          # the table starts to climb
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [lift0, life0, day0], "events": events,
               "mutes": [], "swells": [life0], "close_nist": close_nist, "gps_close": gps_close, "lifetime": [life0, life1], "day": [day0, day1], "lift": [lift0, lift1]}
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
        "head_mark": [[POST_X + 0.75, 1.72, 0.1]] * n,
        "feet_mark": [[POST_X + 0.75, 0.06, 0.1]] * n,
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
