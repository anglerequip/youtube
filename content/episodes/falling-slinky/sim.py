"""Falling slinky: a chain of point masses joined by springs, released from the top.

Physics model
  * N coils of mass m = M/N joined by springs of stiffness k_seg = k*(N-1).
  * A slinky's coils touch when unloaded, so each spring only pulls (rest length = coil pitch d)
    and coils can't pass through each other.
  * At t=0 the chain hangs in equilibrium from the top coil. Then the top is released.
  * Coils that collide stick together (the collapsed part moves as one block), which is what the
    real toy does and what makes the bottom hover until the collapse front arrives.
"""
from __future__ import annotations

import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgba
from matplotlib.patches import FancyArrow, FancyBboxPatch

from factory.simulation_engine import STYLE, Scene

G = 9.81
N = 80          # coils
M = 0.25        # kg, whole slinky
L_HANG = 1.0    # m, hanging length (sets the spring constant)
D = 0.006       # m, coil pitch when touching
K = M * G / (2 * L_HANG)   # whole-slinky spring constant (N/m) that gives ~L_HANG of stretch


def simulate(t_end: float = 0.6, dt: float = 1e-5, sample_dt: float = 1e-3):
    m = M / N
    k_seg = K * (N - 1)
    # Equilibrium: the spring below coil i carries the weight of every coil under it.
    below = np.arange(N - 1, 0, -1)                   # coils below each spring
    gaps = D + below * m * G / k_seg
    y = -np.concatenate([[0.0], np.cumsum(gaps)])     # y up, top coil at 0
    v = np.zeros(N)
    front = 0  # coils 0..front have collapsed into one block
    ts, ys, fronts = [], [], []
    steps_per_sample = int(round(sample_dt / dt))
    n_samples = int(t_end / sample_dt) + 1
    for s in range(n_samples):
        ts.append(s * sample_dt)
        ys.append(y.copy())
        fronts.append(front)
        for _ in range(steps_per_sample):
            ext = (y[:-1] - y[1:]) - D               # spring stretch (>=0 means pulling)
            tension = k_seg * np.maximum(ext, 0.0)
            f = -m * G * np.ones(N)
            f[:-1] -= tension                         # spring pulls upper coil down
            f[1:] += tension                          # and lower coil up
            # collapsed block: one rigid body
            blk = front + 1
            a_blk = f[:blk].sum() / (blk * m)
            a = f / m
            a[:blk] = a_blk
            v += a * dt
            v[:blk] = v[0]
            y += v * dt
            # merge coils as the block hits them
            while front < N - 1 and (y[front] - y[front + 1]) <= D:
                blk = front + 1
                v_new = (blk * v[0] + v[front + 1]) / (blk + 1)
                front += 1
                v[: front + 1] = v_new
                y[front] = y[front - 1] - D
            if front == N - 1:
                y[1:] = y[0] - D * np.arange(1, N)
    return np.array(ts), np.array(ys), np.array(fronts)


TS, YS, FRONTS = simulate()
T_MEET = float(TS[np.argmax(FRONTS == N - 1)])   # when the collapse reaches the bottom
Y0 = YS[0]
Y_BOTTOM0 = Y0[-1]


def state_at(tp: float):
    i = int(np.clip(round(tp / (TS[1] - TS[0])), 0, len(TS) - 1))
    return YS[i], FRONTS[i]


def theory_hover_time() -> float:
    """Ideal slinky (zero coil pitch): the centre of mass starts L/3 above the bottom, falls freely,
    and the collapse reaches the bottom when the centre of mass does: t = sqrt(2L / 3g)."""
    return float(np.sqrt(2 * L_HANG / (3 * G)))


