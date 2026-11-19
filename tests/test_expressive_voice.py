from factory.voice_engine.elevenlabs import to_elevenlabs_text
from factory.voice_engine.expressive import _segments, _stress, clean, sentences


def test_clean_removes_emphasis_markers():
    assert clean("the arch *doubles* too") == "the arch doubles too"


def test_sentences_split_keeps_ellipsis_inside():
    assert sentences("So what pushes it up? Not the chain... The *pile* itself.") == [
        "So what pushes it up?", "Not the chain… The *pile* itself."]


def test_segments_mark_emphasis_and_pauses():
    assert _segments("Here… *four* of them!") == [("Here", False), ("…", False), ("four", True), (" of them!", False)]


def test_stress_adds_primary_stress_and_length():
    assert _stress("dˈʌbəlz") == "dˈʌːbəlz"
    assert "ˈ" in _stress("ðə")


def test_elevenlabs_caps_for_emphasis():
    assert to_elevenlabs_text("the *pile* itself") == "the PILE itself"
