"""Layer 9: the CounterPhysical Critical Designer (independent review).

The generator never grades its own work. This module only:
  1. builds a review packet from the ACTUAL output (frames at phone size, a blind set of frames, the
     intent and scientific spec, the quality standard and the known failure classes), with none of the
     generator's own explanations or automated QA verdicts in it;
  2. reads back `critique.json`, written by an independent reviewer (a separate model context or a
     human), and checks that it reviews exactly this video (sha256) and follows the schema.

If no valid critique exists for the current video, the gate blocks with BLOCKED_REVIEW_UNAVAILABLE.
A review is never simulated, assumed or filled in by the generator.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from .findings import Finding

CATEGORIES = ["scientific_accuracy", "cross_modal_consistency", "visual_clarity", "geometry_and_render",
              "pacing_and_attention", "audio", "design_and_style", "hook_and_retention"]

SCHEMA = {
    "video_sha256": "sha256 of the reviewed MP4 (copy from packet.json)",
    "reviewer": "who reviewed: e.g. 'independent model context' or a person's role",
    "blind_impression": [{"frame": "blind_01.jpg", "what_object": "", "what_happens": "", "where_to_look": "",
                          "confusing": "", "artificial_or_unfinished": ""}],
    "blind_vs_intent": "where the blind reading differs from the intended scene",
    "main_strength": "", "biggest_scientific_risk": "", "biggest_visual_weakness": "", "biggest_technical_risk": "",
    "biggest_pacing_problem": "", "object_recognition_issue": "", "highest_priority_repair": "",
    "expected_improvement": "", "weakest_aspect": "",
    "top_problems": [{"problem": "", "t": 0.0, "severity": "0-4 (0 critical blocker ... 4 optional)",
                      "objective": True, "confidence": 0.0, "repair": ""}],
    "top_improvements": ["", "", ""],
    "scores": {c: "0-5" for c in CATEGORIES},
    "release": "approve | reject",
    "evidence": "what in the frames supports the verdict",
}

INSTRUCTIONS = """# CounterPhysical Critical Designer: review brief

You are a demanding senior creative director with expertise in science visualisation and technical
animation. You are not responsible for defending this work; you decide whether it meets the
CounterPhysical standard. Be sceptical. Inspect the actual frames. Do not accept a statement that
something was implemented unless you can see it. Do not accept a beautiful scene that explains the wrong
science, an accurate simulation nobody can understand, or a valid render with broken geometry. Cuts are
not proof of good pacing and effects are not proof of engagement. Do not invent problems and do not
inflate scores; generic praise ("looks good overall") is not a review.

## Step 1: blind first impression (before reading intent.md)
Open only the files `blind_*.jpg`. For each, write: what object is this, what is happening, where the
viewer is supposed to look, what is confusing, what looks artificial or unfinished.

## Step 2: compare with the intent
Now read `intent.md` (what the video is meant to show, its claims and expected events) and look at the
contact sheets (`sheet_*.jpg`, phone size, one frame every ~1.5 s with time stamps) and, if you can,
the video itself. Say where your blind reading differs from the intent.

## Step 3: the review (every item is required)
1. main strength  2. biggest scientific risk  3. biggest visual weakness  4. biggest technical risk
5. biggest pacing problem  6. most important object-recognition issue  7. highest-priority repair
8. expected improvement from it  9. release: approve or reject  10. evidence for the verdict.
Plus: top five problems (time, severity 0-4, objective or subjective, confidence, repair), top three
improvements, the single weakest aspect, and scores 0-5 per category (5 = broadcast quality,
4 = good with minor issues, 3 = noticeable problems, 2 = poor, 1 = broken, 0 = absent).

Questions to keep asking: what is the viewer supposed to understand, and is that what they actually
get? Is the main object recognisable at phone size? Are the graphics scientifically correct? Does any
scene look like a placeholder render? Are there stretches with nothing new? Would the opening make
somebody curious? Is the ending satisfying?

## Known failure classes (look for these specifically)
- Narration, numbers on screen and the simulation disagree (e.g. "three pieces" while four are shown).
- Thin connected objects that stop reading as connected (chain beads with no visible links).
- Holes in the world: black regions where sky or ground is missing.
- Flicker: z-fighting, shadow seams that cut off or crawl, single-frame blinking lights.
- Labels covering the thing they describe; key events off screen or too small on a phone.

## Output
Write `critique.json` in this folder, following `schema.json` exactly, with `video_sha256` copied
from `packet.json`. Nothing else is needed.
"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _grab(video: Path, t: float, out: Path, w: int = 360, h: int = 640):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                    "-vf", f"scale={w}:{h}:flags=area", str(out)], check=True)


