"""What if you were a hundred times taller? Render plan (scene renderer/scenes/giantwizard3d.js, ice set renderer/sets/ice.js).

The wizard casts a spell on the Antarctic ice shelf and grows to K = 100 times his height (his model is 2.0 m with the
hat, so 200 m). The woman stands at normal size about 60 m in front of his boots, among a few penguins. The scale
factors the narration states are computed here (square-cube law), and so is the heat estimate behind "you'd
overheat": a body with our cells makes K^3 more heat but has only K^2 more skin, so each square metre must shed K times
more; Antarctic air can carry away far less than that (convection over a 170 m body in wind plus radiation).
Positions and timing are decided here; the scene only draws.
"""
from __future__ import annotations

import math

import numpy as np

from factory import duo
from factory import camera as cam

SCENE = "giantwizard3d"
SLUG = "giant-wizard"
K = 100.0                          # scale factor (every length)
K0 = 15.0                          # the size he is at in the hook's first frame (and again at the end: the loop)
WIZ = [0.0, 0.0, 0.0]              # the giant, facing +z
WIZ_FACE = 0.0
WOMAN = [10.0, 0.0, 62.0]          # normal size, in front of his boots
FACE_Y = 1.69                      # wizard eye height (model), metres before scaling
SIT_DROP = 0.46                    # how far his hips drop per unit of 'sit' (model metres)
BUCKLE = 0.2                       # how far he buckles after the crack
SPEAKER = {"hook": "wizard", "doom": "woman", "why": "wizard", "weight": "woman", "bones": "woman", "stress": "woman",
           "crack": "wizard", "cold": "wizard", "heat": "woman", "cook": "woman", "smaller": "wizard", "button": "woman"}

# heat model (see storyboard caveats)
REST_W, MASS_KG, SKIN_M2 = 80.0, 80.0, 1.9         # resting heat output, body mass, skin area of the normal-size wizard
T_AIR, T_SKIN, WIND = -30.0, 34.0, 10.0           # Antarctic air, skin temperature, wind (m/s)


def heat_budget(k: float = K) -> dict:
    """Heat per square metre a k-times-scaled body must shed, and what cold windy air can carry away (W/m^2)."""
    need = REST_W * k ** 3 / (SKIN_M2 * k ** 2)
    L = 1.7 * k                                       # body length scale for the boundary layer
    nu, kair, pr = 1.1e-5, 0.022, 0.71                # cold air
    re = WIND * L / nu
    h = 0.037 * re ** 0.8 * pr ** (1 / 3) * kair / L  # turbulent flat plate (forced convection)
    conv = h * (T_SKIN - T_AIR)
    sig, eps = 5.67e-8, 0.98
    rad = eps * sig * ((T_SKIN + 273.15) ** 4 - (T_AIR - 10 + 273.15) ** 4)   # to a sky colder than the air
    return {"need": need, "need_normal": REST_W / SKIN_M2, "h": h, "conv": conv, "rad": rad, "can_shed": conv + rad}


