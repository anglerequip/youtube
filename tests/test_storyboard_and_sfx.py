import numpy as np
import pytest

from factory import storyboard_engine
from factory.video_editor import SFX_NAMES, sfx


def test_real_episode_loads():
    sb = storyboard_engine.load("falling-slinky")
    assert sb.title and sb.topic and len(sb.beats) >= 5
    assert sb.sources and sb.caveats


def test_duplicate_beat_ids_rejected(tmp_path):
    (tmp_path / "storyboard.yaml").write_text(
        "title: t\ntopic: x\nbeats:\n  - {id: a, text: hi}\n  - {id: a, text: again}\n")
    with pytest.raises(ValueError):
        storyboard_engine.load(tmp_path)


@pytest.mark.parametrize("name", SFX_NAMES)
def test_sfx_are_normalised(name):
    y = sfx(name)
    assert y.dtype == np.float32 and 0.9 < np.max(np.abs(y)) <= 1.0


def test_slinky_physics_self_checks():
    sb = storyboard_engine.load("falling-slinky")
    report = sb.load_sim_class().self_checks()
    assert report and all(ok for ok, _ in report.values()), report
