"""Falling slinky: N point masses joined by pull-only springs, released from the top.

Coils touch when unloaded (rest length = pitch D); collisions are perfectly inelastic, so the
collapsed part moves as one block. Used by both the 2D and 3D slinky episodes.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

G = 9.81
N = 80          # coils
M = 0.25        # kg
L_HANG = 1.0    # m of stretch when hanging (sets the spring constant)
D = 0.006       # m, coil pitch when touching
K = M * G / (2 * L_HANG)


@lru_cache(maxsize=4)
def simulate(t_end: float = 0.6, dt: float = 1e-5, sample_dt: float = 5e-4):
    m = M / N
    k_seg = K * (N - 1)
    below = np.arange(N - 1, 0, -1)
    gaps = D + below * m * G / k_seg
    y = -np.concatenate([[0.0], np.cumsum(gaps)])
    v = np.zeros(N)
    front = 0
    ts, ys, fronts = [], [], []
    steps = int(round(sample_dt / dt))
    for s in range(int(t_end / sample_dt) + 1):
        ts.append(s * sample_dt); ys.append(y.copy()); fronts.append(front)
        for _ in range(steps):
            ext = (y[:-1] - y[1:]) - D
            tension = k_seg * np.maximum(ext, 0.0)
            f = -m * G * np.ones(N)
            f[:-1] -= tension
            f[1:] += tension
            blk = front + 1
            a = f / m
            a[:blk] = f[:blk].sum() / (blk * m)
            v += a * dt
            v[:blk] = v[0]
            y += v * dt
            while front < N - 1 and (y[front] - y[front + 1]) <= D:
                blk = front + 1
                v_new = (blk * v[0] + v[front + 1]) / (blk + 1)
                front += 1
                v[: front + 1] = v_new
                y[front] = y[front - 1] - D
            if front == N - 1:
                y[1:] = y[0] - D * np.arange(1, N)
    ts, ys, fronts = np.array(ts), np.array(ys), np.array(fronts)
    return ts, ys, fronts


def t_meet() -> float:
    ts, _, fr = simulate()
    return float(ts[np.argmax(fr == N - 1)])


def theory_hover_time() -> float:
    """Ideal slinky: centre of mass starts L/3 above the bottom and falls freely: t = sqrt(2L/3g)."""
    return float(np.sqrt(2 * L_HANG / (3 * G)))


def state(tp: float):
    ts, ys, fr = simulate()
    i = int(np.clip(round(tp / (ts[1] - ts[0])), 0, len(ts) - 1))
    return ys[i], int(fr[i])


def self_checks() -> dict:
    ts, ys, _ = simulate()
    tm = t_meet()
    before = ts < 0.98 * tm
    drift_mm = float(np.max(np.abs(ys[before, -1] - ys[0, -1])) * 1000)
    th = theory_hover_time()
    err = abs(tm - th) / th
    a = 2 * np.polyfit(ts, ys.mean(axis=1), 2)[0]
    return {
        "bottom_stationary": (drift_mm < 1.0, f"bottom moved {drift_mm:.3f} mm before the collapse arrived"),
        "hover_time_vs_theory": (err < 0.05, f"sim {tm:.3f}s vs ideal-slinky theory {th:.3f}s ({err:.1%})"),
        "centre_of_mass_freefall": (abs(a + G) / G < 0.02, f"centre of mass accel {a:.2f} m/s^2 (g = {G})"),
    }
