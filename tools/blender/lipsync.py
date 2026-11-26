"""Viseme lip sync and a talking-body layer from word timings (no bpy; any character rig can consume the output).

Audit 3 (2026-11-27): the rough Finn cut drove the mouth from the audio loudness alone, so every syllable was the
same jaw drop into a dark O, the lips never closed on m/b/p, never stretched on "ee", never rounded on "oo", and the
head and hands stayed frozen while he talked. The references' hosts change mouth shape every syllable, show teeth,
smile through lines, and move the head and hands on the stressed words.

  words  = [{'w': 'swore', 's': 0.58, 'e': 1.06}, ...]   (Whisper word timestamps; out/<slug>/words.json)
  track  = visemes(words, n_frames, fps, env=None)        per frame {'vis': {name: weight}, 'jaw': 0..1}
  body   = talk_layer(words, env, n_frames, fps, seed)    per frame head (pitch, yaw, roll) and hand (wrist) degrees

A rig maps viseme names to its own shape keys / bones (see VIS_FINN in render_episode.py). Viseme set (Preston Blair
style, 8 shapes) is enough for a stylised character; more reads as mush at phone size.
"""
import math, random

VISEMES = ('rest', 'MBP', 'FV', 'EE', 'AA', 'OO', 'CONS', 'L')
JAW = {'rest': 0.0, 'MBP': 0.0, 'FV': 0.15, 'EE': 0.3, 'AA': 1.0, 'OO': 0.45, 'CONS': 0.25, 'L': 0.4}

_DIGRAPH = {'th': 'L', 'sh': 'EE', 'ch': 'EE', 'ee': 'EE', 'ea': 'EE', 'oo': 'OO', 'ou': 'OO', 'ow': 'OO', 'oa': 'OO',
            'ph': 'FV', 'qu': 'OO', 'ai': 'EE', 'ay': 'EE', 'oi': 'OO', 'oy': 'OO', 'aw': 'AA', 'au': 'AA'}
_CHAR = {**{c: 'MBP' for c in 'mbp'}, **{c: 'FV' for c in 'fv'}, **{c: 'EE' for c in 'eiy'}, 'a': 'AA',
         **{c: 'OO' for c in 'ouw'}, 'l': 'L', **{c: 'CONS' for c in 'cdgjknqrstxzh'}}
_NUM = {'0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five', '6': 'six', '7': 'seven',
        '8': 'eight', '9': 'nine'}


def phonemes(word):
    """Rough grapheme -> viseme list with relative durations (vowels twice as long as consonants)."""
    w = ''.join(_NUM.get(c, c) for c in word.lower() if c.isalnum())
    out, i = [], 0
    while i < len(w):
        dg = w[i:i + 2]
        if dg in _DIGRAPH:
            v = _DIGRAPH[dg]; i += 2
        else:
            v = _CHAR.get(w[i], 'CONS'); i += 1
        if out and out[-1][0] == v:
            out[-1][1] += 1.0; continue
        out.append([v, 2.0 if v in ('EE', 'AA', 'OO') else 1.0])
    if w.endswith('e') and len(out) > 1 and out[-1][0] == 'EE':      # silent final e
        out.pop()
    return out or [['rest', 1.0]]


def _keys(words):
    """Timeline of (t_start, t_end, viseme), with rests in the gaps."""
    seq = []
    for wd in words:
        ph = phonemes(wd['w']); tot = sum(d for _, d in ph); t = wd['s']; span = max(0.06, wd['e'] - wd['s'])
        for v, d in ph:
            dt = span * d / tot; seq.append((t, t + dt, v)); t += dt
    return seq


def visemes(words, n_frames, fps, env=None, lead=0.04, attack=0.05, release=0.07, smile=0.0):
    """Per-frame viseme weights. The mouth leads the sound by `lead` s (we see shapes before we hear them), each
    shape eases in over `attack` and out over `release` (coarticulation), m/b/p always reach a full closure, and the
    jaw follows the viseme (times the loudness when env is given, so whispers stay small). `smile` is an emotion
    layer added under every shape (0..1)."""
    seq = _keys(words)
    out = []
    j = 0
    for i in range(n_frames):
        t = i / fps + lead
        wts = {v: 0.0 for v in VISEMES}
        while j < len(seq) and seq[j][1] + release < t:
            j += 1
        for k in range(max(0, j - 2), min(len(seq), j + 3)):
            a, b, v = seq[k]
            if t < a - attack or t > b + release:
                continue
            w = 1.0
            if t < a: w = (t - (a - attack)) / attack
            elif t > b: w = 1 - (t - b) / release
            w = w * w * (3 - 2 * w)
            if v == 'MBP' and a <= t <= b: w = 1.0
            wts[v] = max(wts[v], w)
        s = sum(wts.values())
        if s < 1.0: wts['rest'] += 1.0 - s
        else: wts = {k: x / s for k, x in wts.items()}
        loud = 1.0
        if env is not None:
            e = env[min(len(env) - 1, int(i))] if env else 1.0
            loud = 0.55 + 0.45 * min(1.0, e / 0.6)
        jaw = sum(JAW[k] * x for k, x in wts.items()) * loud
        if wts['MBP'] > 0.6: jaw = 0.0
        out.append({'vis': {k: round(x, 3) for k, x in wts.items() if x > 0.01}, 'jaw': round(jaw, 3), 'smile': smile})
    return out


def talk_layer(words, env, n_frames, fps, seed=3, nod=4.0, tilt=2.5, hand=6.0):
    """Head and hand motion that never stops while he talks: a nod (head pitch down then back) on the stressed
    syllable of each word (its loudness peak), slow tilt and yaw drift, and the gesturing hand's wrist beating with
    the same accents a few frames later (hands follow the head). Degrees per frame. Silence relaxes to a slow drift."""
    rnd = random.Random(seed)
    acc = [0.0] * n_frames
    for wd in words:
        f0 = int(wd['s'] * fps); f1 = max(f0 + 1, int(wd['e'] * fps))
        seg = env[f0:f1] if env else []
        pk = f0 + (max(range(len(seg)), key=lambda k: seg[k]) if seg else 0)
        strength = (max(seg) if seg else 0.5)
        strength = min(1.0, strength / 0.6) * (1.3 if len(wd['w']) > 4 else 0.8)
        for d in range(-3, 10):                               # anticipation up, accent down, settle
            f = pk + d
            if 0 <= f < n_frames:
                x = d / 4.0
                acc[f] += strength * (math.exp(-x * x) - 0.25 * math.exp(-((d + 3) / 2.0) ** 2))
    ph = [rnd.uniform(0, 6.28) for _ in range(4)]
    out = []
    for i in range(n_frames):
        t = i / fps
        hand_acc = acc[i - 3] if i >= 3 else 0.0
        out.append({'head_pitch': round(nod * acc[i] + 1.2 * math.sin(t * 0.9 + ph[0]), 2),
                    'head_yaw': round(3.0 * math.sin(t * 0.45 + ph[1]) + 1.0 * math.sin(t * 1.3 + ph[2]), 2),
                    'head_roll': round(tilt * math.sin(t * 0.6 + ph[3]), 2),
                    'wrist': round(hand * hand_acc, 2)})
    return out
