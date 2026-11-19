"""Burned-in captions in the house style (Blueprint section 6, caption spec CP-1..CP-9).

Captions are built from the storyboard text the writer wrote (so "20 km/h" stays "20 km/h"),
never from the pronunciation-normalised text sent to the voice. Word timing is estimated by
spreading each beat's spoken duration over its words weighted by syllables, until forced
alignment is added.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

from .configuration import settings
from .voice_engine.narrate import Timeline

W, H = 1080, 1920

BREAK_BEFORE = {"and", "but", "so", "because", "or", "then", "when", "while", "until", "even", "which",
                "that", "to", "of", "in", "on", "at", "for", "with", "from", "into", "by", "as"}
UNITS = {"m", "s", "km", "km/h", "m/s", "m/s²", "kg", "g", "cm", "mm", "%", "mph", "°C", "°F", "K", "N", "J", "Hz", "ms"}


@lru_cache(maxsize=1)
def rules() -> dict:
    p = settings.root / "config" / "rules.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))["captions"] if p.exists() else {}


def syllables(word: str) -> int:
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return max(1, len(re.sub(r"\D", "", word)))     # numbers: roughly one per digit
    n = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee")) and n > 1:
        n -= 1
    return max(1, n)


def _tokens(text: str) -> list[str]:
    raw = text.split()
    out: list[str] = []
    for tok in raw:
        bare = tok.strip(",.;:!?")
        if out and bare in UNITS and re.search(r"\d[.,]?$", out[-1].rstrip(",.;:!?")):
            out[-1] = f"{out[-1]} {tok}"       # never split a number from its unit
        elif out and out[-1].lower() in ("not", "≈", "~"):
            out[-1] = f"{out[-1]} {tok}"       # keep "not" with its verb, "≈" with its number
        else:
            out.append(tok)
    return out


def chunk(text: str, max_words: int | None = None, max_chars: int | None = None) -> list[str]:
    r = rules()
    max_words = max_words or r.get("max_words_per_chunk", 3)
    max_chars = max_chars or r.get("max_chars_per_chunk", 16)
    chunks, cur = [], []
    for tok in _tokens(text):
        n_words = sum(len(c.split()) for c in cur)
        cand = " ".join(cur + [tok])
        bare = tok.lower().strip(",.;:!?")
        if cur and (n_words + len(tok.split()) > max_words or len(cand) > max_chars
                    or (bare in BREAK_BEFORE and n_words >= 2)):
            chunks.append(" ".join(cur))
            cur = []
        cur.append(tok)
        if re.search(r"[.,!?;:]$", tok):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def _display(c: str) -> str:
    c = re.sub(r"[.,;:]+$", "", c)            # CP-8: no trailing full stops, keep "?"
    return c.replace("{", "(").replace("}", ")")


def timed_chunks(tl: Timeline) -> list[tuple[float, float, str]]:
    r = rules()
    min_s = r.get("min_chunk_s", 0.6)
    clear = r.get("clear_after_word_s", 0.15)
    events = []
    for ln in tl.lines:
        chunks = chunk(ln.text)
        weights = [sum(syllables(w) for w in c.split()) for c in chunks]
        total = sum(weights) or 1
        span = ln.end - ln.start
        t = ln.start
        timed = []
        for c, w in zip(chunks, weights):
            d = span * w / total
            timed.append([t, t + d, c])
            t += d
        # CP-4: merge chunks shorter than the minimum into a neighbour (prefer the next one)
        i = 0
        while i < len(timed) and len(timed) > 1:
            s, e, c = timed[i]
            if e - s < min_s:
                # prefer the next chunk, but never glue the end of a sentence onto the next sentence
                ends_sentence = re.search(r"[.!?]$", c) is not None
                j = i + 1 if i + 1 < len(timed) and not (ends_sentence and i > 0) else i - 1
                a, b = sorted((i, j))
                merged = [timed[a][0], timed[b][1], f"{timed[a][2]} {timed[b][2]}"]
                timed[a:b + 1] = [merged]
                i = max(0, a - 1)
                continue
            i += 1
        for k, (s, e, c) in enumerate(timed):
            end = e if k < len(timed) - 1 else min(e + clear, ln.end + clear)
            events.append((s, end, _display(c)))
    # never overlap the next caption
    for k in range(len(events) - 1):
        s, e, c = events[k]
        events[k] = (s, min(e, events[k + 1][0]), c)
    return events


def write_ass(tl: Timeline, path: Path):
    r = rules()
    cy = int(r.get("center_y", 0.73) * H)
    size = int(r.get("cap_height_frac", 0.03) * H / 0.70)   # Poppins cap height is ~0.70 em
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Poppins SemiBold,{size},&H00FFFFFF,&H00FFFFFF,&H48000000,&H70000000,0,0,0,0,100,100,0,0,1,3.5,3,5,80,80,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for s, e, text in timed_chunks(tl):
        # soft shadow: blurred semi-transparent outline + offset shadow, no box (Blueprint 6)
        tag = rf"{{\pos({W // 2},{cy})\blur4\fad(80,80)}}"
        # wide, faint dark halo underneath (picture review, round 7: white words got lost over the silver
        # chain pile and a yellow car); still no box, just more shadow where the frame is bright
        halo = rf"{{\pos({W // 2},{cy})\bord11\blur14\1a&HFF&\3a&HA8&\4a&HFF&\fad(80,80)}}"
        lines.append(f"Dialogue: 0,{_ts(s)},{_ts(e)},Cap,,0,0,0,,{halo}{text}")
        lines.append(f"Dialogue: 1,{_ts(s)},{_ts(e)},Cap,,0,0,0,,{tag}{text}")
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def _ts(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


# backwards-compatible name used by older tests
chunk_words = chunk
