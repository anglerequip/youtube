"""Layer 8 (audio QA): measurable properties of the narration and the final mix.

Measured: duration (TikTok rule), clipping, true peak, loudness against the target, narration
completeness (every beat voiced, no dead air inside the narration), and that physical sound events
exist for the declared on-screen events. Not measurable here, and therefore reported as NOT performed:
perceptual listening (pronunciation, naturalness, music taste). The gate never counts those as passed.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np

from .findings import Finding


def loudness(path: Path) -> dict:
    """Integrated loudness and true peak (ffmpeg ebur128)."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", txt)
    p = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", txt)
    return {"lufs": float(i.group(1)) if i else None,
            "true_peak_db": (float(p.group(1)) if p and p.group(1) != "-inf" else None)}


def check(ctx, cfg: dict, final: Path | None = None) -> tuple[list[Finding], dict]:
    import soundfile as sf
    c = cfg["audio"]
    out, F, m = ctx.out, [], {}
    voice = out / "voice.wav"
    final = final or (out / "final.mp4")
    if ctx.tl is not None:
        if ctx.tl.duration < c["min_duration_s"]:
            F.append(Finding("audio.too_short", "audio", 0, "BLOCKED_AUDIO",
                             f"narration timeline is {ctx.tl.duration:.1f}s; videos must be over 60 s"))
        voiced = {ln.id for ln in ctx.tl.lines if ln.end - ln.start > 0.3}
        missing = [b.id for b in ctx.sb.beats if b.id not in voiced]
        if missing:
            F.append(Finding("audio.unvoiced_beats", "audio", 0, "BLOCKED_AUDIO", f"beats with no narration: {missing}"))
    if voice.exists():
        y, sr = sf.read(voice, dtype="float32")
        y = y.mean(axis=1) if y.ndim > 1 else y
        clipped = float(np.mean(np.abs(y) > 0.999))
        m["voice_clipped"] = round(clipped, 6)
        if clipped > 1e-4:
            F.append(Finding("audio.voice_clipping", "audio", 1, "BLOCKED_AUDIO", f"{clipped:.4%} of narration samples clip"))
        # dead air inside the narration (between the first and last word)
        hop = int(0.05 * sr)
        env = np.sqrt(np.convolve(y ** 2, np.ones(hop) / hop, mode="same"))[::hop]
        voiced = env > 0.02 * env.max()
        idx = np.nonzero(voiced)[0]
        if len(idx):
            silent, longest, at = 0, 0, 0.0
            for k in range(idx[0], idx[-1]):
                silent = 0 if voiced[k] else silent + 1
                if silent > longest:
                    longest, at = silent, k * 0.05
            m["longest_pause_s"] = round(longest * 0.05, 2)
            if longest * 0.05 > 2.5:
                F.append(Finding("audio.dead_air", "audio", 2, None,
                                 f"{longest * 0.05:.1f}s silence inside the narration at {at:.1f}s", t=at))
    else:
        F.append(Finding("audio.no_voice", "audio", 1, "BLOCKED_AUDIO", "no narration file"))
    if final.exists():
        L = loudness(final)
        m.update(L)
        if L["true_peak_db"] is not None and L["true_peak_db"] > c["peak_dbfs_max"]:
            F.append(Finding("audio.true_peak", "audio", 1, "BLOCKED_AUDIO",
                             f"true peak {L['true_peak_db']:.1f} dBFS (max {c['peak_dbfs_max']})"))
        if L["lufs"] is not None and abs(L["lufs"] - c["lufs_target"]) > c["lufs_tolerance"]:
            F.append(Finding("audio.loudness", "audio", 2, None,
                             f"integrated loudness {L['lufs']:.1f} LUFS (target {c['lufs_target']} ± {c['lufs_tolerance']})"))
    # physical moments must be heard: every declared event has a sound cue within 0.5 s
    events = (ctx.facts.get("events") or {})
    if ctx.module is not None and hasattr(ctx.module, "sfx_events") and events and ctx.plan:
        cues = [float(e[0]) for e in ctx.module.sfx_events(ctx.plan)]
        for name, ev in events.items():
            if ev.get("sound", True) and not any(abs(t - ev["t"]) < 0.5 or (ev["t"] - 3 < t < ev["t"]) for t in cues):
                F.append(Finding(f"audio.silent_event.{name}", "audio", 3, None,
                                 f"event {name} at {ev['t']:.1f}s has no sound cue near it", t=ev["t"]))
    m["perceptual_listening"] = "not performed (needs a human listener)"
    return F, m
