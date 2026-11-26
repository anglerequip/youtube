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
from .expressive import clean
from .providers import get_tts


def _delivery() -> dict:
    import yaml
    from ..configuration import settings
    p = settings.root / "config" / "rules.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")).get("delivery", {}) if p.exists() else {}

LEAD_IN = 0.35   # silence before the first line
TAIL = 1.2       # default silence after the last line, so the video doesn't cut mid-breath


def tail_for(ep) -> float:
    """Time the video holds after the last word. A storyboard sets `end_hold_s` to what its final
    picture needs (a landing, the last label); otherwise the default breath + music fade."""
    extra = getattr(ep, "extra", None) or {}
    v = extra.get("end_hold_s")
    return max(0.5, float(v)) if v is not None else TAIL


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


def clip_dir(ep) -> Path | None:
    """Pre-generated per-beat voice clips (`voice_clips: <dir>` in the storyboard, relative to the repo):
    one <beat id>.mp3/.wav each, e.g. a duo voiced with two ElevenLabs voices through the connector."""
    d = (getattr(ep, "extra", None) or {}).get("voice_clips")
    if not d:
        return None
    from ..configuration import settings
    p = Path(d) if Path(d).is_absolute() else settings.root / d
    return p


def load_clip(path: Path, sr: int = 24000) -> np.ndarray:
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype="<f4").copy()


def cap_pauses(a: np.ndarray, sr: int, max_pause: float, thresh: float = 0.01) -> np.ndarray:
    """Shorten silences inside a clip to `max_pause` seconds (TTS models sometimes linger between sentences)."""
    hop = int(sr * 0.01)
    if max_pause <= 0 or len(a) < hop * 3:
        return a
    loud = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) > thresh for i in range(0, len(a) - hop + 1, hop)])
    keep, run = [], 0
    for k, l in enumerate(loud):
        run = 0 if l else run + 1
        keep.append(l or run * 0.01 <= max_pause / 2 or (k + 1 < len(loud) and _near_loud(loud, k, max_pause / 2 / 0.01)))
    mask = np.repeat(np.array(keep), hop)
    tail = a[len(mask):]
    return np.concatenate([a[:len(mask)][mask], tail])


def _near_loud(loud, k, n):
    n = int(n)
    return bool(loud[k + 1: k + 1 + n].any())


def _clip_for(ep, beat_id: str) -> Path | None:
    d = clip_dir(ep)
    if d is None:
        return None
    for ext in (".wav", ".mp3"):
        if (d / f"{beat_id}{ext}").exists():
            return d / f"{beat_id}{ext}"
    raise FileNotFoundError(f"voice_clips is set but {d}/{beat_id}.mp3 is missing")


def _kokoro_voice(v):
    """A storyboard may name the provider (`voice: elevenlabs`); Kokoro then uses its default (KOKORO_VOICE)."""
    from ..configuration import settings
    return settings.kokoro_voice if v in (None, "", "elevenlabs", "kokoro") else v


def narrate(ep, out_wav: Path, provider: str | None = None) -> Timeline:
    tts = get_tts(provider) if clip_dir(ep) is None else None
    delivery = _delivery()
    # expressive delivery (sentence-by-sentence takes, emphasis, punctuation pauses): see expressive.py
    expr = None
    if tts is not None and getattr(tts, "name", "") == "kokoro" and delivery.get("expressive", True):
        from .expressive import ExpressiveKokoro
        expr = ExpressiveKokoro(tts)
    chunks: list[np.ndarray] = []
    timed: list[TimedLine] = []
    sr_ref = None
    t = LEAD_IN
    last = ep.lines[-1].id if ep.lines else None
    for ln in ep.lines:
        pace = delivery.get(getattr(ln, "pace", "calm") or "calm", {})
        speed = ep.speed * (getattr(ln, "speed", None) or pace.get("speed", 1.0))
        # The voice gets pronunciation-normalised text; captions keep the written text (ln.text).
        spoken = normalise(ln.text)
        clip = _clip_for(ep, ln.id)
        if clip is not None:
            samples, sr = load_clip(clip), 24000
            mp = (getattr(ep, "extra", None) or {}).get("max_inner_pause_s")
            if mp:
                samples = cap_pauses(samples, sr, float(mp))
        elif expr is not None:
            samples, sr = expr.synth(spoken, voice=_kokoro_voice(ep.voice), speed=speed, key=f"{ep.slug}/{ln.id}")
        elif getattr(tts, "name", "") == "elevenlabs":
            i = ep.lines.index(ln)
            ctx = lambda j: normalise(ep.lines[j].text) if 0 <= j < len(ep.lines) else None
            vid = (getattr(ep, "extra", None) or {}).get("voice_id")      # storyboard `voice_id`: an ElevenLabs voice
            samples, sr = tts.synth(spoken, voice=vid, speed=speed, previous_text=ctx(i - 1), next_text=ctx(i + 1))
        else:
            samples, sr = tts.synth(clean(spoken), voice=_kokoro_voice(ep.voice), speed=speed)
        samples = _trim(np.asarray(samples, dtype=np.float32), sr)
        if sr_ref is None:
            sr_ref = sr
            chunks.append(np.zeros(int(LEAD_IN * sr), dtype=np.float32))
        elif sr != sr_ref:
            raise RuntimeError("TTS sample rate changed between lines")
        dur = len(samples) / sr
        timed.append(TimedLine(ln.id, clean(ln.text), round(t, 3), round(t + dur, 3)))
        chunks.append(samples)
        pause = ln.pause_after + pace.get("pause", 0.0)
        if ln.id == last and (getattr(ep, "extra", None) or {}).get("end_hold_s") is not None:
            pause = 0.0                           # the end hold replaces the last pause (no double gap)
        chunks.append(np.zeros(int(pause * sr), dtype=np.float32))
        t += dur + pause
        print(f"  [{timed[-1].start:6.2f}-{timed[-1].end:6.2f}] {ln.id}", flush=True)
    chunks.append(np.zeros(int(tail_for(ep) * sr_ref), dtype=np.float32))
    audio = np.concatenate(chunks)
    peak = float(np.max(np.abs(audio))) or 1.0
    audio = audio * (0.89 / peak)  # normalise to about -1 dBFS
    sf.write(out_wav, audio, sr_ref)
    return Timeline(timed, len(audio) / sr_ref)
