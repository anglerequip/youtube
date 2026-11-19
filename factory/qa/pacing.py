"""Layer 7 (pacing and attention): the attention-event timeline of a Short.

An attention event is anything that gives the eye something new: a cut, a label card, a badge change,
a physical sound event or a reveal. Long stretches without one lose viewers; shots that repeat the same
composition back to back are redundant; footage after the last word is dead air.
"""
from __future__ import annotations

import math

from .findings import Finding


def attention_events(plan: dict, module=None) -> list[tuple[float, str]]:
    ev = [(s["start"], "cut") for s in plan.get("shots", [])[1:]]
    ev += [(c["start"], "card") for c in plan.get("cards", [])]
    badges = (plan.get("frames") or {}).get("badge") or []
    prev = None
    for i, b in enumerate(badges):
        if b != prev and b:
            ev.append((i / plan["fps"], "badge"))
        prev = b
    if module is not None and hasattr(module, "sfx_events"):
        for e in module.sfx_events(plan):
            gain = (e[2] or {}).get("gain", 1.0) if len(e) > 2 and isinstance(e[2], dict) else 1.0
            if gain >= 0.3:                         # ambient texture (chain clatter) is not an attention event
                ev.append((float(e[0]), f"sfx:{e[1]}"))
    for t in (plan.get("timing") or {}).get("reveals", []):
        ev.append((float(t), "reveal"))
    return sorted(ev)


def _cam(s, which):
    if s.get("type") == "keys":
        return s["pos"][0 if which == 0 else -1], s["look"][0 if which == 0 else -1]
    if s.get("type") == "orbit":
        return None, None
    return s.get("pos0"), s.get("look0")


def check(ctx, cfg: dict) -> tuple[list[Finding], dict]:
    c = cfg["pacing"]
    plan, tl, sb = ctx.plan, ctx.tl, ctx.sb
    F: list[Finding] = []
    if plan is None or tl is None:
        return F, {}
    dur = plan["n_frames"] / plan["fps"]
    ev = attention_events(plan, ctx.module)
    times = [0.0] + [t for t, _ in ev if 0 < t < dur] + [dur]
    gaps = [(b - a, a) for a, b in zip(times, times[1:])]
    worst = max(gaps)
    for g, a in gaps:
        if g > c["max_gap_s"]:
            F.append(Finding(f"pacing.dead_stretch.{a:.0f}", "pacing", 2, None,
                             f"{g:.1f}s with no new attention event (cut, card, badge, sound event) from {a:.1f}s",
                             t=a, expected=f"something new at least every {c['max_gap_s']}s",
                             repair="add a cut, a camera beat or a physical event in this stretch"))
    hook = tl.lines[0]
    if hook.end - hook.start > c["hook_max_s"]:
        F.append(Finding("pacing.slow_hook", "pacing", 2, None,
                         f"hook line takes {hook.end - hook.start:.1f}s (target {c['hook_max_s']}s)", t=0))
    shots = plan.get("shots", [])
    for k, s in enumerate(shots):
        d = s["end"] - s["start"]
        if d < c["min_shot_s"] and 0 < k < len(shots) - 1:
            F.append(Finding(f"pacing.flash_shot.{k}", "pacing", 3, None, f"shot {k} lasts only {d:.2f}s", t=s["start"], shot=k))
        if d > c["max_shot_s"]:
            inner = [t for t, _ in ev if s["start"] < t < s["end"]]
            if len(inner) < 2:
                F.append(Finding(f"pacing.long_shot.{k}", "pacing", 3, None,
                                 f"shot {k} holds {d:.1f}s with {len(inner)} events inside", t=s["start"], shot=k))
    # back-to-back shots with the same composition (camera barely moved across a cut)
    for k in range(1, len(shots)):
        a, b = shots[k - 1], shots[k]
        pa, la = _cam(a, 1)
        pb, lb = _cam(b, 0)
        if pa and pb and la and lb and (a.get("lighting") == b.get("lighting")):
            dp = math.dist(pa, pb); dl = math.dist(la, lb)
            scale = max(0.05, math.dist(pa, la))
            if dp < 0.08 * scale and dl < 0.08 * scale:
                F.append(Finding(f"pacing.jump_cut.{k}", "pacing", 2, None,
                                 f"cut at {b['start']:.1f}s changes almost nothing (camera moves {dp:.2f} m): reads as a glitch",
                                 t=b["start"], shot=k, repair="merge the shots or change the angle"))
    trailing = dur - tl.lines[-1].end
    if trailing > c["trailing_max_s"]:
        F.append(Finding("pacing.trailing", "pacing", 3, None, f"{trailing:.1f}s of video after the last word", t=tl.lines[-1].end))
    metrics = {"attention_events": len(ev), "longest_gap_s": round(worst[0], 2), "longest_gap_at": round(worst[1], 2),
               "shots": len(shots), "mean_shot_s": round(dur / max(1, len(shots)), 2), "duration_s": round(dur, 2)}
    return F, metrics
