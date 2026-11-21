from factory.autopilot.ledger import Ledger, Topic
from factory.autopilot.seed import PAST, seed


def _led(tmp_path):
    led = Ledger(tmp_path / "topics.jsonl")
    seed(led)
    return led


def test_seed_is_idempotent(tmp_path):
    led = _led(tmp_path)
    assert seed(led) == 0
    assert len(led.topics()) == len(PAST)


def test_every_past_topic_is_blocked_when_reworded(tmp_path):
    led = _led(tmp_path)
    reworded = [
        ("The Ocean Isn't Reflecting the Sky", "the sea is not reflecting the sky, water itself absorbs red light"),
        ("Why Your Head Ages Faster", "gravity makes clocks at your head run faster than at your feet"),
        ("Bananas Are Radioactive", "a banana is a little radioactive thanks to potassium-40"),
        ("Pasta Never Breaks in Half", "bend dry pasta and it breaks into three pieces, not two"),
        ("Touchscreens Don't Feel Pressure", "your phone screen senses the electric field of your finger, not pressure"),
    ]
    for title, claim in reworded:
        res = led.check(Topic(id="x", core_claim=claim, title=title))
        assert res["verdict"] == "duplicate", (title, res["nearest"][0])


def test_new_topics_pass(tmp_path):
    led = _led(tmp_path)
    for title, claim in [("Why Ice Is Slippery", "ice is slippery because of a thin liquid-like surface layer"),
                         ("The Moon Illusion", "the moon looks bigger near the horizon but its size on the sky is the same"),
                         ("Why Popcorn Pops", "steam pressure inside the kernel bursts the hull at about 180 degrees")]:
        assert led.check(Topic(id="x", core_claim=claim, title=title))["verdict"] == "ok", title


def test_add_refuses_duplicate_and_status_flow(tmp_path):
    led = _led(tmp_path)
    dup = Topic(id="sea-blue-2", core_claim="the ocean is blue because water absorbs red light", title="Why the Sea Is Blue")
    assert led.add(dup)["verdict"] == "duplicate"
    assert "sea-blue-2" not in led.topics()
    led.add(Topic(id="ice", core_claim="ice is slippery because of a thin liquid-like surface layer", title="Why Ice Is Slippery"))
    assert led.set_status("ice", "in_production").status == "in_production"
    assert led.set_status("ice", "published").status == "published"
    assert led.topics()["ice"].core_claim.startswith("ice is slippery")
