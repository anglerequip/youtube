"""Why dry spaghetti breaks into three or more pieces, and why twisting it first gives two.

Model (simplified, after Audoly & Neukirch 2005 and Heisser et al. 2018):
  1. A stick of length 2L is bent by its two grips into a circular arc (pure bending, uniform curvature).
     It cracks where it is weakest once the curvature reaches the strength there.
  2. The crack releases the bending moment at the new free end of each half. Each half then obeys the
     linear Euler-Bernoulli beam equation  rho*A*w_tt = -E*I*w_xxxx  (grip end clamped, new end free),
     starting from the bent shape. A "snap-back" flexural wave runs from the free end towards the grip,
     and in its wake the curvature temporarily rises ABOVE the curvature the stick broke at.
  3. Anywhere that transient curvature exceeds the local strength, the stick breaks again. The freed
     fragment flies off as a rigid body (gravity, bench contact with friction).
  4. Twisted first: we use a combined-stress criterion (bending/kc)^2 + (twist/tc)^2 = 1, so a twisted
     stick breaks with much less bending stored. At fracture the twist unwinds (torsional waves are
     faster than bending waves) and the leftover snap-back burst is too weak to crack it again.

Real fracture takes milliseconds; the renderer shows it slowed down and says so.
Dimensions: dry spaghetti radius 0.85 mm, E ~ 3 GPa, density ~1500 kg/m^3, stick 25 cm (a 10 inch stick,
as in the 2018 MIT model).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

STICK = 0.25                   # m
RADIUS = 0.00085               # m
E_MOD = 3.0e9                  # Pa
RHO = 1500.0                   # kg/m^3
KAPPA_C = 9.6                  # 1/m: curvature at the first crack (~0.8% surface strain; the stick bends ~130 deg)
G = 9.81
GRIP_Y = 0.07                  # m: rod axis height above the bench
TWIST_TC_FRAC = 0.866          # twist / twist-strength used in the twisted run (bending capacity left: 50%)
N_HALF = 100                   # beam nodes per unit (half) length
TAU_CRACK = 0.004             # dimensionless crack-opening time (~0.1 ms)
MAX_SECONDARY = 1              # we track only the first secondary crack in each half (see caveats)
DAMP = 0.6                     # light dimensionless damping so the halves settle


def _time_scale(length):
    """Beam time unit L^2 * sqrt(rho*A / (E*I)) for a solid round rod (I/A = r^2/4)."""
    return length ** 2 * np.sqrt(RHO / (E_MOD * RADIUS ** 2 / 4))


def arc_points(kappa, s, x_mid=0.0):
    """Centreline of a stick bent into a circular arc of curvature kappa, ends at the grip height.
    s in [0, STICK]. The middle bows up. Returns (x, y), tangent angle."""
    L = STICK / 2
    u = s - L
    if abs(kappa) < 1e-9:
        return np.stack([x_mid + u, np.full_like(u, GRIP_Y)], -1), np.zeros_like(u)
    th = kappa * u                                   # tangent angle (0 at the middle)
    x = x_mid + np.sin(th) / kappa
    y = GRIP_Y + (np.cos(th) - np.cos(kappa * L)) / kappa
    return np.stack([x, y], -1), -th


@dataclass
class Fragment:
    s0: float
    s1: float
    t0: float                  # real time it broke free
    pts0: np.ndarray           # (n,2) shape at release
    v0: np.ndarray             # COM velocity (2,)
    w0: float                  # angular velocity (rad/s)
    track: list = field(default_factory=list)   # [(t, com(2), angle)] sampled flight


@dataclass
class SnapRun:
    twist_turns: float
    t_twist: float
    t_bend: float
    t_break: float
    kappa_break: float
    s_flaw: float
    halves: list               # per half: dict(times, kappa (n_t, n) curvature profile, s grid, side)
    fragments: list
    cracks: list               # [(t, s)]
    n_pieces: int
    burst_ratio: float         # max transient curvature / curvature at first fracture

    # ---------------------------------------------------------------- shapes for the renderer
    def phase_at(self, t, s):
        """Twist angle (rad) of the stick's surface stripe at arc position s."""
        tw = 2 * np.pi * self.twist_turns
        if t < self.t_twist:
            f = _smooth(t / self.t_twist) if self.t_twist > 0 else 1.0
            return tw * f * (s / STICK)
        if t < self.t_break or tw == 0:
            return tw * (s / STICK)
        # after the break the twist unwinds quickly (torsional wave), each half towards its grip
        f = np.exp(-(t - self.t_break) / 0.0008)
        return tw * (s / STICK) * f

    def kappa_now(self, t):
        if t <= self.t_twist:
            return 0.0
        return self.kappa_break * _smooth(min(1.0, (t - self.t_twist) / self.t_bend))

    def pieces(self, t):
        """-> list of dict(s (n,), pts (n,3), excess (n,)) for every piece at real time t."""
        out = []
        if t < self.t_break:
            s = np.linspace(0, STICK, 2 * N_HALF + 1)
            p, _ = arc_points(self.kappa_now(t), s)
            out.append({"s": s, "pts": _xyz(p), "excess": np.zeros_like(s), "id": 0})
            return out
        for hi, h in enumerate(self.halves):
            k = int(np.clip(np.searchsorted(h["times"], t) - 1, 0, len(h["times"]) - 1))
            kap, n_alive = h["kappa"][k], h["alive"][k]
            sl = slice(0, n_alive)
            s, pts = self._half_shape(h, kap[sl])
            exc = np.clip(kap[sl] / self.kappa_break - 1.0, 0, None)
            out.append({"s": s, "pts": _xyz(pts), "excess": exc, "id": 1 + hi})
        for fi, fr in enumerate(self.fragments):
            if t < fr.t0:
                continue
            out.append({**self._fragment_shape(fr, t), "id": 10 + fi})
        return out

    def _half_shape(self, h, kap):
        """Integrate the curvature from the grip end: grip position and angle are held fixed."""
        n = len(kap)
        ds = h["ds"]
        s_grip = 0.0 if h["side"] < 0 else STICK
        g, th_g = arc_points(self.kappa_break, np.array([s_grip]))
        th0 = th_g[0] if h["side"] < 0 else th_g[0] + np.pi     # walk inwards from the grip
        sign = 1.0 if h["side"] < 0 else -1.0
        th = th0 + np.concatenate([[0], np.cumsum((kap[:-1] + kap[1:]) / 2 * ds)]) * (-sign)
        x = g[0, 0] + np.concatenate([[0], np.cumsum(np.cos((th[:-1] + th[1:]) / 2) * ds)])
        y = g[0, 1] + np.concatenate([[0], np.cumsum(np.sin((th[:-1] + th[1:]) / 2) * ds)])
        s = s_grip + h["side"] * -1 * np.arange(n) * ds
        return s, np.stack([x, y], -1)

    def _fragment_shape(self, fr, t):
        tr = fr.track
        k = int(np.clip(np.searchsorted([a[0] for a in tr], t) - 1, 0, len(tr) - 1))
        _, com, ang = tr[k]
        loc = fr.pts0 - fr.pts0.mean(axis=0)
        # the fragment's own bend relaxes (it vibrates out within a few ms): blend towards straight
        d = loc[-1] - loc[0]; L = np.linalg.norm(d) + 1e-9
        straight = np.outer(np.linspace(-0.5, 0.5, len(loc)), d) * (np.sum(np.linalg.norm(np.diff(loc, axis=0), axis=1)) / L)
        f = np.exp(-(t - fr.t0) / 0.004)
        loc = f * loc + (1 - f) * straight
        c, sn = np.cos(ang), np.sin(ang)
        pts = loc @ np.array([[c, sn], [-sn, c]]) + com
        s = np.linspace(fr.s0, fr.s1, len(loc))
        z = 0.0
        return {"s": s, "pts": _xyz(pts, z), "excess": np.zeros(len(loc))}


