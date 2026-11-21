"""Layer 1 (specification) and the shared production context every QA layer reads.

The storyboard is the single source of truth: beats (narration), claims (numbers and their
evidence), entities (what must be visible and readable), and the plan's facts/events (what the
simulation actually did). This module loads all of them once, and checks that the specification
itself is complete before anything is rendered.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .findings import Finding

CATEGORIES = {   # semantic geometry-risk taxonomy (brief, Part VI section 10)
    "A": "faces and expressive anatomy: proportions and expression must read",
    "B": "thin connected objects (chains, springs, cables): connections must stay visible and continuous",
    "C": "mechanically recognisable objects (cars, jars, clamps, bars): silhouette and key parts must read",
    "D": "deformable and fracturing objects (sticks, fragments): counts, gaps and break shapes must read",
    "E": "large structural surfaces (roads, ground, sky): no holes, seams, z-fighting or shadow cut-offs",
    "F": "background environmental objects (trees, hills): must frame, never distract or glitch",
}


@dataclass
class Context:
    sb: object
    out: Path
    tl: object | None = None
    plan: dict | None = None
    module: object | None = None
    notes: list = field(default_factory=list)

    @property
    def facts(self) -> dict:
        return (self.plan or {}).get("facts") or {}

    @property
    def cards(self) -> list:
        return (self.plan or {}).get("cards") or []

    @property
    def badges(self) -> list:
        return sorted({b for b in ((self.plan or {}).get("frames") or {}).get("badge", []) if b})

    @property
    def fps(self) -> int:
        return int((self.plan or {}).get("fps", 30))


def load(sb, build_plan: bool = True) -> Context:
    """Load the storyboard's timeline and plan (built fresh from plan.py, never from a stale json)."""
    from ..configuration import settings
    from ..voice_engine import narrate as voice
    out = sb.out_dir
    ctx = Context(sb=sb, out=out)
    tlp = out / "timeline.json"
    if tlp.exists():
        ctx.tl = voice.Timeline.load(tlp)
    else:
        ctx.notes.append("no timeline yet (narration not generated): plan-level checks skipped")
    if build_plan and ctx.tl is not None and (sb.path / "plan.py").exists():
        from .. import retention
        ctx.module = retention.load_plan_module(sb)
        ctx.plan = ctx.module.build_plan(ctx.tl, fps=settings.fps)
    elif (out / "plan.json").exists() and ctx.tl is not None:
        ctx.plan = json.loads((out / "plan.json").read_text())
    return ctx


def check(ctx: Context) -> list[Finding]:
    """Is the specification complete enough to produce and verify a video?"""
    sb, F = ctx.sb, []
    sbf = [str(sb.path / "storyboard.yaml")]
    n = len(sb.beats)
    if n < 2:      # no beat-count target: a story takes the beats it needs (factory/story_length.py)
        F.append(Finding("spec.beat_count", "spec", 2, None, f"{n} beat(s): a hook and a payoff need at least two",
                         files=sbf))
    ents = sb.extra.get("entities") or []
    if not ents:
        F.append(Finding("spec.no_entities", "spec", 1, "BLOCKED_SPEC",
                         "no entities with visual contracts: nothing says what must be visible and readable",
                         repair="add entities: with type, category (A-F), importance and visual_contract", files=sbf))
    for e in ents:
        if e.get("category") and e["category"] not in CATEGORIES:
            F.append(Finding(f"spec.bad_category.{e.get('id')}", "spec", 2, None,
                             f"entity {e.get('id')} has unknown risk category {e['category']}", files=sbf))
        if e.get("importance") == "primary" and not (e.get("visual_contract") or {}).get("must_read_as"):
            F.append(Finding(f"spec.no_contract.{e.get('id')}", "spec", 1, "BLOCKED_SPEC",
                             f"primary entity {e.get('id')} has no visual contract (must_read_as)", files=sbf))
    hero = sb.extra.get("hero")
    if not hero or hero not in {e.get("id") for e in ents}:
        F.append(Finding("spec.no_hero", "spec", 2, None, "no hero entity named (the one thing the viewer must follow)",
                         files=sbf))
    if not (getattr(sb, "sources", None) or sb.extra.get("sources") or []):
        F.append(Finding("spec.no_sources", "spec", 1, "BLOCKED_MISSING_EVIDENCE", "storyboard lists no sources",
                         files=sbf))
    if ctx.tl is not None:
        # no duration target here: length is checked for padding in the length layer (story_length.py)
        hook = next((b for b in ctx.tl.lines if b.id == sb.beats[0].id), None)
        if hook is not None and hook.end - hook.start > 3.6:
            F.append(Finding("spec.slow_hook", "spec", 2, None,
                             f"hook beat lasts {hook.end - hook.start:.1f}s (target: surprising claim under 3.5 s)"))
    return F


def check_events(ctx: Context) -> list[Finding]:
    """Data-level cross-modal check: at each declared event, what the renderer will draw equals what
    the simulation produced (e.g. the number of spaghetti pieces on screen = simulated piece count)."""
    F = []
    events = ctx.facts.get("events") or {}
    if not events or ctx.module is None or not hasattr(ctx.module, "observe"):
        return F
    fps = ctx.fps
    for name, ev in events.items():
        i = int(round(ev["t"] * fps))
        i = max(0, min(i, ctx.plan["n_frames"] - 1))
        got = ctx.module.observe(ctx.plan, i, ev["observe"])
        exp, tol = ev["expect"], float(ev.get("tol", 0))
        bad = abs(got - exp) > (tol * abs(exp) if tol else 1e-9)
        if bad:
            F.append(Finding(f"event.mismatch.{name}", "events", 0, "BLOCKED_VISUAL_CONTRADICTION",
                             f"event {name} at {ev['t']:.2f}s: screen shows {ev['observe']}={got:g}, simulation says {exp:g}",
                             t=ev["t"], expected=f"{exp:g}", evidence={"observed": got},
                             repair="drive the drawn state from the simulation run, not from a hand-set value"))
    return F


def check_tracks(ctx: Context) -> list[Finding]:
    """Temporal data check: on/off tracks in the plan (brake lights, highlights) must not blink for a
    single frame. Each track is a list of '0'/'1' strings (one char per object per frame)."""
    F = []
    for key, v in ((ctx.plan or {}).get("frames") or {}).items():
        if not (isinstance(v, list) and v and isinstance(v[0], str) and set("".join(v[:50])) <= {"0", "1"}):
            continue
        blips, first = 0, None
        for k in range(1, len(v) - 1):
            a, b, c = v[k - 1], v[k], v[k + 1]
            for j in range(min(len(a), len(b), len(c))):
                if b[j] != a[j] and b[j] != c[j]:
                    blips += 1
                    first = first if first is not None else k / ctx.fps
        if blips > 5:
            F.append(Finding(f"temporal.blink.{key}", "events", 1, "BLOCKED_RENDER_ARTIFACT",
                             f"plan track '{key}' switches on/off for a single frame {blips} times (first at {first:.2f}s): "
                             "visible as flicker", t=first, evidence={"blips": blips},
                             repair="add hysteresis / a minimum on-time to the state",
                             regression_test="tests/test_qa_regression.py::test_traffic_brake_chatter"))
    return F
