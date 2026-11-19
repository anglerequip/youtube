"""Base class for episode simulations, plus the frame renderer.

An episode's sim.py defines `class Sim(Scene)` and implements:
  setup(self)      - build matplotlib artists on self.fig (called once)
  update(self, t)  - move them for video time t in seconds (called every frame)

Use self.tl.start("<line id>") / self.tl.end("<line id>") to sync visuals with the narration.
The frame is 1080x1920. Axes coordinates in self.fig are 0..1 horizontally and 0..1 vertically.
Keep important visuals between y=0.25 and y=0.88: YouTube's Shorts UI covers the bottom and the
captions sit at about y=0.30.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from ..voice_engine.narrate import Timeline  # noqa: E402

W, H = 1080, 1920
DPI = 120
FPS = 30

# House style, shared by every episode so the channel looks consistent.
STYLE = {
    "bg": "#0b0f1a",
    "fg": "#f2f4f8",
    "muted": "#8a93a6",
    "accent": "#ffcc33",   # the thing to watch
    "accent2": "#39d0ff",  # secondary highlight
    "warn": "#ff5c7a",
    "font": "DejaVu Sans",
}


class Scene:
    def __init__(self, timeline: Timeline):
        self.tl = timeline
        self.duration = timeline.duration
        plt.rcParams["font.family"] = STYLE["font"]
        self.fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI, facecolor=STYLE["bg"])

    # -- helpers ---------------------------------------------------------
    def full_axes(self, rect=(0, 0, 1, 1), xlim=(0, 1), ylim=(0, 1)):
        ax = self.fig.add_axes(rect)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_facecolor("none")
        ax.axis("off")
        return ax

    def title(self, text: str, y: float = 0.92, size: int = 44):
        return self.fig.text(0.5, y, text, ha="center", va="center", color=STYLE["fg"],
                             fontsize=size, fontweight="bold")

    @staticmethod
    def ramp(t: float, t0: float, t1: float) -> float:
        """0 before t0, 1 after t1, smooth in between. Handy for fades."""
        if t1 <= t0:
            return float(t >= t0)
        x = min(1.0, max(0.0, (t - t0) / (t1 - t0)))
        return x * x * (3 - 2 * x)

    # -- optional hooks ---------------------------------------------------
    ON_SCREEN_Y = 0.80   # where a beat's `on_screen` text is drawn (figure fraction)

    def sfx_events(self) -> list[tuple[float, str]]:
        """Extra sound cues as (video time, sfx name), e.g. a thud at the moment of impact."""
        return []

    def _setup_branding(self):
        from ..configuration import settings
        self.fig.text(0.5, 0.968, settings.channel_name.upper(), ha="center", va="center",
                      color=STYLE["muted"], fontsize=15, fontweight="bold", alpha=0.75, zorder=30)

    def _setup_on_screen(self, beats):
        self._beats_on_screen = [(b.id, b.on_screen) for b in beats if getattr(b, "on_screen", None)]
        self._on_screen = self.fig.text(0.5, self.ON_SCREEN_Y, "", ha="center", va="center",
                                        color=STYLE["accent"], fontsize=40, fontweight="bold", zorder=20)

    def _update_on_screen(self, t):
        txt = ""
        for bid, text in self._beats_on_screen:
            if self.tl.start(bid) <= t < self.tl.end(bid) + 0.3:
                txt = text
        self._on_screen.set_text(txt)

    # -- to implement -----------------------------------------------------
    def setup(self):
        raise NotImplementedError

    def update(self, t: float):
        raise NotImplementedError


def render(scene: Scene, out_path: Path, fps: int = FPS, preview_every: float | None = None, beats=()):
    """Render the scene to a silent H.264 mp4 by piping raw frames into ffmpeg."""
    scene.setup()
    scene._setup_branding()
    scene._setup_on_screen(beats)
    n = int(np.ceil(scene.duration * fps))
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(out_path),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    canvas = scene.fig.canvas
    preview_dir = out_path.parent / "previews"
    if preview_every:
        preview_dir.mkdir(exist_ok=True)
    next_preview = 0.0
    try:
        for i in range(n):
            t = i / fps
            scene.update(t)
            scene._update_on_screen(t)
            canvas.draw()
            buf = canvas.buffer_rgba()
            if buf.shape[:2] != (H, W):
                raise RuntimeError(f"frame is {buf.shape[1]}x{buf.shape[0]}, expected {W}x{H}")
            proc.stdin.write(buf.tobytes())
            if preview_every and t >= next_preview:
                scene.fig.savefig(preview_dir / f"t{t:05.1f}.png", facecolor=STYLE["bg"])
                next_preview += preview_every
            if i % (fps * 5) == 0:
                print(f"  frame {i}/{n}", flush=True)
    finally:
        proc.stdin.close()
        rc = proc.wait()
        plt.close(scene.fig)
    if rc != 0:
        raise RuntimeError(f"ffmpeg exited with {rc}")
