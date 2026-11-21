import json
from pathlib import Path

from factory.autopilot import cloud_post


def test_body_is_private_with_publish_time():
    pkg = {"title": "Why Ice Is Slippery", "description": "d", "tags": ["physics"], "publish_at": "2026-11-21T17:00:00Z"}
    b = cloud_post.body(pkg)
    assert b["status"]["privacyStatus"] == "private"
    assert b["status"]["publishAt"] == "2026-11-21T17:00:00Z"
    assert b["snippet"]["title"] == "Why Ice Is Slippery"
    assert b["status"]["containsSyntheticMedia"] is True


def test_title_is_capped_at_youtube_limit():
    b = cloud_post.body({"title": "x" * 150, "description": "", "publish_at": "2026-11-21T17:00:00Z"})
    assert len(b["snippet"]["title"]) == 100


def test_dry_run_skips_folders_without_publish_time(tmp_path, monkeypatch):
    monkeypatch.setattr(cloud_post, "QUEUE", tmp_path)
    for name, when in [("ready", "2026-11-21T17:00:00Z"), ("unfinished", None)]:
        d = tmp_path / name
        d.mkdir()
        (d / "video.mp4").write_bytes(b"x")
        (d / "package.json").write_text(json.dumps({"title": name, "description": "", "publish_at": when}))
    assert cloud_post.run(dry_run=True) == 0
    assert (tmp_path / "ready").exists() and (tmp_path / "unfinished").exists()


def test_queue_refuses_topics_already_in_the_ledger(tmp_path, monkeypatch):
    from factory.autopilot.ledger import Ledger, Topic
    led = Ledger(tmp_path / "topics.jsonl")
    led.add(Topic(id="old-video", core_claim="an old unique physics claim about springs", status="published"), force=True)
    monkeypatch.setattr(cloud_post, "QUEUE", tmp_path / "q")
    monkeypatch.setattr("factory.autopilot.ledger.LEDGER", tmp_path / "topics.jsonl")
    d = tmp_path / "q" / "old-video"
    d.mkdir(parents=True)
    (d / "video.mp4").write_bytes(b"x")
    (d / "package.json").write_text(json.dumps({"title": "t", "description": "", "publish_at": "2026-11-21T16:00:00Z"}))
    assert cloud_post.run(dry_run=True) == 0
    assert d.exists()


def test_language_is_declared_english():
    b = cloud_post.body({"title": "t", "description": "", "publish_at": "2026-11-21T16:00:00Z"})
    assert b["snippet"]["defaultLanguage"] == "en"
    assert b["snippet"]["defaultAudioLanguage"] == "en"


def test_publish_times_are_spread_out():
    from datetime import datetime, timezone
    now = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    taken = [datetime(2026, 11, 21, 16, 0, tzinfo=timezone.utc)]
    assert cloud_post.space_out("2026-11-21T17:00:00Z", taken, now) == "2026-11-21T20:00:00Z"
    assert cloud_post.space_out("2026-11-22T08:00:00Z", taken, now) == "2026-11-22T08:00:00Z"
    assert cloud_post.space_out("2026-11-20T08:00:00Z", [], now) == "2026-11-21T12:20:00Z"   # never in the past


def test_too_many_hashtags_are_trimmed_and_tags_fit_the_limit():
    desc = "Text.\n\n" + " ".join(f"#t{i}" for i in range(20))
    out = cloud_post.tidy_description(desc)
    assert out.count("#") == 5 and out.startswith("Text.")
    assert cloud_post.tidy_description("a #b #c") == "a #b #c"
    tags = cloud_post.tidy_tags(["cats", "Cats", "#science"] + ["x" * 60] * 20)
    assert tags[:2] == ["cats", "science"] and sum(len(t) for t in tags) + len(tags) - 1 <= 500


def test_series_playlist_follows_topic():
    from factory.autopilot.tagline import playlist
    assert playlist(["cats"], "Why cats stare") == "Animal science"
    assert playlist(["gaming"], "Frame rate") == "Video game science"
    assert playlist([], "Ice", "My series") == "My series"
    assert playlist([], "Something odd") == "Surprising science"
