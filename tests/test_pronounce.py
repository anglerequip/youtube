from factory.narration.pronounce import normalise


def test_midair_is_two_words():
    for text in ("The bottom just hangs there, in midair.", "It hangs in mid-air."):
        out = normalise(text)
        assert "mid air" in out and "midair" not in out.lower().replace(" ", "x"), out


def test_numbers_and_units_still_spoken():
    assert "kilometres" in normalise("about 5 km/s") or "kilometers" in normalise("about 5 km/s")
