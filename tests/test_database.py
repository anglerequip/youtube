import pytest

from factory.database import ALLOWED, DB, STATES, TransitionError


@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "t.db")


def test_every_state_has_rules():
    assert set(ALLOWED) == set(STATES)


def test_happy_path(db):
    db.ensure_video("v", state="STORYBOARDED")
    for s in ("RENDERED", "QUALITY_CHECKED", "PENDING_APPROVAL", "APPROVED", "SCHEDULED", "PUBLISHED", "ANALYZED"):
        db.transition("v", s)
    assert db.get("v")["state"] == "ANALYZED"
    assert len(db.history("v")) == 8


@pytest.mark.parametrize("start,bad", [
    ("STORYBOARDED", "PUBLISHED"),
    ("STORYBOARDED", "APPROVED"),
    ("QUALITY_CHECKED", "APPROVED"),      # must be shown to a human first
    ("PENDING_APPROVAL", "SCHEDULED"),    # approval can't be skipped
    ("PENDING_APPROVAL", "PUBLISHED"),
    ("REJECTED", "APPROVED"),
    ("QC_FAILED", "PENDING_APPROVAL"),
])
def test_forbidden_moves(db, start, bad):
    db.ensure_video("v", state=start)
    with pytest.raises(TransitionError):
        db.transition("v", bad)
    assert db.get("v")["state"] == start


def test_published_cannot_be_rerendered(db):
    db.ensure_video("v", state="PUBLISHED")
    with pytest.raises(TransitionError):
        db.transition("v", "STORYBOARDED")


def test_expect_guards_double_click(db):
    db.ensure_video("v", state="PENDING_APPROVAL")
    db.transition("v", "APPROVED", expect="PENDING_APPROVAL")
    with pytest.raises(TransitionError):
        db.transition("v", "APPROVED", expect="PENDING_APPROVAL")


def test_youtube_id_unique(db):
    import sqlite3
    db.ensure_video("a", state="STORYBOARDED", youtube_id="X")
    with pytest.raises(sqlite3.IntegrityError):
        db.ensure_video("b", state="STORYBOARDED", youtube_id="X")
