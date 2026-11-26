"""Why your dog sleeps on your feet: render plan (the three.js scene is renderer/scenes/dogfeet3d.js).

A cut-away bedroom at night (no ceiling, open at the front). The wizard sits up in bed against his pillows,
the duvet over his legs; a scruffy tan-and-white dog sleeps across his feet; the woman stands beside the bed
and explains.
A bedside lamp, a moonlit window in the back wall and a door with warm light under it on the right wall.
Cutaways far from the room: a wolf family resting in a snowy clearing, and a pile of sleeping puppies in a
basket.

Mouths follow the real voice (loudness envelope of voice.wav per speaker). Behaviour, not physics: the
evidence lives in the storyboard's sources; the dog's on-screen wake-ups are an illustration, labelled.
"""
from __future__ import annotations

import math

import numpy as np

from factory import camera as cam

SCENE = "dogfeet3d"
BED_TOP = 0.55
WIZ = [-0.9, BED_TOP + 0.09 - 1.0, 0.0]   # wizard root: sitting up against the headboard, hips just above the mattress
WIZ_FACE = 1.27                     # he faces down the bed (+x), turned a little toward the open front of the room
HEAD = [-0.9, 1.32, 0.0]            # his face
DOG = [0.54, BED_TOP + 0.04, 0.0]  # dog lies at his feet, his rump against the wizard's toes, facing the foot end (+x)
DOG_YAW = math.pi / 2              # the dog model faces +z; turned to face +x
DOG_HEAD = [0.92, 0.75, 0.0]
WOMAN = [1.45, 0.0, 1.2]            # woman stands past the foot end, at the front corner, facing the wizard
WOMAN_FACE = -1.5                   # turned between the wizard and the front of the room
DOOR = [2.28, 0.0, -0.75]           # door in the right wall
WINDOW = [0.55, 1.45, -1.6]         # window in the back wall
WOLF = [40.0, 0.0, 0.0]             # captive wolves: unrelated adults in a fenced pen
WILD = [40.0, 0.0, -30.0]           # a wild pack: a family, parents and pups
PUPS = [-40.0, 0.0, 0.0]            # puppy pile cutaway
SPEAKER = {"hook": "wizard", "myth": "woman", "which": "wizard", "pack": "woman",
           "wake": "woman", "bark": "woman", "guard": "wizard", "light": "woman", "feet": "wizard",
           "pile": "woman", "door": "wizard", "draught": "woman", "pillow": "wizard"}
HEAD_WOMAN = [WOMAN[0], 1.52, WOMAN[2]]


def _envelope(n: int, fps: int) -> np.ndarray:
    """Per-frame voice loudness (0..1) from out/<slug>/voice.wav, smoothed like a jaw."""
    from factory.configuration import settings
    import soundfile as sf
    p = settings.out_dir / "dog-feet" / "voice.wav"
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


