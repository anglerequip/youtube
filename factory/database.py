"""SQLite store and the video state machine.

Every video moves through:
  IDEA -> RESEARCHED -> SCRIPTED -> STORYBOARDED -> RENDERED -> QUALITY_CHECKED
       -> PENDING_APPROVAL -> APPROVED -> SCHEDULED -> PUBLISHED -> ANALYZED
with side states QC_FAILED, REVISION_REQUESTED, REJECTED and FAILED.

`transition()` refuses any move not listed in ALLOWED, so a bug can't skip approval.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .configuration import settings

STATES = (
    "IDEA", "RESEARCHED", "SCRIPTED", "STORYBOARDED", "RENDERED", "QUALITY_CHECKED",
    "PENDING_APPROVAL", "APPROVED", "SCHEDULED", "PUBLISHED", "ANALYZED",
    "QC_FAILED", "REVISION_REQUESTED", "REJECTED", "FAILED",
)

# Re-rendering is allowed from any pre-approval state, so a changed storyboard can be rebuilt.
_REBUILDABLE = ("STORYBOARDED", "RENDERED", "QUALITY_CHECKED", "QC_FAILED", "REVISION_REQUESTED", "FAILED",
                "PENDING_APPROVAL")

ALLOWED: dict[str, set[str]] = {
    "IDEA": {"RESEARCHED", "REJECTED"},
    "RESEARCHED": {"SCRIPTED", "REJECTED"},
    "SCRIPTED": {"STORYBOARDED", "FAILED"},
    "STORYBOARDED": {"RENDERED", "FAILED"},
    "RENDERED": {"QUALITY_CHECKED", "QC_FAILED", "FAILED"},
    "QUALITY_CHECKED": {"PENDING_APPROVAL", "FAILED"},
    "PENDING_APPROVAL": {"APPROVED", "REJECTED", "REVISION_REQUESTED"},
    "APPROVED": {"SCHEDULED", "FAILED"},
    "SCHEDULED": {"PUBLISHED", "FAILED"},
    "PUBLISHED": {"ANALYZED"},
    "ANALYZED": {"ANALYZED"},
    "QC_FAILED": {"SCRIPTED", "STORYBOARDED", "REJECTED"},
    "REVISION_REQUESTED": {"SCRIPTED", "STORYBOARDED", "REJECTED"},
    "REJECTED": set(),
    "FAILED": {"SCRIPTED", "STORYBOARDED", "APPROVED", "REJECTED"},
}
for _s in _REBUILDABLE:
    ALLOWED[_s].add("STORYBOARDED")
# A failed upload goes back to APPROVED (above) only if the approved file is unchanged; see publisher.

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    slug              TEXT PRIMARY KEY,
    state             TEXT NOT NULL,
    topic             TEXT,
    title             TEXT,
    render_count      INTEGER NOT NULL DEFAULT 0,
    video_path        TEXT,
    video_sha256      TEXT,
    duration_s        REAL,
    approved_sha256   TEXT,
    revision_note     TEXT,
    telegram_msg_id   INTEGER,
    youtube_id        TEXT UNIQUE,
    publish_at        TEXT,
    last_error        TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transitions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    slug       TEXT NOT NULL,
    from_state TEXT,
    to_state   TEXT NOT NULL,
    note       TEXT,
    at         TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ideas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL UNIQUE,
    topic      TEXT,
    hook       TEXT,
    component  TEXT,
    score      REAL,
    score_json TEXT,
    status     TEXT NOT NULL DEFAULT 'IDEA',
    source     TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS qc_reports (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    slug      TEXT NOT NULL,
    passed    INTEGER NOT NULL,
    report    TEXT NOT NULL,
    at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS metrics (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                  TEXT NOT NULL,
    youtube_id            TEXT NOT NULL,
    fetched_at            TEXT NOT NULL,
    views                 INTEGER,
    engaged_views         INTEGER,
    avg_view_duration_s   REAL,
    avg_view_pct          REAL,
    likes                 INTEGER,
    comments              INTEGER,
    shares                INTEGER,
    subs_gained           INTEGER,
    subs_lost             INTEGER,
    raw_json              TEXT
);
"""


class TransitionError(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DB:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path or settings.db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, isolation_level=None)  # autocommit; we use explicit tx
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    @contextmanager
    def tx(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise

    # ---- videos ----------------------------------------------------------
    def get(self, slug: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM videos WHERE slug=?", (slug,)).fetchone()

    def ensure_video(self, slug: str, state: str = "SCRIPTED", **fields) -> sqlite3.Row:
        if state not in STATES:
            raise ValueError(state)
        with self.tx() as c:
            if c.execute("SELECT 1 FROM videos WHERE slug=?", (slug,)).fetchone() is None:
                t = now()
                c.execute("INSERT INTO videos(slug, state, created_at, updated_at) VALUES (?,?,?,?)",
                          (slug, state, t, t))
                c.execute("INSERT INTO transitions(slug, from_state, to_state, note, at) VALUES (?,?,?,?,?)",
                          (slug, None, state, "created", t))
        if fields:
            self.update(slug, **fields)
        return self.get(slug)

    def update(self, slug: str, **fields):
        if not fields:
            return
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE videos SET {cols}, updated_at=? WHERE slug=?",
                          (*fields.values(), now(), slug))

    def transition(self, slug: str, to_state: str, note: str = "", expect: str | tuple | None = None,
                   **fields) -> sqlite3.Row:
        """Atomically move a video to `to_state`. `expect` guards against races (e.g. double clicks)."""
        if to_state not in STATES:
            raise ValueError(to_state)
        with self.tx() as c:
            row = c.execute("SELECT state FROM videos WHERE slug=?", (slug,)).fetchone()
            if row is None:
                raise TransitionError(f"{slug}: no such video")
            cur = row["state"]
            if expect is not None:
                exp = (expect,) if isinstance(expect, str) else tuple(expect)
                if cur not in exp:
                    raise TransitionError(f"{slug}: expected state {exp}, found {cur}")
            if to_state not in ALLOWED[cur]:
                raise TransitionError(f"{slug}: {cur} -> {to_state} is not allowed")
            t = now()
            sets = {"state": to_state, "updated_at": t, **fields}
            cols = ", ".join(f"{k}=?" for k in sets)
            c.execute(f"UPDATE videos SET {cols} WHERE slug=?", (*sets.values(), slug))
            c.execute("INSERT INTO transitions(slug, from_state, to_state, note, at) VALUES (?,?,?,?,?)",
                      (slug, cur, to_state, note, t))
        return self.get(slug)

    def by_state(self, *states: str) -> list[sqlite3.Row]:
        q = f"SELECT * FROM videos WHERE state IN ({','.join('?' * len(states))}) ORDER BY updated_at"
        return list(self.conn.execute(q, states))

    def history(self, slug: str) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM transitions WHERE slug=? ORDER BY id", (slug,)))

    def add_qc_report(self, slug: str, passed: bool, report_json: str):
        self.conn.execute("INSERT INTO qc_reports(slug, passed, report, at) VALUES (?,?,?,?)",
                          (slug, int(passed), report_json, now()))
