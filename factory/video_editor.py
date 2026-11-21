"""Final assembly: sound effects mixed under the voice, captions burned in, audio+video muxed.

All sound effects are synthesised here with numpy, so every asset is original and license-free.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SR_FX = 24000


def _env(n, attack, decay):
    t = np.arange(n) / SR_FX
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - attack, 0) / decay)


def _noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def sfx(name: str) -> np.ndarray:
    """Return a mono float32 sound effect at 24 kHz."""
    if name == "whoosh":
        n = int(0.6 * SR_FX)
        x = _noise(n, 1)
        # sweep a crude low-pass by mixing smoothed noise of varying width
        k = np.ones(40) / 40
        x = np.convolve(x, k, mode="same")
        env = np.sin(np.linspace(0, np.pi, n)) ** 2
        y = x * env * 0.9
    elif name == "thud":
        n = int(0.45 * SR_FX)
        t = np.arange(n) / SR_FX
        f = 110 * np.exp(-t * 9) + 45
        y = np.sin(2 * np.pi * np.cumsum(f) / SR_FX) * _env(n, 0.002, 0.09)
        y += 0.25 * np.convolve(_noise(n, 2), np.ones(12) / 12, "same") * _env(n, 0.001, 0.03)
    elif name == "pop":
        n = int(0.12 * SR_FX)
        t = np.arange(n) / SR_FX
        y = np.sin(2 * np.pi * (900 - 3000 * t) * t) * _env(n, 0.001, 0.03)
    elif name == "tick":
        n = int(0.05 * SR_FX)
        y = _noise(n, 3) * _env(n, 0.0005, 0.006)
    elif name == "rise":
        n = int(1.2 * SR_FX)
        t = np.arange(n) / SR_FX
        y = np.sin(2 * np.pi * (200 * t + 300 * t ** 2)) * (t / t[-1]) ** 2 * 0.5
    elif name == "ding":
        n = int(0.9 * SR_FX)
        t = np.arange(n) / SR_FX
        y = (np.sin(2 * np.pi * 1320 * t) + 0.4 * np.sin(2 * np.pi * 2640 * t)) * _env(n, 0.002, 0.25) * 0.5
    else:
        raise ValueError(f"unknown sfx {name!r} (whoosh, thud, pop, tick, rise, ding)")
    y = y / (np.max(np.abs(y)) or 1)
    return y.astype(np.float32)


SFX_NAMES = ("whoosh", "thud", "pop", "tick", "rise", "ding")


def mix_sfx(voice_wav: Path, events: list[tuple[float, str]], out_wav: Path, fx_gain: float = 0.28) -> Path:
    voice, sr = sf.read(voice_wav, dtype="float32")
    if sr != SR_FX:
        raise ValueError(f"voice track is {sr} Hz, sfx are {SR_FX} Hz")
    mix = voice.copy()
    for t, name in events:
        fx = sfx(name) * fx_gain
        i = int(t * sr)
        if i >= len(mix):
            continue
        j = min(len(mix), i + len(fx))
        mix[i:j] += fx[: j - i]
    peak = float(np.max(np.abs(mix))) or 1.0
    if peak > 0.95:
        mix *= 0.95 / peak
    sf.write(out_wav, mix, sr)
    return out_wav


def _ff_path(p: Path) -> str:
    return str(p).replace("\\", "/").replace(":", r"\:")


def mux(video: Path, audio: Path, ass: Path, out: Path):
    # The subtitles filter needs ':' and '\' escaped in the path (matters on Windows drive letters).
    ass_arg = _ff_path(ass)
    # Bundled house font (Poppins, OFL) so captions look identical on Windows, macOS and Linux.
    fonts = _ff_path(Path(__file__).resolve().parent.parent / "assets" / "fonts")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video), "-i", str(audio),
        "-vf", f"subtitles='{ass_arg}':fontsdir='{fonts}'",
        # delivery encode (quality overhaul v3): YouTube re-encodes everything, so give it a clean master.
        # CRF 17 + slow preset + aq-mode 3 keeps sky gradients and dark scenes free of banding and blocking.
        "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-x264-params", "aq-mode=3", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-shortest", "-movflags", "+faststart", str(out),
    ]
    subprocess.run(cmd, check=True)
    _cap_true_peak(out)


def _true_peak(path: Path) -> float | None:
    import re
    p = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"True peak:\s+Peak:\s+(-?[\d.]+|-inf)", p.stderr.replace("\n", " "))
    return float(m[-1]) if m and m[-1] != "-inf" else None


def _cap_true_peak(out: Path, limit: float = -1.0):
    """AAC encoding overshoots the mastered WAV by up to ~2 dB, more with some ffmpeg builds (seen on
    Windows ffmpeg 9). Measure the delivered file and, if needed, re-encode only the audio a little lower."""
    tp = _true_peak(out)
    if tp is None or tp <= limit:
        return
    tmp = out.with_suffix(".tp.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out), "-c:v", "copy",
                    "-af", f"volume={limit - 0.5 - tp:.2f}dB", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(out)
