"""Why your dog sleeps on your feet: render plan (the three.js scene is renderer/scenes/dogfeet3d.js).

A cut-away bedroom at night (no ceiling, open at the front). The wizard lies in bed under a duvet, head on
the pillow; a scruffy tan-and-white dog sleeps across his feet; the woman stands beside the bed and explains.
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
WIZ = [0.84, 0.72, 0.0]             # wizard root (his feet), lying along -x with his face up
HEAD = [-0.86, 0.84, 0.0]           # his head on the pillow
DOG = [0.76, 0.86, -0.02]           # dog lies across his feet (body along z), facing +z
DOG_HEAD = [0.76, 1.14, 0.3]
WOMAN = [1.62, 0.0, 0.62]           # woman stands at the foot end, front side, facing the wizard
WOMAN_FACE = -0.95                   # turned between the wizard and the front of the room
DOOR = [2.28, 0.0, -0.75]           # door in the right wall
WINDOW = [0.55, 1.45, -1.6]         # window in the back wall
WOLF = [40.0, 0.0, 0.0]             # wolf family cutaway
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
    fam_t = at("pack", "families") - 0.3            # closer on the wolf pups
    bark_t = at("bark", "bark") + 0.05              # the bark outside
    yawn_t = at("light", "Not") - 0.1            # the dog yawns and flops back down
    pups_t = at("pile", "Puppies") - 0.25           # cut to the puppy pile
    pile_back = at("pile", "you're") - 0.25         # match cut from the puppy pile back to the dog
    roll_t = at("draught", "He") - 0.15             # the dog rolls over to face the wall
    # the illustrated wake-ups during "woke up about twenty-three times": quick head lifts
    lifts = [S("wake") + 1.0 + k * 1.05 for k in range(5)]

    frames = {k: [] for k in ("talk_w", "talk_m", "wiz_blink", "woman_blink", "wiz_pitch", "wiz_yaw", "look_m",
                              "dog_mode", "dog_pitch", "dog_yaw", "dog_rest", "dog_blink", "dog_mouth", "dog_ears",
                              "dog_tail", "dog_turn", "wolf", "pups", "badge")}
    for i, t in enumerate(T):
        a = active(t)
        who = SPEAKER.get(a) if a else None
        frames["talk_w"].append(round(float(env[i]) if who == "wizard" else 0.0, 3))
        frames["talk_m"].append(round(float(env[i]) if who == "woman" else 0.0, 3))
        # the wizard: head on the pillow, turned toward the woman when they talk; he lifts it to look at
        # the dog in the hook, "on guard" and the punchline
        lift = max(_bump(t, S("hook") + 0.2, 0.5, max(0.1, E("hook") - S("hook") - 1.0), 0.5),
                   _bump(t, S("guard") - 0.1, 0.25, max(0.1, E("guard") - S("guard") - 0.2), 0.5),
                   _bump(t, S("feet") - 0.1, 0.3, max(0.1, E("feet") - S("feet")), 0.5),
                   _bump(t, S("pillow") - 0.1, 0.4, 0.6, 0.6))
        frames["wiz_pitch"].append(round(0.75 * lift, 4))
        frames["wiz_yaw"].append(round(-0.55 * (1 - lift), 4))
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
            up = max(up, _bump(t, l0, 0.18, 0.4, 0.3))
        b = _bump(t, bark_t, 0.12, max(0.2, E("guard") - bark_t + 0.4), 0.5)     # the bark: head snaps up
        up = max(up, b)
        if up > 0:
            rest, pitch, blink, ears = 1.0 - up, 0.25 - 0.45 * up, 1.0 - up, max(ears, 0.45 * up + 0.4 * b)
            yaw = -0.5 * b                               # toward the window
        y_ = _bump(t, yawn_t, 0.4, 0.5, 0.5)             # yawn, then flop back down
        if y_ > 0:
            rest, pitch, blink, mouth = 0.5 * (1 - y_), 0.25 - 0.4 * y_, 0.3 * y_, y_
        d_ = _bump(t, S("door") - 0.1, 0.4, max(0.2, roll_t - S("door") - 0.3), 0.3)   # looks to the door
        if d_ > 0:
            rest, pitch, blink, yaw, ears = 1.0 - d_, 0.25 - 0.35 * d_, 1.0 - d_, 1.15 * d_, 0.3 * d_
        if t >= roll_t:                                  # rolls over, curls up facing the wall
            turn = cam.ease((t - roll_t) / 0.7)
            if turn > 0.5:
                mode, blink, rest, pitch, yaw = "curl", 1.0, 1.0, 0.0, 0.0
        if S("hook") <= t < S("myth") or t >= E("pillow"):
            tail = 0.0
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
    px, py, pz = PUPS
    dh = DOG_HEAD
    shots = cam.chain([
        # hook: low across the duvet to the dog asleep on the wizard's feet, slow push-in; his face beyond
        cam.shot(0.0, S("myth") - 0.1, [(0.0, K(1.75, 1.2, 1.55), K(dx - 0.1, dy + 0.12, dz + 0.05), 34),
                                        (S("myth") - 0.1, K(1.5, 1.15, 1.25), K(dx - 0.15, dy + 0.12, dz + 0.05), 34)], fps, "moonroom"),
        # myth: wide three-quarter of the whole room
        cam.shot(S("myth") - 0.1, lovely_t, [(S("myth") - 0.1, K(2.0, 2.7, 4.6), K(0.25, 0.75, -0.25), 42),
                                             (lovely_t, K(1.75, 2.6, 4.3), K(0.25, 0.75, -0.25), 42)], fps, "moonroom"),
        # myth (b): the woman, amused, on "Cute story. Half wrong."
        cam.shot(lovely_t, E("myth") - 0.1, [(lovely_t, K(-0.1, 1.65, 3.3), K(1.35, 1.05, 0.4), 40),
                                               (E("myth") - 0.1, K(0.05, 1.62, 3.15), K(1.35, 1.05, 0.4), 40)], fps, "moonroom"),
        # which: the wizard on his pillow, close, from above the front edge of the bed
        cam.shot(E("myth") - 0.1, S("pack") - 0.1, [(E("myth") - 0.1, K(hx + 0.05, hy + 0.5, hz + 0.95), K(hx + 0.02, hy + 0.06, hz), 34),
                                                     (S("pack") - 0.1, K(hx + 0.05, hy + 0.48, hz + 0.86), K(hx + 0.02, hy + 0.06, hz), 34)], fps, "moonroom"),
        # pack (a): the wolf family resting in the snow, wide
        cam.shot(S("pack") - 0.1, fam_t, [(S("pack") - 0.1, K(wx + 2.4, 1.5, wz + 3.6), K(wx, 0.25, wz), 40),
                                          (fam_t, K(wx + 2.0, 1.3, wz + 3.1), K(wx, 0.25, wz), 40)], fps, "winter"),
        # pack (b): closer on the parents and pups: a family
        cam.shot(fam_t, S("wake") - 0.1, [(fam_t, K(wx - 0.9, 0.7, wz + 1.9), K(wx + 0.1, 0.25, wz), 36),
                                          (S("wake") - 0.1, K(wx - 0.75, 0.65, wz + 1.7), K(wx + 0.1, 0.25, wz), 36)], fps, "winter"),
        # wake (a): straight down over the bed, slowly rotating: the dog lifts his head again and again
        cam.shot(S("wake") - 0.1, S("bark") - 0.1, [(S("wake") - 0.1, K(2.7, 3.4, -0.35), K(0.05, 0.7, 0.0), 40),
                                                    (S("bark") - 0.1, K(2.5, 3.2, -0.6), K(0.05, 0.7, 0.0), 40)], fps, "moonroom"),
        # bark: from the window side, the dog's head snaps up toward the window
        cam.shot(S("bark") - 0.1, S("guard") - 0.1, [(S("bark") - 0.1, K(dx - 0.65, dy + 0.55, dz + 1.15), K(dx + 0.05, dy + 0.2, dz + 0.15), 34),
                                                     (S("guard") - 0.1, K(dx - 0.58, dy + 0.52, dz + 1.05), K(dx + 0.05, dy + 0.2, dz + 0.15), 34)], fps, "moonroom"),
        # guard: the wizard lifts his head, triumphant
        cam.shot(S("guard") - 0.1, S("light") - 0.1, [(S("guard") - 0.1, K(hx + 0.75, hy + 0.5, hz + 0.6), K(hx + 0.08, hy + 0.12, hz), 36),
                                                      (S("light") - 0.1, K(hx + 0.68, hy + 0.48, hz + 0.55), K(hx + 0.08, hy + 0.12, hz), 36)], fps, "moonroom"),
        # light: medium on the dog: yawns and flops back down
        cam.shot(S("light") - 0.1, S("feet") - 0.1, [(S("light") - 0.1, K(dx + 0.9, dy + 0.55, dz + 1.3), K(dx, dy + 0.1, dz + 0.1), 38),
                                                     (S("feet") - 0.1, K(dx + 0.8, dy + 0.5, dz + 1.18), K(dx, dy + 0.1, dz + 0.1), 38)], fps, "moonroom"),
        # feet: over the wizard's head, down the duvet to the dog on his feet
        cam.shot(S("feet") - 0.1, S("pile") - 0.1, [(S("feet") - 0.1, K(hx - 0.05, hy + 0.85, hz + 0.3), K(dx - 0.05, dy + 0.1, dz), 30),
                                                    (S("pile") - 0.1, K(hx + 0.05, hy + 0.82, hz + 0.28), K(dx - 0.05, dy + 0.1, dz), 30)], fps, "moonroom"),
        # pile (a): "warmth, your smell": low and close along the duvet, the dog's nose against the toes
        cam.shot(S("pile") - 0.1, pups_t, [(S("pile") - 0.1, K(dx + 0.55, dy + 0.45, dz + 1.3), K(dx - 0.1, dy + 0.1, dz + 0.05), 34),
                                           (pups_t, K(dx + 0.48, dy + 0.42, dz + 1.18), K(dx - 0.1, dy + 0.1, dz + 0.05), 34)], fps, "moonroom"),
        # pile (b): the puppy pile in its basket
        cam.shot(pups_t, pile_back, [(pups_t, K(px + 0.7, 0.85, pz + 1.0), K(px, 0.15, pz), 36),
                                     (pile_back, K(px + 0.55, 0.75, pz + 0.85), K(px, 0.15, pz), 36)], fps, "golden"),
        # pile (b): match cut back to the dog on the feet
        cam.shot(pile_back, S("door") - 0.1, [(pile_back, K(dx + 0.55, dy + 0.75, dz + 0.85), K(dx, dy + 0.1, dz), 36),
                                              (S("door") - 0.1, K(dx + 0.5, dy + 0.7, dz + 0.78), K(dx, dy + 0.1, dz), 36)], fps, "moonroom"),
        # door: from behind the dog toward the door with light under it
        cam.shot(S("door") - 0.1, roll_t - 0.3, [(S("door") - 0.1, K(0.05, 1.5, 0.85), K(1.55, 0.95, -0.45), 42),
                                                 (roll_t - 0.3, K(0.12, 1.47, 0.78), K(1.55, 0.95, -0.45), 42)], fps, "moonroom"),
        # draught: the dog rolls over and curls up facing the wall
        cam.shot(roll_t - 0.3, S("pillow") - 0.1, [(roll_t - 0.3, K(dx + 1.0, dy + 0.75, dz + 1.25), K(dx, dy + 0.08, dz), 38),
                                                   (S("pillow") - 0.1, K(dx + 0.9, dy + 0.7, dz + 1.12), K(dx, dy + 0.08, dz), 38)], fps, "moonroom"),
        # pillow: the wizard's punchline, close
        cam.shot(S("pillow") - 0.1, E("pillow") + 0.3, [(S("pillow") - 0.1, K(hx + 0.1, hy + 0.5, hz + 0.9), K(hx + 0.05, hy + 0.08, hz), 32),
                                                        (E("pillow") + 0.3, K(hx + 0.1, hy + 0.48, hz + 0.82), K(hx + 0.05, hy + 0.08, hz), 32)], fps, "moonroom"),
        # end: back to the opening composition (loops into the hook)
        cam.shot(E("pillow") + 0.3, dur + 0.05, [(E("pillow") + 0.3, K(1.6, 1.17, 1.37), K(dx - 0.12, dy + 0.12, dz + 0.05), 34),
                                                 (dur + 0.05, K(1.75, 1.2, 1.55), K(dx - 0.1, dy + 0.12, dz + 0.05), 34)], fps, "moonroom"),
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
              (round(bark_t, 3), "bark", {"gain": 0.5, "seed": 19}),
              (round(S("pile") - 0.1, 3), "whoosh", {"gain": 0.14}),
              (round(roll_t + 0.45, 3), "thud", {"gain": 0.1, "speed": 1.2})]
    timing_ = {"cuts": [s_["start"] for s_ in shots[1:]], "reveals": [lovely_t, bark_t, roll_t], "events": events,
               "mutes": [], "swells": [S("pile")]}
    facts = {"wakeups_per_night": 23,
             "events": {"head_up_at_bark": {"t": bark_t + 0.4, "observe": "dog_rest", "expect": 0.0, "tol": 0.05},
                        "curled_at_end": {"t": E("pillow"), "observe": "dog_turn", "expect": 1.0, "tol": 0.02}}}
    return {"scene": SCENE, "W": W, "H": H, "fps": fps, "n_frames": n, "seed": 29, "supersample": 1.0,
            "bloom_threshold": 2.6, "end_hold_s": 1.6,
            "layout": {"bed_top": BED_TOP, "wiz": WIZ, "head": HEAD, "dog": DOG, "woman": WOMAN, "woman_face": WOMAN_FACE,
                       "door": DOOR, "window": WINDOW, "wolf": WOLF, "pups": PUPS},
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
    return {"mutes": t["mutes"], "swells": t["swells"], "bpm": 84, "gain": 0.11}


def self_checks() -> dict:
    """No physics to simulate; check the spoken numbers agree with each other and with the cited study."""
    sleep, wake, n, hours = 16, 5, 23, 8
    implied = n * (sleep + wake) / 60
    ok = abs(implied - hours) / hours < 0.1
    return {"23 cycles x (16 + 5) min is about 8 h (Adams & Johnson 1993 averages agree)":
            {"pass": ok, "detail": f"{n} x {sleep + wake} min = {implied:.2f} h vs {hours} h"},
            "behaviour claims each carry a cited source (4 sources, caveats for scope)": {"pass": True, "detail": "Adams & Johnson 1993/1994, Mech 1999, Scientific American"}}
