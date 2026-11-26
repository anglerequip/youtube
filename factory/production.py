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
    cd = voice.clip_dir(sb)
    clips = sorted((p.name, p.stat().st_size) for p in cd.iterdir()) if cd and cd.exists() else None
    vkey = _key([(b.id, b.text, b.pause_after) for b in sb.beats], sb.voice, sb.speed, provider, "expressive-v1", clips,
                *([sb.extra.get("voice_id")] if sb.extra.get("voice_id") else []),
                *([voice.tail_for(sb)] if sb.extra.get("end_hold_s") is not None else []))
    if force or not _cached(out, "voice.wav", vkey) or not (out / "timeline.json").exists():
        log.info("[%s] voice (%s)", sb.slug, provider)
        tl = voice.narrate(sb, out / "voice.wav", provider)
        tl.save(out / "timeline.json")
        _mark(out, "voice.wav", vkey)
    else:
        log.info("[%s] voice: cached", sb.slug)
        tl = voice.Timeline.load(out / "timeline.json")
    timings["voice_s"] = round(time.time() - t0, 1)
    # Length comes from the story (factory/story_length.py): no target, no padding, no trimming. Only a
    # technical ceiling and a broken-output floor are enforced here; padding checks are in the report.
    if tl.duration > settings.max_seconds:
        raise ValueError(f"narration is {tl.duration:.1f}s; the ceiling for a Short is {settings.max_seconds:.0f}s. "
                         "Cut beats that don't earn their place.")
    if tl.duration < settings.min_seconds:
        raise ValueError(f"narration is {tl.duration:.1f}s: shorter than any real story ({settings.min_seconds:.0f}s); "
                         "the voice step probably failed.")
    from . import story_length
    (out / "length.md").write_text(story_length.report(sb, tl), encoding="utf-8")
    log.info("[%s] length %.1fs from the narration (%s); see %s", sb.slug, tl.duration,
             story_length.guide_band(tl.duration), out / "length.md")

    t0 = time.time()
    if sb.renderer == "three":
        events, sim_report = _render_three(sb, tl, out, previews, force)
    elif sb.renderer == "blender":
        events, sim_report = _render_blender(sb, tl, out, previews, force)
    else:
        events, sim_report = _render_matplotlib(sb, tl, out, previews, force)
    timings["render_s"] = round(time.time() - t0, 1)

    t0 = time.time()
    from . import retention
    emph, mode = retention.caption_emphasis(sb)
    caption_engine.write_ass(tl, out / "captions.ass", emphasis=emph, mode=mode,
                             style=sb.extra.get("caption_style"), beats={b.id: b for b in sb.beats})
    events = [(tl.start(b.id), b.sfx) for b in sb.beats if b.sfx] + list(events)
    if sb.renderer in ("three", "blender"):      # designed SFX + music + mastering (factory/sound_design.py)
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


def _render_chunked(node: list, out: Path, n_frames: int, skey: str):
    """Render the frames in chunks that survive a restart: finished chunks (with their .meta.json) are kept
    and skipped next time, then joined without re-encoding. RENDER_CHUNK (frames, default 240) and
    RENDER_JOBS (parallel Chromium processes, default 1) tune it; RENDER_CHUNK=0 renders in one go."""
    import os
    import subprocess
    size = int(os.environ.get("RENDER_CHUNK", "240"))
    if size <= 0:
        subprocess.run(node + ["--out", str(out / "visual.mp4")], check=True)
        return
    d = out / "chunks" / skey[:12]
    d.mkdir(parents=True, exist_ok=True)
    todo = []
    parts = []
    for f0 in range(0, n_frames, size):
        f1 = min(n_frames, f0 + size)
        mp4 = d / f"c{f0:06d}_{f1:06d}.mp4"
        parts.append(mp4)
        if not (mp4.exists() and mp4.with_suffix(".meta.json").exists()):
            todo.append((f0, f1, mp4))
    jobs = max(1, int(os.environ.get("RENDER_JOBS", "1")))
    running = []
    while todo or running:
        while todo and len(running) < jobs:
            f0, f1, mp4 = todo.pop(0)
            tmp = mp4.with_name("tmp_" + mp4.name)
            log.info("  chunk %d-%d", f0, f1)
            running.append((subprocess.Popen(node + ["--out", str(tmp), "--from", str(f0), "--to", str(f1)]), tmp, mp4))
        for pr in list(running):
            if pr[0].poll() is not None:
                running.remove(pr)
                if pr[0].returncode != 0:
                    raise RuntimeError(f"chunk render failed: {pr[2].name}")
                pr[1].with_suffix(".meta.json").replace(pr[2].with_suffix(".meta.json"))
                pr[1].replace(pr[2])
        time.sleep(1)
    lst = d / "list.txt"
    lst.write_text("".join(f"file '{p.name}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
                    str(out / "visual.mp4")], check=True)
    meta = {}
    for p in parts:
        meta.update(json.loads(p.with_suffix(".meta.json").read_text()))
    (out / "visual.meta.json").write_text(json.dumps(meta))


