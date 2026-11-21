"""Cloud posting: uploads queued videos to YouTube as scheduled (private until publishAt), with no PC.

Runs inside GitHub Actions (.github/workflows/publish.yml). Secrets come from the repository's Actions
secrets: YOUTUBE_TOKEN_JSON (the signed-in token). Nothing here prints a secret value.

Queue layout (committed by the render job, one folder per video):
  autopilot_queue/<slug>/package.json   {"title", "description", "tags", "category_id",
                                          "publish_at" (RFC 3339, UTC), "made_for_kids": false,
                                          "contains_synthetic_media": true,
                                          "playlist": optional series name (else picked from the tags)}
  autopilot_queue/<slug>/video.mp4
  autopilot_queue/<slug>/cover.jpg      optional
After a successful upload the folder is deleted (the video lives on YouTube; Caesar's rule: clean up).
A video with no publish_at is skipped, so an unfinished render is never posted by accident.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "autopilot_queue"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    raw = os.environ.get("YOUTUBE_TOKEN_JSON", "").lstrip("﻿").strip()   # a secret pasted from PowerShell can start with a BOM
    if not raw:
        raise SystemExit("YOUTUBE_TOKEN_JSON secret is missing")
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())          # in memory only; nothing is written back
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


# YouTube audit 2026-11-21: on this new channel, four Shorts published 13:00-20:00 UTC on 20 Nov (two in the
# same minute) got almost no views, while the next three, spaced 4-5 h apart, each reached 700-1,100. So
# public times are spread at least this far apart, counting the Shorts already scheduled on the channel.
MIN_GAP = timedelta(hours=4)
MAX_HASHTAGS = 15       # over 15 hashtags in a description and YouTube ignores all of them
KEEP_HASHTAGS = 5       # 3-5 topical ones is the recommended amount
TAGS_MAX_CHARS = 500    # API limit for all tags together (a tag with a space counts its quotes too)


def tidy_tags(tags) -> list[str]:
    out, used = [], 0
    for t in tags or []:
        t = str(t).strip().lstrip("#")
        if not t or t.lower() in (x.lower() for x in out):
            continue
        cost = len(t) + (2 if " " in t else 0) + (1 if out else 0)
        if used + cost > TAGS_MAX_CHARS:
            break
        out.append(t)
        used += cost
    return out


def tidy_description(desc: str) -> str:
    """Keep only the first few hashtags when there are so many that YouTube would ignore them all."""
    tags = re.findall(r"#\w+", desc or "")
    if len(tags) <= MAX_HASHTAGS:
        return desc or ""
    seen = []
    def keep(m):
        if len(seen) < KEEP_HASHTAGS and m.group(0) not in seen:
            seen.append(m.group(0))
            return m.group(0)
        return ""
    return re.sub(r"[ \t]{2,}", " ", re.sub(r"#\w+", keep, desc)).rstrip()


def _parse(t: str) -> datetime:
    return datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone(timezone.utc)


def _fmt(t: datetime) -> str:
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def space_out(wanted: str, taken: list[datetime], now: datetime | None = None, gap: timedelta = MIN_GAP) -> str:
    """The first time at or after `wanted` that is at least `gap` from every time in `taken` (and in the future)."""
    now = now or datetime.now(timezone.utc)
    t = max(_parse(wanted), now + timedelta(minutes=20))
    moved = True
    while moved:
        moved = False
        for x in sorted(taken):
            if abs(t - x) < gap:
                t = x + gap
                moved = True
    return _fmt(t)


def _taken_times(yt) -> list[datetime]:
    """Public times of the channel's latest uploads (scheduled ones use publishAt). Best effort."""
    try:
        ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
        uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        items = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=25).execute()["items"]
        ids = ",".join(i["contentDetails"]["videoId"] for i in items)
        if not ids:
            return []
        vids = yt.videos().list(part="status,snippet", id=ids).execute()["items"]
        return [_parse(v["status"].get("publishAt") or v["snippet"]["publishedAt"]) for v in vids]
    except Exception as e:   # noqa: BLE001
        print(f"could not read the channel's schedule ({type(e).__name__}); spacing only within this batch")
        return []


