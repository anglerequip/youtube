"""Expressive delivery for the narrator: free techniques that make a TTS voice sound less robotic.

Adapted from common human-sounding AI-voiceover practice (studied 2026-11-19), using only what costs
nothing extra with a local voice:

1. Sentence by sentence. Each sentence is generated on its own, never a whole beat in one call, so
   each one can get its own tone, pace and pause.
2. Takes. A few takes of every sentence, each with a slightly different tone (the voice's style
   vector blended with a little of a sibling voice) and pace (a few percent). The liveliest take is
   kept: the one whose pitch moves most, as long as its length is close to the others (so no take
   that rushes or drags). Different sentences end up with different tones, like a person talking.
3. Punctuation drives delivery. "!" is a touch faster, "?" gets a longer pause after it, "..." is
   a deliberate pause inside the sentence, commas are short breaths (handled by the model).
4. Emphasis. Wrap a word in asterisks in the storyboard (*four*) to stress it: the word gets primary
   stress and a longer vowel, with a tiny breath before it. Captions show the word without the stars.
5. Intentional pauses only. Dead air the model leaves at the ends is trimmed; pauses come from the
   script (pause_after, pace) and from the rules here.

Everything is deterministic (seeded), so a re-run of an episode gives the same narration.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

# sibling voices used for small tone variations of the house voice (af_bella); kept to US female
# voices with a similar register so the narrator stays recognisably the same person
SIBLINGS = ("af_heart", "af_nicole", "af_sarah", "af_aoede")
TAKES = 3                       # takes per sentence (local and fast, so this costs only seconds)
BLEND = (0.0, 0.07, 0.12)       # how much of a sibling voice each take borrows
PACE_JITTER = (0.0, -0.025, 0.025)
PAUSE = {".": 0.24, "!": 0.22, "?": 0.36, "…": 0.30}
ELLIPSIS_PAUSE = 0.42           # a "..." inside a sentence
EMPHASIS_BREATH = 0.06          # tiny gap before an emphasised word

_EMPH = re.compile(r"\*([^*]+)\*")
_VOWELS = "aeiouæɐɑɒɔəɚɛɜɝɪʊʌʏøœɤɯɨʉɘɵɞɶyɪ"


def clean(text: str) -> str:
    """Text for captions and pronunciation: emphasis stars removed."""
    return _EMPH.sub(r"\1", text)


def sentences(text: str) -> list[str]:
    """Split a beat into sentences, keeping '...' and the end punctuation with each sentence."""
    t = re.sub(r"\.\.\.", "…", text.strip())
    parts = re.split(r"(?<=[.!?])\s+(?=[\"'*A-Z0-9])", t)
    return [p.strip() for p in parts if p.strip()]


def _seed(*parts) -> int:
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def _stress(ph: str) -> str:
    """Primary stress on the word's stressed syllable and a lengthened vowel there."""
    ph = ph.strip()
    if "ˈ" not in ph:
        ph = ph.replace("ˌ", "ˈ", 1) if "ˌ" in ph else "ˈ" + ph
    i = ph.index("ˈ") + 1
    while i < len(ph) and ph[i] not in _VOWELS:
        i += 1
    while i < len(ph) and ph[i] in _VOWELS:
        i += 1
    if i <= len(ph) and "ː" not in ph[max(0, i - 3): i + 1]:
        ph = ph[:i] + "ː" + ph[i:]
    return ph


def _segments(sentence: str) -> list[tuple[str, bool]]:
    """[(text, emphasised)], splitting on *word* markers and on '…' (which becomes a pause)."""
    out = []
    for chunk in re.split(r"(…)", sentence):
        if chunk == "…":
            out.append(("…", False))
            continue
        pos = 0
        for m in _EMPH.finditer(chunk):
            if m.start() > pos:
                out.append((chunk[pos:m.start()], False))
            out.append((m.group(1), True))
            pos = m.end()
        if pos < len(chunk):
            out.append((chunk[pos:], False))
    return [(t, e) for t, e in out if t.strip()]


def _pitch_movement(y: np.ndarray, sr: int) -> float:
    """How much the pitch moves (std of f0 in semitones over voiced frames): higher = less monotone."""
    import librosa
    f0 = librosa.yin(y.astype(np.float32), fmin=120, fmax=420, sr=sr, frame_length=1024, hop_length=256)
    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=256)[0][: len(f0)]
    voiced = f0[(rms > 0.25 * rms.max()) & (f0 > 125) & (f0 < 410)]
    if len(voiced) < 8:
        return 0.0
    st = 12 * np.log2(voiced / np.median(voiced))
    return float(np.std(np.clip(st, -7, 7)))


