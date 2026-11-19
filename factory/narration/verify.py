"""Automatic listening check: transcribe narration with Whisper and compare it to the script.

Catches missing, extra or wrong words (often mispronunciations) and truncated endings. It cannot
judge how *good* a voice sounds; that stays a human decision.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache

from num2words import num2words

MODEL = "small.en"


@lru_cache(maxsize=1)
def _model(name: str = MODEL):
    from faster_whisper import WhisperModel
    return WhisperModel(name, device="cpu", compute_type="int8")


def words(text: str) -> list[str]:
    text = text.lower().replace("-", " ")
    text = re.sub(r"\d+(\.\d+)?", lambda m: num2words(float(m.group()) if "." in m.group() else int(m.group())), text)
    text = text.replace("-", " ")
    return re.findall(r"[a-z']+", text)


@dataclass
class Verdict:
    expected: str
    heard: str
    wer: float
    problems: list[str]
    last_word_ok: bool


def transcribe(wav_path, prompt: str | None = None) -> str:
    segs, _ = _model().transcribe(str(wav_path), language="en", beam_size=5, initial_prompt=prompt,
                                  condition_on_previous_text=False)
    return " ".join(s.text.strip() for s in segs)


def check(wav_path, expected_spoken: str) -> Verdict:
    heard = transcribe(wav_path)
    exp, got = words(expected_spoken), words(heard)
    sm = SequenceMatcher(None, exp, got, autojunk=False)
    problems, errors = [], 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        errors += max(i2 - i1, j2 - j1)
        problems.append(f"{op}: expected '{' '.join(exp[i1:i2])}' heard '{' '.join(got[j1:j2])}'")
    wer = errors / max(1, len(exp))
    last_ok = bool(exp and got and exp[-1] == got[-1])
    return Verdict(expected_spoken, heard, round(wer, 3), problems, last_ok)
