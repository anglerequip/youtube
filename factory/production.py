"""Production workflow: storyboard -> voice -> simulation -> captions -> sfx -> final mp4 -> QC.

Steps are cached by content hash, so a revision only regenerates what changed (edit one line of
narration and the voice + visuals re-time; edit only sim.py and the voice is reused).
Publishing is a separate workflow (see youtube_publisher.py) and is never triggered from here.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
import traceback
from pathlib import Path

from . import caption_engine, quality_control, simulation_engine, video_editor
from .configuration import settings
from .database import DB
from .storyboard_engine import Storyboard, load
from .voice_engine import narrate as voice

log = logging.getLogger("factory.production")

PRE_APPROVAL = ("SCRIPTED", "STORYBOARDED", "RENDERED", "QUALITY_CHECKED", "QC_FAILED",
                "REVISION_REQUESTED", "FAILED", "PENDING_APPROVAL")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _key(*parts) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:16]


def _cached(out: Path, name: str, key: str) -> bool:
    k = out / f".{name}.key"
    return k.exists() and k.read_text() == key and (out / name).exists()


def _mark(out: Path, name: str, key: str):
    (out / f".{name}.key").write_text(key)


def render(sb: Storyboard, provider: str | None = None, previews: bool = False, force: bool = False) -> dict:
    """Build out/<slug>/final.mp4. Returns a dict with paths, timings and the sim's self-check report."""
    out = sb.out_dir
    provider = provider or settings.tts_provider
    timings = {}

    t0 = time.time()
    vkey = _key([(b.id, b.text, b.pause_after) for b in sb.beats], sb.voice, sb.speed, provider)
    if force or not _cached(out, "voice.wav", vkey) or not (out / "timeline.json").exists():
        log.info("[%s] voice (%s)", sb.slug, provider)
        tl = voice.narrate(sb, out / "voice.wav", provider)
        tl.save(out / "timeline.json")
        _mark(out, "voice.wav", vkey)
    else:
        log.info("[%s] voice: cached", sb.slug)
        tl = voice.Timeline.load(out / "timeline.json")
    timings["voice_s"] = round(time.time() - t0, 1)
    if tl.duration > settings.max_seconds:
        raise ValueError(f"narration is {tl.duration:.1f}s; limit is {settings.max_seconds:.0f}s. Trim the script.")

    t0 = time.time()
    Sim = sb.load_sim_class()
    sim_src = (sb.path / "sim.py").read_text(encoding="utf-8")
    base_src = (Path(simulation_engine.__file__).parent / "base.py").read_text(encoding="utf-8")
    skey = _key(sim_src, base_src, (out / "timeline.json").read_text(), [(b.id, b.on_screen) for b in sb.beats])
    scene = Sim(tl)
    if force or not _cached(out, "visual.mp4", skey):
        log.info("[%s] simulation render (%.1fs of video)", sb.slug, tl.duration)
        simulation_engine.render(scene, out / "visual.mp4", fps=settings.fps,
                                 preview_every=2.0 if previews else None, beats=sb.beats)
        _mark(out, "visual.mp4", skey)
    else:
        log.info("[%s] simulation: cached", sb.slug)
        scene.setup()
    timings["render_s"] = round(time.time() - t0, 1)

    t0 = time.time()
    caption_engine.write_ass(tl, out / "captions.ass")
    events = [(tl.start(b.id), b.sfx) for b in sb.beats if b.sfx]
    events += list(scene.sfx_events())
    video_editor.mix_sfx(out / "voice.wav", events, out / "mix.wav")
    video_editor.mux(out / "visual.mp4", out / "mix.wav", out / "captions.ass", sb.final_video)
    timings["mux_s"] = round(time.time() - t0, 1)

    sim_report = Sim.self_checks() if hasattr(Sim, "self_checks") else None
    return {"video": sb.final_video, "duration": tl.duration, "timings": timings, "sim_report": sim_report,
            "sfx": events}


def produce(slug: str, db: DB | None = None, provider: str | None = None, previews: bool = False,
            force: bool = False) -> dict:
    """Render + QC one storyboard and record every state change in the database."""
    db = db or DB()
    sb = load(slug)
    row = db.ensure_video(sb.slug, state="STORYBOARDED", topic=sb.topic, title=sb.title)
    if row["state"] not in PRE_APPROVAL:
        raise RuntimeError(f"{sb.slug} is {row['state']}; approved/published videos are never re-rendered. "
                           "Make a new slug for a new version.")
    if row["state"] != "STORYBOARDED":
        db.transition(sb.slug, "STORYBOARDED", note="re-render requested")
    try:
        res = render(sb, provider=provider, previews=previews, force=force)
        digest = sha256_file(res["video"])
        db.transition(sb.slug, "RENDERED", note=json.dumps(res["timings"]), video_path=str(res["video"]),
                      video_sha256=digest, duration_s=res["duration"],
                      render_count=(row["render_count"] or 0) + 1, last_error=None)
        passed, checks = quality_control.run_all(sb, res["sim_report"])
        db.add_qc_report(sb.slug, passed, json.dumps([c.__dict__ for c in checks]))
        log.info("[%s] QC %s\n%s", sb.slug, "passed" if passed else "FAILED", quality_control.summarize(checks))
        db.transition(sb.slug, "QUALITY_CHECKED" if passed else "QC_FAILED",
                      note="qc passed" if passed else "qc failed")
        res.update(qc_passed=passed, checks=checks, sha256=digest)
        return res
    except Exception as e:
        db.update(sb.slug, last_error=f"{type(e).__name__}: {e}")
        try:
            db.transition(sb.slug, "FAILED", note=traceback.format_exc()[-1500:])
        except Exception:  # noqa: BLE001 - already failing; keep the original error
            pass
        raise
