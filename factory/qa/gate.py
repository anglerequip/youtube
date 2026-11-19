"""Release gate: combine every layer's findings into a state, a rubric score and a verdict, and write
the QA report (out/<slug>/qa/report.json and report.md).

Rules (production brief):
  * any open severity 0-1 finding blocks, whatever the scores say;
  * a layer that did not run is reported as NOT performed, never as passed;
  * approve only with weighted score >= approve_at and no primary category below primary_min;
  * READY_FOR_RELEASE still means "ready for Caesar's approval in Telegram": nothing is published here.
"""
from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

from .findings import BLOCKED, RETURN_TO, SEVERITY_NAMES, STATES, LayerResult

PENALTY = {0: 4.0, 1: 2.5, 2: 1.0, 3: 0.3, 4: 0.0}


def category(fid: str) -> str:
    if fid.startswith(("science.card", "science.badge", "event.", "recognition.piece_count")) or \
            (fid.startswith("science.mismatch") and False):
        return "cross_modal_consistency"
    if fid.startswith(("science.", "spec.no_sources", "spec.no_claims")):
        return "scientific_accuracy"
    if fid.startswith(("geometry.", "render.", "temporal.")):
        return "geometry_and_render"
    if fid.startswith(("recognition.", "readability.")):
        return "visual_clarity"
    if fid.startswith(("pacing.slow_hook", "spec.slow_hook")):
        return "hook_and_retention"
    if fid.startswith(("pacing.", "spec.too", "spec.beat")):
        return "pacing_and_attention"
    if fid.startswith(("audio.", "sound.")):
        return "audio"
    if fid.startswith("review."):
        return "design_and_style"
    return "design_and_style"


def evaluate(layers: list[LayerResult], cfg: dict, review: dict | None, video_exists: bool) -> dict:
    rub = cfg["rubric"]
    findings = [f for L in layers for f in L.findings]
    blockers = [f for f in findings if f.is_blocker]
    # automated rubric: 5 minus penalties per category
    auto = {c: 5.0 for c in rub["weights"]}
    for f in findings:
        if f.status == "open" and not f.id.startswith("review."):
            c = category(f.id)
            if c == "cross_modal_consistency" and f.id.startswith("science.mismatch"):
                pass
            auto[c] = max(0.0, auto[c] - PENALTY.get(f.severity, 0))
    for f in findings:          # a narration/simulation mismatch hurts both categories
        if f.status == "open" and f.id.startswith("science.mismatch") and f.blocks == "BLOCKED_VISUAL_CONTRADICTION":
            auto["cross_modal_consistency"] = max(0.0, auto["cross_modal_consistency"] - PENALTY[f.severity])
    reviewer = (review or {}).get("scores") or {}
    scores = {c: round(min(auto[c], float(reviewer[c])) if c in reviewer else auto[c], 2) for c in auto}
    total = round(sum(scores[c] * w for c, w in rub["weights"].items()) / sum(rub["weights"].values()), 2)
    weak_primary = [c for c in rub["primary"] if scores[c] < rub["primary_min"]]
    not_run = [L.layer for L in layers if not L.ran]

    # state: the earliest stage that can repair the first blocker; otherwise how far the video got
    if blockers:
        order = {s: i for i, s in enumerate(STATES)}
        b = min(blockers, key=lambda f: (order.get(RETURN_TO.get(f.blocks or "", "IDEA"), 0), f.severity))
        state = b.blocks if b.blocks in BLOCKED else "BLOCKED_VISUAL_CONTRADICTION"
        return_to = RETURN_TO.get(state, "IDEA")
    elif not video_exists:
        state, return_to = "ASSETS_VALIDATED", None
    elif review is None or weak_primary or total < rub["approve_at"]:
        state, return_to = ("FINAL_QA_PASSED" if review is None else "FINAL_RENDERED"), None
    else:
        state, return_to = "READY_FOR_RELEASE", None
    verdict = "approve" if state == "READY_FOR_RELEASE" else "block" if blockers else "not ready"
    return {"state": state, "return_to": return_to, "verdict": verdict, "score": total, "scores": scores,
            "automated_scores": {c: round(v, 2) for c, v in auto.items()}, "reviewer_scores": reviewer,
            "weak_primary": weak_primary, "blockers": len(blockers), "layers_not_run": not_run}


