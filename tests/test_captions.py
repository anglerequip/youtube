from factory.caption_engine import chunk, syllables, timed_chunks, write_ass
from factory.narration.pronounce import normalise
from factory.voice_engine.narrate import TimedLine, Timeline


def test_chunks_respect_punctuation_size_and_units():
    assert chunk("Drop it. Watch the bottom very closely") == ["Drop it.", "Watch the bottom", "very closely"]
    c = chunk("It moves at about 20 km/h backward")
    assert any("20 km/h" in x for x in c)                       # CP-1: number stays with unit
    assert all(len(x) <= 16 or " " not in x for x in c)          # CP-1: <= 16 chars unless one token


def test_not_stays_with_verb():
    assert any("not fall" in x for x in chunk("The bottom does not fall"))


def test_min_duration_merges_short_chunks():
    tl = Timeline([TimedLine("a", "Watch the bottom closely now.", 0.0, 1.0)], 2.0)
    ev = timed_chunks(tl)
    assert all(e - s >= 0.6 - 1e-6 for s, e, _ in ev[:-1])


def test_no_trailing_full_stop_and_no_overlap(tmp_path):
    tl = Timeline([TimedLine("a", "One two three four.", 0.5, 2.5), TimedLine("b", "Five six?", 2.6, 3.4)], 5.0)
    ev = timed_chunks(tl)
    assert ev[0][0] == 0.5 and ev[-1][2].endswith("?")
    assert not any(c.endswith(".") for _, _, c in ev)
    assert all(a[1] <= b[0] + 1e-9 for a, b in zip(ev, ev[1:]))
    p = tmp_path / "c.ass"
    write_ass(tl, p)
    assert "\\pos(540,1401)" in p.read_text() or "\\pos(540,1402)" in p.read_text()


def test_syllables():
    assert syllables("cat") == 1 and syllables("gravity") == 3


def test_captions_use_written_text_but_voice_gets_words():
    assert normalise("about 20 km/h") == "about twenty kilometres per hour"


def test_style_modules_duo_and_build(tmp_path):
    """DUO colours the stressed word by speaker; BUILD shows one ALL-CAPS word at a time."""
    from factory import caption_engine as ce
    from factory.storyboard_engine import Beat
    from factory.voice_engine.narrate import Timeline, TimedLine
    tl = Timeline([TimedLine("a", "Heavy ball lands first.", 0.2, 2.0), TimedLine("b", "Drop them.", 2.2, 3.0)], 3.2)
    beats = {"a": Beat.from_dict({"id": "a", "text": "Heavy ball lands *first*.", "speaker": "woman"}),
             "b": Beat.from_dict({"id": "b", "text": "*Drop* them.", "speaker": "man"})}
    p = tmp_path / "duo.ass"
    ce.write_ass(tl, p, style="duo", beats=beats)
    txt = p.read_text()
    assert r"\1c&H0047B5FF" in txt and "first" in txt          # amber for the woman
    assert r"\1c&H00FFCB8E" in txt and "Drop" in txt           # sky blue for the man
    p2 = tmp_path / "build.ass"
    ce.write_ass(tl, p2, style="build", beats=beats)
    dialogue = [ln for ln in p2.read_text().splitlines() if ln.startswith("Dialogue")]
    assert len(dialogue) == 6                                   # one word per caption
    assert all(ln.split(",,")[-1].split("}")[-1].isupper() for ln in dialogue)
