"""Story length: let the content decide how long a Short is.

There is no target duration. A Short is as long as its story needs: a single surprising event can be
done in about 20 s, a phenomenon with a hidden mechanism in about 30 s, a multi-step explanation with a
twist in about 40 s, and only a genuinely rich topic should run toward a minute. This module helps the
writer find that natural length *before* any voice or frames are made, and then checks the result for
the things that make a Short feel stretched.

1. Plan (before writing). The storyboard's `story:` block answers the planning questions:

       story:
         core_idea: "the one sentence the viewer must leave with"
         fascination: "what makes this surprising"
         steps: 2               # explanation steps the viewer genuinely needs (0-6)
         buildup: low           # low | medium | high: setup the payoff needs to land
         extras: [history]      # optional layers that earn their place (twist, history, scale, counter_example...)
         payoff: reveal         # beat id where the complete payoff lands
         cut: ["details deliberately left out, and why"]

   `estimate()` turns those answers into a natural length and a word budget. It is a starting point for
   the writer, never a target: no check fails because a script is longer or shorter than the estimate.

2. Check (after writing, and again with real TTS timings). `check()` looks for padding, not for a
   number of seconds: recap beats that repeat earlier lines, beats after the payoff that add nothing,
   generic hooks and endings, calls to action, slowed-down narration or long pauses that stretch the
   voice, and sped-up narration that crams a script instead of cutting it. With a narration timeline it
   uses the measured TTS durations, never an estimate.

3. Platforms. Duration rules that come from a platform (for example TikTok's Creator Rewards programme,
   which only pays for videos over a minute) are opt-in per storyboard (`platforms:`), off by default.
   They never change the script automatically; they only report that a video does not qualify.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

from .configuration import settings
from .qa.findings import Finding

# --------------------------------------------------------------------------------------------- config


def rules() -> dict:
    p = settings.root / "config" / "rules.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def _cfg() -> dict:
    return rules().get("length") or {}


# ------------------------------------------------------------------------------------------- estimate

BUILDUP_S = {"none": 0.0, "low": 0.0, "medium": 4.0, "high": 8.0}

# reference observations (Caesar's brief, 2026-11-19): how long the best Shorts in this space ran.
# Guidance only. Nothing in the pipeline aims for, pads toward or trims toward these numbers.
GUIDE = [
    (18, 25, "simple concept, surprising fact, quick reveal, single event"),
    (25, 35, "straightforward explainer, interesting phenomenon, short narrative"),
    (35, 45, "extra context, several steps or a stronger build-up"),
    (45, 60, "exceptionally compelling or complex topic that genuinely needs the time"),
]


@dataclass
class LengthPlan:
    seconds: float                    # natural length the story structure suggests
    low: float                        # plausible spread around it (a tight and a roomy telling)
    high: float
    words: tuple[int, int]            # word budget for that spread at the episode's narration speed
    guide: str                        # which reference band this falls in, in words
    parts: dict = field(default_factory=dict)

    def summary(self) -> str:
        p = ", ".join(f"{k} {v:.1f}s" for k, v in self.parts.items() if v)
        return (f"natural length about {self.seconds:.0f}s ({self.low:.0f}-{self.high:.0f}s; "
                f"{self.words[0]}-{self.words[1]} words): {self.guide}. Built from {p}")


def words_per_second(speed: float = 1.0) -> float:
    """Speaking rate of the house voice per unit of speed, sentence pauses included (calibrated on the
    real Kokoro timelines in tests/fixtures/regression: 3.2-3.5 words/s at speed 1.1)."""
    return float(_cfg().get("words_per_s_at_speed_1", 3.05)) * speed


def guide_band(seconds: float) -> str:
    for lo, hi, what in GUIDE:
        if seconds < hi:
            return f"{lo}-{hi}s range ({what})"
    return "over 60s: only if every beat is genuinely needed"


def estimate(story: dict | None, speed: float = 1.0) -> LengthPlan | None:
    """Natural length from the story's structure: hook + each explanation step + build-up + each extra
    layer + payoff + ending. Each part costs about what a clear spoken sentence or two takes."""
    if not story:
        return None
    c = _cfg().get("parts_s", {})
    steps = max(0, int(story.get("steps", 1)))
    extras = story.get("extras") or []
    parts = {
        "hook": float(c.get("hook", 3.0)),
        f"{steps} step(s)": steps * float(c.get("step", 7.0)),
        "build-up": BUILDUP_S.get(str(story.get("buildup", "low")), 0.0),
        f"{len(extras)} extra(s)": len(extras) * float(c.get("extra", 5.0)),
        "payoff": float(c.get("payoff", 5.0)),
        "ending": float(c.get("ending", 2.0)),
    }
    s = sum(parts.values())
    lo, hi = s * 0.85, s * 1.15
    wps = words_per_second(speed)
    return LengthPlan(round(s, 1), round(lo, 1), round(hi, 1),
                      (int(lo * wps * 0.85), int(hi * wps * 0.85)), guide_band(s), parts)


def predicted_duration(sb) -> float:
    """Narration length predicted from the words alone (before any TTS has run)."""
    from .voice_engine.narrate import LEAD_IN, tail_for
    delivery = rules().get("delivery", {})
    t = LEAD_IN
    for b in sb.beats:
        pace = delivery.get(b.pace or "calm", {})
        speed = sb.speed * (b.speed or pace.get("speed", 1.0))
        t += _words(b.text) / words_per_second(speed) + b.pause_after + pace.get("pause", 0.0)
    if sb.beats and sb.extra.get("end_hold_s") is not None:
        last = sb.beats[-1]
        t -= last.pause_after + delivery.get(last.pace or "calm", {}).get("pause", 0.0)
    return t + tail_for(sb)


# --------------------------------------------------------------------------------------------- checks

_STOP = set("""a an the and or but so of to in on at by for with from as is are was were be been being it its
this that these those there here then than you your we our they their he she his her i me my do does did
not no just very much more most can could would should will about into over under up down out off if when
what which who how why all any some each one two three four five six seven eight nine ten s t now""".split())

GENERIC_HOOKS = [r"^did you know\b", r"^have you ever (wondered|thought)", r"^in this video\b", r"^today,? (we|i)\b",
                 r"^let'?s (talk|look|take)\b", r"^welcome\b", r"^hey\b", r"^here'?s (a|an) (fun|interesting) fact"]
GENERIC_ENDINGS = [r"\bfollow (for|me)\b", r"\bsubscribe\b", r"\blike (and|this)\b", r"\bcomment (below|down)\b",
                   r"\blet me know\b", r"\bnow you know\b", r"\band that'?s (why|how)\b", r"\bin (summary|conclusion)\b",
                   r"\bto sum (it )?up\b", r"\bnext time you\b", r"\bpretty (cool|amazing|wild)\b", r"\bmind[- ]blowing\b",
                   r"\bstay tuned\b", r"\bpart two\b"]


def _words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text))


def _seq(text: str) -> list[str]:
    ws = [w.lower().strip("'") for w in re.findall(r"[A-Za-z0-9']+", text)]
    ws = [w[:-1] if len(w) > 4 and w.endswith("s") else w for w in ws]
    return [w for w in ws if w not in _STOP and len(w) > 2]


def _content(text: str) -> set[str]:
    return set(_seq(text))


def _pairs(text: str) -> set[tuple[str, str]]:
    s = _seq(text)
    return set(zip(s, s[1:]))


def recap_overlap(text: str, earlier: list[str]) -> float:
    """Share of this beat's content words that the viewer has already heard."""
    mine = _content(text)
    if len(mine) < 3:
        return 0.0
    seen = set().union(*(_content(e) for e in earlier)) if earlier else set()
    return len(mine & seen) / len(mine)