class ExpressiveKokoro:
    """Wraps KokoroTTS (factory.voice_engine.kokoro) with the techniques above."""

    def __init__(self, tts):
        self.tts, self.k = tts, tts.k
        self.last_report: list[dict] = []

    def _style(self, voice: str, sib: str, w: float):
        base = self.k.get_voice_style(voice)
        return base if w <= 0 else ((1 - w) * base + w * self.k.get_voice_style(sib)).astype(np.float32)

    def _phonemes(self, segs) -> list[tuple[str, bool]]:
        out = []
        for txt, emph in segs:
            if txt == "…":
                out.append(("…", False))
                continue
            ph = self.k.tokenizer.phonemize(txt, "en-us").strip()
            out.append((_stress(ph) if emph else ph, emph))
        return out

    def _render(self, phs, style, speed) -> tuple[np.ndarray, int]:
        """Render phoneme segments; pauses at '…' and a breath before emphasised words."""
        pieces, sr, buf = [], 24000, []

        def flush():
            if buf:
                y, s = self.k.create(" ".join(buf), voice=style, speed=speed, is_phonemes=True, lang="en-us")
                pieces.append(np.asarray(y, dtype=np.float32)); buf.clear()
                return s
            return sr
        for ph, emph in phs:
            if ph == "…":
                sr = flush(); pieces.append(np.zeros(int(ELLIPSIS_PAUSE * sr), np.float32))
            else:
                buf.append(ph)
        sr = flush()
        return np.concatenate(pieces) if pieces else np.zeros(1, np.float32), sr

    def synth_sentence(self, sentence: str, voice: str, speed: float, key: str = ""):
        end = sentence.rstrip()[-1:] if sentence.rstrip()[-1:] in ".!?…" else "."
        sp = speed * (1.04 if end == "!" else 1.0)
        phs = self._phonemes(_segments(sentence))
        if any(e for _, e in phs):
            # emphasis: a tiny breath before the stressed word, by splitting the phrase there
            split, cur = [], []
            for ph, e in phs:
                if e and cur:
                    split.append(cur); cur = []
                cur.append((ph, e))
            split.append(cur)
        else:
            split = [phs]
        rng = np.random.default_rng(_seed(key, sentence))
        sibs = rng.permutation(SIBLINGS)
        takes = []
        for n in range(TAKES):
            style = self._style(voice, sibs[n % len(sibs)], BLEND[n % len(BLEND)])
            parts, sr = [], 24000
            for j, grp in enumerate(split):
                y, sr = self._render(grp, style, sp * (1 + PACE_JITTER[n % len(PACE_JITTER)]))
                if j:
                    parts.append(np.zeros(int(EMPHASIS_BREATH * sr), np.float32))
                parts.append(_trim(y, sr))
            y = np.concatenate(parts)
            takes.append({"y": y, "sr": sr, "dur": len(y) / sr, "move": _pitch_movement(y, sr), "take": n})
        med = float(np.median([t["dur"] for t in takes]))
        ok = [t for t in takes if abs(t["dur"] - med) <= 0.08 * med] or takes
        best = max(ok, key=lambda t: t["move"])
        self.last_report.append({"sentence": sentence, "take": best["take"],
                                 "pitch_movement": [round(t["move"], 2) for t in takes]})
        return best["y"], best["sr"], PAUSE.get(end, 0.24)

    def synth(self, text: str, voice: str, speed: float = 1.0, key: str = ""):
        """A whole beat: sentence by sentence with the pauses between them."""
        out, sr = [], 24000
        ss = sentences(text)
        for i, s in enumerate(ss):
            y, sr, pause = self.synth_sentence(s, voice, speed, key)
            out.append(y)
            if i < len(ss) - 1:
                out.append(np.zeros(int(pause * sr), np.float32))
        return np.concatenate(out), sr


def _trim(samples: np.ndarray, sr: int, thresh: float = 0.01) -> np.ndarray:
    idx = np.nonzero(np.abs(samples) > thresh)[0]
    if len(idx) == 0:
        return samples
    pad = int(0.03 * sr)
    return samples[max(0, idx[0] - pad): idx[-1] + pad]