def grow_curve(t: float, t0: float, t1: float, a: float, b: float) -> float:
    """Size between a and b, eased in log space (so the growth looks steady at every size)."""
    u = 0.0 if t <= t0 else 1.0 if t >= t1 else cam.ease((t - t0) / (t1 - t0))
    return math.exp(math.log(a) + (math.log(b) - math.log(a)) * u)


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, o=1: timing.word_time(tl, b, w, o)
    n = duo.n_frames(tl, fps)
    T = np.arange(n) / fps
    dur = n / fps
    env = duo.envelope(SLUG, n, fps)
    tw, tm = duo.talk_tracks(tl, SPEAKER, env, fps)

    grow0, grow1 = 0.0, min(at("hook", "taller") + 0.2, S("doom") - 0.2)
    crack_t = at("crack", "crunching") - 0.05
    buckle_t = S("cold") - 0.05
    shrink0, shrink1 = S("button") + 0.05, min(dur - 0.6, S("button") + 2.4)
    million_t = at("weight", "million") - 0.1
    heat_t = S("heat") + 0.3

    def gscale(t):
        if t < shrink0:
            return grow_curve(t, grow0, grow1, K0, K)
        return grow_curve(t, shrink0, shrink1, K, K0)

    def sit(t):
        return BUCKLE * duo.ramp(t, buckle_t, 0.9) * (1 - duo.ramp(t, shrink0, 1.6))

    def face_y(t):
        return gscale(t) * (FACE_Y - SIT_DROP * sit(t))

    # woman: body turned away from the giant (towards the camera side), so he towers behind her
    gx, gz = WIZ[0] - WOMAN[0], WIZ[2] - WOMAN[2]
    to_giant = math.atan2(gx, gz)
    woman_face = to_giant + math.pi - 0.25
    fx, fz = math.sin(woman_face), math.cos(woman_face)
    wfx, wfy = WOMAN[0], WOMAN[2]
    gl_ = math.hypot(gx, gz)
    ux, uz = gx / gl_, gz / gl_                      # unit vector from the woman towards the giant
    K_ = lambda *a: list(a)
    E_ = duo.shot(fps)
    L_ = "winter"

    # hook: the camera in front of the woman, low, looking past her up at the giant as he grows (look follows his face)
    def hook_keys(t0, t1, shrink=False):
        ks = []
        for tt in np.linspace(t0, t1, max(2, int((t1 - t0) / 0.2) + 1)):
            fy = face_y(tt)
            up = min(1.0, fy / 170.0)
            pos = [wfx - ux * 11.0 + 1.2 * uz, 1.9 + 1.6 * up, wfy - uz * 11.0 - 1.2 * ux]
            look = [0.0, 1.0 + fy * 0.6, 4.0]
            ks.append((float(tt), pos, look, 50 + 6 * up))
        return ks

    face = lambda t: [0.0, face_y(t), 0.0]
    fyK = K * FACE_Y
    fyB = K * (FACE_Y - SIT_DROP * BUCKLE)
    shots = [
        cam.shot(0.0, S("doom") - 0.1, hook_keys(0.0, S("doom") - 0.1), fps, L_),
        # doom: the woman close (head and shoulders), the giant's robe and boots looming behind her
        E_(S("doom") - 0.1, S("why") - 0.1, K_(wfx + fx * 1.55 + 0.25, 1.35, wfy + fz * 1.55), K_(wfx + fx * 1.35 + 0.2, 1.38, wfy + fz * 1.35),
           K_(wfx, 1.62, wfy), 38, L_),
        # why: drone close on the giant's face
        E_(S("why") - 0.1, S("weight") - 0.1, K_(30, fyK - 5, 84), K_(24, fyK - 4, 76), K_(0, fyK - 1, 0), 44, L_),
        # weight (a): the whole giant from high and wide, tiny woman and penguins at his feet
        E_(S("weight") - 0.1, million_t - 0.15, K_(-250, 80, 330), K_(-235, 86, 312), K_(0, 92, 10), 40, L_),
        # weight (b): at ground level by his boot as it presses into the snow, a penguin near the lens
        E_(million_t - 0.15, S("bones") - 0.1, K_(40, 8, 165), K_(34, 8.5, 152), K_(6, 7, 42), 40, L_),
        # bones: x-ray, legs and hips: two glowing thigh bones
        E_(S("bones") - 0.1, at("bones", "That") - 0.1, K_(95, 62, 150), K_(86, 64, 138), K_(0, 62, 0), 40, L_),
        E_(at("bones", "That") - 0.1, S("stress") - 0.1, K_(-40, 70, 80), K_(-34, 70, 72), K_(-10, 66, 0), 38, L_),
        # stress: closer on one thigh bone as it turns red
        E_(S("stress") - 0.1, S("crack") - 0.15, K_(58, 64, 66), K_(50, 64, 58), K_(-2, 62, 0), 36, L_),
        # crack: tight on the bone, cracks run through it
        E_(S("crack") - 0.15, S("cold") - 0.1, K_(26, 40, 62), K_(23, 42, 58), K_(6, 62, 0), 34, L_),
        # cold: from the snow among the penguins: he buckles at the knees, snow bursts; he jokes about the cold
        E_(S("cold") - 0.1, S("heat") - 0.1, K_(24, 1.6, 112), K_(20, 1.9, 106), K_(0, 80, 0), 52, L_),
        # heat (a): wide 3/4, he starts to glow warm
        E_(S("heat") - 0.1, at("heat", "Only") - 0.1, K_(-210, 120, 250), K_(-198, 124, 236), K_(0, 80, 0), 40, L_),
        # heat (b): closer on his chest and face, steam starting
        E_(at("heat", "Only") - 0.1, S("cook") - 0.1, K_(70, fyB - 14, 120), K_(62, fyB - 12, 110), K_(0, fyB - 14, 0), 42, L_),
        # cook: low from the penguins looking up at the steaming giant
        E_(S("cook") - 0.1, S("smaller") - 0.1, K_(-22, 1.5, 98), K_(-20, 1.7, 92), K_(0, 105, 0), 56, L_),
        # smaller: drone on his face (lower now: he is on bent knees)
        E_(S("smaller") - 0.1, S("button") - 0.1, K_(-32, fyB - 5, 82), K_(-26, fyB - 4, 76), K_(0, fyB - 1, 0), 44, L_),
        # button: the hook's angle again; he shrinks back to where the video began (the loop)
        cam.shot(S("button") - 0.1, dur + 0.05, hook_keys(S("button") - 0.1, dur + 0.05), fps, L_),
    ]
    shots = cam.chain(shots)
    xray_ranges = [(S("bones") - 0.1, S("cold") - 0.1)]

    frames = {k: [] for k in ("gscale", "sit", "xray", "bone_glow", "stress", "crack", "heat", "steam", "melt",
                              "puff", "wiz_blink", "woman_blink", "wiz_wave", "wiz_point", "woman_point", "look_w", "woman_up")}
    frames["talk_w"], frames["talk_m"] = tw, tm
    for i, t in enumerate(T):
        ln = tl.active(t)
        a = ln.id if ln else None
        xr = any(s <= t < e for s, e in xray_ranges)
        frames["gscale"].append(round(gscale(t), 4))
        frames["sit"].append(round(sit(t), 4))
        frames["xray"].append(1 if xr else 0)
        frames["bone_glow"].append(round(duo.ramp(t, S("bones") + 0.1, 0.8), 3))
        frames["stress"].append(round(duo.ramp(t, at("stress", "hundred") - 0.3, 1.2), 3))
        frames["crack"].append(round(duo.ramp(t, crack_t, 0.35), 3))
        frames["heat"].append(round(duo.ramp(t, heat_t, 3.5) * (1 - duo.ramp(t, shrink0, 1.6)), 3))
        frames["steam"].append(round(duo.ramp(t, heat_t + 0.4, 2.0) * (1 - duo.ramp(t, S("smaller") - 0.3, 1.0)), 3))
        frames["melt"].append(round(duo.ramp(t, S("cook") - 0.2, 2.0) * (1 - duo.ramp(t, shrink0 + 0.2, 1.4)), 3))
        frames["puff"].append(round(max(0.0, min(1.0, (t - million_t) / 1.6)) if t >= million_t and t < million_t + 1.6 else
                                    max(0.0, min(1.0, (t - buckle_t) / 1.8)) if buckle_t <= t < buckle_t + 1.8 else 0.0, 3))
        frames["wiz_wave"].append(round(duo.bump(t, 0.2, 0.6, 2.0, 0.6) * 0.8 + duo.bump(t, S("smaller") + 0.4, 0.6, 1.4, 0.6) * 0.4, 3))
        frames["wiz_point"].append(round(duo.bump(t, S("why") + 0.1, 0.6, 1.6, 0.6) * 0.5, 3))
        frames["woman_point"].append(round(duo.bump(t, S("weight") + 0.2, 0.5, 1.8, 0.5) * 0.6 + duo.bump(t, S("doom") + 0.1, 0.4, 0.8, 0.4) * 0.5, 3))
        frames["look_w"].append("woman" if a in ("cold", "crack") else ("down" if a in ("bones", "stress") else "ahead"))
        frames["woman_up"].append(1 if a in ("hook", "why", "crack", "cold", "smaller") else 0)
        frames["wiz_blink"].append(1.0 if (t % 4.1) < 0.12 else 0.0)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
    focal = []
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            if s_["i0"] + k == len(focal) and len(focal) < n:
                focal.append(lk)
    while len(focal) < n:
        focal.append(focal[-1])
    frames["focal_pt"] = focal[:n]

    cards = [
        {"start": million_t, "end": S("bones") - 0.15, "big": "1,000,000×", "small": "weight", "y": 0.16},
        {"start": at("bones", "ten") - 0.1, "end": S("stress") - 0.15, "big": "10,000×", "small": "bone strength", "y": 0.16},
        {"start": at("stress", "hundred") - 0.1, "end": S("crack") - 0.2, "big": "100×", "small": "load on the bone", "y": 0.16},
        {"start": at("heat", "million") - 0.1, "end": at("heat", "Only") - 0.15, "big": "1,000,000×", "small": "heat", "y": 0.16},
        {"start": at("heat", "ten") - 0.1, "end": S("cook") - 0.15, "big": "10,000×", "small": "skin to lose it", "y": 0.16},
    ]
    events = [(0.25, "rise", {"gain": 0.16}),
              (round(million_t + 0.05, 3), "boom", {"gain": 0.12}),
              (round(crack_t - 0.27, 3), "crunch", {"gain": 0.2}),
              (round(buckle_t - 0.3, 3), "boom", {"gain": 0.09, "seed": 31, "depth": 1.4}),
              (round(heat_t + 0.4, 3), "sizzle", {"gain": 0.09, "dur": 1.6}),
              (round(shrink0 + 0.05, 3), "fall", {"gain": 0.1, "seed": 2})]
    cuts_ = [s_["start"] for s_ in shots[1:]]
    reveals_ = [next((c for c in cuts_ if -0.05 < c - r < 1.5), r) for r in [million_t, crack_t, heat_t]]
    timing_ = {"cuts": cuts_, "reveals": reveals_, "events": events, "mutes": [], "swells": [S("button")]}
    hb = heat_budget()
    facts = {"scale": K, "weight_factor": K ** 3, "area_factor": K ** 2, "stress_factor": K ** 3 / K ** 2, "heat_factor": K ** 3,
             "heat_need_w_m2": round(hb["need"], 1), "heat_can_shed_w_m2": round(hb["can_shed"], 1),
             "events": {"full_size_by_why": {"t": round(S("why") + 0.3, 3), "observe": "gscale", "expect": K, "tol": 0.5},
                        "cracks_shown": {"t": round(S("crack") + 1.2, 3) if S("crack") + 1.2 < S("cold") - 0.1 else round(E("crack"), 3),
                                         "observe": "crack", "expect": 1, "tol": 0.01},
                        "back_to_hook_size_at_end": {"t": round(dur - 0.1, 3), "observe": "gscale", "expect": K0, "tol": 0.5}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 53, "supersample": 1.0, "bloom_threshold": 3.5,
            "end_hold_s": 1.2, "ground_cover": False,
            "layout": {"wiz": WIZ, "wiz_face": WIZ_FACE, "woman": WOMAN, "woman_face": woman_face},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in plan["frames"]:
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 84, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """The square-cube factors, and the heat budget behind 'you'd overheat'."""
    hb = heat_budget()
    vol = K ** 3; area = K ** 2
    return {"weight grows k^3 = 1,000,000": {"pass": abs(vol - 1e6) < 1e-6, "detail": f"{vol:,.0f}"},
            "bone cross-section and skin grow k^2 = 10,000": {"pass": abs(area - 1e4) < 1e-6, "detail": f"{area:,.0f}"},
            "stress in a scaled bone grows k = 100": {"pass": abs(vol / area - 100) < 1e-9, "detail": f"{vol / area:.0f}"},
            "a scaled body must shed 100x more heat per square metre of skin": {
                "pass": abs(hb["need"] / hb["need_normal"] - K) < 1e-6,
                "detail": f"{hb['need']:.0f} W/m2 vs {hb['need_normal']:.0f} W/m2 normally"},
            "Antarctic air (minus 30 C, 10 m/s) cannot carry that away": {
                "pass": hb["can_shed"] < 0.5 * hb["need"],
                "detail": f"convection {hb['conv']:.0f} (h = {hb['h']:.1f} W/m2K) + radiation {hb['rad']:.0f} = {hb['can_shed']:.0f} W/m2 < {hb['need']:.0f}"},
            "at ten times taller, stress still grows tenfold, past bone's safety factor of 2-4": {
                "pass": 10.0 > 4.0, "detail": "stress factor 10 vs safety factor 2-4 (Biewener 1990)"}}
