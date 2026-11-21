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
    vkey = _key([(b.id, b.text, b.pause_after) for b in sb.beats], sb.voice, sb.speed, provider, "expressive-v1")
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
    if tl.duration + 0.8 < settings.min_seconds:
        raise ValueError(f"narration is {tl.duration:.1f}s; every video must be at least {settings.min_seconds:.0f}s. "
                         "Extend the script with real content (not filler).")

    t0 = time.time()
    if sb.renderer == "three":
        events, sim_report = _render_three(sb, tl, out, previews, force)
    else:
        events, sim_report = _render_matplotlib(sb, tl, out, previews, force)
    timings["render_s"] = round(time.time() - t0, 1)

    t0 = time.time()
    caption_engine.write_ass(tl, out / "captions.ass", style=sb.extra.get("caption_style"),
                             beats={b.id: b for b in sb.beats})
    events = [(tl.start(b.id), b.sfx) for b in sb.beats if b.sfx] + list(events)
    if sb.renderer == "three":      # designed SFX + music + mastering (factory/sound_design.py)
        from . import sound_design
        music_cfg = getattr(sb, "_music_cfg", None)
        stats = sound_design.build_mix(out / "voice.wav", events, out / "mix.wav",
                                       duration=tl.duration + 0.8, music=music_cfg,
                                       ambience=getattr(sb, "_ambience", None))
        (out / "audio_stats.json").write_text(json.dumps(stats))
        log.info("[%s] audio master: %s", sb.slug, stats)
    else:
        video_editor.mix_sfx(out / "voice.wav", events, out / "mix.wav")
    video_editor.mux(out / "visual.mp4", out / "mix.wav", out / "captions.ass", sb.final_video)
    timings["mux_s"] = round(time.time() - t0, 1)

    return {"video": sb.final_video, "duration": tl.duration, "timings": timings, "sim_report": sim_report,
            "sfx": events}


def _render_matplotlib(sb: Storyboard, tl, out: Path, previews: bool, force: bool):
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
    return list(scene.sfx_events()), (Sim.self_checks() if hasattr(Sim, "self_checks") else None)


RENDERER_DIR = Path(__file__).resolve().parent.parent / "renderer"


def _render_three(sb: Storyboard, tl, out: Path, previews: bool, force: bool):
    """3D diorama renderer (renderer/, three.js in headless Chromium). plan.py builds the per-frame plan."""
    import subprocess
    mod = sb.load_module("plan.py")
    plan = mod.build_plan(tl, fps=settings.fps)
    scene = sb.extra.get("scene") or plan["scene"]
    plan_json = json.dumps(plan, separators=(",", ":"))
    (out / "plan.json").write_text(plan_json)
    srcs = sorted(p for p in RENDERER_DIR.rglob("*") if p.suffix in (".js", ".mjs", ".html")
                  and "node_modules" not in p.parts)
    skey = _key(plan_json, [p.read_text(encoding="utf-8") for p in srcs])
    node = ["node", str(RENDERER_DIR / "render.mjs"), "--scene", scene, "--plan", str(out / "plan.json")]
    if previews:
        stills = ",".join(f"{t:.1f}" for t in [x * 2.5 for x in range(int(tl.duration / 2.5) + 1)])
        subprocess.run(node + ["--stills", stills, "--stills-dir", str(out / "previews")], check=True)
    # pre-render QA (factory/qa): spec, science, cross-modal events, geometry inspection, pacing. Takes
    # seconds to minutes; a blocker stops here, before the hours-long full render.
    from . import qa
    ctx = qa.spec.Context(sb=sb, out=out, tl=tl, plan=plan, module=mod)
    layers, _ = qa.pre_render(sb, ctx)
    sb._qa = (layers, ctx)
    verdict = qa.gate.evaluate(layers, qa.inspect3d.config(), None, False)
    if verdict["blockers"]:
        rep = qa.gate.write_report(ctx, layers, verdict, None, None)
        raise qa.QABlocked(verdict, rep)
    log.info("[%s] pre-render QA: no blockers (%s)", sb.slug, verdict["state"])
    if force or not _cached(out, "visual.mp4", skey):
        log.info("[%s] 3D render (%d frames)", sb.slug, plan["n_frames"])
        subprocess.run(node + ["--out", str(out / "visual.mp4")], check=True)
        _mark(out, "visual.mp4", skey)
    else:
        log.info("[%s] 3D render: cached", sb.slug)
    report = mod.self_checks() if hasattr(mod, "self_checks") else None
    sb._music_cfg = mod.music(plan) if hasattr(mod, "music") else None
    sb._ambience = sb.extra.get("ambience") or plan.get("ambience")      # sound_design.AMBIENCES
    return mod.sfx_events(plan), report

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
        # post-render QA + release gate (factory/qa): pixels, flicker, audio, independent review
        verdict = None
        if getattr(sb, "_qa", None):
            from . import qa
            layers, ctx = sb._qa
            verdict, rep, _ = qa.post_render(sb, sb.final_video, ctx, layers)
            log.info("[%s] release gate: %s (%s, score %.2f); report %s", sb.slug, verdict["verdict"],
                     verdict["state"], verdict["score"], rep.with_suffix(".md"))
        ok = passed and (verdict is None or verdict["state"] == "READY_FOR_RELEASE")
        note = "qc passed" if passed else "qc failed"
        if verdict is not None:
            note += f"; gate {verdict['state']} score {verdict['score']}"
        db.transition(sb.slug, "QUALITY_CHECKED" if ok else "QC_FAILED", note=note)
        res.update(qc_passed=ok, checks=checks, sha256=digest, gate=verdict)
        return res
    except Exception as e:
        db.update(sb.slug, last_error=f"{type(e).__name__}: {e}")
        try:
            db.transition(sb.slug, "FAILED", note=traceback.format_exc()[-1500:])
        except Exception:  # noqa: BLE001 - already failing; keep the original error
            pass
        raise
