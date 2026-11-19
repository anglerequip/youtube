"""Shared test sim for the length fixtures: a marker moves one step per beat, timed from the narration,
so a frame at any beat's start shows that beat's state (visual sync is checkable from the pictures)."""
import numpy as np

from factory.simulation_engine import STYLE, Scene


class BeatSim(Scene):
    @classmethod
    def self_checks(cls):
        return {"fixture": (True, "length fixture")}

    def setup(self):
        self.ax = self.full_axes(rect=(0, 0.35, 1, 0.5), xlim=(-0.5, 12.5), ylim=(-1, 1))
        self.dot, = self.ax.plot([], [], "o", ms=40, color=STYLE["accent"])
        self.title("Length fixture")

    def update(self, t):
        ids = [ln.id for ln in self.tl.lines]
        ln = self.tl.active(t)
        k = ids.index(ln.id) if ln else (len(ids) - 1 if t > self.tl.lines[-1].end else 0)
        u = 0.0 if ln is None else (t - ln.start) / max(1e-6, ln.end - ln.start)
        self.dot.set_data([k + 0.3 * u], [np.sin(2 * np.pi * u) * 0.3])
