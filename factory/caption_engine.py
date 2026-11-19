"""Burned-in captions, a few words at a time (the standard Shorts look).

Timing comes from the narration timeline. Within one line, chunks get time in proportion
to their character count, which is close enough for 2-3 word chunks.
"""
from __future__ import annotations

import re
from pathlib import Path

from .voice_engine.narrate import Timeline

MAX_WORDS = 3
FONT = "DejaVu Sans"
SIZE = 82
MARGIN_V = 560  # px from the bottom of the 1920px frame; clears the Shorts UI

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},{SIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,80,80,{MARGIN_V},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ts(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def chunk_words(text: str, max_words: int = MAX_WORDS) -> list[str]:
    words = text.split()
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or re.search(r"[.,!?;:…]$", w):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def write_ass(tl: Timeline, path: Path):
    events = []
    for ln in tl.lines:
        chunks = chunk_words(ln.text)
        weights = [len(c) + 2 for c in chunks]
        total = sum(weights)
        t = ln.start
        span = ln.end - ln.start
        for c, w in zip(chunks, weights):
            d = span * w / total
            text = c.upper().replace("{", "(").replace("}", ")")
            pop = r"{\fscx112\fscy112\t(0,90,\fscx100\fscy100)}"
            events.append(f"Dialogue: 0,{_ts(t)},{_ts(t + d)},Cap,,0,0,0,,{pop}{text}")
            t += d
    path.write_text(HEADER + "\n".join(events) + "\n", encoding="utf-8")
