from factory.autopilot.tagline import tagline


def test_topic_picks_the_line():
    assert tagline(["cat", "myth"], "Why Your Cat Sits Like a Loaf") == "animal science that breaks your intuition."
    assert tagline(["crystal"], "Crystals") == "chemistry that breaks your intuition."
    assert tagline(["gravity"], "Your Head Is Older") == "physics that breaks your intuition."
    assert tagline(["toast"], "Toast Lands Butter-Side Down") == "science that breaks your intuition."


def test_storyboard_override_wins():
    assert tagline(["cat"], "x", override="my own line.") == "my own line."
