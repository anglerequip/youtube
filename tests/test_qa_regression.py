"""Regression tests built from the three videos Caesar rejected on 2026-11-19 (production brief Part XXIX).

For each defect: the old version must FAIL the relevant QA layer and the fixed version must PASS it.
  A  other lane:  sidewalk / shadow seams (tree shadows cut by the shadow-map edge); brake lights that
                  blink for single frames (found by the new flicker layer, root cause in the plan)
  B  spaghetti:   narration said three pieces, the simulation showed four (tests/test_qa_science.py);
                  label cards covering the pieces; a separated fracture is NOT a geometry defect
                  (false-positive control)
  C  chain:       black triangle where the sky dome was clipped; beads with no links (loose balls)

Old scenes live in renderer/scenes/regression/ (exact copies from commit 3f10b09). Tests that need
the headless renderer are skipped when node/Chromium are not available.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import yaml

from factory.qa import frames, inspect3d, spec

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "regression"
CFG = yaml.safe_load((ROOT / "config" / "quality.yaml").read_text())


def _has_renderer() -> bool:
    if not shutil.which("node"):
        return False
    r = subprocess.run(["node", "-e", "require('playwright')"], cwd=ROOT / "renderer", capture_output=True)
    return r.returncode == 0


renderer = pytest.mark.skipif(not _has_renderer(), reason="needs node + playwright (headless Chromium)")


def _plan(slug: str) -> dict:
    """Build the episode's current plan from the fixture timeline (no voice synthesis needed)."""
    from factory.storyboard_engine import load
    from factory.voice_engine import narrate as voice
    sb = load(slug)
    tl = voice.Timeline.load(FIX / f"{slug}.timeline.json")
    return sb, sb.load_module("plan.py").build_plan(tl, fps=30)


def _inspect(scene: str, plan: dict, times, tmp: Path) -> list:
    pp = tmp / "plan.json"
    pp.write_text(json.dumps(plan))
    rep = inspect3d.run(scene, pp, times, tmp / "inspect.json")
    return inspect3d.analyse(rep, plan, None, CFG)


def _blockers(F, prefix):
    return [f for f in F if f.id.startswith(prefix) and f.severity <= 1]


# ---------------------------------------------------------------- C: chain fountain
def test_chain_v1_black_triangle_in_pixels():
    """The shipped video: a solid black region around 57 s."""
    F, _ = frames.check_pixels(FIX / "chain_v1_55-59s.mp4", CFG, exclude_bands=[(0.64, 0.82)])
    assert [f for f in F if f.id == "render.black_region" and f.severity == 0]


@renderer
def test_chain_v1_black_triangle(tmp_path):
    sb, plan = _plan("chain-fountain")
    old = _inspect("regression/chain3d_v1", plan, [57.0, 58.0], tmp_path)
    new = _inspect("chain3d", plan, [57.0, 58.0], tmp_path)
    assert _blockers(old, "geometry.world_missing"), "old scene must show the hole (clipped sky dome)"
    assert not _blockers(new, "geometry.world_missing")


@renderer
def test_chain_v1_loose_beads(tmp_path):
    sb, plan = _plan("chain-fountain")
    t = [3.0, 10.0, 30.0]
    old = _inspect("regression/chain3d_v1", plan, t, tmp_path)
    new = _inspect("chain3d", plan, t, tmp_path)
    assert _blockers(old, "recognition.chain_loose_beads")
    assert not _blockers(new, "recognition.chain_loose_beads")


# ---------------------------------------------------------------- A: other lane
@renderer
def test_traffic_v1_shadow_seams(tmp_path):
    sb, plan = _plan("other-lane-faster")
    t = [55.0, 56.0, 57.0, 58.0, 59.0]
    old = _inspect("regression/traffic3d_v1", plan, t, tmp_path)
    new = _inspect("traffic3d", plan, t, tmp_path)
    assert _blockers(old, "render.shadow_cutoff"), "old scene: tree shadows cut by the shadow-map edge"
    assert not _blockers(new, "render.shadow_cutoff")


def test_traffic_brake_chatter():
    old = json.loads((FIX / "other_lane_v1_brake_tracks.json").read_text())
    assert spec.check_tracks(NS(plan=old, fps=30)), "old tracks blink for single frames"
    from importlib import util
    mspec = util.spec_from_file_location("olp", ROOT / "content" / "episodes" / "other-lane-faster" / "plan.py")
    m = util.module_from_spec(mspec); mspec.loader.exec_module(m)
    import numpy as np
    rng = np.random.default_rng(0)
    a = rng.normal(-0.7, 0.25, size=(400, 30))          # acceleration hovering at the threshold: worst case
    on = m._brakes(a)
    blips = ((on[1:-1] != on[:-2]) & (on[1:-1] != on[2:])).sum()
    assert blips == 0, "brake lights with hysteresis never blink for one frame"


def test_traffic_v1_flicker_in_pixels():
    F, m = frames.check_flicker(FIX / "other_lane_v1_43.5-46s.mp4", CFG, [], [], region=(0.0, 0.64))
    assert F and m["flicker_tiles"] >= 1


def test_flicker_false_positive_control():
    """A clean clip (accepted slinky video) shows no flicker and no black regions."""
    F, m = frames.check_flicker(FIX / "slinky_control_20-24s.mp4", CFG, [], [], region=(0.0, 0.64))
    P, _ = frames.check_pixels(FIX / "slinky_control_20-24s.mp4", CFG, exclude_bands=[(0.64, 0.82)])
    assert not F and not P


# ---------------------------------------------------------------- B: spaghetti
@renderer
def test_spaghetti_cards_never_cover_the_pieces(tmp_path):
    sb, plan = _plan("spaghetti-two-pieces")
    ev = plan["facts"]["events"]["snap_twisted"]["t"]
    times = [ev, ev + 0.3, ev + 0.6, ev + 1.0]
    new = _inspect("spaghetti3d", plan, times, tmp_path)
    old_plan = json.loads(json.dumps(plan))
    for c in old_plan["cards"]:
        if c["big"].endswith("pieces") and "twisted" in c["small"]:
            c["y"], c["start"] = 0.2, ev - 0.6 + 0.6       # as shipped: y 0.2, right at the break
    old = _inspect("spaghetti3d", old_plan, times, tmp_path)
    assert _blockers(old, "recognition.card_covers_hero")
    assert not _blockers(new, "recognition.card_covers_hero")


@renderer
def test_spaghetti_fracture_is_not_a_geometry_defect(tmp_path):
    """False-positive control: deliberate fracture (separate pieces, gaps, flying fragments) must not be
    reported as missing geometry, NaN, z-fighting or popping, and the piece counts must read."""
    sb, plan = _plan("spaghetti-two-pieces")
    evs = plan["facts"]["events"]
    times = sorted({round(e["t"] + d, 2) for e in evs.values() for d in (0.0, 0.3, 0.6)})
    F = _inspect("spaghetti3d", plan, times, tmp_path)
    bad = [f for f in F if f.severity <= 1]
    assert not bad, [f.message for f in bad]
