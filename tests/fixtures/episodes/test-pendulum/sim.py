import numpy as np

from factory.simulation_engine import STYLE, Scene

L, G = 1.0, 9.81


class Sim(Scene):
    @classmethod
    def self_checks(cls):
        T = 2 * np.pi * np.sqrt(L / G)
        return {"period": (abs(T - 2.006) < 0.01, f"small-angle period {T:.3f}s")}

    def setup(self):
        self.ax = self.full_axes(rect=(0, 0.35, 1, 0.5), xlim=(-1.2, 1.2), ylim=(-1.3, 0.2))
        self.rod, = self.ax.plot([], [], color=STYLE["fg"], lw=4)
        self.bob, = self.ax.plot([], [], "o", ms=40, color=STYLE["accent"])
        self.title("Pipeline test")

    def update(self, t):
        th = 0.5 * np.cos(np.sqrt(G / L) * t)
        x, y = L * np.sin(th), -L * np.cos(th)
        self.rod.set_data([0, x], [0, y])
        self.bob.set_data([x], [y])
