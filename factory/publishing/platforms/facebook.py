"""Facebook Reels on a Facebook Page, via the Graph API Reels Publishing endpoints.

Reels can only be published to a Page through the API (not to a personal profile).
Setup (once): a Facebook Page for the channel, a Meta developer app (type Business) with Facebook
Login, a long-lived Page access token with pages_show_list, pages_read_engagement and
pages_manage_posts, set in .env as FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN.
Limits: 3-90 s vertical video, 30 API-published reels per Page per 24 h.
"""
from __future__ import annotations

import os
import time

import requests

from . import NotConfigured

GRAPH = "https://graph.facebook.com"
RUPLOAD = "https://rupload.facebook.com/video-upload"


def _cfg():
    page, tok = os.environ.get("FACEBOOK_PAGE_ID"), os.environ.get("FACEBOOK_PAGE_TOKEN")
    if not page or not tok:
        raise NotConfigured("Facebook: set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_TOKEN in .env (see docs/PUBLISHING.md)")
    return page, tok, os.environ.get("FACEBOOK_GRAPH_VERSION", "v21.0")


def _ok(r: requests.Response, what: str) -> dict:
    d = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in d:
        raise RuntimeError(f"Facebook {what}: HTTP {r.status_code} {d.get('error', d)}")
    return d


def check() -> str:
    page, tok, ver = _cfg()
    d = _ok(requests.get(f"{GRAPH}/{ver}/{page}", params={"fields": "name", "access_token": tok}, timeout=30), "page")
    return f"Facebook: token works for Page '{d.get('name')}'"


def post(pkg: dict) -> tuple[str, str]:
    page, tok, ver = _cfg()
    f = pkg["platforms"]["facebook"]
    start = _ok(requests.post(f"{GRAPH}/{ver}/{page}/video_reels",
                              data={"upload_phase": "start", "access_token": tok}, timeout=60), "start")
    vid = start["video_id"]
    size = int(pkg["video"]["bytes"])
    with open(pkg["video"]["path"], "rb") as fh:
        _ok(requests.post(f"{RUPLOAD}/{ver}/{vid}", data=fh, timeout=900, headers={
            "Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)}), "upload")
    finish = {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "access_token": tok,
              "title": f["title"], "description": f["description"]}
    if f.get("publish_at"):   # Facebook holds the reel as SCHEDULED until scheduled_publish_time (unix seconds)
        from datetime import datetime
        finish["video_state"] = "SCHEDULED"
        finish["scheduled_publish_time"] = str(int(datetime.fromisoformat(f["publish_at"]).timestamp()))
    if f.get("is_ai_generated"):
        finish["is_ai_generated"] = "true"
    _ok(requests.post(f"{GRAPH}/{ver}/{page}/video_reels", data=finish, timeout=60), "finish")
    try:   # custom cover, best effort
        with open(pkg["cover"]["path"], "rb") as img:
            requests.post(f"{GRAPH}/{ver}/{vid}/thumbnails", data={"is_preferred": "true", "access_token": tok},
                          files={"source": ("cover.jpg", img, "image/jpeg")}, timeout=60)
    except Exception:   # noqa: BLE001
        pass
    for _ in range(60):
        st = _ok(requests.get(f"{GRAPH}/{ver}/{vid}", params={"fields": "status", "access_token": tok},
                              timeout=30), "status").get("status", {})
        if st.get("video_status") in ("ready", "published") or st.get("publishing_phase", {}).get("status") == "complete":
            break
        if st.get("video_status") == "error":
            raise RuntimeError(f"Facebook processing failed: {st}")
        time.sleep(5)
    return vid, f"https://www.facebook.com/reel/{vid}"
