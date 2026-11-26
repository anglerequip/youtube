"""YouTube Shorts via the YouTube Data API v3 (videos.insert, then thumbnails.set).

Setup (once): a Google Cloud project with "YouTube Data API v3" enabled, an OAuth client of type
"Desktop app", its JSON saved as client_secret.json in the repo root (git-ignored), then
`python -m factory publish-auth youtube` opens a browser to sign in to the channel's Google account.

A video up to 3 minutes long, vertical, is classified as a Short automatically; there is no Shorts flag.
Quota: an upload costs most of the default daily quota, so a few uploads a day is the free limit.
"""
from __future__ import annotations

import os
from pathlib import Path

from ...configuration import settings
from . import NotConfigured

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]


def _paths():
    secrets = Path(os.environ.get("YOUTUBE_CLIENT_SECRETS", settings.root / "client_secret.json"))
    token = Path(os.environ.get("YOUTUBE_TOKEN_FILE", settings.data_dir / "tokens" / "youtube.json"))
    if not secrets.is_absolute():
        secrets = settings.root / secrets
    if not token.is_absolute():
        token = settings.root / token
    return secrets, token


def authorize():
    """Interactive, run once on Caesar's PC."""
    from google_auth_oauthlib.flow import InstalledAppFlow
    secrets, token = _paths()
    if not secrets.exists():
        raise NotConfigured(f"YouTube: put the OAuth client file at {secrets} (see docs/PUBLISHING.md)")
    creds = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES).run_local_server(port=0)
    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json())
    return f"YouTube token saved to {token}"


def _service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    _, token = _paths()
    if not token.exists():
        raise NotConfigured("YouTube: not signed in. Run `python -m factory publish-auth youtube`.")
    creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if not creds.valid and creds.refresh_token:
        creds.refresh(Request())
        token.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def check() -> str:
    yt = _service()
    items = yt.channels().list(part="snippet", mine=True).execute().get("items") or []
    if not items:
        raise NotConfigured("YouTube: this Google account has no YouTube channel. Run "
                            "`python -m factory publish-auth youtube` again and pick the Counterphysical "
                            "channel (brand account) on Google's account chooser.")
    return f"YouTube: signed in as channel '{items[0]['snippet']['title']}'"


def body(pkg: dict) -> dict:
    f = pkg["platforms"]["youtube"]
    status = {"privacyStatus": os.environ.get("YOUTUBE_PRIVACY", "public"),
              "selfDeclaredMadeForKids": f["made_for_kids"],
              "containsSyntheticMedia": f["contains_synthetic_media"]}
    if f.get("publish_at"):   # YouTube keeps a scheduled video private until publishAt, then publishes it itself
        status["privacyStatus"] = "private"
        status["publishAt"] = f["publish_at"]
    return {
        "snippet": {"title": f["title"], "description": f["description"], "tags": f["tags"],
                    "categoryId": f["category_id"]},
        "status": status,
    }


def post(pkg: dict) -> tuple[str, str]:
    from googleapiclient.http import MediaFileUpload
    yt = _service()
    media = MediaFileUpload(pkg["video"]["path"], mimetype="video/mp4", chunksize=8 << 20, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body(pkg), media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    try:   # Custom thumbnails need a verified channel and may not show in the Shorts feed; best effort.
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(pkg["cover"]["path"], mimetype="image/jpeg")).execute()
    except Exception:   # noqa: BLE001  the video is live either way
        pass
    return vid, f"https://youtube.com/shorts/{vid}"
