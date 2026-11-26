from factory.autopilot.tagline import rebrand, sign_off, tagline


def test_topic_picks_the_line():
    assert tagline(["pike", "lure"], "Which colour for pike") == "the right lure and colour, picked on real data."
    assert tagline(["lake"], "Where fish hide") == "real depth maps and ranked spots."
    assert tagline(["fishing", "sound"], "Quiet on the boat") == "the science behind every cast."
    assert tagline(["toast"], "Toast Lands Butter-Side Down") == "fish smarter."


def test_storyboard_override_wins():
    assert tagline(["cat"], "x", override="my own line.") == "my own line."


def test_sign_off_names_the_site():
    assert sign_off(["fishing"], "x") == "AnglerMind: the science behind every cast. Try it free at anglermind.com."


def test_old_copy_is_rebranded_at_post_time():
    old = "Why?\n\nCounterphysical: fishing physics that breaks your intuition.\n\n#shorts #fishing #counterphysical"
    new = rebrand(old)
    assert "ounter" not in new
    assert "AnglerMind: fishing physics that breaks your intuition. Try it free at anglermind.com." in new
    assert new.endswith("#shorts #fishing #anglermind")
    assert rebrand(new) == new
    assert rebrand("Animated with real physics by CounterPhysical. AI voice.") == \
        "Animated with real physics by AnglerMind. AI voice."
    assert rebrand("plain text") == "plain text" and rebrand("") == ""