def add_to_playlist(yt, video_id: str, name: str, cache: dict) -> None:
    """Find or create the series playlist and add the video. Best effort: never fails the upload."""
    try:
        if not cache:
            req = yt.playlists().list(part="snippet", mine=True, maxResults=50)
            while req is not None:
                resp = req.execute()
                cache.update({p["snippet"]["title"]: p["id"] for p in resp.get("items", [])})
                req = yt.playlists().list_next(req, resp)
            cache.setdefault("", "")
        if name not in cache:
            made = yt.playlists().insert(part="snippet,status", body={
                "snippet": {"title": name, "description": f"Counterphysical Shorts: {name.lower()}.",
                            "defaultLanguage": "en"},
                "status": {"privacyStatus": "public"}}).execute()
            cache[name] = made["id"]
        yt.playlistItems().insert(part="snippet", body={"snippet": {
            "playlistId": cache[name], "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
    except Exception as e:   # noqa: BLE001
        print(f"playlist skipped for {video_id}: {type(e).__name__}")


def body(pkg: dict) -> dict:
    status = {"privacyStatus": "private",
              "publishAt": pkg["publish_at"],
              "selfDeclaredMadeForKids": bool(pkg.get("made_for_kids", False)),
              "containsSyntheticMedia": bool(pkg.get("contains_synthetic_media", True))}
    return {"snippet": {"title": pkg["title"][:100], "description": tidy_description(pkg["description"]),
                        "tags": tidy_tags(pkg.get("tags", [])), "categoryId": str(pkg.get("category_id", "28")),
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": status}


def post_one(folder: Path, yt, taken: list[datetime] | None = None, playlists: dict | None = None) -> str:
    from googleapiclient.http import MediaFileUpload
    from .tagline import playlist
    pkg = json.loads((folder / "package.json").read_text(encoding="utf-8"))
    if taken is not None:
        when = space_out(pkg["publish_at"], taken)
        if when != pkg["publish_at"]:
            print(f"{folder.name}: publish time moved {pkg['publish_at']} -> {when} (keeps Shorts {MIN_GAP} apart)")
            pkg["publish_at"] = when
        taken.append(_parse(when))
    media = MediaFileUpload(str(folder / "video.mp4"), mimetype="video/mp4", chunksize=8 << 20, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body(pkg), media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    cover = folder / "cover.jpg"
    if cover.exists():
        try:   # best effort: a custom thumbnail needs a verified channel
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(cover), mimetype="image/jpeg")).execute()
        except Exception as e:   # noqa: BLE001
            print(f"thumbnail skipped for {folder.name}: {type(e).__name__}")
    if playlists is not None:
        add_to_playlist(yt, vid, playlist(pkg.get("tags", []), pkg["title"], pkg.get("playlist")), playlists)
    return vid


def run(dry_run: bool = False) -> int:
    from .ledger import Ledger
    seen = Ledger().topics()
    folders = sorted(p for p in QUEUE.glob("*") if (p / "package.json").exists() and (p / "video.mp4").exists())
    due = []
    for f in folders:
        pkg = json.loads((f / "package.json").read_text(encoding="utf-8"))
        topic = seen.get(f.name)
        if topic and topic.status in ("scheduled", "published"):
            print(f"refusing {f.name}: already {topic.status} in the topic ledger")
            continue
        if pkg.get("publish_at"):
            due.append(f)
    if not due:
        print("nothing queued with a publish time")
        return 0
    if dry_run:
        for f in due:
            print("would schedule:", f.name)
        return 0
    yt = _service()
    taken, playlists = _taken_times(yt), {}
    due.sort(key=lambda f: json.loads((f / "package.json").read_text(encoding="utf-8"))["publish_at"])
    failures = 0
    for f in due:
        try:
            vid = post_one(f, yt, taken, playlists)
            print(f"scheduled {f.name}: https://youtube.com/shorts/{vid}")
            Ledger().set_status(f.name, "scheduled", f"queued by cloud job, YouTube https://youtube.com/shorts/{vid}")
            shutil.rmtree(f)            # clean-up: the file now lives on YouTube
        except Exception as e:   # noqa: BLE001  keep the folder so the next run retries it
            failures += 1
            print(f"FAILED {f.name}: {type(e).__name__}: {str(e)[:200]}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv))
