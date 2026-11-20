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
