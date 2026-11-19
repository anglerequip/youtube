"""Sound team regression tests (Caesar, 2026-11-19: the chain fountain went "ding ding ding" every half
second). The round-1 chain cue list must be blocked; the current episodes must not be."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace as NS

import yaml

from factory.qa import sound, spec

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "regression"
CFG = yaml.safe_load((ROOT / "config" / "quality.yaml").read_text())


def _ctx(events, tmp):
    mod = NS(sfx_events=lambda plan: [tuple(e) for e in events])
    return NS(module=mod, plan={"n_frames": 2000, "fps": 30}, out=tmp)     # no voice.wav: cue checks only


def _blocking(F):
    return [f for f in F if f.severity <= 1]


def test_chain_v1_ding_is_blocked(tmp_path):
    old = json.loads((FIX / "chain_v1_sfx_events.json").read_text())["events"]
    F, m = sound.check(_ctx(old, tmp_path), CFG)
    ids = {f.id for f in _blocking(F)}
    assert "sound.repetition" in ids, [f.message for f in F]
    assert "sound.density" in ids
    assert m["max_identical_total"] >= 200


def test_chain_v2_varied_click_train_is_blocked(tmp_path):
    """Round 2 swapped the dings for 168 varied 'coil' clicks, ~3 per second: still a ticking clock.
    The old logic let it through as 'texture'; the Sound Reviewer caught it (2026-11-19)."""
    old = json.loads((FIX / "chain_v2_sfx_events.json").read_text())["events"]
    F, m = sound.check(_ctx(old, tmp_path), CFG)
    ids = {f.id for f in _blocking(F)}
    assert "sound.click_train.coil" in ids, [f.message for f in F]
    assert "sound.density" in ids


def test_four_evenly_spaced_ticks_are_flagged(tmp_path):
    """Spaghetti round 2: four rising ticks 0.55 s apart sounded like an app chime."""
    ev = [(5.06 + 0.55 * k, "tick", {"gain": 0.2, "pitch": 1 + 0.1 * k}) for k in range(4)]
    F, _ = sound.check(_ctx(ev, tmp_path), CFG)
    assert any(f.id == "sound.periodic.tick" for f in F), [f.message for f in F]


def _current(slug):
    from factory.storyboard_engine import load
    from factory.voice_engine import narrate as voice
    sb = load(slug)
    tl = voice.Timeline.load(FIX / f"{slug}.timeline.json")
    plan = sb.load_module("plan.py").build_plan(tl, fps=30)
    return sb.load_module("plan.py"), plan


def test_chain_now_passes_the_sound_logic(tmp_path):
    mod, plan = _current("chain-fountain")
    F, m = sound.check(NS(module=mod, plan=plan, out=tmp_path), CFG)
    assert not _blocking(F), [f.message for f in F]
    assert m.get("max_identical_total", 0) <= 4


def test_spaghetti_cracks_are_not_flagged(tmp_path):
    """Control: a quick burst of different cracks at a snap is meaning, not annoyance."""
    mod, plan = _current("spaghetti-two-pieces")
    F, _ = sound.check(NS(module=mod, plan=plan, out=tmp_path), CFG)
    assert not _blocking(F), [f.message for f in F]


def test_one_identical_bell_on_repeat_is_caught_even_if_quiet(tmp_path):
    ev = [(0.5 + 0.6 * k, "ding", {"gain": 0.05}) for k in range(12)]
    F, _ = sound.check(_ctx(ev, tmp_path), CFG)
    assert any(f.id == "sound.repetition" and f.severity <= 1 for f in F)


def test_sound_critique_required_and_bound_to_video(tmp_path):
    from factory.qa import critic
    vid = tmp_path / "final.mp4"; vid.write_bytes(b"x")
    ctx = NS(out=tmp_path)
    F, c = sound.read(ctx, vid)
    assert c is None and F[0].id == "review.audio_unavailable" and F[0].severity == 1
    d = tmp_path / "qa" / "review_audio"; d.mkdir(parents=True)
    good = {"video_sha256": critic.sha256(vid), "release": "approve", "annoyances": [],
            "scores": {k: "4" for k in sound.SOUND_CATEGORIES}}
    (d / "critique_audio.json").write_text(json.dumps(good))
    F, c = sound.read(ctx, vid)
    assert c is not None and c["scores"]["overall"] == 4.0 and not _blocking(F)
    (d / "critique_audio.json").write_text(json.dumps({**good, "video_sha256": "0" * 64}))
    F, c = sound.read(ctx, vid)
    assert c is None and F[0].id == "review.audio_stale"


def test_doubled_tink_is_flagged(tmp_path):
    """Spaghetti round 2: two tinks 60 ms apart sounded like a doubled trigger (Sound Reviewer)."""
    ev = [(29.47, "tink", {"gain": 0.3, "seed": 1}), (29.53, "tink", {"gain": 0.3, "seed": 2})]
    F, _ = sound.check(_ctx(ev, tmp_path), CFG)
    assert any(f.id == "sound.double_trigger.tink" for f in F), [f.message for f in F]


def test_two_picture_reviewers_are_averaged_and_one_rejection_does_not_block(tmp_path):
    """Caesar, 2026-11-19: two independent picture reviews, averaged, so one harsh or lenient reviewer
    can't swing the verdict."""
    from factory.qa import critic
    vid = tmp_path / "final.mp4"; vid.write_bytes(b"x")
    ctx = NS(out=tmp_path)
    d = tmp_path / "qa" / "review"; d.mkdir(parents=True)
    base = {"video_sha256": critic.sha256(vid), "blind_impression": "a", "main_strength": "b",
            "biggest_visual_weakness": "c", "highest_priority_repair": "d", "evidence": "e",
            "top_problems": [{"problem": "p", "severity": 3}]}
    (d / "critique.json").write_text(json.dumps({**base, "release": "approve",
                                                 "scores": {k: 4 for k in critic.CATEGORIES}}))
    F, c = critic.read(ctx, vid)
    assert c is None and any(f.id == "review.unavailable" and "critique_2.json" in f.message for f in F)
    (d / "critique_2.json").write_text(json.dumps({**base, "release": "reject",
                                                   "top_problems": [{"problem": "q", "severity": 1}],
                                                   "scores": {k: 3 for k in critic.CATEGORIES}}))
    F, c = critic.read(ctx, vid)
    assert c is not None and all(v == 3.5 for v in c["scores"].values()) and c["release"] == "split"
    assert not _blocking(F) and any(f.severity == 2 and "one of two" in f.message for f in F)
    (d / "critique.json").write_text(json.dumps({**base, "release": "reject",
                                                 "scores": {k: 2 for k in critic.CATEGORIES}}))
    F, c = critic.read(ctx, vid)
    assert _blocking(F) and any(f.id.startswith("review.rejected") for f in F)
    F, c = critic.read(ctx, vid, n=1)
    assert c["scores"][critic.CATEGORIES[0]] == 2