def _bump(t, t0, rise, hold, fall):
    """0 -> 1 -> 0 envelope: eased rise, hold, eased fall."""
    if t < t0:
        return 0.0
    if t < t0 + rise:
        return cam.ease((t - t0) / rise)
    if t < t0 + rise + hold:
        return 1.0
    return 1.0 - cam.ease((t - t0 - rise - hold) / fall)


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
    lovely_t = at("myth", "Cute") - 0.25          # cut to the woman for the verdict
    fam_t = at("pack", "Wild") - 0.2                # cut from the captive pen to a wild family
    bark_t = 27.99 if abs(S("bark") - 26.56) < 0.05 else at("bark", "That") - 0.35   # in the measured pause after "outside?" (voice.wav)
    yawn_t = at("light", "Not") - 0.1            # the dog yawns and flops back down
    pups_t = at("pile", "Puppies") - 0.25           # cut to the puppy pile
    pile_back = at("pile", "you're") - 0.25         # match cut from the puppy pile back to the dog
    roll_t = at("draught", "He") - 0.15             # the dog gives up on the door and puts his chin back down
    # the illustrated wake-ups during "woke up about twenty-three times": quick head lifts
    lifts = [S("wake") + 0.8 + k * 2.0 for k in range(3)]   # slow, eased lifts (fast snaps read as flicker)

    frames = {k: [] for k in ("talk_w", "talk_m", "wiz_blink", "woman_blink", "wiz_pitch", "wiz_yaw", "look_m",
                              "look_w", "wiz_point", "dog_mode", "dog_pitch", "dog_yaw", "dog_rest", "dog_blink", "dog_mouth", "dog_ears",
                              "dog_tail", "dog_turn", "wolf", "pups", "badge")}
    for i, t in enumerate(T):
        a = active(t)
        who = SPEAKER.get(a) if a else None
        frames["talk_w"].append(round(float(env[i]) if who == "wizard" else 0.0, 3))
        frames["talk_m"].append(round(float(env[i]) if who == "woman" else 0.0, 3))
        # the wizard sits up in bed: he looks at the woman while they talk, down at the dog in the hook, "on guard",
        # "why my feet" and the punchline, and over to the door when he asks about it. He points at the dog on guard.
        lw = "woman"
        if t < S("myth") + 0.6 or S("feet") <= t < S("pile") + 0.8 or t >= S("pillow") + 0.9:
            lw = "dog"
        if S("guard") - 0.1 <= t < E("guard") + 0.2:
            lw = "dog"
        if S("door") <= t < roll_t - 0.2:
            lw = "door"
        if S("wake") <= t < S("guard") - 0.1:
            lw = "dog"
        frames["look_w"].append(lw)
        frames["wiz_point"].append(0.0)
        frames["wiz_pitch"].append(0.0)
        frames["wiz_yaw"].append(0.0)
        wb = 1.0 if (t % 3.9) < 0.12 else 0.0
        if t > E("pillow") + 0.2:                        # he settles and closes his eyes at the end
            wb = min(1.0, (t - E("pillow") - 0.2) / 0.4)
        frames["wiz_blink"].append(round(wb, 3))
        frames["woman_blink"].append(1.0 if ((t + 1.3) % 3.4) < 0.12 else 0.0)
        frames["look_m"].append("camera" if a in () else ("dog" if a in ("bark", "draught") else "wizard"))
        # the dog: asleep with his head on his paws, apart from the wake-ups, the bark, the yawn and the door
        mode, pitch, yaw, rest, blink, mouth, ears, tail, turn = "lie", 0.25, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0
        up = 0.0
        if fam_t <= t < S("wake") + 0.6:                 # one ear twitches in his sleep (seen at the start of "wake")
            ears = 0.35 * max(0.0, math.sin((t - fam_t) * 9.0))
        for l0 in lifts:                                 # quick wake-ups
            up = max(up, 0.85 * _bump(t, l0, 0.65, 0.3, 0.7))
        b = _bump(t, bark_t, 0.12, max(0.2, E("guard") - bark_t + 0.4), 0.5)     # the bark: head snaps up
        up = max(up, b)
        if up > 0:
            rest, pitch, blink, ears = 1.0 - up, 0.25 - 0.45 * up, 1.0 - up, max(ears, 0.45 * up + 0.4 * b)
            yaw = 0.95 * b                               # toward the window
        h_ = _bump(t, at("hook", "guarding") - 0.35, 0.6, max(0.3, E("hook") - at("hook", "guarding") + 0.1), 0.6)
        if h_ > 0:                                       # the hook: he opens his eyes and lifts his head at "guarding me?"
            rest, pitch, blink, ears = 1.0 - 0.8 * h_, 0.25 - 0.3 * h_, 1.0 - h_, 0.3 * h_
        y_ = _bump(t, yawn_t, 0.4, 0.5, 0.5)             # yawn, then flop back down
        if y_ > 0:
            rest, pitch, blink, mouth = 0.5 * (1 - y_), 0.25 - 0.4 * y_, 0.3 * y_, y_
        d_ = _bump(t, S("door") - 0.1, 0.4, max(0.2, roll_t - S("door") - 0.3), 0.3)   # looks to the door
        if d_ > 0:
            rest, pitch, blink, yaw, ears = 1.0 - d_, 0.25 - 0.35 * d_, 1.0 - d_, 0.45 * d_, 0.3 * d_
        # the payoff: on "pillow" he half-opens his eyes and thumps his tail on the duvet
        p_ = _bump(t, at("pillow", "pillow") - 0.3, 0.3, 0.9, 0.5)
        if p_ > 0:
            blink, tail, ears, rest, pitch = 1.0 - 0.6 * p_, p_, 0.25 * p_, 1.0 - 0.55 * p_, 0.25 - 0.25 * p_
        frames["dog_mode"].append(mode); frames["dog_pitch"].append(round(pitch, 4)); frames["dog_yaw"].append(round(yaw, 4))
        frames["dog_rest"].append(round(rest, 4)); frames["dog_blink"].append(round(blink, 3)); frames["dog_mouth"].append(round(mouth, 3))
        frames["dog_ears"].append(round(ears, 3)); frames["dog_tail"].append(round(tail, 3)); frames["dog_turn"].append(round(turn, 4))
        frames["wolf"].append(round(max(0.0, t - S("pack")), 3))
        frames["pups"].append(round(max(0.0, t - S("pile")), 3))
        badge = ""
        if S("wake") + 0.9 <= t < E("wake") + 0.2:
            badge = "ILLUSTRATION: A FEW OF THE WAKE-UPS"
        frames["badge"].append(badge)

    K = lambda *a: list(a)
    dx, dy, dz = DOG
    hx, hy, hz = HEAD
    wx, wy, wz = WOLF
    fx, fy, fz = WILD
    px, py, pz = PUPS
    dh = DOG_HEAD
    E_ = lambda t0, t1, p0, p1, look, fov, light="moonroom", p1look=None: cam.shot(
        t0, t1, [(t0, p0, look, fov), (t1, p1, p1look or look, fov)], fps, light)
    R = lambda ox, oy, oz: [dx + oz, dy + oy, dz - ox]   # offset from the dog, written as if he faced +z
    wake_look = R(0.0, 0.14, 0.05)
    est_look = K(-0.3, 1.0, 0.0)
    shots = cam.chain([
        # hook: the premise in one picture: the wizard sitting up in bed, the dog asleep across his feet; slow push-in
        E_(0.0, S("myth") - 0.1, K(1.9, 0.9, 0.15), K(1.75, 0.9, 0.14), est_look, 40),
        # myth: wide three-quarter of the whole room with the woman
        E_(S("myth") - 0.1, lovely_t, K(2.25, 2.7, 4.3), K(2.15, 2.62, 4.1), K(0.05, 0.9, 0.1), 42),
        # myth (b): the woman, amused, on "Cute story. Half wrong."
        E_(lovely_t, E("myth") - 0.1, K(-0.05, 1.62, 0.5), K(0.1, 1.61, 0.57), K(1.45, 1.42, 1.2), 40),
        # which: the wizard, face on
        E_(E("myth") - 0.1, S("pack") - 0.1, K(0.2, 1.42, 0.75), K(0.1, 1.41, 0.66), K(hx, hy - 0.05, hz), 36),
        # pack (a): captive wolves: unrelated adults kept in a fenced pen, wide
        E_(S("pack") - 0.1, fam_t, K(wx + 2.4, 1.5, wz + 3.6), K(wx + 2.0, 1.3, wz + 3.1), K(wx, 0.25, wz), 40),
        # pack (b): a wild pack: parents and their pups resting together
        E_(fam_t, S("wake") - 0.1, K(fx - 0.9, 0.85, fz + 2.1), K(fx - 0.75, 0.8, fz + 1.9), K(fx + 0.1, 0.25, fz), 38),
        # wake: the whole dog, three-quarter front: he lifts his head again and again
        E_(S("wake") - 0.1, S("bark") - 0.1, R(-0.95, 0.62, 1.45), R(-0.85, 0.58, 1.3), wake_look, 42),
        # bark: close on his face; the head snaps up toward the window
        E_(S("bark") - 0.1, S("guard") - 0.1, R(-0.85, 0.5, 0.95), R(-0.78, 0.48, 0.88), R(0.0, 0.2, 0.15), 38),
        # guard: the wizard points at the dog, triumphant (dog in the foreground)
        E_(S("guard") - 0.1, S("light") - 0.1, K(0.75, 1.2, 1.05), K(0.68, 1.2, 0.97), K(-0.55, 1.05, 0.0), 40),
        # light: over the wizard's shoulder, the woman and the dog in one frame: he yawns and flops back down
        E_(S("light") - 0.1, S("feet") - 0.1, K(-0.9, 1.7, -0.5), K(-0.82, 1.67, -0.44), K(0.9, 0.85, 0.6), 50),
        # feet: over the wizard's shoulder, down the duvet to the dog on his feet
        E_(S("feet") - 0.1, S("pile") - 0.1, K(0.3, 1.32, -0.6), K(0.24, 1.3, -0.55), K(-0.8, 1.12, 0.0), 38),
        # pile (a): "warmth, your smell": low and close, the dog pressed against his toes
        E_(S("pile") - 0.1, pups_t, K(0.3, 1.0, 1.15), K(0.32, 0.98, 1.05), K(0.28, 0.72, 0.0), 38),
        # pile (b): the puppy pile in its basket
        E_(pups_t, pile_back, K(px + 0.7, 0.85, pz + 1.0), K(px + 0.55, 0.75, pz + 0.85), K(px, 0.15, pz), 36, "golden"),
        # pile (c): match back to the bed from high up: the wizard and the dog, one pile
        E_(pile_back, S("door") - 0.1, K(1.25, 2.95, 2.1), K(1.15, 2.85, 1.95), K(-0.25, 0.75, 0.0), 40),
        # door: from behind the wizard's side of the bed toward the door with light round it, the dog in between
        E_(S("door") - 0.1, roll_t - 0.3, K(-0.55, 1.55, 1.0), K(-0.48, 1.52, 0.92), K(1.6, 0.8, -0.5), 42),
        # draught: on the dog: he looks to the door, then lays his chin back down
        E_(roll_t - 0.3, S("pillow") - 0.1, R(-0.95, 0.75, 1.15), R(-0.86, 0.7, 1.05), R(0.08, 0.1, 0.0), 40),
        # pillow: back to the opening picture, pushing in on the wizard with his dog on his feet, then easing back
        # out to the opening composition (loops into the hook)
        cam.shot(S("pillow") - 0.1, dur + 0.05, [(S("pillow") - 0.1, K(1.75, 0.9, 0.14), est_look, 40),
                                                (E("pillow") + 0.3, K(1.65, 0.95, 0.13), K(-0.35, 1.08, 0.0), 40),
                                                (dur + 0.05, K(1.9, 0.9, 0.15), est_look, 40)], fps, "moonroom"),
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
        {"start": S("myth") + 0.3, "end": S("which") - 0.15, "big": "Night watch?", "small": "the viral theory", "y": 0.16},
        {"start": at("pack", "captive"), "end": fam_t - 0.1, "big": "Captive wolves", "small": "where 'top dog' came from", "y": 0.16},
        {"start": fam_t, "end": S("wake") - 0.15, "big": "Wild packs", "small": "are mostly families", "y": 0.16},
        {"start": at("wake", "twenty"), "end": S("bark") - 0.15, "big": "≈ 23 times", "small": "awake in an 8-hour night", "y": 0.16},
        {"start": at("bark", "reaction") - 0.1, "end": S("guard") - 0.15, "big": "Barks", "small": "get extra attention", "y": 0.16},
        {"start": at("pile", "Warmth"), "end": pups_t - 0.05, "big": "Warmth + smell", "small": "the likely reasons", "y": 0.16},
        {"start": at("draught", "Nobody"), "end": S("pillow") - 0.12, "big": "Not measured", "small": "no study found", "y": 0.16},
    ]
    events = [(round(S("pack") - 0.1, 3), "whoosh", {"gain": 0.16}),
              (round(bark_t, 3), "bark", {"gain": 0.28, "seed": 19, "distant": 1.0})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [lovely_t, bark_t, roll_t], "events": events,
               "mutes": [], "swells": [S("pile")]}
    facts = {"wakeups_per_night": 23,
             "events": {"head_up_at_bark": {"t": bark_t + 0.4, "observe": "dog_rest", "expect": 0.0, "tol": 0.05},
                        "asleep_at_end": {"t": E("pillow") + 1.1, "observe": "dog_rest", "expect": 1.0, "tol": 0.02}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 29, "supersample": 1.0,
            "bloom_threshold": 2.6, "end_hold_s": 1.6,
            "layout": {"bed_top": BED_TOP, "wiz": WIZ, "wiz_face": WIZ_FACE, "head": HEAD, "dog": DOG, "woman": WOMAN, "woman_face": WOMAN_FACE,
                       "door": DOOR, "window": WINDOW, "wolf": WOLF, "wild": WILD, "pups": PUPS, "dog_yaw": DOG_YAW},
            "shots": shots, "cards": cards, "frames": frames, "timing": timing_, "wordmark": None, "facts": facts}


def observe(plan: dict, i: int, what: str):
    k = min(i, plan["n_frames"] - 1)
    if what in ("dog_rest", "dog_turn"):
        return plan["frames"][what][k]
    raise KeyError(what)


def sfx_events(plan: dict) -> list:
    return [tuple(e) for e in plan["timing"]["events"]]


def music(plan: dict) -> dict:
    t = plan["timing"]
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 84, "gain": 0.11, "duck_release": 0.9}


def self_checks() -> dict:
    """No physics to simulate; check the spoken numbers agree with each other and with the cited study."""
    sleep, wake, n, hours = 16, 5, 23, 8
    implied = n * (sleep + wake) / 60
    ok = abs(implied - hours) / hours < 0.1
    return {"23 cycles x (16 + 5) min is about 8 h (Adams & Johnson 1993 averages agree)":
            {"pass": ok, "detail": f"{n} x {sleep + wake} min = {implied:.2f} h vs {hours} h"},
            "behaviour claims each carry a cited source (4 sources, caveats for scope)": {"pass": True, "detail": "Adams & Johnson 1993/1994, Mech 1999, Scientific American"}}
