"""Reusable camera tools for the 3D renderer (brief section 13).

Shots are emitted as per-frame "keys" (position + look-at + fov per frame), which the renderer
plays back exactly. Authored camera motion is eased; physics never is.

  shot(...)            waypoint shot: eased moves between (t, pos, look, fov) keys
  follow(...)          same, but positions/looks are offsets from a moving subject
  hold_on_reveals(...) freeze camera motion for `still_s` after each reveal time (CAM-5)
"""
from __future__ import annotations

import math


def ease(u: float) -> float:
    """Smooth in/out (smootherstep). Starts and ends at rest."""
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


def _lerp(a, b, u):
    return [x + (y - x) * u for x, y in zip(a, b)]


def _key_at(keys, t):
    k = 0
    while k < len(keys) - 2 and t >= keys[k + 1][0]:
        k += 1
    a, b = keys[k], keys[min(k + 1, len(keys) - 1)]
    u = ease((t - a[0]) / max(1e-6, b[0] - a[0])) if b is not a else 1.0
    return a, b, u


def shot(start: float, end: float, keys: list, fps: int, lighting: str = "key", subject=None) -> dict:
    """keys: [(t, pos, look, fov)]. If `subject(i)` is given, pos and look are offsets from it."""
    i0, i1 = int(round(start * fps)), int(round(end * fps))
    pos, look, fovs = [], [], []
    for i in range(i0, max(i0 + 1, i1)):
        t = i / fps
        a, b, u = _key_at(keys, t)
        p, l = _lerp(a[1], b[1], u), _lerp(a[2], b[2], u)
        f = a[3] + (b[3] - a[3]) * u
        if subject is not None:
            s = subject(i)
            p = [p[0] + s[0], p[1] + s[1], p[2] + s[2]]
            l = [l[0] + s[0], l[1] + s[1], l[2] + s[2]]
        pos.append([round(v, 4) for v in p]); look.append([round(v, 4) for v in l]); fovs.append(round(f, 2))
    return {"type": "keys", "start": round(start, 3), "end": round(end, 3), "i0": i0, "pos": pos, "look": look,
            "fov": fovs[0], "fovs": fovs, "lighting": lighting}


def chain(shots: list) -> list:
    """Make shot boundaries contiguous (each shot ends where the next starts)."""
    for k in range(len(shots) - 1):
        shots[k]["end"] = shots[k + 1]["start"]
    return shots
