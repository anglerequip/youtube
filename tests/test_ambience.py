import numpy as np
import pytest

from factory import sound_design as sd


@pytest.mark.parametrize("kind", sd.AMBIENCES)
def test_ambience_is_quiet_stereo_and_deterministic(kind):
    a = sd.ambience_bed(kind, 4.0)
    b = sd.ambience_bed(kind, 4.0)
    assert a.shape == (4 * sd.SR, 2)
    assert np.array_equal(a, b)
    rms_db = 20 * np.log10(np.sqrt(np.mean(a * a)))
    assert -37.5 < rms_db < -34.5            # a bed, never competing with the voice
    assert not np.allclose(a[:, 0], a[:, 1])  # decorrelated left/right


def test_unknown_ambience_is_rejected(tmp_path):
    import soundfile as sf
    v = tmp_path / "v.wav"
    sf.write(v, np.zeros(sd.SR, dtype=np.float32), sd.SR)
    with pytest.raises(ValueError):
        sd.stems(v, [], 1.0, False, ambience="jungle")


def test_ambience_dips_under_the_voice(tmp_path):
    import soundfile as sf
    v = tmp_path / "v.wav"
    y = np.zeros(4 * sd.SR); y[sd.SR:2 * sd.SR] = 0.3 * np.sin(np.arange(sd.SR) * 2 * np.pi * 220 / sd.SR)
    sf.write(v, y.astype(np.float32), sd.SR)
    st = sd.stems(v, [], 4.0, False, ambience="lake")
    assert "amb" in st and st["amb"].shape == (4 * sd.SR, 2)