def write_report(ctx, layers: list[LayerResult], verdict: dict, review: dict | None, video: Path | None) -> Path:
    d = ctx.out / "qa"
    d.mkdir(parents=True, exist_ok=True)
    rep = {"slug": ctx.sb.slug, "title": ctx.sb.title, "generated": _dt.datetime.now().isoformat(timespec="seconds"),
           "video": str(video) if video else None, **verdict,
           "layers": [L.to_dict() for L in layers],
           "review": review}
    (d / "report.json").write_text(json.dumps(rep, indent=2, default=str))
    md = [f"# QA report: {ctx.sb.title}", "",
          f"**Verdict: {verdict['verdict'].upper()}**, state `{verdict['state']}`"
          + (f", returns to `{verdict['return_to']}`" if verdict["return_to"] else ""),
          f"Score {verdict['score']:.2f} / 5 (approve at {ctx_cfg(ctx)['rubric']['approve_at']}), "
          f"{verdict['blockers']} blocking finding(s).", ""]
    if verdict["state"] == "READY_FOR_RELEASE":
        md += ["Ready for Caesar's review in Telegram. Nothing is published without that approval.", ""]
    md += ["| category | automated | reviewer | final |", "|---|---|---|---|"]
    for c, v in verdict["scores"].items():
        md.append(f"| {c} | {verdict['automated_scores'][c]:.1f} | {verdict['reviewer_scores'].get(c, '-')} | {v:.1f} |")
    md += ["", "## Layers", ""]
    for L in layers:
        status = "ran" if L.ran else "**NOT performed**"
        nb = sum(1 for f in L.findings if f.is_blocker)
        md.append(f"- **{L.layer}**: {status}; {len(L.findings)} finding(s), {nb} blocking"
                  + (f". {L.note}" if L.note else "") + (f" Metrics: {json.dumps(L.metrics, default=str)}" if L.metrics else ""))
    fs = sorted((f for L in layers for f in L.findings), key=lambda f: (f.severity, f.t or 0))
    md += ["", "## Findings (most severe first)", ""]
    if not fs:
        md.append("None.")
    for f in fs:
        md.append(f"- [{f.severity} {SEVERITY_NAMES.get(f.severity)}] `{f.id}`"
                  + (f" at {f.t:.1f}s" if isinstance(f.t, (int, float)) else "") + f": {f.message}"
                  + (f" Repair: {f.repair}" if f.repair else "") + ("" if f.objective else " (subjective)"))
    if review:
        md += ["", "## Critical Designer review", "",
               f"Reviewer: {review.get('reviewer', '')}. Release: **{review.get('release')}**.", "",
               *[f"- Reviewer {k + 1} ({r['file']}): release {r['release']}, scores "
                 + ", ".join(f"{c} {float(v):.1f}" for c, v in r["scores"].items()) for k, r in
                 enumerate(review.get("reviewers", []))],
               *(["- Scores below are the average of the reviewers.", ""] if review.get("reviewers") else []),
               f"- Main strength: {review.get('main_strength', '')}",
               f"- Biggest scientific risk: {review.get('biggest_scientific_risk', '')}",
               f"- Biggest visual weakness: {review.get('biggest_visual_weakness', '')}",
               f"- Biggest technical risk: {review.get('biggest_technical_risk', '')}",
               f"- Biggest pacing problem: {review.get('biggest_pacing_problem', '')}",
               f"- Object recognition: {review.get('object_recognition_issue', '')}",
               f"- Highest-priority repair: {review.get('highest_priority_repair', '')}",
               f"- Expected improvement: {review.get('expected_improvement', '')}",
               f"- Weakest aspect: {review.get('weakest_aspect', '')}",
               f"- Blind vs intent: {review.get('blind_vs_intent', '')}",
               f"- Evidence: {review.get('evidence', '')}"]
    md += ["", "## Not verified automatically", "",
           "- Perceptual listening (pronunciation, naturalness of the voice, music taste): needs a human.",
           "- Engagement on the platform (retention, likes): only real viewers can tell; see the YouTube/TikTok analytics after release."]
    (d / "report.md").write_text("\n".join(md))
    return d / "report.json"


def ctx_cfg(ctx) -> dict:
    from .inspect3d import config
    return config()
