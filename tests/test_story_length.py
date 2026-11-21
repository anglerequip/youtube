"""Content-driven length (factory/story_length.py): no duration target anywhere, padding is caught,
and four topics with different storytelling needs produce four cohesive videos of different lengths."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from factory import story_length as L
from factory.narration.pronounce import normalise
from factory.qa import spec
from factory.storyboard_engine import load
from factory.voice_engine.narrate import TimedLine, Timeline

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "length"
# (slug, natural length the story structure suggests): a single event, an explainer, a multi-step
# story with a simulation, and a genuinely complex topic
TOPICS = [("hammer-feather", 17), ("horizontal-drop", 28), ("monty-hall", 40), ("braess-paradox", 56)]


def _sb(slug):
    return load(FIX / slug)


def _copy(tmp_path, slug, edit):
    d = tmp_path / slug
    d.mkdir()
    data = yaml.safe_load((FIX / slug / "storyboard.yaml").read_text())
    edit(data)
    (d / "storyboard.yaml").write_text(yaml.safe_dump(data, sort_keys=False))
    return load(d)


def _tl(sb, seconds_per_beat=3.0, tail=1.0):
    t, lines = 0.35, []
    for b in sb.beats:
        lines.append(TimedLine(b.id, b.text, t, t + seconds_per_beat))
        t += seconds_per_beat + 0.25
    return Timeline(lines, lines[-1].end + tail)


# ------------------------------------------------------------------ the plan follows the content


def test_estimate_follows_story_structure_not_a_target():
    est = [L.estimate(_sb(s).extra["story"], 1.1).seconds for s, _ in TOPICS]
    assert est == sorted(est) and len(set(est)) == 4, est
    for (slug, want), got in zip(TOPICS, est):
        assert abs(got - want) <= 2, (slug, got)
    # nothing gravitates to one number: the four natural lengths span the whole guide
    assert est[0] < 25 and est[-1] > 45


def test_predicted_lengths_differ_and_match_their_plan():
    for slug, _ in TOPICS:
        sb = _sb(slug)
        plan = L.estimate(sb.extra["story"], sb.speed)
        d = L.predicted_duration(sb)
        assert plan.low * 0.8 <= d <= plan.high * 1.1, (slug, d, plan.summary())
    ds = [L.predicted_duration(_sb(s)) for s, _ in TOPICS]
    assert ds == sorted(ds) and ds[-1] - ds[0] > 25, ds


def test_good_scripts_have_no_padding_findings():
    for slug, _ in TOPICS:
        F, m = L.check(_sb(slug))
        assert not [f for f in F if f.severity <= 2], (slug, [(f.id, f.message) for f in F])
        assert m["duration_s"] < 60 or slug == "braess-paradox"


# ------------------------------------------------------------------------- padding is caught


def test_stretched_script_is_flagged(tmp_path):
    def stretch(d):
        d["beats"][2]["speed"] = 0.85                                 # slowed narration
        d["beats"][1]["pause_after"] = 1.4                            # dead pause
        d["beats"].append({"id": "recap", "text": "So without air, a hammer and a feather fall at the same rate, "
                                                  "because gravity pulls both of them down the same."})
        d["beats"].append({"id": "outro", "text": "Pretty cool, right? Follow for more physics."})
    sb = _copy(tmp_path, "hammer-feather", stretch)
    ids = {f.id for f in L.check(sb)[0]}
    assert {"length.recap.recap", "length.generic_ending", "length.slowed.apollo", "length.long_pause.why",
            "length.after_payoff"} <= ids, ids


def test_generic_hook_and_crammed_voice_are_flagged(tmp_path):
    def bad(d):
        d["beats"][0]["text"] = "Did you know a hammer and a feather can land together?"
        d["beats"][1]["speed"] = 1.3
    ids = {f.id for f in L.check(_copy(tmp_path, "hammer-feather", bad))[0]}
    assert {"length.generic_hook", "length.rushed.why"} <= ids


def test_recaps_in_our_own_stretched_scripts_are_found():
    """The pre-change episodes were stretched to pass the old 61 s rule; their summary outros are found."""
    for slug in ("chain-fountain", "other-lane-faster"):
        F, _ = L.check(load(slug))
        assert any(f.id == "length.recap.outro" and f.severity == 2 for f in F), slug
    F, _ = L.check(load("falling-slinky"))
    assert any(f.id == "length.generic_ending" for f in F)


# ------------------------------------------------------------------ no hidden 60-second target


def test_no_fixed_duration_target_anywhere():
    from factory.configuration import settings
    assert settings.min_seconds <= 10, "the floor is a broken-render guard, not a length target"
    rules = yaml.safe_load((ROOT / "config" / "rules.yaml").read_text())
    assert "length_s" not in rules["script"] and "beats" not in rules["script"]
    q = yaml.safe_load((ROOT / "config" / "quality.yaml").read_text())
    assert "min_duration_s" not in q["audio"]
    assert rules["platforms"]["tiktok"]["creator_rewards"] is False
    pat = re.compile(r"over 60 s|61-75|60-75|> ?60 ?s|min_duration_s|TikTok rule")
    for p in list((ROOT / "factory").rglob("*.py")) + [ROOT / "CLAUDE.md", ROOT / "docs" / "QA.md"]:
        assert not pat.search(p.read_text(encoding="utf-8")), p


def test_spec_layer_has_no_duration_rule():
    for slug, _ in TOPICS:
        sb = _sb(slug)
        ctx = spec.Context(sb=sb, out=Path("/nonexistent"), tl=_tl(sb, seconds_per_beat=1.2))
        assert not [f for f in spec.check(ctx) if "too_short" in f.id or "too_long" in f.id or "beat_count" in f.id]


def test_tiktok_creator_rewards_is_opt_in(tmp_path):
    sb = _sb("hammer-feather")
    assert not [f for f in L.check(sb)[0] if "tiktok" in f.id]
    on = _copy(tmp_path, "hammer-feather", lambda d: d.update(platforms={"tiktok": {"creator_rewards": True}}))
    F, m = L.check(on)
    f = [f for f in F if f.id == "length.tiktok_creator_rewards"]
    assert f and not f[0].is_blocker and m["tiktok_creator_rewards"] is False
    long_tl = _tl(on, seconds_per_beat=16.0)
    assert not [f for f in L.check(on, long_tl)[0] if "tiktok" in f.id]


def test_measured_timeline_beats_the_estimate():
    sb = _sb("monty-hall")
    tl = _tl(sb, seconds_per_beat=2.0)
    _, m = L.check(sb, tl)
    assert m["measured"] and abs(m["duration_s"] - tl.duration) < 1e-6
    assert m["tail_s"] == pytest.approx(1.0, abs=0.01)


# ------------------------------------------------------------ end to end: four cohesive videos


def _probe(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@pytest.mark.parametrize("slug", [s for s, _ in TOPICS])
def test_produce_each_length_end_to_end(tmp_path, slug):
    """voice -> visuals -> captions -> mix -> mux -> QC for each topic: the video is exactly as long as
    its narration planned (plus the declared end hold), picture and sound end together, captions follow
    the voice, and nothing is padded or cut."""
    env = dict(os.environ, CONTENT_DIR=str(FIX), OUT_DIR=str(tmp_path / "out"), DATA_DIR=str(tmp_path / "data"),
               TTS_PROVIDER="dummy", FPS="6")
    r = subprocess.run([sys.executable, "-m", "factory", "produce", slug], cwd=ROOT, env=env,
                       capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, r.stdout[-3000:] + r.stderr[-3000:]
    out = tmp_path / "out" / slug
    qc = {c["name"]: c for c in json.loads((out / "qc.json").read_text())}
    for name in ("duration_matches_plan", "narration_complete", "av_same_length", "captions_sync",
                 "captions_in_range", "ends_after_payoff"):
        assert qc[name]["ok"], (name, qc[name]["detail"])
    tl = json.loads((out / "timeline.json").read_text())
    info = _probe(out / "final.mp4")
    dur = float(info["format"]["duration"])
    last = tl["lines"][-1]["end"]
    assert dur - last == pytest.approx(1.0, abs=0.25)           # end_hold_s: 1.0, no padding
    # each beat lasts as long as its words take (dummy voice: 2.6 words/s), none is stretched to fill
    sb = load(FIX / slug)
    for b, ln in zip(sb.beats, tl["lines"]):
        words = len(normalise(b.text).split())            # what the voice actually says
        assert ln["end"] - ln["start"] == pytest.approx(max(0.6, words / (2.6 * sb.speed)), abs=0.1), b.id
    assert (out / "length.md").exists()
