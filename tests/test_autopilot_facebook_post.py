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


def test_morning_run_schedules_for_18_stockholm(q):
    when, _ = fb.next_slot(utc("2026-11-22T06:46:00"), {})               # 07:46 Stockholm
    assert when == utc("2026-11-22T17:00:00")                           # 18:00 Stockholm


def test_evening_run_posts_now_late_run_waits_for_tomorrow(q):
    now = utc("2026-11-22T18:30:00")                                    # 19:30 Stockholm
    assert fb.next_slot(now, {})[0] == now
    assert fb.next_slot(utc("2026-11-22T21:45:00"), {})[0] == utc("2026-11-23T17:00:00")


def test_one_reel_per_day_and_nothing_while_one_is_scheduled(q):
    fb.log_post("a", "1", utc("2026-11-22T17:00:00"))                   # live today 18:00
    assert fb.next_slot(utc("2026-11-22T19:00:00"), fb.posted())[0] == utc("2026-11-23T17:00:00")
    fb.log_post("b", "2", utc("2026-11-23T17:00:00"))                   # scheduled for tomorrow
    assert fb.next_slot(utc("2026-11-22T23:00:00"), fb.posted())[0] is None


def test_gap_after_a_late_post(q):
    fb.log_post("a", "1", utc("2026-11-24T21:11:00"))                   # 22:11 Stockholm
    # 25 Nov 18:00 is 19.8 h later: fine with the 18 h minimum
    assert fb.next_slot(utc("2026-11-25T04:12:00"), fb.posted())[0] == utc("2026-11-25T17:00:00")
    fb.log_post("b", "2", utc("2026-11-25T03:00:00"))                   # 04:00 Stockholm (manual)
    assert fb.next_slot(utc("2026-11-25T04:12:00"), fb.posted())[0] == utc("2026-11-26T17:00:00")


def test_scheduled_run_uploads_with_publish_time(q, monkeypatch):
    _add(q, "next", "2026-11-21T20:00:01Z")
    sent = []
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "p")
    monkeypatch.setenv("FACEBOOK_PAGE_TOKEN", "t")
    monkeypatch.setattr(fb, "post_reel", lambda f, page, token, at=None: sent.append((f.name, at)) or "77")
    assert fb.run(now=utc("2026-11-25T04:12:00")) == 0
    assert sent == [("next", utc("2026-11-25T17:00:00"))]
    assert fb.posted()["next"]["posted_at"] == "2026-11-25T17:00:00Z"


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


def test_post_now_skips_the_slot_but_needs_a_queued_video(q, monkeypatch):
    fb.log_post("today", "1", utc("2026-11-21T19:33:00"))
    _add(q, "first", "2026-11-21T20:00:01Z")
    _add(q, "falling-cat", "2026-11-21T20:00:02Z")
    sent = []
    monkeypatch.setenv("FACEBOOK_PAGE_ID", "p")
    monkeypatch.setenv("FACEBOOK_PAGE_TOKEN", "t")
    monkeypatch.setattr(fb, "post_reel", lambda f, page, token, at=None: sent.append(f.name) or "99")
    assert fb.run(now=utc("2026-11-21T20:55:00"), now_slug="falling-cat") == 0
    assert sent == ["falling-cat"] and "falling-cat" in fb.posted()
    assert fb.run(now=utc("2026-11-21T21:00:00"), now_slug="falling-cat") == 1     # already posted
    assert fb.run(now=utc("2026-11-21T21:00:00"), dry_run=True) == 0 and sent == ["falling-cat"]
