"""TikTok via the Content Posting API, Direct Post (scope video.publish).

Setup (once): a TikTok developer account, an app with Login Kit + Content Posting API (Direct Post
enabled), its client key/secret in .env as TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET, a redirect URI
registered on the app and set as TIKTOK_REDIRECT_URI, then `python -m factory publish-auth tiktok`.

Until TikTok audits the app, its posts are private (SELF_ONLY) and the account must be private.
After the audit, TIKTOK_PRIVACY=PUBLIC_TO_EVERYONE posts publicly.
Rate limit: 6 requests a minute per user token.
"""
from __future__ import annotations

import os
import secrets
import time
import urllib.parse

import requests

from . import NotConfigured, load_token, save_token

API = "https://open.tiktokapis.com"
AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
SCOPES = "user.info.basic,video.publish"


def _client():
    key, sec = os.environ.get("TIKTOK_CLIENT_KEY"), os.environ.get("TIKTOK_CLIENT_SECRET")
    if not key or not sec:
        raise NotConfigured("TikTok: set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET in .env (see docs/PUBLISHING.md)")
    return key, sec


def authorize(input_fn=input, print_fn=print) -> str:
    key, sec = _client()
    redirect = os.environ.get("TIKTOK_REDIRECT_URI")
    if not redirect:
        raise NotConfigured("TikTok: set TIKTOK_REDIRECT_URI to the redirect URI registered on your TikTok app")
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urllib.parse.urlencode({"client_key": key, "scope": SCOPES, "response_type": "code",
                                                   "redirect_uri": redirect, "state": state})
    print_fn(f"Open this link, sign in as @counterphysical and allow access:\n{url}\n")
    pasted = input_fn("Paste the full address you were sent to: ").strip()
    q = urllib.parse.parse_qs(urllib.parse.urlparse(pasted).query)
    if q.get("state", [None])[0] != state:
        raise RuntimeError("TikTok: state mismatch, start again")
    code = q["code"][0]
    tok = _token({"client_key": key, "client_secret": sec, "code": code, "grant_type": "authorization_code",
                  "redirect_uri": redirect})
    return f"TikTok token saved (open_id {tok.get('open_id', '?')})"


def _token(form: dict) -> dict:
    r = requests.post(f"{API}/v2/oauth/token/", data=form, timeout=30,
                      headers={"Content-Type": "application/x-www-form-urlencoded"})
    d = r.json()
    if "access_token" not in d:
        raise RuntimeError(f"TikTok token error: {d}")
    d["expires_at"] = time.time() + int(d.get("expires_in", 0)) - 60
    save_token("tiktok", d)
    return d


def _access_token() -> str:
    tok = load_token("tiktok")
    if not tok:
        raise NotConfigured("TikTok: not signed in. Run `python -m factory publish-auth tiktok`.")
    if time.time() >= tok.get("expires_at", 0):
        key, sec = _client()
        tok = _token({"client_key": key, "client_secret": sec, "grant_type": "refresh_token",
                      "refresh_token": tok["refresh_token"]})
    return tok["access_token"]


def _call(path: str, payload: dict | None = None) -> dict:
    r = requests.post(f"{API}{path}", json=payload or {}, timeout=60,
                      headers={"Authorization": f"Bearer {_access_token()}",
                               "Content-Type": "application/json; charset=UTF-8"})
    d = r.json()
    err = d.get("error", {})
    if err.get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok {path}: {err.get('code')}: {err.get('message')}")
    return d.get("data", {})


def creator_info() -> dict:
    return _call("/v2/post/publish/creator_info/query/")


def check() -> str:
    ci = creator_info()
    return (f"TikTok: signed in as @{ci.get('creator_username')} ({ci.get('creator_nickname')}); "
            f"privacy options {ci.get('privacy_level_options')}; max {ci.get('max_video_post_duration_sec')} s")


def choose_privacy(options: list[str]) -> str:
    want = os.environ.get("TIKTOK_PRIVACY", "PUBLIC_TO_EVERYONE")
    if want in options:
        return want
    if "SELF_ONLY" in options:          # unaudited apps only get SELF_ONLY
        return "SELF_ONLY"
    raise RuntimeError(f"TikTok: privacy {want} not offered (options {options})")


def post(pkg: dict) -> tuple[str, str]:
    f = pkg["platforms"]["tiktok"]
    ci = creator_info()
    if pkg["video"]["duration_s"] > float(ci.get("max_video_post_duration_sec", 600)):
        raise RuntimeError(f"TikTok: video longer than this account allows ({ci.get('max_video_post_duration_sec')} s)")
    size = int(pkg["video"]["bytes"])
    chunk = size if size <= 64_000_000 else 10_000_000
    n = 1 if chunk == size else size // chunk           # TikTok: the last chunk absorbs the remainder
    data = _call("/v2/post/publish/video/init/", {
        "post_info": {
            "title": f["caption"],
            "privacy_level": choose_privacy(ci.get("privacy_level_options", [])),
            "disable_comment": f["disable_comment"] or bool(ci.get("comment_disabled")),
            "disable_duet": f["disable_duet"] or bool(ci.get("duet_disabled")),
            "disable_stitch": f["disable_stitch"] or bool(ci.get("stitch_disabled")),
            "video_cover_timestamp_ms": f["cover_timestamp_ms"],
            "is_aigc": f["is_aigc"],
            "brand_content_toggle": False,
            "brand_organic_toggle": False,
        },
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": chunk, "total_chunk_count": n},
    })
    publish_id, upload_url = data["publish_id"], data["upload_url"]
    with open(pkg["video"]["path"], "rb") as fh:
        for i in range(n):
            start = i * chunk
            end = size - 1 if i == n - 1 else start + chunk - 1
            fh.seek(start)
            body = fh.read(end - start + 1)
            r = requests.put(upload_url, data=body, timeout=600, headers={
                "Content-Type": "video/mp4", "Content-Length": str(len(body)),
                "Content-Range": f"bytes {start}-{end}/{size}"})
            if r.status_code not in (200, 201, 206):
                raise RuntimeError(f"TikTok upload chunk {i + 1}/{n}: HTTP {r.status_code} {r.text[:200]}")
    for _ in range(60):                                     # up to ~5 minutes of processing
        st = _call("/v2/post/publish/status/fetch/", {"publish_id": publish_id})
        if st.get("status") == "PUBLISH_COMPLETE":
            ids = st.get("publicaly_available_post_id") or st.get("publicly_available_post_id") or []
            url = f"https://www.tiktok.com/@{ci.get('creator_username')}/video/{ids[0]}" if ids else None
            return str(ids[0] if ids else publish_id), url or "posted (private until the app is audited)"
        if st.get("status") == "FAILED":
            raise RuntimeError(f"TikTok processing failed: {st.get('fail_reason')}")
        time.sleep(5)
    return publish_id, "still processing on TikTok; check the app"
