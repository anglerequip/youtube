"""Self-checking production: QA layers and the release gate (see docs/QA.md).

    pre_render(sb)          spec, science, events, temporal tracks, 3D inspection, pacing, sound (cue sheet + stems)
                            (seconds; runs before the hours-long full render and blocks it on a blocker)
    post_render(sb, video)  pixels, flicker, audio, Critical Designer and Sound Reviewer packets/critiques, gate + report
    run(sb)                 both, on an existing render

Layers that cannot run are reported as NOT performed. Nothing here publishes anything.
"""
from __future__ import annotations

import logging
from pathlib import Path

from . import audio, critic, frames, gate, hud, inspect3d, pacing, science, sound, spec
from .findings import LayerResult

log = logging.getLogger("factory.qa")


class QABlocked(RuntimeError):
    def __init__(self, verdict: dict, report: Path):
        super().__init__(f"QA blocked: state {verdict['state']}, {verdict['blockers']} blocker(s); see {report.with_suffix('.md')}")
        self.verdict, self.report = verdict, report


def _layer(name, fn):
    try:
        out = fn()
        F, m = out if isinstance(out, tuple) else (out, {})
        return LayerResult(name, True, F, m or {})
    except Exception as e:      # a layer that crashes did not run; never treat that as a pass
        log.exception("QA layer %s failed to run", name)
        return LayerResult(name, False, [], {}, note=f"crashed: {type(e).__name__}: {e}")


def pre_render(sb, ctx=None, inspect: bool = True) -> tuple[list[LayerResult], spec.Context]:
    ctx = ctx or spec.load(sb)
    cfg = inspect3d.config()
    L = [_layer("spec", lambda: spec.check(ctx)),
         _layer("science", lambda: science.check(sb, ctx.facts, ctx.cards, ctx.badges)),
         _layer("events", lambda: spec.check_events(ctx) + spec.check_tracks(ctx)),
         _layer("pacing", lambda: pacing.check(ctx, cfg)),
         _layer("sound", lambda: sound.check(ctx, cfg))]
    if ctx.plan is not None and ctx.plan.get("hud"):            # retention toolkit (factory/retention)
        from ..retention import config as rcfg
        L.append(_layer("hud", lambda: hud.check(ctx, rcfg())))
    if inspect and ctx.plan is not None:
        L.append(_layer("geometry", lambda: inspect3d.check(ctx)))
    elif inspect:
        L.append(LayerResult("geometry", False, note="no 3D plan (matplotlib episode or no timeline)"))
    return L, ctx


def post_render(sb, video: Path, ctx, layers: list[LayerResult] | None = None, review: bool = True):
    cfg = inspect3d.config()
    layers = list(layers or [])
    caption_band = [(0.64, 0.82)]
    cuts = [s["start"] for s in (ctx.plan or {}).get("shots", [])]
    evs = []
    if ctx.module is not None and hasattr(ctx.module, "sfx_events") and ctx.plan:
        evs = [float(e[0]) for e in ctx.module.sfx_events(ctx.plan)]
    evs += list(((ctx.plan or {}).get("timing") or {}).get("reveals", []))
    if video.exists():
        layers.append(_layer("pixels", lambda: frames.check_pixels(video, cfg, exclude_bands=caption_band)))
        layers.append(_layer("flicker", lambda: frames.check_flicker(video, cfg, cuts, evs, region=(0.0, 0.64))))
    else:
        layers += [LayerResult("pixels", False, note="no video"), LayerResult("flicker", False, note="no video")]
    layers.append(_layer("audio", lambda: audio.check(ctx, cfg, video)))
    crit = None
    if review and video.exists():
        critic.build_packet(ctx, video)
        F, crit = critic.read(ctx, video)
        layers.append(LayerResult("review", crit is not None, F, {},
                                  note="independent Critical Designer review" if crit else
                                  "NOT performed yet: packet ready in out/<slug>/qa/review/"))
    snd = None
    if review and video.exists():
        sound.build_packet(ctx, video, cfg)
        F, snd = sound.read(ctx, video)
        layers.append(LayerResult("sound_review", snd is not None, F, {},
                                  note="independent Sound Reviewer" if snd else
                                  "NOT performed yet: packet ready in out/<slug>/qa/review_audio/"))
    merged = crit
    if crit is not None and snd is not None:     # sound is the Sound Reviewer's call: the picture reviewer's
        # audio score is provisional (it only sees levels), so the specialist's overall score replaces it
        merged = {**crit, "scores": {**crit["scores"], "audio": float(snd["scores"]["overall"])}}
    verdict = gate.evaluate(layers, cfg, merged, video.exists())
    rep = gate.write_report(ctx, layers, verdict, merged, video)
    return verdict, rep, layers


def run(sb, video: Path | None = None, inspect: bool = True):
    layers, ctx = pre_render(sb, inspect=inspect)
    video = video or sb.final_video
    return post_render(sb, Path(video), ctx, layers)