class Sim(Scene):
    @classmethod
    def self_checks(cls) -> dict:
        """Physics sanity checks run by quality control. Each value is (ok, detail)."""
        before = TS < 0.98 * T_MEET
        drift_mm = float(np.max(np.abs(YS[before, -1] - Y_BOTTOM0)) * 1000)
        th = theory_hover_time()
        err = abs(T_MEET - th) / th
        cm = YS.mean(axis=1)
        a = 2 * np.polyfit(TS, cm, 2)[0]
        return {
            "bottom_stationary": (drift_mm < 1.0, f"bottom moved {drift_mm:.3f} mm before the collapse arrived"),
            "hover_time_vs_theory": (err < 0.05, f"sim {T_MEET:.3f}s vs ideal-slinky theory {th:.3f}s ({err:.1%})"),
            "centre_of_mass_freefall": (abs(a + G) / G < 0.02, f"centre of mass accel {a:.2f} m/s^2 (g = {G})"),
        }

    def sfx_events(self):
        return [
            (self.d1_t0, "pop"),                                  # hand lets go
            (self.d1_t0 + T_MEET * self.d1_slow, "thud"),         # collapse hits the bottom
            (self.d2_t0, "pop"),
            (self.d2_t0 + T_MEET * self.d2_slow, "thud"),
        ]

    RING_W = 0.30    # drawn coil width (m)
    RING_H = 0.028   # drawn coil height (m), flattened ellipse = coil seen from the side

    def setup(self):
        tl = self.tl
        # Drop 1 starts as "let go" is said; the collapse reaches the bottom just after "midair".
        self.d1_t0 = tl.start("release") + 0.9
        self.d1_slow = max(4.0, (tl.end("hover") + 0.2 - self.d1_t0) / T_MEET)
        # Replay: drop 2 starts with "coil by coil"; meets the bottom on "finally start to fall".
        self.d2_t0 = tl.start("why2") + 0.4
        self.d2_slow = max(4.0, (tl.start("land") + 2.4 - self.d2_t0) / T_MEET)

        self.ax = self.full_axes(rect=(0.0, 0.37, 0.70, 0.50), xlim=(-0.45, 0.45), ylim=(-1.62, 0.12))
        ax = self.ax
        self.title("Why doesn't the bottom fall?", y=0.93, size=35)

        # where the bottom started
        ax.axhline(Y_BOTTOM0 - self.RING_H / 2 - 0.01, color=STYLE["muted"], lw=2, ls=(0, (6, 6)), alpha=0.8)
        ax.text(-0.43, Y_BOTTOM0 - 0.065, "bottom's starting height", color=STYLE["muted"], fontsize=17)

        # hand holding the top
        self.hand = FancyBboxPatch((-0.09, 0.015), 0.18, 0.07, boxstyle="round,pad=0.01,rounding_size=0.03",
                                   fc="#c9a27e", ec="none", zorder=5)
        ax.add_patch(self.hand)

        th = np.linspace(0, 2 * np.pi, 48)
        self.ring_x = self.RING_W / 2 * np.cos(th)
        self.ring_y = self.RING_H / 2 * np.sin(th)
        base = np.array([to_rgba(c) for c in ["#5b6b8c"] * N])
        base[:, :3] = np.linspace([0.45, 0.55, 0.78], [0.75, 0.82, 0.95], N)
        base[-1] = to_rgba(STYLE["accent"])
        self.base_colors = base
        self.coils = LineCollection([], linewidths=np.r_[np.full(N - 1, 2.2), 5.0], colors=base, zorder=3)
        ax.add_collection(self.coils)

        # front highlight for the replay
        self.front_glow, = ax.plot([], [], color=STYLE["accent2"], lw=14, alpha=0.35, solid_capstyle="round")
        self.front_label = ax.text(0, 0, "", color=STYLE["accent2"], fontsize=20, fontweight="bold", va="center")

        # force arrows for "setup"
        self.arrow_artists = []

        # badges
        self.badge = self.fig.text(0.5, 0.885, "", ha="center", color=STYLE["accent"], fontsize=24,
                                   fontweight="bold")
        self.clock = self.fig.text(0.5, 0.858, "", ha="center", color=STYLE["muted"], fontsize=20, family="DejaVu Sans Mono")

        # inset: height of the bottom coil vs time
        self.inset = self.fig.add_axes((0.73, 0.50, 0.23, 0.22))
        iax = self.inset
        iax.set_facecolor("none")
        for s in iax.spines.values():
            s.set_color(STYLE["muted"])
        iax.tick_params(colors=STYLE["muted"], labelsize=11)
        iax.set_xlim(0, TS[-1])
        yb = YS[:, -1] - Y_BOTTOM0
        iax.set_ylim(min(-0.5, yb.min()), 0.08)
        iax.set_xlabel("time (s)", color=STYLE["muted"], fontsize=12)
        iax.set_ylabel("drop (m)", color=STYLE["muted"], fontsize=12)
        iax.set_title("bottom coil", color=STYLE["accent"], fontsize=16, fontweight="bold")
        iax.axvline(T_MEET, color=STYLE["accent2"], lw=1.5, ls=":")
        self.inset_line, = iax.plot([], [], color=STYLE["accent"], lw=3)
        iax.set_visible(False)

    # ---------------------------------------------------------------
    def _phase(self, t):
        """Return (physical time, which drop, slow factor) for video time t."""
        if t >= self.d2_t0:
            return (t - self.d2_t0) / self.d2_slow, 2, self.d2_slow
        if t >= self.d1_t0:
            tp = (t - self.d1_t0) / self.d1_slow
            # before the replay, rewind to hanging during the "why1" line
            if t >= self.tl.start("why1") + 0.8:
                return 0.0, 0, 1
            return tp, 1, self.d1_slow
        return 0.0, 0, 1

    def update(self, t):
        tl = self.tl
        outro = t >= tl.start("outro") + 0.6
        tp, drop, slow = self._phase(t)
        if outro:
            tp, drop = 0.0, 0     # loop back to the opening frame for a seamless replay
        tp = min(tp, TS[-1])
        y, front = state_at(tp)

        segs = [np.column_stack([self.ring_x, yi + self.ring_y]) for yi in y]
        self.coils.set_segments(segs)

        # hand lets go
        if drop:
            lift = min(0.25, tp * 3)
            self.hand.set_y(0.015 + lift)
            self.hand.set_alpha(max(0.0, 1 - tp * 8))
        else:
            self.hand.set_y(0.015)
            self.hand.set_alpha(1.0)

        # badge + clock
        if drop:
            self.badge.set_text(("REPLAY  ·  " if drop == 2 else "") + f"{slow:.0f}× SLOW MOTION")
            self.clock.set_text(f"t = {tp:0.3f} s")
        else:
            self.badge.set_text("")
            self.clock.set_text("")

        # forces on the bottom coil during "setup"
        for a in self.arrow_artists:
            a.remove()
        self.arrow_artists = []
        alpha = self.ramp(t, tl.start("setup") + 1.0, tl.start("setup") + 1.6) * \
            (1 - self.ramp(t, tl.end("setup") + 0.1, tl.end("setup") + 0.5))
        if alpha > 0.01 and not drop:
            yb = y[-1]
            for sign, color, label in ((-1, STYLE["warn"], "gravity"), (1, STYLE["accent2"], "spring")):
                arr = FancyArrow(0.2, yb, 0, sign * 0.13, width=0.012, head_width=0.045, head_length=0.04,
                                 length_includes_head=True, color=color, alpha=alpha, zorder=6)
                self.ax.add_patch(arr)
                txt = self.ax.text(0.25, yb + sign * 0.09, label, color=color, alpha=alpha, fontsize=20,
                                   fontweight="bold", va="center")
                self.arrow_artists += [arr, txt]

        # collapse front highlight on the replay
        if drop == 2 and front < N - 1:
            yf = y[front]
            self.front_glow.set_data([-self.RING_W / 2, self.RING_W / 2], [yf, yf])
            self.front_label.set_position((self.RING_W / 2 + 0.02, yf))
            self.front_label.set_text("← the news")
        else:
            self.front_glow.set_data([], [])
            self.front_label.set_text("")

        # inset graph appears with the replay and stays
        show_inset = drop > 0 or t >= self.d2_t0
        self.inset.set_visible(show_inset)
        if show_inset:
            tp_plot = tp if drop else TS[-1]
            n = int(tp_plot / (TS[1] - TS[0])) + 1
            self.inset_line.set_data(TS[:n], YS[:n, -1] - Y_BOTTOM0)
