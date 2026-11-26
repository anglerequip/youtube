"""Sound team (Caesar, 2026-11-19: the chain fountain went "ding ding ding" every half second).

Two parts, like the picture QA:
  check(ctx)        automated "logic" checks on the cue sheet and the exact stems the mixer sums
                    (factory/sound_design.stems): runs before the render and can block it.
  build_packet/read an independent Sound Reviewer, who never sees the generator's reasoning, judges
                    from the cue sheet, an onset timeline and a spectrogram whether a person would
                    find anything annoying; without that critique the release gate blocks.

What "annoying" is measured as (thresholds in config/quality.yaml, sound:):
  repetition   the same identical sample again and again (hash of the rendered cue), per window
  density      cues per second in any window (every cue counts, texture too)
  click train  one kind of cue going on without a pause (varied samples do not help)
  periodicity  a metronome: many same-name cues at near-constant spacing
  masking      sound effects loud against the voice while she speaks
  startle      a cue louder than the voice's own peaks
  music        the bed too loud under the voice
These are proxies: nothing here listens. The report says so.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .findings import Finding

SOUND_CATEGORIES = ["sfx_restraint", "voice_clarity", "music_balance", "sync_and_meaning", "overall"]


def _cfg(cfg):
    return cfg.get("sound", {})


def cue_sheet(ctx) -> list[dict]:
    """Every sound event with what it actually is: name, time, gain, length, and a hash of its samples."""
    from .. import sound_design as sd
    if ctx.module is None or not hasattr(ctx.module, "sfx_events") or ctx.plan is None:
        return []
    out = []
    for ev in sorted(ctx.module.sfx_events(ctx.plan), key=lambda e: e[0]):
        t, name = float(ev[0]), ev[1]
        p = dict(ev[2]) if len(ev) > 2 and ev[2] else {}
        y = sd.render_cue(name, p, t)
        y = np.asarray(y, dtype=np.float64)
        nz = np.nonzero(np.abs(y) > 0.01 * (np.max(np.abs(y)) or 1))[0]
        dur = (nz[-1] + 1) / sd.SR if len(nz) else 0.0
        h = hashlib.sha1(np.round(y / (np.max(np.abs(y)) or 1), 3).tobytes()).hexdigest()[:10]
        out.append({"t": round(t, 3), "name": name, "gain": round(float(p.get("gain", 0.35 if name == "coil" else 1.0)), 3),
                    "dur_s": round(dur, 3), "sample": h,
                    "peak": round(float(np.max(np.abs(y))) * float(p.get("gain", 0.35 if name == "coil" else 1.0)), 4)})
    return out


def _stems(ctx):
    from .. import sound_design as sd
    voice = ctx.out / "voice.wav"
    if not voice.exists() or ctx.module is None or ctx.plan is None:
        return None
    ev = ctx.module.sfx_events(ctx.plan) if hasattr(ctx.module, "sfx_events") else []
    mus = ctx.module.music(ctx.plan) if hasattr(ctx.module, "music") else None
    dur = ctx.plan.get("n_frames", 0) / max(1, ctx.plan.get("fps", 30)) or None
    amb = ctx.sb.extra.get("ambience") if getattr(ctx, "sb", None) is not None else None
    return sd.stems(voice, ev, dur, mus, ambience=amb or ctx.plan.get("ambience"))


def _rms_frames(x, sr, hop=0.05):
    m = int(hop * sr)
    n = len(x) // m
    if x.ndim > 1:
        x = x.mean(axis=1)
    return np.sqrt(np.mean(x[: n * m].reshape(n, m) ** 2, axis=1) + 1e-12)


def _merge(ts, gap):
    out = []
    for t in ts:
        if not out or t - out[-1] > gap:
            out.append(t)
    return np.array(out)


def check(ctx, cfg) -> tuple[list[Finding], dict]:
    c = _cfg(cfg)
    F: list[Finding] = []
    cues = cue_sheet(ctx)
    m = {"cues": len(cues)}
    if not cues:
        return F, {**m, "note": "no sound events"}
    tex_dur = c.get("texture_max_dur_s", 0.08)
    # texture = very short cues whose samples are never the same (coil clatter): a bed, not a "sound"
    by_sample = defaultdict(list)
    for q in cues:
        by_sample[q["sample"]].append(q)
    for q in cues:
        q["texture"] = q["dur_s"] <= tex_dur and len(by_sample[q["sample"]]) == 1

    # 1. identical-sample repetition (the "ding ding ding")
    W = c.get("repeat_window_s", 5.0)
    worst = []
    for h, qs in by_sample.items():
        ts = np.array([q["t"] for q in qs])
        if len(ts) < 2:
            continue
        in_win = max(int(np.sum((ts >= t0) & (ts < t0 + W))) for t0 in ts)
        worst.append((in_win, len(ts), qs[0]["name"], float(np.median(np.diff(ts))) if len(ts) > 1 else 0, ts[0]))
    worst.sort(reverse=True)
    if worst:
        in_win, total, name, med, t0 = worst[0]
        m.update({"max_identical_in_window": in_win, "max_identical_total": total})
        sev = 1 if (in_win >= c.get("repeat_block", 8) or total >= c.get("repeat_total_block", 30)) else \
            2 if (in_win >= c.get("repeat_warn", 4) or total >= c.get("repeat_total_warn", 12)) else None
        if sev is not None:
            F.append(Finding("sound.repetition", "sound", sev, "BLOCKED_AUDIO" if sev <= 1 else None,
                             f"the same '{name}' sample plays {total} times ({in_win} within {W:.0f} s, typically every "
                             f"{med:.2f} s): a listener hears one sound on repeat",
                             t=float(t0), evidence={"top": [list(w[:3]) + [round(w[3], 2)] for w in worst[:5]]},
                             repair="use fewer cues, vary the sample (seed, pitch, length) and only mark events that matter"))
    # 2. density of all cues (cues within 0.15 s of each other are one event: a crack-crack burst). Texture
    # cues count too: round 2 of the chain fountain hid 168 varied "coil" clicks (3 per second) from this check
    # by calling them texture, and the Sound Reviewer heard a ticking clock.
    allc = sorted(q["t"] for q in cues)
    ts = _merge(allc, c.get("burst_s", 0.15))
    Wd = c.get("density_window_s", 5.0)
    if len(ts):
        dens = max(np.sum((ts >= t0) & (ts < t0 + Wd)) for t0 in ts) / Wd
        m["max_cues_per_s"] = round(float(dens), 2)
        sev = 1 if dens > c.get("density_block", 2.0) else 2 if dens > c.get("density_warn", 1.0) else None
        if sev is not None:
            t0 = float(next(t for t in ts if np.sum((ts >= t) & (ts < t + Wd)) / Wd >= dens - 1e-9))
            F.append(Finding("sound.density", "sound", sev, "BLOCKED_AUDIO" if sev <= 1 else None,
                             f"{dens:.1f} sound effects per second around {t0:.1f}s: constant effects stop meaning anything",
                             t=t0, repair="keep one cue per physical event that the viewer should notice"))
    # 3. click train: one kind of cue (by name, whatever its sample) going on and on without a real pause.
    #    Varying the sample does not help: the ear hears the rhythm, not the waveform.
    by_name = defaultdict(list)
    for q in cues:
        by_name[q["name"]].append(q["t"])
    gap, longest = c.get("train_gap_s", 1.2), (0.0, 0, "", 0.0)
    for name, tt in by_name.items():
        tt = list(_merge(sorted(tt), c.get("burst_s", 0.15)))
        i0 = 0
        for i in range(1, len(tt) + 1):
            if i == len(tt) or tt[i] - tt[i - 1] > gap:
                dur, cnt = tt[i - 1] - tt[i0], i - i0
                if cnt >= 6 and dur > longest[0]:
                    longest = (dur, cnt, name, tt[i0])
                i0 = i
    m["longest_click_train_s"] = round(longest[0], 1)
    if longest[0] >= c.get("train_warn_s", 5.0):
        dur, cnt, name, t0 = longest
        sev = 1 if dur >= c.get("train_block_s", 10.0) else 2
        F.append(Finding(f"sound.click_train.{name}", "sound", sev, "BLOCKED_AUDIO" if sev <= 1 else None,
                         f"'{name}' plays {cnt} times in {dur:.1f} s from {t0:.1f}s with no pause over {gap:.1f} s "
                         f"(about {cnt / max(dur, 1e-6):.1f} per second): it reads as a ticking clock, even with varied samples",
                         t=float(t0), repair="mark only the moments that matter; let silence or the music carry the rest"))
    # 4. metronome: same-name cues at near-constant spacing (a short even run already sounds mechanical)
    for name, tt in by_name.items():
        tt = list(_merge(sorted(tt), c.get("burst_s", 0.15)))
        d = np.diff(tt)
        hit = None
        for k, cv, sev in ((c.get("periodic_min_run", 8), c.get("periodic_cv", 0.35), 1),
                           (c.get("periodic_short_run", 3), c.get("periodic_short_cv", 0.12), 2)):
            for i in range(0, max(0, len(d) - k + 1)):
                seg = d[i:i + k]
                if seg.mean() < c.get("periodic_max_interval_s", 2.5) and seg.std() / (seg.mean() + 1e-9) < cv:
                    hit = (k, seg.mean(), tt[i], sev)
                    break
            if hit:
                break
        if hit:
            k, mean, t0, sev = hit
            F.append(Finding(f"sound.periodic.{name}", "sound", sev, "BLOCKED_AUDIO" if sev <= 1 else None,
                             f"'{name}' ticks like a metronome ({k + 1} cues about every {mean:.2f} s from {t0:.1f}s)",
                             t=float(t0), repair="break the rhythm or drop most of these cues"))
    # 5. doubled trigger: two ringing cues of one kind a few tens of ms apart read as a glitch, not a burst
    #    (round 5, Sound Reviewer: two tinks 60 ms apart at 29.5 s, missed by every check above)
    ring = sorted((q["t"], q["name"]) for q in cues if q["name"] in c.get("ringing_cues", ["tink", "ding", "tick", "rise"]))
    for (t1, n1), (t2, n2) in zip(ring, ring[1:]):
        if n1 == n2 and 0.02 <= t2 - t1 < c.get("double_trigger_s", 0.25):
            F.append(Finding(f"sound.double_trigger.{n1}", "sound", 2, None,
                             f"two '{n1}' cues {1000 * (t2 - t1):.0f} ms apart at {t1:.2f}s: sounds like a doubled trigger",
                             t=float(t1), repair="keep one of them"))
            break
    # 4-6. stems: masking, startle, music balance
    st = _stems(ctx)
    if st is None:
        m["stems"] = "not measured (no voice.wav yet)"
        return F, m
    sr = st["sr"]
    v, fx, bed = _rms_frames(st["voice"], sr), _rms_frames(st["fx"], sr), _rms_frames(st["bed"], sr)
    n = min(len(v), len(fx), len(bed))
    v, fx, bed = v[:n], fx[:n], bed[:n]
    voiced = v > 10 ** (-40 / 20) * np.max(v)
    voiced &= v > np.percentile(v[voiced], 20) if voiced.any() else voiced
    if voiced.any():
        rel = 20 * np.log10(fx[voiced] / v[voiced])
        frac = float(np.mean(rel > c.get("masking_db", -12.0)))
        m["sfx_over_voice_frac"] = round(frac, 3)
        sev = 1 if frac > c.get("masking_block", 0.15) else 2 if frac > c.get("masking_warn", 0.05) else None
        if sev is not None:
            i0 = int(np.nonzero(voiced)[0][np.argmax(rel)])
            F.append(Finding("sound.masking", "sound", sev, "BLOCKED_AUDIO" if sev <= 1 else None,
                             f"sound effects within {abs(c.get('masking_db', -12)):.0f} dB of the voice in {frac:.0%} of spoken moments "
                             f"(worst near {i0 * 0.05:.1f}s): they compete with the narration",
                             t=i0 * 0.05, repair="lower or move cues off the words; duck effects under the voice"))
        mb = float(np.median(20 * np.log10(bed[voiced] / v[voiced])))
        m["music_under_voice_db"] = round(mb, 1)
        if mb > c.get("music_max_db", -12.0):
            F.append(Finding("sound.music_balance", "sound", 2, None,
                             f"music only {abs(mb):.0f} dB under the voice while she speaks (want <= {c.get('music_max_db', -12)} dB)",
                             repair="lower the bed or duck it harder"))
    vpk = float(np.max(np.abs(st["voice"])))
    fpk = np.max(np.abs(st["fx"]), axis=1)
    if vpk > 0 and fpk.max() > vpk * 10 ** (c.get("startle_db", 0.0) / 20):
        i = int(np.argmax(fpk))
        F.append(Finding("sound.startle", "sound", 2, None,
                         f"a sound effect at {i / sr:.1f}s peaks {20 * np.log10(fpk.max() / vpk):+.1f} dB over the voice's loudest moment",
                         t=i / sr, repair="lower that cue"))
    m["fatigue_score"] = round(max(0.0, 5 - sum({0: 4, 1: 2.5, 2: 1, 3: 0.3}.get(f.severity, 0) for f in F)), 2)
    return F, m


# ---------------------------------------------------------------- independent Sound Reviewer
INSTRUCTIONS = """# Sound review (independent)