def _smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (u * 6 - 15) + 10)


def _xyz(p, z=0.0):
    return np.column_stack([p[:, 0], p[:, 1], np.full(len(p), z)])


# -------------------------------------------------------------------- the snap-back dynamics
def _simulate_half(length, kappa0, strength, t_end_real, side, rng):
    """Linear beam, x=0 at the grip (clamped), x=1 at the crack (free). Units: length=1, kappa0=1.
    strength(x): local breaking curvature / kappa0. Returns sampled curvature and break events."""
    n = max(20, int(round(N_HALF * length / (STICK / 2))))
    dx = 1.0 / n
    x = np.arange(n + 1) * dx
    w = 0.5 * x ** 2
    v = np.zeros_like(w)
    dt = 0.2 * dx ** 2
    T = _time_scale(length)
    end = n                        # index of the current free end
    rel_t, rel_k = 0.0, 1.0        # time of the last release and the curvature released there
    min_frag = max(4, int(round(0.012 / length * n)))   # fragments shorter than 12 mm don't form
    samples_t, samples_k, alive, breaks = [], [], [], []
    every_real = 2.0e-5
    next_sample = 0.0
    peak = 1.0
    steps = int(t_end_real / T / dt)
    for k in range(steps):
        m = end
        g = np.empty(m + 5)
        g[2:m + 3] = w[:m + 1]
        g[1] = w[1]; g[0] = w[2]                         # clamped at the grip
        # free end: the moment drops to zero over the crack-opening time TAU_CRACK (not instantly)
        Mend = rel_k * (1 - _smooth((k * dt - rel_t) / TAU_CRACK))
        g[m + 3] = 2 * w[m] - w[m - 1] + Mend * dx ** 2
        g[m + 4] = 2 * g[m + 3] - 2 * w[m - 1] + w[m - 2]   # free end: zero shear
        d4 = (g[4:] - 4 * g[3:-1] + 6 * g[2:-2] - 4 * g[1:-3] + g[:-4]) / dx ** 4
        a = -d4 - DAMP * v[:m + 1]
        a[0] = 0
        v[:m + 1] += dt * a
        w[:m + 1] += dt * v[:m + 1]
        w[0] = 0; v[0] = 0
        if k % 10 == 0:
            kap = np.zeros(n + 1)
            kap[1:m] = (w[2:m + 1] - 2 * w[1:m] + w[:m - 1]) / dx ** 2
            kap[0] = (2 * w[1] - 2 * w[0]) / dx ** 2
            peak = max(peak, float(np.abs(kap[2:m - 1]).max()) if m > 4 else 1.0)
            over = np.nonzero(np.abs(kap[2:m - 2]) > strength[2:m - 2])[0]
            over = over[over + 2 <= m - min_frag]
            if len(over):
                j = 2 + int(over[np.argmax(np.abs(kap[2 + over]) - strength[2 + over])])
                if j <= m - min_frag and k * dt - rel_t > 2 * TAU_CRACK and len(breaks) < MAX_SECONDARY:
                    breaks.append((k * dt * T, j, m, w.copy(), v.copy()))
                    rel_k = float(kap[j]); rel_t = k * dt
                    end = j
            t_real = k * dt * T
            if t_real >= next_sample:
                samples_t.append(t_real); samples_k.append(kap.copy()); alive.append(end + 1)
                next_sample += every_real if t_real < 0.004 else 10 * every_real
    return {"t": np.array(samples_t), "kappa": np.array(samples_k), "alive": np.array(alive), "n": n,
            "breaks": breaks, "peak": peak, "T": T}


