import json
from datetime import datetime, timezone

import pytest

from factory.autopilot import facebook_post as fb


@pytest.fixture
def q(tmp_path, monkeypatch):
    monkeypatch.setattr(fb, "QUEUE", tmp_path / "q")
    monkeypatch.setattr(fb, "LOG", tmp_path / "facebook.jsonl")
    (tmp_path / "q").mkdir()
    return tmp_path


def _add(q, slug, queued_at):
    d = q / "q" / slug
    d.mkdir()
    (d / "video.mp4").write_bytes(b"x")
    (d / "package.json").write_text(json.dumps({"title": slug, "description": "", "queued_at": queued_at}))
    return d


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


def test_slot_waits_for_18_stockholm(q):
    assert fb.slot_open(utc("2026-11-22T16:15:00"), {})[0] is False     # 17:15 Stockholm
    assert fb.slot_open(utc("2026-11-22T17:15:00"), {})[0] is True      # 18:15 Stockholm


def test_only_one_reel_per_day_and_20h_gap(q):
    fb.log_post("a", "1", utc("2026-11-22T17:15:00"))
    log = fb.posted()
    assert fb.slot_open(utc("2026-11-22T21:15:00"), log)[0] is False    # same Stockholm day
    assert fb.slot_open(utc("2026-11-23T17:15:00"), log)[0] is True     # next day, 24 h later
    fb.log_post("b", "2", utc("2026-11-23T22:30:00"))
    assert fb.slot_open(utc("2026-11-24T17:15:00"), fb.posted())[0] is False   # 18.75 h < 20 h


def test_oldest_queued_goes_first(q):
    _add(q, "second", "2026-11-21T20:00:02Z")
    _add(q, "first", "2026-11-21T20:00:01Z")
    assert [p.name for p in fb.queue_folders()] == ["first", "second"]


def test_videos_already_on_facebook_are_dropped(q):
    fb.log_post("old", "9", utc("2026-11-20T10:00:00"))
    d = _add(q, "old", "2026-11-21T20:00:01Z")
    assert fb.run(now=utc("2026-11-21T08:00:00")) == 0
    assert not d.exists()


def test_enqueue_moves_video_and_refuses_duplicates(q, tmp_path):
    src = tmp_path / "yt" / "new-video"
    src.mkdir(parents=True)
    (src / "video.mp4").write_bytes(b"v")
    dst = fb.enqueue(src, {"title": "T", "description": "D"}, now=utc("2026-11-22T10:00:00"))
    assert dst and (dst / "video.mp4").read_bytes() == b"v"
    pkg = json.loads((dst / "package.json").read_text())
    assert pkg["is_ai_generated"] is True and pkg["queued_at"] == "2026-11-22T10:00:00Z"
    src.mkdir(exist_ok=True)
    (src / "video.mp4").write_bytes(b"v")
    assert fb.enqueue(src, {"title": "T"}) is None                     # already queued
    fb.log_post("posted-one", "5", utc("2026-11-20T10:00:00"))
    other = tmp_path / "yt" / "posted-one"
    other.mkdir()
    (other / "video.mp4").write_bytes(b"v")
    assert fb.enqueue(other, {"title": "T"}) is None                   # already on Facebook


def test_missing_secrets_post_nothing(q, monkeypatch):
    monkeypatch.delenv("FACEBOOK_PAGE_ID", raising=False)
    monkeypatch.delenv("FACEBOOK_PAGE_TOKEN", raising=False)
    d = _add(q, "waiting", "2026-11-21T20:00:01Z")
    assert fb.run(now=utc("2026-11-22T17:15:00")) == 1
    assert d.exists()


def test_repo_log_lists_every_reel_already_on_the_page():
    slugs = set(fb.posted())
    assert {"touchscreen-field", "banana-radioactive", "cat-stare", "cat-loaf", "why-ocean-blue", "dog-feet"} <= slugs
