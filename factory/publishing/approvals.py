"""Per-platform approvals, stored next to the existing video state machine.

One row per (slug, platform):
  READY      packaged, waiting to be sent for review
  IN_REVIEW  sent to the human in Telegram
  APPROVED   the human pressed Approve for exactly `package_hash`
  SKIPPED    the human chose not to post on this platform
  POSTING    the publisher has claimed it (guards against double posting)
  POSTED     live; remote_id/remote_url set
  FAILED     the upload failed; `last_error` says why. Needs a fresh approval to retry.

Only `approve()` can move a row to APPROVED, it requires the hash the human saw, and the publisher
re-verifies that hash against the files on disk before uploading.
"""
from __future__ import annotations

from ..database import DB, TransitionError, now
from . import PLATFORMS

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    slug          TEXT NOT NULL,
    platform      TEXT NOT NULL,
    status        TEXT NOT NULL,
    package_hash  TEXT NOT NULL,
    review_msg_id INTEGER,
    approved_hash TEXT,
    approved_by   TEXT,
    approved_at   TEXT,
    remote_id     TEXT,
    remote_url    TEXT,
    last_error    TEXT,
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (slug, platform)
);
"""

LIVE = ("POSTING", "POSTED")


def init(db: DB) -> DB:
    db.conn.executescript(SCHEMA)
    return db


def get(db: DB, slug: str, platform: str):
    return db.conn.execute("SELECT * FROM posts WHERE slug=? AND platform=?", (slug, platform)).fetchone()


def rows(db: DB, slug: str | None = None, status: str | None = None):
    q, a = "SELECT * FROM posts WHERE 1=1", []
    if slug:
        q, a = q + " AND slug=?", a + [slug]
    if status:
        q, a = q + " AND status=?", a + [status]
    return list(db.conn.execute(q + " ORDER BY slug, platform", a))


def register(db: DB, pkg: dict) -> list[str]:
    """Record a (new or rebuilt) package. A platform already posted or posting is left alone;
    anything else resets to READY with the new hash, which voids any earlier approval."""
    init(db)
    changed = []
    with db.tx() as c:
        for p in PLATFORMS:
            h = pkg["platforms"][p]["hash"]
            row = c.execute("SELECT * FROM posts WHERE slug=? AND platform=?", (pkg["slug"], p)).fetchone()
            if row is None:
                c.execute("INSERT INTO posts(slug, platform, status, package_hash, updated_at) VALUES (?,?,?,?,?)",
                          (pkg["slug"], p, "READY", h, now()))
                changed.append(p)
            elif row["status"] not in LIVE and row["package_hash"] != h:
                c.execute("UPDATE posts SET status='READY', package_hash=?, approved_hash=NULL, approved_by=NULL,"
                          " approved_at=NULL, review_msg_id=NULL, updated_at=? WHERE slug=? AND platform=?",
                          (h, now(), pkg["slug"], p))
                changed.append(p)
    return changed


def mark_shown(db: DB, slug: str):
    """Video-level state: QUALITY_CHECKED -> PENDING_APPROVAL once the package is in front of the human."""
    v = db.get(slug)
    if v is not None and v["state"] == "QUALITY_CHECKED":
        db.transition(slug, "PENDING_APPROVAL", note="publishing package sent for review")


def mark_in_review(db: DB, slug: str, platform: str, msg_id: int | None):
    db.conn.execute("UPDATE posts SET status='IN_REVIEW', review_msg_id=?, updated_at=? "
                    "WHERE slug=? AND platform=? AND status IN ('READY','IN_REVIEW','FAILED','SKIPPED')",
                    (msg_id, now(), slug, platform))


def approve(db: DB, slug: str, platform: str, seen_hash: str, by: str) -> None:
    """The only way into APPROVED. `seen_hash` must be the hash shown to the human (full or prefix >= 8)."""
    if len(seen_hash) < 8:
        raise TransitionError("approval hash too short")
    with db.tx() as c:
        row = c.execute("SELECT * FROM posts WHERE slug=? AND platform=?", (slug, platform)).fetchone()
        if row is None:
            raise TransitionError(f"{slug}/{platform}: no package")
        if row["status"] not in ("IN_REVIEW", "READY", "FAILED"):
            raise TransitionError(f"{slug}/{platform}: cannot approve from {row['status']}")
        if not row["package_hash"].startswith(seen_hash):
            raise TransitionError(f"{slug}/{platform}: the package changed since you saw it; review the new one")
        c.execute("UPDATE posts SET status='APPROVED', approved_hash=package_hash, approved_by=?, approved_at=?,"
                  " last_error=NULL, updated_at=? WHERE slug=? AND platform=?", (by, now(), now(), slug, platform))
    v = db.get(slug)
    if v is not None and v["state"] == "PENDING_APPROVAL":
        db.transition(slug, "APPROVED", note=f"approved for {platform} by {by}", approved_sha256=v["video_sha256"])


def skip(db: DB, slug: str, platform: str, by: str):
    db.conn.execute("UPDATE posts SET status='SKIPPED', approved_by=?, updated_at=? WHERE slug=? AND platform=? "
                    "AND status NOT IN ('POSTING','POSTED')", (by, now(), slug, platform))


def claim(db: DB, slug: str, platform: str) -> bool:
    """APPROVED -> POSTING atomically. False if someone else got there first."""
    with db.tx() as c:
        cur = c.execute("UPDATE posts SET status='POSTING', updated_at=? WHERE slug=? AND platform=? "
                        "AND status='APPROVED' AND approved_hash=package_hash", (now(), slug, platform))
        return cur.rowcount == 1


def posted(db: DB, slug: str, platform: str, remote_id: str, url: str | None):
    db.conn.execute("UPDATE posts SET status='POSTED', remote_id=?, remote_url=?, updated_at=? "
                    "WHERE slug=? AND platform=?", (remote_id, url, now(), slug, platform))
    v = db.get(slug)
    if v is None:
        return
    if v["state"] == "APPROVED":
        db.transition(slug, "SCHEDULED", note=f"posting to {platform}")
        v = db.get(slug)
    if v["state"] == "SCHEDULED":
        extra = {"youtube_id": remote_id} if platform == "youtube" else {}
        db.transition(slug, "PUBLISHED", note=f"live on {platform}: {url or remote_id}", **extra)
    elif platform == "youtube" and not v["youtube_id"]:
        db.update(slug, youtube_id=remote_id)


def failed(db: DB, slug: str, platform: str, error: str):
    db.conn.execute("UPDATE posts SET status='FAILED', last_error=?, approved_hash=NULL, updated_at=? "
                    "WHERE slug=? AND platform=?", (error[:2000], now(), slug, platform))