CLIP_GARMENT_VERTS = 200      # garment poke-through below this many vertices per keyframe is a cuff or hem, not visible


def clipping_blockers(rows: list) -> list:
    """Rows of tools/blender/render_episode.py --check-clipping that must block a render: any prop crossing the
    character, garment poke-through of CLIP_GARMENT_VERTS or more, feet sunk into or floating above the floor."""
    out = []
    for r in rows:
        bad = []
        for a, b, k in r.get("hits", []):
            if b.startswith("clear of the hand"):
                continue                                   # advice (how far to lift), not a finding of its own
            if " through " in a:
                if isinstance(k, (int, float)) and k >= CLIP_GARMENT_VERTS:
                    bad.append(f"{a} ({k} verts)")
            else:
                bad.append(f"{a} x {b} ({k} tris)")
        if r.get("feet") and not str(r["feet"]).startswith("on deck"):
            bad.append(str(r["feet"]))
        if bad:
            out.append(f"shot {r['shot']} {r['at']} t={r['t']}: " + "; ".join(bad))
    return out


def _render_blender(sb: Storyboard, tl, out: Path, previews: bool, force: bool):
    """Character renderer (HOST style, docs/styles/HOST.md): Blender Eevee, run headless on Caesar's PC.
    plan.py builds the per-shot / per-frame plan; tools/blender/render_episode.py renders frames from it.
    BLENDER_EXE points at blender(.exe); RENDER_SAMPLES / RENDER_SCALE tune quality for previews."""
    import os
    import subprocess
    from . import retention
    mod = retention.load_plan_module(sb)
    plan = mod.build_plan(tl, fps=settings.fps)
    plan_json = json.dumps(plan, separators=(",", ":"))
    (out / "plan.json").write_text(plan_json)
    root = Path(__file__).resolve().parent.parent
    srcs = sorted((root / "tools" / "blender").glob("*.py"))
    skey = _key(plan_json, [p.read_text(encoding="utf-8") for p in srcs])
    exe = os.environ.get("BLENDER_EXE", "blender")
    script = root / "tools" / "blender" / "render_episode.py"
    base = [exe, "-b", "--python", str(script), "--", "--plan", str(out / "plan.json"), "--episode", str(sb.path)]
    if previews:
        stills = ",".join(f"{t:.1f}" for t in [x * 2.5 for x in range(int(tl.duration / 2.5) + 1)])
        subprocess.run(base + ["--stills", stills, "--out", str(out / "previews")], check=True)
    if force or not _cached(out, "visual.mp4", skey):
        # clipping gate (docs/styles/HOST_RENDER_RULES.md 2): the 2026-11-26 rough cut rendered with findings in
        # 54 of 54 keyframes because the check was optional. Now it runs first and blocks the long render.
        qa = out / "qa"
        subprocess.run(base + ["--check-clipping", "--out", str(qa)], check=True)
        blockers = clipping_blockers(json.loads((qa / "clipping.json").read_text()))
        if blockers and not sb.extra.get("allow_clipping"):
            raise ValueError(f"clipping gate: {len(blockers)} keyframes with interpenetration, first: {blockers[0]}. "
                             f"See {qa / 'clipping.md'}. Fix the staging or the layers; `allow_clipping: true` in the "
                             "storyboard overrides it for a test render only.")
        frames = out / "frames"
        frames.mkdir(parents=True, exist_ok=True)
        log.info("[%s] Blender render (%d frames)", sb.slug, plan["n_frames"])
        subprocess.run(base + ["--out", str(frames)], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(plan["fps"]), "-i", str(frames / "f%05d.png"),
                        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", str(out / "visual.mp4")], check=True)
        _mark(out, "visual.mp4", skey)
    else:
        log.info("[%s] Blender render: cached", sb.slug)
    report = mod.self_checks() if hasattr(mod, "self_checks") else None
    sb._music_cfg = mod.music(plan) if hasattr(mod, "music") else None
    sb._ambience = sb.extra.get("ambience") or plan.get("ambience")
    return mod.sfx_events(plan), report


def _render_three(sb: Storyboard, tl, out: Path, previews: bool, force: bool):
    """3D diorama renderer (renderer/, three.js in headless Chromium). plan.py builds the per-frame plan."""
    import subprocess
    from . import retention
    mod = retention.load_plan_module(sb)       # plan.py, plus the storyboard's retention block (HUD, cues)
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
        _render_chunked(node, out, plan["n_frames"], skey)
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
