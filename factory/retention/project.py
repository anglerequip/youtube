"""Project 3D points to the screen with the plan's own camera (the same math three.js uses), so the
pre-render QA can check tracked callouts and dimension lines before anything is rendered.

Only keyed shots (`type: keys`, the house camera from factory/camera.py) are supported; other shot types
return None and the check is reported as not performed for those frames.
"""
from __future__ import annotations

import math


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _norm(v):
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2) or 1e-12
    return [v[0] / n, v[1] / n, v[2] / n]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def camera_at(plan: dict, i: int):
    """(pos, look, fov_deg) of frame i, or None when the shot is not keyed."""
    t = i / plan["fps"]
    shots = plan.get("shots") or []
    shot = next((s for s in shots if s["start"] <= t < s["end"]), shots[-1] if shots else None)
    if not shot or shot.get("type") != "keys":
        return None
    k = min(max(0, i - shot["i0"]), len(shot["pos"]) - 1)
    fov = shot["fovs"][k] if shot.get("fovs") else shot.get("fov", 38)
    return shot["pos"][k], shot["look"][k], fov


def to_screen(p, cam, W: int, H: int):
    """World point -> (x, y) as fractions of the frame (0,0 top left), plus depth. None if behind the camera."""
    pos, look, fov = cam
    f = _norm(_sub(look, pos))
    up = [0.0, 1.0, 0.0]
    r = _cross(f, up)
    if abs(r[0]) + abs(r[1]) + abs(r[2]) < 1e-9:      # looking straight down: three.js picks another up
        r = _cross(f, [0.0, 0.0, -1.0])
    r = _norm(r)
    u = _cross(r, f)
    d = _sub(p, pos)
    z = _dot(d, f)
    if z <= 1e-6:
        return None
    th = math.tan(math.radians(fov) / 2)
    aspect = W / H
    x_ndc = _dot(d, r) / (z * th * aspect)
    y_ndc = _dot(d, u) / (z * th)
    return 0.5 + x_ndc / 2, 0.5 - y_ndc / 2, z