def recap_score(text: str, earlier: list[str], closing: bool = False) -> float:
    """How much a beat re-says instead of adding. Topic words naturally recur, so single words count
    less than repeated phrases (word pairs); a closing beat (last, or after the payoff) is where recaps
    usually hide, so it gets a small bump. Calibrated on our own scripts: the stretched 'So gravity
    pulls the chain... the pile pushes it up' outro scores 0.86; a normal development beat stays < 0.6."""
    uni = recap_overlap(text, earlier)
    mine = _pairs(text)
    seen = set().union(*(_pairs(e) for e in earlier)) if earlier else set()
    bi = len(mine & seen) / len(mine) if mine else 0.0
    return 0.7 * uni + bi + (0.1 if closing else 0.0)


def platform_flags(sb) -> dict:
    """Per-platform duration options. Defaults from config/rules.yaml `platforms:`, overridden per
    storyboard. Everything is off unless switched on."""
    base = {k: dict(v or {}) for k, v in (rules().get("platforms") or {}).items()}
    for k, v in ((sb.extra.get("platforms") or {}) if hasattr(sb, "extra") else {}).items():
        base.setdefault(k, {}).update(v or {})
    return base


def check(sb, tl=None) -> tuple[list[Finding], dict]:
    """Padding and stretching checks. Never a duration target. `tl`: narration Timeline if it exists."""
    c = _cfg()
    delivery = rules().get("delivery", {})
    sbf = [str(sb.path / "storyboard.yaml")]
    F: list[Finding] = []
    beats = sb.beats
    story = sb.extra.get("story") or {}
    plan = estimate(story, sb.speed)
    measured = tl is not None
    dur = tl.duration if measured else predicted_duration(sb)
    speech_end = tl.lines[-1].end if measured and tl.lines else None
    m = {"duration_s": round(dur, 2), "measured": measured, "words": sum(_words(b.text) for b in beats),
         "beats": len(beats)}
    if plan:
        m.update(estimate_s=plan.seconds, estimate_range=[plan.low, plan.high], word_budget=list(plan.words))
    m["guide"] = guide_band(dur)

    if not story:
        F.append(Finding("length.no_story_plan", "length", 3, None,
                         "no `story:` block: the script's length was not planned from its content",
                         repair="add story: core_idea, fascination, steps, buildup, extras, payoff (CLAUDE.md step 3)",
                         files=sbf, objective=False))
    ids = [b.id for b in beats]
    payoff = story.get("payoff")
    if payoff and payoff not in ids:
        F.append(Finding("length.bad_payoff", "length", 2, None, f"story.payoff '{payoff}' is not a beat id", files=sbf))
        payoff = None

    # 1. recap beats: most of what they say was already said
    hi_thr, lo_thr = float(c.get("recap_block", 0.72)), float(c.get("recap_warn", 0.6))
    closing_from = ids.index(payoff) + 1 if payoff else len(beats) - 1
    for k, b in enumerate(beats[1:], start=1):
        ov = recap_score(b.text, [x.text for x in beats[:k]], closing=k >= closing_from)
        if ov >= lo_thr:
            F.append(Finding(f"length.recap.{b.id}", "length", 2 if ov >= hi_thr else 3, None,
                             f"beat '{b.id}' mostly re-says earlier beats (recap score {ov:.2f}): \"{b.text[:70]}\"",
                             expected="every beat advances the story, raises a question or lands the payoff",
                             repair="cut it, or replace it with the detail it was standing in for",
                             t=tl.start(b.id) if measured else None, files=sbf, objective=False, confidence=0.7))

    # 2. after the payoff: only a short decisive ending, no tour of extras
    if payoff:
        after = beats[ids.index(payoff) + 1:]
        words_after = sum(_words(b.text) for b in after)
        m["words_after_payoff"] = words_after
        total = max(1, m["words"])          # a decisive ending scales with the story: ~15% of its words
        max_after = int(max(12, min(float(c.get("max_words_after_payoff", 30)),
                                    float(c.get("after_payoff_share", 0.15)) * total)))
        if words_after > max_after:
            F.append(Finding("length.after_payoff", "length", 2, None,
                             f"{len(after)} beat(s), {words_after} words after the payoff beat '{payoff}'",
                             expected=f"end within about {max_after} words of the payoff",
                             repair="move any genuinely new detail before the payoff, or cut it", files=sbf))

    # 3. generic hook and ending
    first = beats[0].text.strip().lower() if beats else ""
    if any(re.search(p, first) for p in GENERIC_HOOKS):
        F.append(Finding("length.generic_hook", "length", 2, None, f"generic opening: \"{beats[0].text[:60]}\"",
                         repair="open on the surprising thing itself", t=0.0, files=sbf))
    if beats:
        last = beats[-1]
        hits = [p for p in GENERIC_ENDINGS if re.search(p, last.text.lower())]
        if hits:
            F.append(Finding("length.generic_ending", "length", 2, None,
                             f"ending '{last.id}' uses a generic close or call to action: \"{last.text[:80]}\"",
                             repair="end on the payoff's last concrete image or fact", files=sbf))

    # 4. delivery that stretches or crams the voice
    pauses = 0.0
    for b in beats:
        pace = delivery.get(b.pace or "calm", {})
        rel = b.speed or pace.get("speed", 1.0)
        p = b.pause_after + pace.get("pause", 0.0)
        pauses += p
        if rel < float(c.get("min_rel_speed", 0.94)) and not b.reveal:
            F.append(Finding(f"length.slowed.{b.id}", "length", 2, None,
                             f"beat '{b.id}' is slowed to {rel:.2f}x without being a reveal",
                             repair="keep natural speed; slow down only for a reveal", files=sbf))
        if rel > float(c.get("max_rel_speed", 1.12)):
            F.append(Finding(f"length.rushed.{b.id}", "length", 2, None,
                             f"beat '{b.id}' is sped up to {rel:.2f}x", repair="cut words instead of speeding up the voice",
                             files=sbf))
        if p > float(c.get("max_pause_s", 0.8)) and not b.reveal:
            F.append(Finding(f"length.long_pause.{b.id}", "length", 3, None,
                             f"{p:.2f}s pause after '{b.id}' (not a reveal)", repair="shorten it", files=sbf))
    if not 0.9 <= sb.speed <= 1.25:
        F.append(Finding("length.episode_speed", "length", 2, None,
                         f"episode speed {sb.speed}: the house voice sounds natural at about 1.0-1.15",
                         repair="fix length in the script, not in the speaking rate", files=sbf))
    speech = (speech_end - tl.lines[0].start) if measured and tl.lines else max(1e-6, dur)
    share = pauses / max(1e-6, speech)
    m["pause_share"] = round(share, 3)
    if share > float(c.get("max_pause_share", 0.15)):
        F.append(Finding("length.pause_share", "length", 2, None,
                         f"script pauses are {share:.0%} of the narration", repair="tighten pause_after values", files=sbf))

    # 5. measured tail after the last word
    if measured and speech_end is not None:
        m["tail_s"] = round(tl.duration - speech_end, 2)

    # 6. structure vs length: soft, informative only
    if plan:
        ratio = dur / plan.seconds
        m["vs_estimate"] = round(ratio, 2)
        if ratio > float(c.get("long_vs_estimate", 1.4)):
            F.append(Finding("length.long_for_structure", "length", 3, None,
                             f"{dur:.1f}s for a story planned at about {plan.seconds:.0f}s ({plan.summary()})",
                             expected="either the plan undercounts real steps (update story:), or beats can be cut",
                             files=sbf, objective=False, confidence=0.6))
        elif ratio < float(c.get("short_vs_estimate", 0.6)):
            F.append(Finding("length.short_for_structure", "length", 3, None,
                             f"{dur:.1f}s for a story planned at about {plan.seconds:.0f}s: check the explanation is complete",
                             files=sbf, objective=False, confidence=0.6))

    # 7. technical ceiling (not a target)
    if dur > settings.max_seconds:
        F.append(Finding("length.over_ceiling", "length", 1, "BLOCKED_SPEC",
                         f"{dur:.1f}s is over the {settings.max_seconds:.0f}s ceiling for a Short", files=sbf))

    # 8. opt-in platform programmes (off by default)
    pf = platform_flags(sb)
    tk = pf.get("tiktok") or {}
    if tk.get("creator_rewards"):
        need = float(tk.get("creator_rewards_min_s", 60.0))
        m["tiktok_creator_rewards"] = dur > need
        if dur <= need:
            F.append(Finding("length.tiktok_creator_rewards", "length", 3, None,
                             f"{dur:.1f}s does not qualify for TikTok Creator Rewards (needs over {need:.0f}s)",
                             expected="opt-in only: extend with real content, or post without the programme. Never pad",
                             files=sbf, objective=True))
    return F, m


def report(sb, tl=None) -> str:
    """Human-readable plan + checks (python -m factory length <slug>)."""
    F, m = check(sb, tl)
    story = sb.extra.get("story") or {}
    plan = estimate(story, sb.speed)
    src = "measured from the narration" if m["measured"] else "predicted from the words (no narration yet)"
    lines = [f"# Story length: {sb.slug}", "",
             f"- Length: {m['duration_s']:.1f}s, {src}; {m['words']} words in {m['beats']} beats",
             f"- Reference band: {m['guide']}"]
    if plan:
        lines.append(f"- Plan: {plan.summary()}")
        if story.get("core_idea"):
            lines.append(f"- Core idea: {story['core_idea']}")
    if "tail_s" in m:
        lines.append(f"- Video after the last word: {m['tail_s']:.2f}s")
    lines.append(f"- Pauses: {m['pause_share']:.0%} of the narration")
    lines += ["", "## Findings", ""] + ([f"- [{f.severity}] `{f.id}` {f.message}" + (f" Fix: {f.repair}" if f.repair else "")
                                        for f in sorted(F, key=lambda f: f.severity)] or ["- none: no padding found"])
    return "\n".join(lines) + "\n"