def run(twist_turns: float = 0.0, s_flaw_frac: float = 0.47, seed: int = 1, t_bend: float = 1.6,
        t_twist: float = 0.0, t_after: float = 0.06) -> SnapRun:
    rng = np.random.default_rng(seed)
    # bending capacity left after pre-twist (combined-stress criterion)
    tf = TWIST_TC_FRAC if twist_turns > 0 else 0.0
    kappa_break = KAPPA_C * np.sqrt(1 - tf ** 2)
    t_break = t_twist + t_bend
    s_flaw = s_flaw_frac * STICK
    halves, fragments, cracks = [], [], [(t_break, s_flaw)]
    peak = 1.0
    for side, length in ((-1, s_flaw), (1, STICK - s_flaw)):
        res_n = max(20, int(round(N_HALF * length / (STICK / 2))))
        xg = np.arange(res_n + 1) / res_n
        # local strength relative to the curvature at first fracture: the flaw broke first; elsewhere
        # dry pasta is 10-50% stronger, varying smoothly along the stick (flaws are random)
        noise = sum(rng.normal(0, 1) * np.sin((j + 1) * np.pi * xg + rng.uniform(0, 6)) / (j + 1) for j in range(5))
        strength = (KAPPA_C * np.maximum(1.08, 1.32 + 0.10 * noise)) / kappa_break
        sim = _simulate_half(length, 1.0, strength, t_after, side, rng)
        peak = max(peak, sim["peak"])
        ds = length / sim["n"]
        h = {"times": t_break + sim["t"], "kappa": sim["kappa"] * kappa_break, "alive": sim["alive"],
             "ds": ds, "side": side, "length": length}
        halves.append(h)
        # fragments: shape and rigid velocity at release from consecutive samples
        tmp = SnapRun(twist_turns, t_twist, t_bend, t_break, kappa_break, s_flaw, [h], [], [], 0, 1.0)
        prev_end = sim["n"]
        for (tb, j, m, w, v) in sim["breaks"]:
            t_abs = t_break + tb
            k = int(np.clip(np.searchsorted(h["times"], t_abs) - 1, 1, len(h["times"]) - 1))
            kap_b = h["kappa"][k].copy()
            kap_b[m + 1:] = 0
            _, p1 = tmp._half_shape(h, kap_b[:m + 1])
            _, p0 = tmp._half_shape(h, h["kappa"][k - 1][:m + 1])
            dtt = h["times"][k] - h["times"][k - 1]
            seg1, seg0 = p1[j:m + 1], p0[j:m + 1]
            vel = (seg1 - seg0) / max(dtt, 1e-7)
            com = seg1.mean(axis=0)
            vcom = vel.mean(axis=0)
            r = seg1 - com
            wz = float(np.sum(r[:, 0] * (vel[:, 1] - vcom[1]) - r[:, 1] * (vel[:, 0] - vcom[0])) / max(np.sum(r * r), 1e-12))
            s_grip = 0.0 if side < 0 else STICK
            s0, s1 = s_grip - side * j * ds, s_grip - side * m * ds
            fr = Fragment(min(s0, s1), max(s0, s1), t_abs, seg1 if side > 0 else seg1, vcom, wz)
            fr.track = _fly(fr, seg1 - com, com, rng)
            fragments.append(fr)
            cracks.append((t_abs, s0))
            prev_end = j
    n_pieces = 2 + len(fragments)
    return SnapRun(twist_turns, t_twist, t_bend, t_break, kappa_break, s_flaw, halves, fragments, cracks,
                   n_pieces, peak)