You are the sound team for a short vertical science Short (its length is whatever its story needs). You did not make it. Your only question:
**would a real viewer, watching on a phone with sound on, find anything in this soundtrack annoying,
distracting or confusing?** Be strict: an annoying sound makes people swipe away.

You cannot hear the audio, so judge from the evidence in this folder like a sound engineer reading a session:
- `cue_sheet.md`: every sound effect: time, cue name, gain, length, and `sample` (cues with the same sample id
  are the *identical* sound played again).
- `timeline.png`: top: voice level (grey) and sound-effect level (red) over time; ticks: every cue, one row
  per cue name. Bottom: spectrogram of the final mix (if present) with spoken stretches marked.
- `intent.md`: the narration with times, so you know what each moment is about.
- `stats.json`: measured numbers (repetition, density, masking, music level).

Look for, in this order:
1. Repetition: the same sound over and over (especially bright tonal "ding/tink" cues), metronome rhythms.
2. Clutter: more effects than events the viewer can see; effects with no on-screen reason.
3. Competition with the voice: effects or music loud while she speaks.
4. Startle: a cue much louder than its neighbours; sudden onsets.
5. Missing sound: an important physical moment (a snap, an impact) with no cue, or a cue in the wrong place.
6. Fatigue over the whole video: would the 3rd viewing be irritating?

