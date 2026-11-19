from factory.caption_engine import chunk_words, write_ass
from factory.voice_engine.narrate import TimedLine, Timeline


def test_chunks_respect_punctuation_and_size():
    assert chunk_words("Drop it. Watch the bottom very closely") == ["Drop it.", "Watch the bottom", "very closely"]


def test_ass_timing_covers_each_line(tmp_path):
    tl = Timeline([TimedLine("a", "one two three four", 0.5, 2.5), TimedLine("b", "five six", 3.0, 4.0)], 5.0)
    p = tmp_path / "c.ass"
    write_ass(tl, p)
    events = [l for l in p.read_text().splitlines() if l.startswith("Dialogue")]
    assert len(events) == 3
    assert events[0].split(",")[1] == "0:00:00.50"
    assert events[1].split(",")[2] == "0:00:02.50"
    assert events[2].split(",")[1] == "0:00:03.00"
    assert "{" not in events[0].split("}")[-1]  # text is plain after the override tag
