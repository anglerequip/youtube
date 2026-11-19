"""Narrate every beat, stitch them into one track, and record when each line starts and ends.

The resulting Timeline is what keeps the simulation and captions in sync with the voice.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from ..narration.pronounce import normalise
from .providers import get_tts


def _delivery() -> dict:
    import yaml
    from ..configuration import settings
    p = settings.root / "config" / "rules.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")).get("delivery", {}) if p.exists() else {}

LEAD_IN = 0.35   # silence before the first line
TAIL = 1.2       # silence after the last line, so the video doesn't cut mid-breath


@dataclass
class TimedLine:
    id: str
    text: str
    start: float
    end: float


class Timeline:
    def __init__(self, lines: list[TimedLine], duration: float):
        self.lines = lines
        self.duration = duration
        self._by_id = {ln.id: ln for ln in lines}

    def start(self, cue: str) -> float:
        return self._by_id[cue].start

    def end(self, cue: str) -> float:
        return self._by_id[cue].end

    def active(self, t: float) -> TimedLine | None:
        for ln in self.lines:
            if ln.start <= t < ln.end:
                return ln
        return None

    def save(self, path: Path):
        path.write_text(json.dumps({"duration": self.duration, "lines": [asdict(l) for l in self.lines]}, indent=2))

    @classmethod
    def load(cls, path: Path) -> "Timeline":
        d = json.loads(path.read_text())
        return cls([TimedLine(**l) for l in d["lines"]], d["duration"])


def _trim(samples: np.ndarray, sr: int, thresh: float = 0.01) -> np.ndarray:
    """Cut leading/trailing near-silence so pauses are controlled by the script, not the model."""
    idx = np.nonzero(np.abs(samples) > thresh)[0]
    if len(idx) == 0:
        return samples
    pad = int(0.03 * sr)
    return samples[max(0, idx[0] - pad): idx[-1] + pad]


def narrate(ep, out_wav: Path, provider: str | None = None) -> Timeline:
    tts = get_tts(provider)
    chunks: list[np.ndarray] = []
    timed: list[TimedLine] = []
    sr_ref = None
    t = LEAD_IN
    delivery = _delivery()
    for ln in ep.lines:
        pace = delivery.get(getattr(ln, "pace", "calm") or "calm", {})
        speed = ep.speed * (getattr(ln, "speed", None) or pace.get("speed", 1.0))
        # The voice gets pronunciation-normalised text; captions keep the written text (ln.text).
        samples, sr = tts.synth(normalise(ln.text), voice=ep.voice, speed=speed)
        samples = _trim(np.asarray(samples, dtype=np.float32), sr)
        if sr_ref is None:
            sr_ref = sr
            chunks.append(np.zeros(int(LEAD_IN * sr), dtype=np.float32))
        elif sr != sr_ref:
            raise RuntimeError("TTS sample rate changed between lines")
        dur = len(samples) / sr
        timed.append(TimedLine(ln.id, ln.text, round(t, 3), round(t + dur, 3)))
        chunks.append(samples)
        pause = ln.pause_after + pace.get("pause", 0.0)
        chunks.append(np.zeros(int(pause * sr), dtype=np.float32))
        t += dur + pause
        print(f"  [{timed[-1].start:6.2f}-{timed[-1].end:6.2f}] {ln.id}", flush=True)
    chunks.append(np.zeros(int(TAIL * sr_ref), dtype=np.float32))
    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio * (0.89 / peak)  # normalise to about -1 dBFS
    sf.write(out_wav, audio, sr_ref)
    return Timeline(timed, len(audio) / sr_ref)
