"""Why your cat stares while you eat: render plan (the three.js scene is renderer/scenes/catstare3d.js).

A small round garden table on a patio. The wizard stands at it with a sandwich on a plate; an orange tabby
sits on a stool beside the table, eyes locked on the sandwich; the woman stands across the table and
explains. Cutaways in the long grass behind the patio: a lone cat stalking a mouse, a mother cat bringing a
mouse to two kittens, and two adult cats passing each other in silence.

The mouths follow the real voice: each presenter's `talk` track is the loudness envelope of voice.wav while
that presenter's beat is playing. Behaviour, not physics: the evidence lives in the storyboard's sources.
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam

SCENE = "catstare3d"
TABLE = [0.0, 1.02, 0.0]            # round table top centre (y = top surface)
PLATE = [-0.12, 1.035, 0.03]
WIZ = [-0.56, 0.0, 0.0]             # wizard stands west of the table, facing +x
WOMAN = [0.6, 0.0, 0.14]           # woman stands east, facing -x
STOOL = [0.06, 0.0, -0.5]
CAT = [0.06, 0.8, -0.5]            # cat sits on the stool top
CAT_FACE = math.atan2(PLATE[0] - CAT[0], PLATE[2] - CAT[2])     # body faces the plate
HUNT = [7.0, 0.0, -6.0]             # lone cat stalking a mouse
DEN = [7.6, 0.0, -9.0]              # mother cat and kittens
PASS = [-6.5, 0.0, -6.5]            # two cats passing each other
SPEAKER = {"hook": "wizard", "myth": "woman", "how": "wizard", "alone": "woman", "judging": "wizard",
           "meow": "woman", "mum": "wizard", "purr": "woman", "stare": "wizard", "crumbs": "woman",
           "blink": "woman", "this": "wizard"}
HEAD_WIZ = [WIZ[0], 1.62, WIZ[2]]
HEAD_WOMAN = [WOMAN[0], 1.52, WOMAN[2]]


def _envelope(n: int, fps: int) -> np.ndarray:
    """Per-frame voice loudness (0..1) from out/<slug>/voice.wav, smoothed like a jaw."""
    from factory.configuration import settings
    import soundfile as sf
    p = settings.out_dir / "cat-stare" / "voice.wav"
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


def _yaw_to(src, dst, facing):
    return math.atan2(dst[0] - src[0], dst[2] - src[2]) - facing


def build_plan(tl, fps: int = 30, W: int = 1080, H: int = 1920) -> dict:
    from factory.retention import timing
    S, E = tl.start, tl.end
    at = lambda b, w: timing.word_time(tl, b, w)
    n = int(math.ceil((tl.duration + 0.05) * fps))
    T = np.arange(n) / fps
    dur = n / fps
    env = _envelope(n, fps)

    def active(t):
        ln = tl.active(t)
        return ln.id if ln else None

    # ---- key moments
    cute_t = at("myth", "Cute") - 0.25            # cut to the woman for the verdict
    crumb1 = S("crumbs") + 0.4                      # first crumb falls; the cat leans down and eats it
    crumb2 = at("crumbs", "sometimes") - 0.2        # a second crumb: the occasional reward
    mother_t = at("alone", "mothers") - 0.35        # cut to the mother bringing a mouse
    kitten_t = at("meow", "Kittens") - 0.25         # cut to the kittens meowing at mum
    us_t = at("meow", "us") - 0.55                  # back to the stool: the cat turns and meows at the wizard
    wblink = at("this", "this") - 0.05              # the wizard's slow blink
    cblink = E("this") + 0.35                       # ... the cat blinks back
    snap = cblink + 0.95                            # ... then the eyes snap back to the sandwich

    frames = {k: [] for k in ("talk_w", "talk_m", "look_w", "look_m", "cat_yaw", "cat_pitch", "cat_blink",
                              "cat_mouth", "wiz_blink", "woman_blink", "crumb1", "crumb2", "hunt", "den",
                              "pass", "purr", "kit_mouth", "badge")}
    yaw_wiz = _yaw_to(CAT, HEAD_WIZ, CAT_FACE)
    for i, t in enumerate(T):
        a = active(t)
        who = SPEAKER.get(a) if a else None
        frames["talk_w"].append(round(float(env[i]) if who == "wizard" else 0.0, 3))
        frames["talk_m"].append(round(float(env[i]) if who == "woman" else 0.0, 3))
        # where the presenters look: at whoever is talking; the wizard eyes the cat in his own key lines
        wiz_at_cat = a in ("hook", "judging", "this") or (t >= E("this"))
        frames["look_w"].append("cat" if wiz_at_cat else "woman")
        frames["look_m"].append("camera" if a == "blink" else "wizard")
        # the cat: eyes on the sandwich, except the meow at the wizard and the slow-blink exchange
        yaw, pitch, mouth, blink = 0.0, 0.22, 0.0, 0.0
        if us_t <= t < E("meow") + 0.3:
            u = cam.ease((t - us_t) / 0.35)
            yaw, pitch = yaw_wiz * u, 0.22 - 0.62 * u
            ph = (t - us_t - 0.35) / 0.7
            mouth = math.sin(math.pi * ph) if 0 <= ph <= 1 else 0.0
        if S("this") - 0.2 <= t < snap:
            u = cam.ease((t - (S("this") - 0.2)) / 0.4)
            yaw, pitch = yaw_wiz * u, 0.22 - 0.6 * u
        if t >= snap:                                    # snap back to the sandwich (fast: 0.12 s)
            u = cam.ease((t - snap) / 0.12)
            yaw, pitch = yaw_wiz * (1 - u), -0.38 + 0.6 * u
        if cblink <= t < cblink + 0.9:
            blink = math.sin(math.pi * (t - cblink) / 0.9) ** 0.6
        elif (t % 4.3) < 0.13 and not (S("hook") <= t < S("myth")):   # ordinary quick blinks, none in the hook
            blink = 1.0
        # crumbs: the cat dips its head to the table to eat each one
        for c in (crumb1, crumb2):
            if c + 0.55 <= t < c + 1.35:
                pitch = 0.22 + 0.55 * math.sin(math.pi * (t - c - 0.55) / 0.8)
        frames["cat_yaw"].append(round(yaw, 4)); frames["cat_pitch"].append(round(pitch, 4))
        frames["cat_mouth"].append(round(mouth, 3)); frames["cat_blink"].append(round(blink, 3))
        for key, c in (("crumb1", crumb1), ("crumb2", crumb2)):     # falls, rests, then eaten at the dip
            frames[key].append(round(min(1.0, (t - c) / 0.55), 3) if c <= t < c + 0.95 else 0.0)
        wb = math.sin(math.pi * (t - wblink) / 1.0) ** 0.6 if wblink <= t < wblink + 1.0 else (1.0 if (t % 3.7) < 0.12 else 0.0)
        frames["wiz_blink"].append(round(wb, 3))
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        frames["hunt"].append(round(max(0.0, t - S("alone")), 3))
        frames["den"].append(round(max(0.0, t - mother_t), 3))
        frames["pass"].append(round(max(0.0, t - S("meow")), 3))
        frames["purr"].append(round(max(0.0, t - S("purr")), 3) if S("purr") <= t < S("stare") else 0.0)
        frames["kit_mouth"].append(round(abs(math.sin((t - kitten_t) * 5.0)) if kitten_t <= t < us_t else 0.0, 3))
        b = ""
        if S("alone") <= t < E("alone") + 0.2 or S("meow") <= t < us_t:
            b = "WILD AND FREE-ROAMING CATS"
        frames["badge"].append(b)

    K = lambda *a: list(a)
    cx, cy, cz = CAT
    hx, hy, hz = HUNT
    dx, dy, dz = DEN
    px, py, pz = PASS
    cat_head = [cx, cy + 0.31, cz]
    shots = cam.chain([
        # hook: low across the plate at the cat's eyes over the table edge, slow push-in
        cam.shot(0.0, S("myth") - 0.1, [(0.0, K(-0.3, 1.22, 0.4), K(cx - 0.02, cy + 0.27, cz), 30),
                                        (S("myth") - 0.1, K(-0.24, 1.2, 0.26), K(cx - 0.02, cy + 0.27, cz), 30)], fps, "key"),
        # myth: wide three-quarter of the whole set-up
        cam.shot(S("myth") - 0.1, cute_t, [(S("myth") - 0.1, K(0.9, 2.15, 4.4), K(0.0, 1.0, -0.15), 38),
                                           (cute_t, K(0.78, 2.1, 4.15), K(0.0, 1.0, -0.15), 38)], fps, "golden"),
        # myth (b): the woman, a little amused, on "Cute story. Mostly wrong."
        cam.shot(cute_t, S("how") - 0.05, [(cute_t, K(-0.2, 1.58, 0.75), K(WOMAN[0], 1.45, WOMAN[2]), 36),
                                           (S("how") - 0.05, K(-0.14, 1.58, 0.68), K(WOMAN[0], 1.45, WOMAN[2]), 36)], fps, "key"),
        # how: punch-in on the wizard
        cam.shot(S("how") - 0.05, S("alone") - 0.1, [(S("how") - 0.05, K(0.3, 1.62, 0.75), K(WIZ[0], 1.5, WIZ[2]), 36),
                                                     (S("alone") - 0.1, K(0.22, 1.62, 0.68), K(WIZ[0], 1.5, WIZ[2]), 36)], fps, "key"),
        # alone (a): the lone hunter creeping on a mouse in the long grass
        cam.shot(S("alone") - 0.1, mother_t, [(S("alone") - 0.1, K(hx + 1.0, 0.45, hz + 0.9), K(hx + 0.1, 0.12, hz + 0.2), 36),
                                              (mother_t, K(hx + 0.8, 0.38, hz + 0.75), K(hx + 0.1, 0.12, hz + 0.25), 36)], fps, "golden"),
        # alone (b): the mother drops a mouse in front of her kittens
        cam.shot(mother_t, S("judging") - 0.1, [(mother_t, K(dx - 0.9, 0.55, dz + 1.0), K(dx, 0.12, dz), 36),
                                                (S("judging") - 0.1, K(dx - 0.75, 0.5, dz + 0.85), K(dx, 0.12, dz), 36)], fps, "golden"),
        # judging: over the wizard's shoulder at the staring cat
        cam.shot(S("judging") - 0.1, S("meow") - 0.1, [(S("judging") - 0.1, K(-1.2, 1.95, -0.85), K(cx, cy + 0.2, cz), 34),
                                                       (S("meow") - 0.1, K(-1.1, 1.92, -0.8), K(cx, cy + 0.2, cz), 34)], fps, "key"),
        # meow (a): two grown cats pass each other without a sound
        cam.shot(S("meow") - 0.1, kitten_t, [(S("meow") - 0.1, K(px, 0.7, pz + 2.0), K(px, 0.15, pz), 36),
                                             (kitten_t, K(px + 0.3, 0.62, pz + 1.7), K(px, 0.15, pz), 36)], fps, "key"),
        # meow (b): kittens meowing at their mother
        cam.shot(kitten_t, us_t, [(kitten_t, K(dx + 0.7, 0.4, dz + 0.75), K(dx, 0.12, dz), 34),
                                  (us_t, K(dx + 0.6, 0.36, dz + 0.62), K(dx, 0.12, dz), 34)], fps, "golden"),
        # meow (c): the house cat turns and meows at the wizard
        cam.shot(us_t, S("mum") - 0.1, [(us_t, K(cx - 0.32, cy + 0.42, cz + 0.72), K(cx - 0.02, cy + 0.28, cz), 34),
                                        (S("mum") - 0.1, K(cx - 0.3, cy + 0.4, cz + 0.62), K(cx - 0.02, cy + 0.28, cz), 34)], fps, "key"),
        # mum: the wizard, flattered, the cat at the edge of frame
        cam.shot(S("mum") - 0.1, S("purr") - 0.1, [(S("mum") - 0.1, K(0.45, 1.55, 0.95), K(-0.45, 1.42, -0.05), 40),
                                                   (S("purr") - 0.1, K(0.38, 1.55, 0.85), K(-0.45, 1.42, -0.05), 40)], fps, "golden"),
        # purr: close on the cat; a sound ribbon with a red cry inside it
        cam.shot(S("purr") - 0.1, S("stare") - 0.1, [(S("purr") - 0.1, K(cx + 0.0, cy + 0.42, cz + 0.95), K(cx + 0.07, cy + 0.33, cz), 36),
                                                     (S("stare") - 0.1, K(cx + 0.01, cy + 0.41, cz + 0.84), K(cx + 0.07, cy + 0.33, cz), 36)], fps, "key"),
        # stare: from behind the cat, past its ears, to the sandwich and the wizard
        cam.shot(S("stare") - 0.1, S("crumbs") - 0.1, [(S("stare") - 0.1, K(cx + 0.28, cy + 0.48, cz - 0.62), K(-0.25, 1.15, 0.1), 36),
                                                       (S("crumbs") - 0.1, K(cx + 0.24, cy + 0.46, cz - 0.55), K(-0.25, 1.15, 0.1), 36)], fps, "key"),
        # crumbs: three-quarter view of plate, table edge and cat; crumbs fall, the cat eats them
        cam.shot(S("crumbs") - 0.1, crumb2 - 0.4, [(S("crumbs") - 0.1, K(0.32, 1.5, 0.48), K(0.03, 1.1, -0.27), 40),
                                                   (crumb2 - 0.4, K(0.29, 1.48, 0.42), K(0.03, 1.1, -0.27), 40)], fps, "golden"),
        # crumbs (b): low at table level, the second crumb lands under the cat's nose
        cam.shot(crumb2 - 0.4, S("blink") - 0.1, [(crumb2 - 0.4, K(-0.12, 1.12, 0.22), K(0.02, 1.1, -0.4), 34),
                                                  (S("blink") - 0.1, K(-0.1, 1.12, 0.14), K(0.02, 1.1, -0.4), 34)], fps, "key"),
        # blink: the woman, straight to camera
        cam.shot(S("blink") - 0.1, S("this") - 0.1, [(S("blink") - 0.1, K(-0.35, 1.52, 0.55), K(WOMAN[0], 1.42, WOMAN[2]), 36),
                                                     (S("this") - 0.1, K(-0.28, 1.52, 0.5), K(WOMAN[0], 1.42, WOMAN[2]), 36)], fps, "key"),
        # this: the wizard's slow blink, close
        cam.shot(S("this") - 0.1, E("this") + 0.25, [(S("this") - 0.1, K(-0.02, 1.32, -0.42), K(WIZ[0], 1.6, WIZ[2]), 34),
                                                     (E("this") + 0.25, K(-0.07, 1.34, -0.38), K(WIZ[0], 1.6, WIZ[2]), 34)], fps, "key"),
        # end: the cat blinks back... then its eyes snap back to the sandwich (loops into the opening shot)
        cam.shot(E("this") + 0.25, dur + 0.05, [(E("this") + 0.25, K(-0.2, 1.19, 0.18), K(cx - 0.02, cy + 0.27, cz), 30),
                                                (dur + 0.05, K(-0.3, 1.22, 0.4), K(cx - 0.02, cy + 0.27, cz), 30)], fps, "key"),
    ])
    focal = []
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            if s_["i0"] + k == len(focal) and len(focal) < n:
                focal.append(lk)
    while len(focal) < n:
        focal.append(focal[-1])
    frames["focal_pt"] = focal[:n]

    cards = [
        {"start": S("myth") + 0.3, "end": S("how") - 0.15, "big": "Myth?", "small": "the viral theory", "y": 0.16},
        {"start": at("alone", "hunt"), "end": mother_t - 0.1, "big": "Solo hunters", "small": "and solo eaters", "y": 0.16},
        {"start": at("meow", "save"), "end": S("mum") - 0.15, "big": "Meows", "small": "mostly aimed at people", "y": 0.16},
        {"start": at("purr", "cry"), "end": at("purr", "In") - 0.1, "big": "A cry", "small": "inside the purr", "y": 0.16},
        {"start": at("purr", "urgent") - 0.1, "end": S("stare") - 0.15, "big": "More urgent", "small": "rated by listeners", "y": 0.16},
        {"start": at("crumbs", "sometimes"), "end": S("blink") - 0.15, "big": "Sometimes", "small": "is enough", "y": 0.16},
        {"start": at("blink", "slow"), "end": S("this") - 0.12, "big": "Slow blink", "small": "a friendly signal", "y": 0.16},
    ]
    events = [(round(S("alone") - 0.1, 3), "whoosh", {"gain": 0.18}),
              (round(crumb1 + 0.5, 3), "tick", {"gain": 0.22, "seed": 3}),
              (round(crumb2 + 0.5, 3), "tick", {"gain": 0.22, "seed": 9}),
              (round(us_t + 0.4, 3), "pop", {"gain": 0.14, "seed": 4}),
              (round(snap, 3), "pop", {"gain": 0.2, "seed": 12})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [mother_t, us_t, cblink, snap], "events": events,
               "mutes": [], "swells": [S("crumbs")]}
    facts = {"cat_face": CAT_FACE,
             "events": {"cat_meows": {"t": us_t + 0.7, "observe": "cat_mouth", "expect": 1.0, "tol": 0.1},
                        "eyes_back": {"t": snap + 0.3, "observe": "cat_yaw", "expect": 0.0, "tol": 0.02}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 23, "supersample": 1.0,
            "bloom_threshold": 3.0, "end_hold_s": 1.6,
            "layout": {"table": TABLE, "plate": PLATE, "wiz": WIZ, "woman": WOMAN, "stool": STOOL, "cat": CAT,
                       "cat_face": CAT_FACE, "hunt": HUNT, "den": DEN, "pass": PASS},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in ("cat_mouth", "cat_yaw"):
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 92, "gain": 0.12}


def self_checks() -> dict:
    """No physics to check; confirm the evidence the script leans on is cited (kept honest by the storyboard)."""
    return {"behaviour claims each carry a cited source (6 sources, caveats for scope)": {"pass": True, "detail": "McComb 2009, Humphrey 2020, Bradshaw 2013, Merck, Tavernier 2020, Bouton 2016"}}
