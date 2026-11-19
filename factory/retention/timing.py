"""Time expressions: how the storyboard says *when* something happens, without hard-coding seconds.

    12.5                 seconds from the start of the video
    "payoff"             start of beat `payoff`
    "payoff.end"         end of beat `payoff` (last word)
    "payoff+0.4"         offsets work on any form ("payoff.end-0.2")
    "double@doubles"     when the word "doubles" is spoken in beat `double` (estimated: syllable-weighted,
                         exactly as the captions are timed, so the cue lands with the caption)
    "hud:arch.settle"    a HUD event (see hud.py: appear, settle, cross, answer, hide)
    "end"                end of the video

Rewording a beat re-times everything bound to it, like the rest of the factory.
"""
from __future__ import annotations

import re

_EXPR = re.compile(r"^\s*(?P<base>[^+\-]+?)\s*(?:(?P<sign>[+\-])\s*(?P<off>\d+(?:\.\d+)?))?\s*$")


class TimeError(ValueError):
    pass


def word_time(tl, beat_id: str, word: str, occurrence: int = 1) -> float:
    """Estimated time the `occurrence`-th match of `word` starts in beat `beat_id`."""
    from ..caption_engine import syllables
    ln = next((l for l in tl.lines if l.id == beat_id), None)
    if ln is None:
        raise TimeError(f"no beat '{beat_id}'")
    words = ln.text.replace("*", "").split()
    w = [syllables(x) for x in words]
    total = sum(w) or 1
    target = re.sub(r"[^a-z0-9]", "", word.lower())
    seen, acc = 0, 0.0
    for x, wx in zip(words, w):
        if re.sub(r"[^a-z0-9]", "", x.lower()).startswith(target) and target:
            seen += 1
            if seen == occurrence:
                return ln.start + (ln.end - ln.start) * acc / total
        acc += wx
    raise TimeError(f"word '{word}' not found in beat '{beat_id}': \"{ln.text}\"")


def resolve(expr, tl, events: dict | None = None, duration: float | None = None) -> float:
    """Turn a time expression into seconds. `events` maps 'hud:<id>.<event>' to seconds."""
    if expr is None:
        raise TimeError("missing time")
    if isinstance(expr, (int, float)):
        return float(expr)
    m = _EXPR.match(str(expr))
    if not m:
        raise TimeError(f"bad time expression {expr!r}")
    base, off = m["base"].strip(), float(m["off"] or 0) * (-1 if m["sign"] == "-" else 1)
    try:
        return float(base) + off
    except ValueError:
        pass
    if base == "end":
        if duration is None:
            raise TimeError("'end' needs the video duration")
        return duration + off
    if base.startswith("hud:"):
        if events is None or base not in events:
            raise TimeError(f"unknown HUD event {base!r} (known: {sorted(events or {})})")
        return events[base] + off
    if "@" in base:
        beat, word = base.split("@", 1)
        occ = 1
        if "#" in word:
            word, n = word.split("#", 1)
            occ = int(n)
        return word_time(tl, beat.strip(), word.strip(), occ) + off
    beat, _, edge = base.partition(".")
    ids = {l.id for l in tl.lines}
    if beat not in ids:
        raise TimeError(f"unknown beat '{beat}' in {expr!r} (beats: {sorted(ids)})")
    if edge in ("", "start"):
        return tl.start(beat) + off
    if edge == "end":
        return tl.end(beat) + off
    raise TimeError(f"unknown beat edge '.{edge}' in {expr!r} (use .start or .end)")


def window(spec, tl, events=None, duration=None) -> tuple[float, float]:
    """`show:` as [from, to] time expressions, or one beat id meaning that beat's start..end."""
    if isinstance(spec, str) and not any(c in spec for c in "+-@:.") and spec != "end":
        return tl.start(spec), tl.end(spec)
    if not isinstance(spec, (list, tuple)) or len(spec) != 2:
        raise TimeError(f"show must be a beat id or [from, to], got {spec!r}")
    a = resolve(spec[0], tl, events, duration)
    b_expr = spec[1]
    # a bare beat id as the end of a window means "until that beat ends"
    if isinstance(b_expr, str) and b_expr in {l.id for l in tl.lines}:
        b = tl.end(b_expr)
    else:
        b = resolve(b_expr, tl, events, duration)
    if b <= a:
        raise TimeError(f"window {spec!r} ends before it starts ({a:.2f}s -> {b:.2f}s)")
    return a, b