def test_round_cap_delivers_to_caesar_after_two_review_rounds(tmp_path):
    """Caesar, 2026-11-19: at most two review rounds per video; after that the video goes to Caesar with its
    score and the reviewers' notes, whatever it scored (the 4.0 bar stays as the reported score)."""
    from factory import qa
    from factory.qa import critic, gate
    from factory.qa.findings import LayerResult
    review = {"scores": {k: 3.0 for k in critic.CATEGORIES}}
    lay = [LayerResult("review", True, [], {})]
    assert gate.evaluate(lay, CFG, review, True, rounds=1, max_rounds=2)["verdict"] == "not ready"
    v = gate.evaluate(lay, CFG, review, True, rounds=2, max_rounds=2)
    assert v["verdict"] == "deliver" and v["round_cap_reached"] and v["score"] < 4.0
    assert gate.evaluate(lay, CFG, None, True, rounds=5, max_rounds=2)["verdict"] != "deliver"   # no review yet
    # rounds are counted per distinct reviewed video, seeded from the PC's qa_round* backups
    (tmp_path / "qa_round1").mkdir(); (tmp_path / "qa_round2").mkdir()
    vid = tmp_path / "final.mp4"; vid.write_bytes(b"a")
    ctx = NS(out=tmp_path)
    assert qa._review_round(ctx, vid) == 3 and qa._review_round(ctx, vid) == 3
    vid.write_bytes(b"b")
    assert qa._review_round(ctx, vid) == 4
