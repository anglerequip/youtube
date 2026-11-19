"""Retention toolkit (factory/retention): time expressions, HUD compiler, cues, caption emphasis, the HUD QA
layer, and the guarantee that episodes without a `retention:` block render exactly as before."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import yaml

from factory import retention
from factory.retention import cues, hud, project, timing
from factory.voice_engine import narrate as voice

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "regression"
CFG = yaml.safe_load((ROOT / "config" / "retention.yaml").read_text())


def _tl():
    return voice.Timeline([voice.TimedLine("hook", "This chain jumps out of its jar.", 0.35, 3.0),
                           voice.TimedLine("double", "Double the drop, and the arch doubles too.", 3.3, 6.0),
                           voice.TimedLine("outro", "So the chain is pushed.", 6.3, 9.0)], 9.5)


def _plan(n=300, fps=30):
    h = [1.0 + min(1.0, max(0.0, (i / fps - 3.5) / 1.5)) for i in range(n)]
    pos = [[0.0, 1.0, 5.0]] * n
    look = [[0.0, 1.0, 0.0]] * n
    return {"fps": fps, "n_frames": n, "W": 1080, "H": 1920, "frames": {"h2": h},
            "facts": {"drop_2m": 2.0}, "cards": [],
            "shots": [{"type": "keys", "start": 0.0, "end": n / fps, "i0": 0, "pos": pos, "look": look,
                       "fov": 38, "fovs": [38.0] * n, "lighting": "key"}],
            "anchors": {"a": [[0.0, 1.0, 0.0]] * n, "b": [[0.0, 1.5, 0.0]] * n}}


# ---------------------------------------------------------------- time expressions
def test_time_expressions():
    tl = _tl()
    assert timing.resolve(2.5, tl) == 2.5
    assert timing.resolve("double", tl) == 3.3
    assert timing.resolve("double.end", tl) == 6.0
    assert timing.resolve("double+0.5", tl) == pytest.approx(3.8)
    assert timing.resolve("double.end-0.2", tl) == pytest.approx(5.8)
    assert timing.resolve("end", tl, duration=9.5) == 9.5
    assert timing.resolve("hud:x.settle+1", tl, {"hud:x.settle": 4.0}) == 5.0
    w = timing.resolve("double@doubles", tl)
    assert 3.3 < w < 6.0 and w > timing.resolve("double@arch", tl)     # word order is preserved
    with pytest.raises(timing.TimeError):
        timing.resolve("nobeat", tl)
    with pytest.raises(timing.TimeError):
        timing.resolve("double@banana", tl)
    assert timing.window("double", tl) == (3.3, 6.0)
    assert timing.window(["hook+1", "double"], tl) == (pytest.approx(1.35), 6.0)   # bare beat id ends at its end


# ---------------------------------------------------------------- HUD compiler
def test_counter_follows_the_simulation_and_settles():
    plan = _plan()
    h = hud.compile_hud([{"id": "drop", "type": "counter", "label": "drop", "value": {"frames": "h2"},
                          "format": "{v:.1f} m", "show": ["hook", "outro"], "ticks": {"max": 4}}], plan, _tl(), CFG)
    w = h["widgets"][0]
    assert w["texts"][0] == "1.0 m" and w["texts"][-1] == "2.0 m"
    assert 4.9 < h["events"]["hud:drop.settle"] < 5.1                  # ramp ends at 5.0 s
    assert max(w["pulse"]) == 1.0                                       # the number pulses when it changes
    ticks = hud.tick_events(h, CFG, 30)
    assert 0 < len(ticks) <= 4
    assert all(b[0] - a[0] >= 1 / CFG["ticks"]["max_rate_hz"] - 1e-6 for a, b in zip(ticks, ticks[1:]))
    assert ticks[-1][2]["pitch"] > ticks[0][2]["pitch"]                 # a rising number is heard rising


def test_meter_threshold_and_question_events():
    plan = _plan()
    plan["frames"]["a"] = [12.0 * max(0.0, 1 - max(0.0, i / 30 - 4.0)) for i in range(300)]
    h = hud.compile_hud([
        {"id": "q", "type": "question", "text": "Why?", "ask": "hook+0.5", "answer": "double+0.2", "answer_text": "the pile"},
        {"id": "m", "type": "meter", "label": "push", "value": {"frames": "a"}, "format": "{v:.0f} %",
         "min": 0, "max": 15, "threshold": {"value": 1}, "show": ["hud:q.answer", "outro.end"]},
    ], plan, _tl(), CFG)
    ev = h["events"]
    assert ev["hud:q.answer"] > ev["hud:q.appear"]
    assert ev["hud:m.appear"] == pytest.approx(ev["hud:q.answer"])     # windows can chain on HUD events
    assert 4.8 < ev["hud:m.cross"] < 5.0                                # 12 % falls through 1 % at ~4.92 s
    m = next(w for w in h["widgets"] if w["id"] == "m")
    assert m["fracs"][0] > m["fracs"][-1] and m["threshold"]["frac"] == pytest.approx(1 / 15)


def test_hud_errors_are_explicit():
    plan, tl = _plan(), _tl()
    with pytest.raises(hud.HudError):
        hud.compile_hud([{"id": "x", "type": "gauge", "show": "hook"}], plan, tl, CFG)
    with pytest.raises(hud.HudError):
        hud.compile_hud([{"id": "x", "type": "counter", "value": {"frames": "nope"}, "show": "hook"}], plan, tl, CFG)
    with pytest.raises(hud.HudError):
        hud.compile_hud([{"id": "x", "type": "callout", "anchor": "missing", "label": "hi", "show": "hook"}], plan, tl, CFG)


# ---------------------------------------------------------------- cues
def test_cues_place_sounds_music_and_punch_ins():
    plan, tl = _plan(), _tl()
    out = cues.compile_cues([
        {"at": "double@doubles", "punch_in": 0.1, "punch_s": 0.5},
        {"at": "outro", "riser": 1.5, "music": "swell", "reveal": True},
        {"at": "double", "music": "drop", "until": "outro"},
        {"at": "hook.end", "sfx": "lock", "gain": 0.3},
    ], plan, tl, {}, CFG, {"auto_accents": False})
    assert out["swells"] == [6.3] and out["reveals"] == [6.3]
    assert out["mutes"] == [[3.3, 6.3]]
    rise = next(e for e in out["events"] if e[1] == "rise")
    assert rise[0] == pytest.approx(4.8) and rise[2]["dur"] == 1.5     # the riser ends on the reveal
    fov = plan["shots"][0]["fovs"]
    t = timing.resolve("double@doubles", tl)
    assert fov[int(t * 30) - 1] == 38.0 and fov[-1] == pytest.approx(38 * 0.9)
    with pytest.raises(cues.CueError):
        cues.compile_cues([{"at": 99.0, "sfx": "lock"}], _plan(), tl, {}, CFG, {})


def test_auto_accents_are_off_by_default_and_explicit_accent_works():
    plan = _plan()
    plan["hud"] = hud.compile_hud([{"id": "c", "type": "counter", "value": {"frames": "h2"}, "show": "double"},
                                   {"id": "d", "type": "counter", "value": {"frames": "h2"}, "show": "outro", "accent": True}],
                                  plan, _tl(), CFG)
    out = cues.compile_cues([], plan, _tl(), plan["hud"]["events"], CFG, {"auto_accents": CFG["features"]["auto_accents"]})
    assert [e[0] for e in out["events"]] == [6.3]


# ---------------------------------------------------------------- projection (QA mirror of the renderer camera)
def test_projection_centre_and_up():
    cam = ([0.0, 1.0, 5.0], [0.0, 1.0, 0.0], 38)
    x, y, _ = project.to_screen([0.0, 1.0, 0.0], cam, 1080, 1920)
    assert (x, y) == (pytest.approx(0.5), pytest.approx(0.5))
    _, y_up, _ = project.to_screen([0.0, 1.5, 0.0], cam, 1080, 1920)
    assert y_up < 0.5                                                   # up in the world is up on screen
    assert project.to_screen([0.0, 1.0, 9.0], cam, 1080, 1920) is None # behind the camera


# ---------------------------------------------------------------- caption emphasis
def test_caption_emphasis_is_weight_only_and_off_by_default():
    from factory.caption_engine import _emphasise
    assert _emphasise("the arch doubles", {"doubles"}, "none") == "the arch doubles"
    assert _emphasise("the arch doubles", {"doubles"}, "weight") == r"the arch {\b1}doubles{\b0}"
    assert CFG["features"]["caption_emphasis"] == "none"


# ---------------------------------------------------------------- integration
def _load(slug):
    from factory.storyboard_engine import load
    return load(slug), voice.Timeline.load(FIX / "chain-fountain.timeline.json")


def test_episodes_without_retention_are_unchanged():
    sb, tl = _load("chain-fountain")
    assert retention.load_plan_module(sb).build_plan(tl, fps=30) == sb.load_module("plan.py").build_plan(tl, fps=30)


def _ctx(slug, edit=None):
    from factory.qa import spec
    sb, tl = _load(slug)
    if edit:
        sb.extra = copy.deepcopy(sb.extra)
        edit(sb.extra)
    mod = retention.load_plan_module(sb)
    plan = mod.build_plan(tl, fps=30)
    return spec.Context(sb=sb, out=ROOT / "out" / "_test", tl=tl, plan=plan, module=mod)


def test_demo_episode_passes_hud_sound_and_science_qa(tmp_path):
    from factory.qa import hud as qhud, science, sound
    ctx = _ctx("chain-fountain-hud")
    ctx.out = tmp_path
    qcfg = yaml.safe_load((ROOT / "config" / "quality.yaml").read_text())
    F, m = qhud.check(ctx, CFG)
    assert not [f for f in F if f.severity <= 2], [f.message for f in F]
    assert m["widgets"] == 6 and m["max_screen_widgets"] <= CFG["limits"]["max_widgets"]
    F, _ = sound.check(ctx, qcfg)
    assert not [f for f in F if f.severity <= 1], [f.message for f in F]
    F = science.check(ctx.sb, ctx.facts, ctx.cards, ctx.badges)
    assert not [f for f in F if f.severity <= 1], [f.message for f in F]
    # the drawn arch follows the model through the no-push experiment and comes back for the loop
    h1 = ctx.plan["frames"]["h1"]
    t_off = timing.word_time(ctx.tl, "catch", "no")
    assert h1[int((t_off + 2.0) * 30)] < 0.005 and h1[-1] > 0.1
    assert set(json.loads(json.dumps(ctx.plan["hud"]))) == {"widgets", "anchors", "events"}   # serialisable


def test_hud_qa_blocks_hand_set_numbers_and_wrong_values():
    from factory.qa import hud as qhud

    def hand_set(extra):
        extra["retention"]["hud"].append({"id": "fake", "type": "counter", "label": "speed", "value": {"keys": [[0, 9.0]]},
                                          "format": "{v:.0f} m/s", "show": ["links", "links.end"]})

    F, _ = qhud.check(_ctx("chain-fountain-hud", hand_set), CFG)
    assert "hud.unbacked_number.fake" in {f.id for f in F if f.severity <= 1}

    def wrong(extra):
        w = next(w for w in extra["retention"]["hud"] if w["id"] == "arch")
        w["value"] = {"frames": "h1", "scale": 120}                    # draws 20 % too high
    F, _ = qhud.check(_ctx("chain-fountain-hud", wrong), CFG)
    assert any(f.id.startswith("hud.claim_mismatch.arch") and f.severity == 0 for f in F), [f.id for f in F]


def test_hud_qa_flags_clutter_and_unsafe_layout():
    from factory.qa import hud as qhud

    def clutter(extra):
        for k, slot in enumerate(["top_left", "top_right", "mid_left"]):
            extra["retention"]["hud"].append({"id": f"c{k}", "type": "counter", "label": "drop", "value": {"frames": "h2"},
                                              "format": "{v:.1f} m", "slot": slot, "show": ["links", "push"]})
        extra["retention"]["hud"].append({"id": "edge", "type": "counter", "label": "drop", "value": {"frames": "h2"},
                                          "format": "{v:.1f} m", "at": [0.93, 0.5], "show": ["rope", "rope.end"]})
    F, _ = qhud.check(_ctx("chain-fountain-hud", clutter), CFG)
    ids = {f.id for f in F}
    assert "hud.clutter" in ids and "hud.unsafe.edge" in ids


def test_pacing_counts_hud_events():
    from factory.qa import pacing
    ctx = _ctx("chain-fountain-hud")
    names = {n for _, n in pacing.attention_events(ctx.plan, ctx.module)}
    assert {"hud:why.answer", "hud:push.cross", "hud:drop.settle"} <= names


def test_new_sounds_render():
    from factory import sound_design as sd
    for name, p in [("blip", {"pitch": 1.2, "seed": 3}), ("lock", {}), ("rise", {"dur": 0.8})]:
        y = sd.render_cue(name, p, 1.0)
        assert 0.01 < len(y) / sd.SR < 2.0 and abs(y).max() <= 1.0
    assert len(sd.render_cue("rise", {"dur": 0.8}, 0)) == int(0.8 * sd.SR)
