"""Shared helpers for duo (wizard + woman) episode plans: mouth envelopes from the real voice, eased bumps,
per-frame talk/blink/look tracks and the shot helper. Keeps each episode's plan.py about its own story.
"""
from __future__ import annotations

import math

import numpy as np

from . import camera as cam


def envelope(slug: str, n: int, fps: int) -> np.ndarray:
    """Per-frame voice loudness (0..1) from out/<slug>/voice.wav, smoothed like a jaw (fast open, slower close)."""
    from .configuration import settings
    import soundfile as sf
    p = settings.out_dir / slug / "voice.wav"
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
    for i in range(n):
        prev = out[i - 1] if i else 0.0
        out[i] = prev + (env[i] - prev) * (0.7 if env[i] > prev else 0.35)
    return np.clip(out, 0, 1)


def bump(t: float, t0: float, rise: float, hold: float, fall: float) -> float:
    """0 -> 1 -> 0 envelope: eased rise, hold, eased fall."""
    if t < t0:
        return 0.0
    if t < t0 + rise:
        return cam.ease((t - t0) / rise)
    if t < t0 + rise + hold:
        return 1.0
    if t < t0 + rise + hold + fall:
        return 1.0 - cam.ease((t - t0 - rise - hold) / fall)
    return 0.0


def ramp(t: float, t0: float, dur: float) -> float:
    """0 before t0, eased 0 -> 1 over dur, then 1."""
    if t <= t0:
        return 0.0
    if t >= t0 + dur:
        return 1.0
    return cam.ease((t - t0) / dur)


def talk_tracks(tl, speaker_of: dict, env: np.ndarray, fps: int) -> tuple[list, list]:
    """Mouth tracks for the wizard and the woman from who speaks each beat."""
    tw, tm = [], []
    for i in range(len(env)):
        ln = tl.active(i / fps)
        who = speaker_of.get(ln.id) if ln else None
        tw.append(round(float(env[i]) if who == "wizard" else 0.0, 3))
        tm.append(round(float(env[i]) if who == "woman" else 0.0, 3))
    return tw, tm


def blinks(n: int, fps: int, period: float, offset: float = 0.0) -> list:
    return [1.0 if ((i / fps + offset) % period) < 0.12 else 0.0 for i in range(n)]


def focal_track(shots: list, n: int) -> list:
    focal = []
    for s_ in shots:
        for k, lk in enumerate(s_["look"]):
            if s_["i0"] + k == len(focal) and len(focal) < n:
                focal.append(lk)
    while len(focal) < n:
        focal.append(focal[-1])
    return focal[:n]


def shot(fps: int):
    """E(t0, t1, p0, p1, look, fov, light, p1look) -> a two-key eased camera move."""
    def E(t0, t1, p0, p1, look, fov, light="key", p1look=None):
        return cam.shot(t0, t1, [(t0, p0, look, fov), (t1, p1, p1look or look, fov)], fps, light)
    return E


def n_frames(tl, fps: int) -> int:
    return int(math.ceil((tl.duration + 0.05) * fps))
