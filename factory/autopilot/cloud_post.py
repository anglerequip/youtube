"""Cloud posting: uploads queued videos to YouTube as scheduled (private until publishAt), with no PC.

Runs inside GitHub Actions (.github/workflows/publish.yml). Secrets come from the repository's Actions
secrets: YOUTUBE_TOKEN_JSON (the signed-in token). Nothing here prints a secret value.

Queue layout (committed by the render job, one folder per video):
  autopilot_queue/<slug>/package.json   {"title", "description", "tags", "category_id",
                                          "publish_at" (RFC 3339, UTC), "made_for_kids": false,
                                          "contains_synthetic_media": true}
  autopilot_queue/<slug>/video.mp4
  autopilot_queue/<slug>/cover.jpg      optional
After a successful upload the folder is deleted (the video lives on YouTube; Caesar's rule: clean up).
A video with no publish_at is skipped, so an unfinished render is never posted by accident.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "autopilot_queue"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    raw = os.environ.get("YOUTUBE_TOKEN_JSON", "")
    if not raw:
        raise SystemExit("YOUTUBE_TOKEN_JSON secret is missing")
    creds = Credentials.from_authorized_user_info(json.loads(raw), SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())          # in memory only; nothing is written back
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def body(pkg: dict) -> dict:
    status = {"privacyStatus": "private",
              "publishAt": pkg["publish_at"],
              "selfDeclaredMadeForKids": bool(pkg.get("made_for_kids", False)),
              "containsSyntheticMedia": bool(pkg.get("contains_synthetic_media", True))}
    return {"snippet": {"title": pkg["title"][:100], "description": pkg["description"],
                        "tags": pkg.get("tags", []), "categoryId": str(pkg.get("category_id", "28")),
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"},
            "status": status}


def post_one(folder: Path, yt) -> str:
    from googleapiclient.http import MediaFileUpload
    pkg = json.loads((folder / "package.json").read_text(encoding="utf-8"))
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
    failures = 0
    for f in due:
        try:
            vid = post_one(f, yt)
            print(f"scheduled {f.name}: https://youtube.com/shorts/{vid}")
            Ledger().set_status(f.name, "scheduled", f"queued by cloud job, YouTube https://youtube.com/shorts/{vid}")
            shutil.rmtree(f)            # clean-up: the file now lives on YouTube
        except Exception as e:   # noqa: BLE001  keep the folder so the next run retries it
            failures += 1
            print(f"FAILED {f.name}: {type(e).__name__}: {str(e)[:200]}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv))
