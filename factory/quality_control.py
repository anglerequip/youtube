"""Automatic checks before a draft is shown to a human.

Each check returns a Check(name, ok, detail, severity). "error" failures block approval
(the video goes to QC_FAILED); "warn" failures are shown to the reviewer in Telegram.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from fractions import Fraction
from pathlib import Path

import numpy as np
import soundfile as sf

from .configuration import settings
from .storyboard_engine import Storyboard, all_storyboards
from .voice_engine.narrate import Timeline

SAFE_TOP = 0.06      # fraction of height kept clear at the top
SAFE_BOTTOM = 0.20   # Shorts UI (title, buttons) covers roughly the bottom fifth


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    severity: str = "error"   # or "warn"

    def __post_init__(self):
        self.ok = bool(self.ok)        # numpy bools aren't JSON serialisable
        self.detail = str(self.detail)


def ffprobe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def check_file(path: Path) -> list[Check]:
    if not path.exists() or path.stat().st_size < 10_000:
        return [Check("file", False, f"{path} missing or too small")]
    # Full decode catches truncated or corrupt files.
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                       capture_output=True, text=True)
    errs = r.stderr.strip()
    return [Check("integrity", r.returncode == 0 and not errs, errs[:300] or "decodes cleanly")]


def check_streams(info: dict) -> list[Check]:
    v = [s for s in info["streams"] if s["codec_type"] == "video"]
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    out = []
    if not v:
        return [Check("video_stream", False, "no video stream")]
    w, h = int(v[0]["width"]), int(v[0]["height"])
    out.append(Check("resolution", (w, h) == (1080, 1920), f"{w}x{h} (want 1080x1920, 9:16)"))
    try:
        fps = float(Fraction(v[0].get("avg_frame_rate", "0/1")))
    except (ValueError, ZeroDivisionError):
        fps = 0.0
    out.append(Check("frame_rate", abs(fps - settings.fps) < 0.5, f"{fps:.2f} fps (configured {settings.fps})"))
    out.append(Check("audio_stream", bool(a), "present" if a else "no audio stream"))
    dur = float(info["format"]["duration"])
    out.append(Check("duration", settings.min_seconds <= dur <= settings.max_seconds,
                     f"{dur:.1f}s (allowed {settings.min_seconds:.0f}-{settings.max_seconds:.0f}s)"))
    return out


def check_audio(wav: Path) -> list[Check]:
    x, sr = sf.read(wav, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    clipped = float(np.mean(np.abs(x) > 0.999)) if len(x) else 0.0
    rms = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    return [
        Check("audio_level", rms > 0.01, f"rms {rms:.3f}"),
        Check("audio_clipping", clipped < 1e-4, f"peak {peak:.3f}, clipped samples {clipped:.5%}"),
    ]


def check_captions(tl: Timeline, ass: Path, duration: float) -> list[Check]:
    text = ass.read_text(encoding="utf-8")
    times = re.findall(r"Dialogue: \d+,(\d+):(\d\d):(\d\d\.\d\d),(\d+):(\d\d):(\d\d\.\d\d)", text)
    to_s = lambda h, m, s: int(h) * 3600 + int(m) * 60 + float(s)  # noqa: E731
    spans = [(to_s(*t[:3]), to_s(*t[3:])) for t in times]
    out = [Check("captions_present", len(spans) > 0, f"{len(spans)} caption events")]
    if spans:
        overlaps = sum(1 for a, b in zip(spans, spans[1:]) if b[0] < a[1] - 0.011)
        out.append(Check("captions_order", overlaps == 0, f"{overlaps} overlapping events"))
        out.append(Check("captions_in_range", spans[-1][1] <= duration + 0.05,
                         f"last caption ends {spans[-1][1]:.2f}s, video {duration:.2f}s"))
        # Captions are timed from the narration timeline, so each beat's captions must start at its start.
        starts = {round(s, 2) for s, _ in spans}
        drift = [ln.id for ln in tl.lines if min(abs(round(ln.start, 2) - s) for s in starts) > 0.02]
        out.append(Check("captions_sync", not drift, "aligned to narration" if not drift else f"drift in {drift}"))
    m = re.search(r"Style: Cap,[^,]*,(\d+),.*,(\d+),1\s*$", text, re.M)
    if m:
        margin_v = int(m.group(2))
        ok = margin_v >= SAFE_BOTTOM * 1920
        out.append(Check("captions_safe_area", ok, f"caption baseline {margin_v}px above bottom "
                                                   f"(needs >= {SAFE_BOTTOM * 1920:.0f}px)"))
    return out


def check_frames(video: Path, duration: float) -> list[Check]:
    """Catch blank or frozen output: sample frames and look at variation."""
    n = 6
    stats = []
    for i in range(n):
        t = duration * (i + 0.5) / n
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                              "-vf", "scale=108:192", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                             capture_output=True).stdout
        if len(raw) == 108 * 192:
            stats.append(np.frombuffer(raw, np.uint8).astype(float))
    if len(stats) < n:
        return [Check("frames", False, f"could only decode {len(stats)}/{n} sample frames")]
    blank = [i for i, f in enumerate(stats) if f.std() < 2]
    diffs = [np.abs(a - b).mean() for a, b in zip(stats, stats[1:])]
    return [
        Check("frames_not_blank", not blank, "ok" if not blank else f"blank sample frames {blank}"),
        Check("frames_change", max(diffs) > 0.5, f"max mean frame diff {max(diffs):.2f}"),
    ]


def check_metadata(sb: Storyboard) -> list[Check]:
    out = [
        Check("title_length", 10 <= len(sb.title) <= 100, f"{len(sb.title)} chars"),
        Check("description", 20 <= len(sb.description) <= 5000, f"{len(sb.description)} chars"),
        Check("tags", 3 <= len(sb.tags) and sum(len(t) for t in sb.tags) <= 450, f"{len(sb.tags)} tags"),
        Check("sources", bool(sb.sources), f"{len(sb.sources)} sources listed", "warn"),
    ]
    bad = re.findall(r"[<>]", sb.title + sb.description)
    out.append(Check("metadata_chars", not bad, "YouTube rejects < and > in titles/descriptions"))
    return out


def check_similarity(sb: Storyboard, threshold: float = 0.6) -> list[Check]:
    """Flag scripts that are too close to another episode (duplicate topics or recycled templates)."""
    mine = sb.full_text().lower()
    worst, who = 0.0, None
    for other in all_storyboards():
        if other.slug == sb.slug:
            continue
        r = SequenceMatcher(None, mine, other.full_text().lower()).ratio()
        if r > worst:
            worst, who = r, other.slug
    return [Check("originality", worst < threshold, f"closest episode {who}: {worst:.0%} similar")]


def check_assets(sb: Storyboard) -> list[Check]:
    """Only generated assets are allowed: no media files inside an episode folder unless declared."""
    media = [p.name for p in sb.path.iterdir() if p.suffix.lower() in
             (".mp3", ".wav", ".mp4", ".mov", ".png", ".jpg", ".jpeg", ".gif", ".webm", ".ogg")]
    declared = set(sb.extra.get("licensed_assets", {}) or {})
    undeclared = [m for m in media if m not in declared]
    return [Check("assets_licensed", not undeclared,
                  "all visuals and audio generated in code" if not undeclared
                  else f"undeclared media files: {undeclared}")]


def check_science(sb: Storyboard, sim_report: dict | None) -> list[Check]:
    out = [Check("caveats_listed", bool(sb.caveats), f"{len(sb.caveats)} caveats", "warn")]
    for name, (ok, detail) in (sim_report or {}).items():
        out.append(Check(f"science:{name}", bool(ok), detail))
    if not sim_report:
        out.append(Check("science:self_checks", False, "sim defines no self_checks()", "warn"))
    return out


def run_all(sb: Storyboard, sim_report: dict | None = None) -> tuple[bool, list[Check]]:
    out_dir = sb.out_dir
    video = sb.final_video
    checks = check_file(video)
    if checks[0].ok:
        info = ffprobe(video)
        duration = float(info["format"]["duration"])
        checks += check_streams(info)
        checks += check_audio(out_dir / "mix.wav")
        checks += check_captions(Timeline.load(out_dir / "timeline.json"), out_dir / "captions.ass", duration)
        checks += check_frames(video, duration)
    checks += check_metadata(sb)
    checks += check_similarity(sb)
    checks += check_assets(sb)
    checks += check_science(sb, sim_report)
    passed = all(c.ok for c in checks if c.severity == "error")
    (out_dir / "qc.json").write_text(json.dumps([asdict(c) for c in checks], indent=2))
    return passed, checks


def summarize(checks: list[Check]) -> str:
    lines = []
    for c in checks:
        mark = "PASS" if c.ok else ("FAIL" if c.severity == "error" else "WARN")
        lines.append(f"{mark:4}  {c.name:<22} {c.detail}")
    return "\n".join(lines)
