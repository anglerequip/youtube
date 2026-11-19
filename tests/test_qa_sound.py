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
