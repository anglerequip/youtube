"""Why does my cat sit like a loaf? Render plan (the three.js scene is renderer/scenes/catloaf3d.js).

A cosy living room on a winter afternoon: wooden floor, a round rug, a sofa, a radiator under a window with a
low sun outside. The orange tabby lies on the rug and folds into a loaf; the wizard and the woman stand in the
room and talk about it. The one number on screen (how much less surface the loaf exposes) is computed from
our own cat mesh by renderer/cat_area.mjs and stored in cat_area.json next to this file; it is labelled
"our model". The sun patch on the floor is real: the sun shines through the window and the walls cast the
shadow, so moving the sun direction slides the patch onto the rug for the ending.

The presenters' mouths follow the real voice (loudness envelope of voice.wav during their own beats).
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np

from factory import camera as cam

SCENE = "catloaf3d"
HERE = Path(__file__).resolve().parent
ROOM = {"x0": -3.0, "x1": 3.0, "z0": -3.0, "z1": 3.0, "h": 2.7}
WINDOW = {"cx": 0.4, "w": 1.4, "y0": 0.85, "y1": 2.1, "z": -3.0}
RUG = [0.25, 0.0, -0.6]
RUG_R = 1.1
CAT_A = [0.0, 0.0, -0.4]            # where she loafs for most of the video
CAT_B = [0.78, 0.0, -1.08]          # the spot the sun patch reaches at the end
CAT_FACE = 0.55                      # body faces +z, turned a little to camera right
WIZ = [-0.95, 0.0, 0.95]
WOMAN = [1.45, 0.0, 0.7]
TWIN = [-1.3, 0.0, -1.55]            # the side-by-side comparison (stretched in front, loaf behind)
PATCH_A = [1.45, 0.0, -1.5]          # sun patch, beats 1-9: on the bare floor, off the rug
PATCH_B = [CAT_B[0] - 0.05, 0.0, CAT_B[2] + 0.1]
SPEAKER = {"hook": "wizard", "loaf": "woman", "coat": "wizard", "comfy": "woman", "leak": "woman", "knees": "woman",
           "trust": "wizard", "tucked": "woman", "pain": "woman", "warm": "wizard"}
HEAD_WIZ = [WIZ[0], 1.62, WIZ[2]]
HEAD_WOMAN = [WOMAN[0], 1.52, WOMAN[2]]


def cat_area() -> dict:
    """Exposed surface of our cat in each pose (renderer/cat_area.mjs). Recomputed if the JSON is missing."""
    p = HERE / "cat_area.json"
    if not p.exists():
        root = HERE.parents[2]
        subprocess.run(["node", str(root / "renderer" / "cat_area.mjs"), str(p)], check=True, cwd=root / "renderer",
                       capture_output=True)
    return json.loads(p.read_text())


def _envelope(n: int, fps: int) -> np.ndarray:
    """Per-frame voice loudness (0..1) from out/<slug>/voice.wav, smoothed like a jaw."""
    from factory.configuration import settings
    import soundfile as sf
    p = settings.out_dir / "cat-loaf" / "voice.wav"
    env = np.zeros(n)
    if not p.exists():
        return env
    a, sr = sf.read(p, dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    hop = sr / fps
    for i in range(n):
        s = a[int(i * hop): int((i + 1) * hop)]
        env[i] = float(np.sqrt(np.mean(s * s))) if len(s) else 0.0
    env = env / (np.percentile(env[env > 0], 95) if np.any(env > 0) else 1.0)
    out = np.zeros(n)
    for i in range(n):                                   # fast open, slower close
        prev = out[i - 1] if i else 0.0
        out[i] = prev + (env[i] - prev) * (0.7 if env[i] > prev else 0.35)
    return np.clip(out, 0, 1)


def _face(src, dst):
    return math.atan2(dst[0] - src[0], dst[2] - src[2])


def _off(base, dx, dy, dz):
    return [base[0] + dx, base[1] + dy, base[2] + dz]


def _rot(v, a):
    """Rotate an (x, z) offset by angle a about y (same convention as three.js rotation.y)."""
    x, y, z = v
    return [x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a)]


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w, k=1: timing.word_time(tl, b, w, k)
    n = int(math.ceil((tl.duration + 0.05) * fps))
    T = np.arange(n) / fps
    dur = n / fps
    env = _envelope(n, fps)
    area = cat_area()
    less_pct = float(area["loaf_less_than_stretched_pct"])

    def active(t):
        ln = tl.active(t)
        return ln.id if ln else None

    # ---- key moments
    fold0 = 0.25                                      # hook: legs and tail tuck away
    fold1 = min(S("loaf") - 0.15, fold0 + 1.6)
    heat_on = S("leak") - 0.1                        # thermal look on
    legs_t = at("leak", "Legs") - 0.15               # legs and tail glow hardest
    fold_t = at("leak", "folds") - 0.25              # ... and fold away
    fridge_t = at("comfy", "Your") - 0.2             # room goes cold around her
    womc_t = S("comfy") - 0.1
    blink_t = at("tucked", "Cats") + 0.2             # relaxed slow blink
    tucked_b = at("tucked", "Cats") - 0.2
    hunch_t = S("pain") + 0.25                       # posture tightens
    pain_b = at("pain", "That") - 0.2
    walk0 = S("warm") - 0.05                         # she gets up and walks into the sun
    walk1 = walk0 + 1.1
    end_b = walk1                                    # final shot: she settles in the sun and loafs again
    sun0, sun1 = E("pain") - 0.2, walk0 + 0.6        # the sun patch slides onto the rug (it arrives first; she follows it)

    face_walk = _face(CAT_A, CAT_B)
    frames = {k: [] for k in ("talk_w", "talk_m", "look_w", "look_m", "cat_mode", "cat_x", "cat_z", "cat_face",
                              "fold", "hunch", "ears", "cat_blink", "cat_pitch", "cat_yaw", "walk", "heat", "heat_body",
                              "wiz_blink", "woman_blink", "cool", "thermal", "sat", "ring", "twin", "bars", "sun_u",
                              "badge")}
    for i, t in enumerate(T):
        a = active(t)
        who = SPEAKER.get(a) if a else None
        frames["talk_w"].append(round(float(env[i]) if who == "wizard" else 0.0, 3))
        frames["talk_m"].append(round(float(env[i]) if who == "woman" else 0.0, 3))
        frames["look_w"].append("woman" if a == "coat" else "cat")
        frames["look_m"].append("camera" if womc_t <= t < fridge_t else "wizard")
        # ---- the cat
        mode, x, z, face, fold, hunch, ears, blink, pitch, yaw, walk = "lie", CAT_A[0], CAT_A[2], CAT_FACE, 1.0, 0.0, 0.0, 0.0, -0.05, 0.0, 0.0
        if t < fold1:
            fold = cam.ease((t - fold0) / (fold1 - fold0))
        if heat_on <= t < S("knees"):                     # the heat-loss demo: stretched out, then folds
            fold = cam.ease((t - fold_t) / 1.1)
            pitch = 0.05
        if S("pain") <= t < walk0:                       # tense, hunched, squinting, head down
            u = cam.ease((t - hunch_t) / 1.3)
            hunch, ears, blink, pitch = u, 0.75 * u, 0.6 * u, -0.05 + 0.42 * u
        if blink_t <= t < blink_t + 1.3:                 # the relaxed slow blink
            blink = math.sin(math.pi * (t - blink_t) / 1.3) ** 0.7
            pitch = -0.05 + 0.06 * blink
        elif t < S("pain") and (t % 4.1) < 0.12 and not (t < fold1):
            blink = 1.0
        if walk0 <= t < walk1:                           # up and over into the sun patch
            u = cam.ease((t - walk0) / (walk1 - walk0))
            mode, face, walk = "stand", face_walk, (t - walk0) * 7.0
            x, z = CAT_A[0] + (CAT_B[0] - CAT_A[0]) * u, CAT_A[2] + (CAT_B[2] - CAT_A[2]) * u
            pitch, blink, hunch, ears = 0.05, 0.0, 0.0, 0.0
        if t >= walk1:                                   # settles flat in the sun, then tucks into a loaf
            x, z = CAT_B[0], CAT_B[2]
            fold = cam.ease((t - walk1 - 0.05) / 0.8)
            blink = 0.35 * cam.ease((t - walk1 - 1.0) / 0.5)   # eyes half-closed, content
        for key, v in (("cat_mode", mode), ("cat_x", round(x, 4)), ("cat_z", round(z, 4)), ("cat_face", round(face, 4)),
                       ("fold", round(fold, 4)), ("hunch", round(hunch, 4)), ("ears", round(ears, 4)),
                       ("cat_blink", round(blink, 3)), ("cat_pitch", round(pitch, 4)), ("cat_yaw", round(yaw, 4)),
                       ("walk", round(walk, 3))):
            frames[key].append(v)
        # heat-loss view: limbs glow while they are out, then fade as they tuck in
        h = 0.0
        if heat_on <= t < S("knees"):
            h = min(1.0, (t - heat_on) / 0.4) * (0.55 + 0.45 * cam.ease((t - legs_t) / 0.5)) * (1 - 0.85 * fold)
        frames["heat"].append(round(h, 3))
        frames["heat_body"].append(round(min(1.0, (t - heat_on) / 0.4), 3) if heat_on <= t < S("knees") else 0.0)
        frames["thermal"].append(round(min(1.0, (t - heat_on) / 0.4), 3) if heat_on <= t < S("knees") else 0.0)
        frames["ring"].append(round(min(1.0, (t - fold_t) / 0.4), 3) if fold_t <= t < S("knees") else 0.0)
        frames["cool"].append(round(cam.ease((t - fridge_t) / 0.9), 3) if fridge_t <= t < heat_on else 0.0)
        frames["sat"].append(round(1.0 - 0.65 * cam.ease((t - hunch_t) / 1.3), 3) if S("pain") <= t < walk0 else 1.0)
        frames["twin"].append(1 if S("knees") - 0.1 <= t < S("trust") else 0)
        frames["bars"].append(round(cam.ease((t - S("knees") - 0.3) / 1.0), 3) if S("knees") - 0.1 <= t < S("trust") else 0.0)
        frames["sun_u"].append(round(cam.ease((t - sun0) / (sun1 - sun0)), 4))
        wb = 1.0 if (t % 3.7) < 0.12 else 0.0
        frames["wiz_blink"].append(wb)
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        frames["badge"].append("")

    K = lambda *a: list(a)
    A, B = CAT_A, CAT_B
    head_a = _off(A, 0, 0.15, 0)
    hook_off = lambda d, h: _rot([0.0, h, d], CAT_FACE + 0.75)          # in front and to her right
    mid = lambda a, b: [(a[0] + b[0]) / 2, 0, (a[2] + b[2]) / 2]
    face_w = _face(WIZ, mid(A, WOMAN))      # body between the cat and the woman, so the head turns only a little
    face_m = _face(WOMAN, mid(A, WIZ))
    wiz_cam = lambda d, h, side: _off(WIZ, *_rot([side, 0, d], face_w))[0:1] + [h] + _off(WIZ, *_rot([side, 0, d], face_w))[2:3]
    wom_cam = lambda d, h, side: _off(WOMAN, *_rot([side, 0, d], face_m))[0:1] + [h] + _off(WOMAN, *_rot([side, 0, d], face_m))[2:3]
    tw = TWIN
    du = math.hypot(WIZ[0] - A[0], WIZ[2] - A[2])
    tc = [-(WIZ[0] - A[0]) / du * 1.3, 0.5, -(WIZ[2] - A[2]) / du * 1.3]   # behind the cat, away from the wizard
    shots = cam.chain([
        # hook: low and close, pushing in as the paws and tail vanish under her
        cam.shot(0.0, S("loaf") - 0.1, [(0.0, _off(A, *hook_off(1.55, 0.46)), _off(A, 0, 0.1, 0), 34),
                                        (S("loaf") - 0.1, _off(A, *hook_off(1.2, 0.4)), _off(A, 0, 0.11, 0), 34)], fps, "golden"),
        # loaf: wide three-quarter of the room: rug, cat, radiator, low winter sun in the window
        cam.shot(S("loaf") - 0.1, S("coat") - 0.1, [(S("loaf") - 0.1, K(0.75, 1.5, 1.85), K(0.12, 0.3, -0.85), 40),
                                                    (S("coat") - 0.1, K(0.65, 1.42, 1.65), K(0.12, 0.3, -0.85), 40)], fps, "golden"),
        # coat: punch-in on the wizard
        cam.shot(S("coat") - 0.1, womc_t, [(S("coat") - 0.1, wiz_cam(1.05, 1.58, -0.12), K(WIZ[0], 1.52, WIZ[2]), 34),
                                           (womc_t, wiz_cam(0.95, 1.58, -0.1), K(WIZ[0], 1.52, WIZ[2]), 34)], fps, "golden"),
        # comfy (a): the woman with the number
        cam.shot(womc_t, fridge_t, [(womc_t, wom_cam(0.92, 1.6, -0.05), K(WOMAN[0], 1.53, WOMAN[2]), 34),
                                    (fridge_t, wom_cam(0.84, 1.6, -0.04), K(WOMAN[0], 1.53, WOMAN[2]), 34)], fps, "golden"),
        # comfy (b): high over the rug; the room goes cold blue around the warm cat
        cam.shot(fridge_t, heat_on, [(fridge_t, _off(A, 0.55, 1.6, 1.35), _off(A, 0.0, 0.1, -0.1), 40),
                                     (heat_on, _off(A, 0.5, 1.5, 1.22), _off(A, 0.0, 0.1, -0.15), 40)], fps, "winter"),
        # leak (a): thermal-style view from above: legs and tail glowing
        cam.shot(heat_on, legs_t + 0.9, [(heat_on, _off(A, 0.35, 2.0, 0.8), _off(A, 0.02, 0.05, -0.05), 36),
                                         (legs_t + 0.9, _off(A, 0.3, 1.85, 0.72), _off(A, 0.02, 0.05, -0.05), 36)], fps, "winter"),
        # leak (b): low side view as she folds them away; a white ring on the floor
        cam.shot(legs_t + 0.9, S("knees") - 0.1, [(legs_t + 0.9, _off(A, *_rot([1.5, 0.62, 0.35], CAT_FACE + 1.25)), _off(A, 0, 0.08, 0), 36),
                                                  (S("knees") - 0.1, _off(A, *_rot([1.3, 0.55, 0.3], CAT_FACE + 1.25)), _off(A, 0, 0.08, 0), 36)], fps, "winter"),
        # knees: the same cat twice side by side (stretched out left, loafed right), a bar behind each at the same depth
        cam.shot(S("knees") - 0.1, S("trust") - 0.1, [(S("knees") - 0.1, _off(tw, 0.0, 1.3, 1.6), _off(tw, 0.0, 0.14, -0.3), 40),
                                                      (S("trust") - 0.1, _off(tw, 0.0, 1.2, 1.42), _off(tw, 0.0, 0.14, -0.3), 40)], fps, "golden"),
        # trust: two-shot from behind the loafing cat, up at the hopeful wizard
        cam.shot(S("trust") - 0.1, S("tucked") - 0.1, [(S("trust") - 0.1, _off(A, *[v * 1.0 for v in tc]), K(-0.55, 0.78, 0.45), 55),
                                                       (S("tucked") - 0.1, _off(A, *[v * 0.9 for v in tc]), K(-0.55, 0.8, 0.45), 55)], fps, "golden"),
        # tucked (a): low side view of the tucked paws
        cam.shot(S("tucked") - 0.1, tucked_b, [(S("tucked") - 0.1, _off(A, *_rot([0.55, 0.24, 0.85], CAT_FACE)), _off(A, 0, 0.08, 0.0), 34),
                                               (tucked_b, _off(A, *_rot([0.48, 0.22, 0.75], CAT_FACE)), _off(A, 0, 0.09, 0.05), 34)], fps, "golden"),
        # tucked (b): close on her face for the slow blink
        cam.shot(tucked_b, S("pain") - 0.1, [(tucked_b, _off(A, *_rot([0.0, 0.24, 0.62], CAT_FACE + 0.15)), _off(head_a, 0, 0.03, 0.08), 32),
                                             (S("pain") - 0.1, _off(A, *_rot([0.0, 0.23, 0.54], CAT_FACE + 0.15)), _off(head_a, 0, 0.03, 0.08), 32)], fps, "golden"),
        # pain (a): the same cat tightens into a tense, hunched loaf
        cam.shot(S("pain") - 0.1, pain_b, [(S("pain") - 0.1, _off(A, *_rot([0.0, 0.42, 0.95], CAT_FACE + 0.5)), _off(A, 0, 0.1, 0), 34),
                                           (pain_b, _off(A, *_rot([0.0, 0.38, 0.85], CAT_FACE + 0.5)), _off(A, 0, 0.1, 0), 34)], fps, "winter"),
        # pain (b): close on the squint
        cam.shot(pain_b, S("warm") - 0.1, [(pain_b, _off(A, *_rot([0.0, 0.22, 0.6], CAT_FACE + 0.1)), _off(head_a, 0, 0.0, 0.08), 32),
                                           (S("warm") - 0.1, _off(A, *_rot([0.0, 0.22, 0.54], CAT_FACE + 0.1)), _off(head_a, 0, 0.0, 0.08), 32)], fps, "winter"),
        # warm (a): the sun patch slides onto the rug and she walks into it
        cam.shot(S("warm") - 0.1, end_b, [(S("warm") - 0.1, K(1.0, 1.22, 1.35), K(0.42, 0.15, -0.85), 38),
                                          (end_b, K(0.95, 1.18, 1.2), K(0.47, 0.15, -0.9), 38)], fps, "golden"),
        # end: same framing as the opening, now in the sun: she settles and tucks in again (loops to frame 1)
        cam.shot(end_b, dur + 0.05, [(end_b, _off(B, *hook_off(1.55, 0.46)), _off(B, 0, 0.1, 0), 34),
                                     (dur + 0.05, _off(B, *hook_off(1.3, 0.42)), _off(B, 0, 0.11, 0), 34)], fps, "golden"),
    ])
    focal = []
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            if s_["i0"] + k == len(focal) and len(focal) < n:
                focal.append(lk)
    while len(focal) < n:
        focal.append(focal[-1])
    frames["focal_pt"] = focal[:n]

    pct_txt = f"≈ {round(less_pct):d}% less"
    cards = [
        {"start": at("loaf", "loaf"), "end": S("coat") - 0.2, "big": "The loaf", "small": "paws tucked, tail wrapped in", "y": 0.16},
        {"start": S("comfy") + 0.3, "end": heat_on - 0.15, "big": "≈ 30 °C", "small": "comfy for a cat", "y": 0.16},
        {"start": legs_t, "end": S("knees") - 0.15, "big": "Legs + tail", "small": "lose heat fastest", "y": 0.16},
        {"start": S("knees") + 1.0, "end": S("trust") - 0.15, "big": pct_txt, "small": "exposed surface (our model)", "y": 0.16},
        {"start": at("pain", "squinting") - 0.1, "end": S("warm") - 0.15, "big": "Hunched + squinting", "small": "worth a vet check", "y": 0.16},
    ]
    events = [(round(fold0 + 0.6, 3), "whoosh", {"gain": 0.1}),
              (round(heat_on, 3), "rise", {"gain": 0.12}),
              (round(fold_t + 0.35, 3), "whoosh", {"gain": 0.1, "seed": 4}),
              (round(E("warm") + 0.3, 3), "pop", {"gain": 0.1, "seed": 11})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [fold_t, hunch_t, walk1], "events": events,
               "mutes": [], "swells": [S("warm")]}
    poses = area["poses"]
    facts = {"loaf_less_pct": less_pct,
             "stretched_exposed_cm2": poses["stretched"]["exposed_cm2"], "loaf_exposed_cm2": poses["loaf"]["exposed_cm2"],
             "cat_face": CAT_FACE,
             "events": {"loafed": {"t": fold1 + 0.2, "observe": "fold", "expect": 1.0, "tol": 0.02},
                        "folded_in_demo": {"t": S("knees") - 0.2, "observe": "fold", "expect": 1.0, "tol": 0.05},
                        "in_the_sun": {"t": dur - 0.1, "observe": "cat_x", "expect": CAT_B[0], "tol": 0.01}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 29, "supersample": 1.0,
            "bloom_threshold": 2.2, "end_hold_s": 1.4,
            "layout": {"room": ROOM, "window": WINDOW, "rug": RUG, "rug_r": RUG_R, "cat_a": CAT_A, "cat_b": CAT_B,
                       "wiz": WIZ, "woman": WOMAN, "twin": TWIN, "patch_a": PATCH_A, "patch_b": PATCH_B,
                       "face_w": face_w, "face_m": face_m,
                       "bar_h": [0.32, round(0.32 * poses["loaf"]["exposed_cm2"] / poses["stretched"]["exposed_cm2"], 4)]},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in ("fold", "cat_x", "hunch"):
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 84, "gain": 0.11}


def self_checks() -> dict:
    """The one computed number: the loaf exposes less surface than the stretched-out pose, by a plausible amount."""
    a = cat_area()
    s, l = a["poses"]["stretched"]["exposed_cm2"], a["poses"]["loaf"]["exposed_cm2"]
    pct = a["loaf_less_than_stretched_pct"]
    ok = l < s and 5.0 <= pct <= 45.0 and abs(100 * (1 - l / s) - pct) < 0.2
    return {"loaf exposes less surface than stretched out (our cat mesh)": {
        "pass": bool(ok), "detail": f"stretched {s} cm2, loaf {l} cm2 exposed: {pct}% less"}}