Write `critique_audio.json` following `schema.json` exactly. Copy `video_sha256` from packet.json.
Scores 0-5 (numbers): 5 = nothing a viewer would notice negatively; 3 = noticeable but tolerable; below 3 =
viewers will be annoyed. `release` is "approve" only if you would ship this soundtrack as is.
Do not read anything outside this folder.
"""

SCHEMA = {
    "video_sha256": "copy from packet.json",
    "reviewer": "who reviewed",
    "first_impression": "how the soundtrack would feel to a viewer, in two sentences",
    "annoyances": [{"t": 0.0, "what": "", "why_annoying": "", "severity": "0-4 (0 critical .. 4 optional)", "repair": ""}],
    "missing_or_misplaced": [{"t": 0.0, "what": ""}],
    "scores": {c: 0.0 for c in SOUND_CATEGORIES},
    "release": "approve | revise | reject",
}


def build_packet(ctx, video: Path, cfg) -> Path:
    from .critic import sha256
    d = ctx.out / "qa" / "review_audio"
    d.mkdir(parents=True, exist_ok=True)
    cues = cue_sheet(ctx)
    F, stats = check(ctx, cfg)
    lines = ["| t (s) | cue | gain | length (s) | sample |", "|---|---|---|---|---|"]
    lines += [f"| {q['t']:.2f} | {q['name']} | {q['gain']:.2f} | {q['dur_s']:.2f} | {q['sample']} |" for q in cues]
    (d / "cue_sheet.md").write_text(f"# Cue sheet: {len(cues)} sound effects\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    (d / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    narr = [f"- {s.id} [{ctx.tl.start(s.id):.1f}-{ctx.tl.end(s.id):.1f}s]: {s.text}" for s in ctx.sb.beats] if ctx.tl else []
    (d / "intent.md").write_text("# Narration\n\n" + "\n".join(narr) + "\n", encoding="utf-8")
    (d / "INSTRUCTIONS.md").write_text(INSTRUCTIONS, encoding="utf-8")
    (d / "schema.json").write_text(json.dumps(SCHEMA, indent=2), encoding="utf-8")
    (d / "packet.json").write_text(json.dumps({"slug": ctx.sb.slug, "video_sha256": sha256(video)}, indent=2), encoding="utf-8")
    _plot(ctx, cues, video, d / "timeline.png")
    return d


def _plot(ctx, cues, video, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    st = _stems(ctx)
    fig, ax = plt.subplots(3, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [2, 2, 3]}, sharex=True)
    if st is not None:
        sr = st["sr"]
        for x, col, lab in ((st["voice"], "0.5", "voice"), (st["fx"], "tab:red", "sound effects"), (st["bed"], "tab:blue", "music")):
            r = _rms_frames(x, sr)
            ax[0].plot(np.arange(len(r)) * 0.05, 20 * np.log10(r + 1e-9), color=col, lw=0.8, label=lab)
        ax[0].set_ylim(-70, 0); ax[0].legend(loc="upper right"); ax[0].set_ylabel("level dBFS (50 ms)")
    names = sorted({q["name"] for q in cues})
    for q in cues:
        ax[1].plot([q["t"], q["t"]], [names.index(q["name"]) - 0.35, names.index(q["name"]) + 0.35],
                   color="tab:red", lw=0.8 + 3 * q["gain"])
    ax[1].set_yticks(range(len(names))); ax[1].set_yticklabels(names); ax[1].set_ylabel("cues")
    import subprocess, tempfile, soundfile as sf
    mix = None
    if video.exists():
        with tempfile.TemporaryDirectory() as td:
            w = Path(td) / "a.wav"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-ac", "1", "-ar", "16000", str(w)], check=False)
            if w.exists():
                mix, msr = sf.read(w)
    if mix is not None:
        ax[2].specgram(mix, NFFT=512, Fs=msr, noverlap=384, cmap="magma", vmin=-110)
        ax[2].set_ylim(0, 8000); ax[2].set_ylabel("final mix (Hz)")
    if ctx.tl:
        for s in ctx.sb.beats:
            for a in ax:
                a.axvspan(ctx.tl.start(s.id), ctx.tl.end(s.id), color="0.85", alpha=0.25, lw=0)
    ax[2].set_xlabel("time (s); grey bands: narration")
    fig.tight_layout(); fig.savefig(out, dpi=90); plt.close(fig)


def read(ctx, video: Path) -> tuple[list[Finding], dict | None]:
    from .critic import sha256
    p = ctx.out / "qa" / "review_audio" / "critique_audio.json"
    if not p.exists():
        return [Finding("review.audio_unavailable", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE",
                        "no independent Sound Reviewer critique of this video's soundtrack",
                        repair=f"run the sound review on {p.parent} then python -m factory qa-gate <slug>")], None
    try:
        c = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return [Finding("review.audio_invalid", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE", f"critique_audio.json unreadable: {e}")], None
    if c.get("video_sha256") != sha256(video):
        return [Finding("review.audio_stale", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE",
                        "the sound critique reviews a different version of the video", repair="review the current render")], None
    sc = c.get("scores") or {}
    for k in SOUND_CATEGORIES:
        try:
            sc[k] = float(sc[k])
        except (KeyError, TypeError, ValueError):
            pass
    bad = [k for k in SOUND_CATEGORIES if not isinstance(sc.get(k), float) or not 0 <= sc[k] <= 5]
    if bad or c.get("release") not in ("approve", "revise", "reject"):
        return [Finding("review.audio_incomplete", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE",
                        f"sound critique incomplete: {bad or 'release'}")], None
    c["scores"] = sc
    F = []
    for k, a in enumerate(c.get("annoyances") or []):
        try:
            sev = int(str(a.get("severity", 2))[0])
        except ValueError:
            sev = 2
        F.append(Finding(f"review.audio_problem.{k + 1}", "review", sev,
                         "BLOCKED_AUDIO" if sev <= 1 else None, f"{a.get('what', '')}: {a.get('why_annoying', '')}",
                         t=a.get("t"), repair=a.get("repair", "")))
    if c["release"] == "reject":
        F.append(Finding("review.audio_rejected", "review", 1, "BLOCKED_AUDIO", "the Sound Reviewer rejected the soundtrack"))
    return F, c