def _fly(fr, loc, com, rng, t_end=2.5, dt=2e-4):
    """Rigid 2D flight with gravity, then a damped landing and sliding on the bench (y = RADIUS)."""
    track = []
    c, v, a, wz = com.copy(), fr.v0.copy(), 0.0, fr.w0
    t = fr.t0
    on_bench = False
    while t < fr.t0 + t_end:
        track.append((t, c.copy(), a))
        if not on_bench:
            v[1] -= G * dt
            c += v * dt; a += wz * dt
            ca, sa = np.cos(a), np.sin(a)
            low = np.min((loc @ np.array([[ca, sa], [-sa, ca]]))[:, 1]) + c[1]
            if low < RADIUS:
                c[1] += RADIUS - low
                v[1] = -0.25 * v[1]; v[0] *= 0.6; wz *= 0.3
                if abs(v[1]) < 0.15:
                    on_bench = True
                    # settle flat: rotate to the nearest lying angle
                    d = loc[-1] - loc[0]
                    a_target = -np.arctan2(d[1], d[0])
                    fr_target = a_target + np.pi * np.round((a - a_target) / np.pi)
                    settle = (fr_target, t)
        else:
            v[1] = 0
            v[0] *= np.exp(-6 * dt)
            c[0] += v[0] * dt
            ft, ts = settle
            u = min(1.0, (t - ts) / 0.08)
            a = a + (ft - a) * u
            ca, sa = np.cos(a), np.sin(a)
            low = np.min((loc @ np.array([[ca, sa], [-sa, ca]]))[:, 1]) + c[1]
            c[1] += RADIUS - low
        t += dt if t < fr.t0 + 0.5 else 5 * dt
    return track


@lru_cache(maxsize=8)
def standard_runs():
    """Runs used by the episode: the plain snap (several flaws) and the twisted snap."""
    plain = run(0.0, 0.47, seed=1)
    extra = [run(0.0, f, seed=s) for f, s in ((0.55, 4), (0.42, 7), (0.51, 11))]
    twisted = run(1.0, 0.5, seed=3, t_twist=2.0, t_bend=2.4)
    return plain, extra, twisted


def self_checks() -> dict:
    plain, extra, twisted = standard_runs()
    counts = [plain.n_pieces] + [r.n_pieces for r in extra]
    return {
        "snap_back_burst_exceeds_breaking_curvature": (plain.burst_ratio > 1.15,
                                                       f"transient curvature reaches {plain.burst_ratio:.2f}x the curvature at the first crack"),
        "untwisted_sticks_break_into_3_or_more": (min(counts) >= 3, f"pieces per untwisted snap: {counts}"),
        "twisted_stick_breaks_in_two": (twisted.n_pieces == 2,
                                        f"twisted snap: {twisted.n_pieces} pieces; burst {twisted.burst_ratio:.2f}x of a "
                                        f"{twisted.kappa_break / KAPPA_C:.0%}-capacity bend"),
    }