def build_packet(ctx, video: Path) -> Path:
    """Write the review packet to out/<slug>/qa/review/ and return its folder."""
    from PIL import Image, ImageDraw
    d = ctx.out / "qa" / "review"
    d.mkdir(parents=True, exist_ok=True)
    for old in d.glob("*.jpg"):
        old.unlink()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)],
                               capture_output=True, text=True, check=True).stdout.strip())
    # contact sheets: a frame every 1.5 s at phone size, 4 x 3 per sheet, time-stamped
    times = [round(t * 1.5 + 0.4, 2) for t in range(int((dur - 0.5) / 1.5) + 1)]
    tmp = d / "_f.png"
    frames = []
    for t in times:
        _grab(video, t, tmp, 240, 427)
        frames.append((t, Image.open(tmp).convert("RGB")))
    per = 12
    for s in range(0, len(frames), per):
        sheet = Image.new("RGB", (4 * 244, 3 * 450), "#202020")
        dr = ImageDraw.Draw(sheet)
        for k, (t, im) in enumerate(frames[s:s + per]):
            x, y = (k % 4) * 244 + 2, (k // 4) * 450 + 2
            sheet.paste(im, (x, y))
            dr.text((x + 4, y + 430), f"{t:5.1f}s", fill="#ffffff")
        sheet.save(d / f"sheet_{s // per + 1:02d}.jpg", quality=88)
    # blind frames: six moments spread over the video, full phone size
    for k in range(6):
        _grab(video, round(dur * (0.05 + 0.17 * k), 2), d / f"blind_{k + 1:02d}.jpg")
    tmp.unlink(missing_ok=True)
    sb = ctx.sb
    claims = sb.extra.get("claims") or []
    ents = sb.extra.get("entities") or []
    lines = [f"# Intent: {sb.title}", "", f"Topic: {sb.extra.get('topic', '')}", "", "## Narration (what the viewer hears)"]
    lines += [f"- [{ln.start:5.1f}-{ln.end:5.1f}s] {ln.text}" for ln in (ctx.tl.lines if ctx.tl else [])] or \
             [f"- {b.text}" for b in sb.beats]
    lines += ["", "## Claims that must be true and visible"]
    lines += [f"- {c.get('id')}: {c.get('unit')} = {c.get('value', c.get('sim'))} ({c.get('scope')}), beat {c.get('beat') or c.get('card')}"
              for c in claims]
    lines += ["", "## Entities and their visual contracts"]
    lines += [f"- {e.get('id')} ({e.get('importance')}, risk category {e.get('category', '-')}): "
              f"{(e.get('visual_contract') or {}).get('must_read_as', '')}" for e in ents]
    evs = ctx.facts.get("events") or {}
    if evs:
        lines += ["", "## Expected physical events"]
        lines += [f"- {k} at {v['t']:.1f}s: {v.get('observe')} = {v.get('expect')}" for k, v in evs.items()]
    lines += ["", "## Honest caveats (already disclosed to viewers)"] + [f"- {c}" for c in sb.caveats]
    lines += ["", "## House style (summary)",
              "Stylised low-poly 3D miniature world, warm soft daylight, hard sun shadows, gentle haze, muted",
              "pastels; the only saturated colour is the red that signals the phenomenon. Captions white with a soft",
              "shadow at ~73% height; off-white label cards with red text, used sparingly near the top third."]
    (d / "intent.md").write_text("\n".join(lines))
    (d / "INSTRUCTIONS.md").write_text(INSTRUCTIONS)
    (d / "schema.json").write_text(json.dumps(SCHEMA, indent=2))
    (d / "packet.json").write_text(json.dumps({"slug": sb.slug, "video": str(video), "video_sha256": sha256(video),
                                               "duration_s": dur, "sheets": len(range(0, len(frames), per))}, indent=2))
    return d


def read(ctx, video: Path) -> tuple[list[Finding], dict | None]:
    """Findings and scores from an independent critique of exactly this video, or a blocker."""
    d = ctx.out / "qa" / "review"
    p = d / "critique.json"
    if not video.exists():
        return [], None
    if not p.exists():
        return [Finding("review.unavailable", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE",
                        "no independent Critical Designer review of this video",
                        repair=f"run the review on {d} then python -m factory qa-gate <slug>")], None
    try:
        c = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        return [Finding("review.invalid", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE", f"critique.json is not valid JSON: {e}")], None
    if c.get("video_sha256") != sha256(video):
        return [Finding("review.stale", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE",
                        "the critique reviews a different version of the video (sha256 mismatch)",
                        repair="review the current render")], None
    missing = [k for k in ("blind_impression", "main_strength", "biggest_visual_weakness", "highest_priority_repair",
                           "top_problems", "scores", "release", "evidence") if not c.get(k)]
    bad_scores = [k for k in CATEGORIES if not isinstance((c.get("scores") or {}).get(k), (int, float))]
    if missing or bad_scores:
        return [Finding("review.incomplete", "review", 1, "BLOCKED_REVIEW_UNAVAILABLE",
                        f"critique incomplete: missing {missing + bad_scores}")], None
    F = []
    for k, prob in enumerate(c["top_problems"]):
        try:
            sev = int(str(prob.get("severity", 3))[0])
        except ValueError:
            sev = 3
        F.append(Finding(f"review.problem.{k + 1}", "review", sev,
                         "BLOCKED_OBJECT_RECOGNITION" if sev <= 1 else None, prob.get("problem", ""),
                         t=prob.get("t"), repair=prob.get("repair", ""), confidence=float(prob.get("confidence", 0.5)),
                         objective=bool(prob.get("objective", False)),
                         evidence={"reviewer": c.get("reviewer", "")}))
    if str(c.get("release", "")).lower().startswith("rej"):
        F.append(Finding("review.rejected", "review", 1, "BLOCKED_OBJECT_RECOGNITION",
                         f"Critical Designer rejects this version: {c.get('highest_priority_repair', '')}",
                         objective=False, evidence={"evidence": c.get("evidence", "")}))
    return F, c
