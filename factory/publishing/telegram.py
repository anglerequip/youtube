"""Telegram review: the only place a post gets approved.

  python -m factory review <slug>   send the package (cover, video, one message per platform)
  python -m factory bot             listen for button presses and edits (Ctrl+C to stop)
  python -m factory bot --once      handle what's waiting, then exit (for Task Scheduler)

Each platform message has two buttons: "Post to <platform>" and "Skip". Pressing Post approves that
platform for the exact text, video and cover shown (by hash) and posts it right away.
To change the text, reply to the platform's message:
  any text            replaces the TikTok caption / YouTube description / Facebook description
  "title: New title"  replaces the YouTube or Facebook title
The bot rebuilds the hash, voids any earlier approval and sends the updated message for review.

Only messages from TELEGRAM_CHAT_ID (your own chat with the bot) are accepted.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import requests

from ..configuration import settings
from ..database import DB
from . import PLATFORMS, approvals, package, publisher

log = logging.getLogger("factory.telegram")

NAMES = {"youtube": "YouTube Shorts", "tiktok": "TikTok", "facebook": "Facebook Reels"}
CODE = {"youtube": "y", "tiktok": "t", "facebook": "f"}
UNCODE = {v: k for k, v in CODE.items()}
MAX_BOT_UPLOAD = 50_000_000


class Telegram:
    def __init__(self, token: str | None = None, chat_id: str | None = None, session=None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
        self.chat_id = str(chat_id or os.environ.get("TELEGRAM_CHAT_ID") or "")
        if not self.token or not self.chat_id:
            raise RuntimeError("Telegram: set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env (see docs/PUBLISHING.md)")
        self.http = session or requests.Session()

    def call(self, method: str, files=None, **params):
        data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}
        r = self.http.post(f"https://api.telegram.org/bot{self.token}/{method}", data=data, files=files, timeout=120)
        d = r.json()
        if not d.get("ok"):
            raise RuntimeError(f"Telegram {method}: {d.get('description')}")
        return d["result"]

    def send(self, text: str, **kw):
        return self.call("sendMessage", chat_id=self.chat_id, text=text, **kw)


# ---- what Caesar sees ---------------------------------------------------------------------------
def platform_text(pkg: dict, platform: str) -> str:
    f = pkg["platforms"][platform]
    if platform == "youtube":
        body = (f"Title: {f['title']}\n\n{f['description']}\n\nTags: {', '.join(f['tags'])}\n"
                f"Altered/synthetic content label: {'on' if f['contains_synthetic_media'] else 'off'}")
    elif platform == "tiktok":
        body = (f"{f['caption']}\n\nAI-generated label: {'on' if f['is_aigc'] else 'off'} · cover frame "
                f"{f['cover_timestamp_ms'] / 1000:.1f} s · privacy {os.environ.get('TIKTOK_PRIVACY', 'PUBLIC_TO_EVERYONE')}"
                " (private-only until TikTok audits the app)")
    else:
        body = f"Title: {f['title']}\n\n{f['description']}\n\nAI info label: {'on' if f['is_ai_generated'] else 'off'}"
    head = f"{NAMES[platform]} · {pkg['slug']} · {f['hash'][:8]}"
    text = f"{head}\n\n{body}\n\nReply to this message to edit the text."
    return text[:4000]


def buttons(pkg: dict, platform: str) -> dict:
    h = pkg["platforms"][platform]["hash"][:16]
    return {"inline_keyboard": [[
        {"text": f"Post to {NAMES[platform]}", "callback_data": f"ok:{CODE[platform]}:{h}"},
        {"text": "Skip", "callback_data": f"no:{CODE[platform]}:{h}"},
    ]]}


def send_review(db: DB, slug: str, tg: Telegram | None = None, platforms=PLATFORMS) -> list[int]:
    tg = tg or Telegram()
    pkg = package.load_package(slug)
    approvals.register(db, pkg)
    if platforms == PLATFORMS:
        v = pkg["video"]
        fails = [c["name"] for c in pkg["checks"] if not c["ok"]]
        summary = (f"New video ready to post: {slug}\n{v['duration_s']:.1f} s · {v['width']}x{v['height']}\n"
                   + (f"Package checks failed: {', '.join(fails)}" if fails else "All package checks passed."))
        with open(pkg["cover"]["path"], "rb") as img:
            tg.call("sendPhoto", chat_id=tg.chat_id, caption=summary, files={"photo": img})
        if v["bytes"] <= MAX_BOT_UPLOAD:
            with open(v["path"], "rb") as vid:
                tg.call("sendVideo", chat_id=tg.chat_id, supports_streaming="true", files={"video": vid},
                        caption="The exact file that will be posted.")
        else:
            tg.send(f"The video is too big for a Telegram bot ({v['bytes'] / 1e6:.0f} MB). Watch it at {v['path']}")
    ids = []
    for p in platforms:
        row = approvals.get(db, slug, p)
        if row["status"] in approvals.LIVE:
            continue
        m = tg.send(platform_text(pkg, p), reply_markup=buttons(pkg, p))
        approvals.mark_in_review(db, slug, p, m["message_id"])
        ids.append(m["message_id"])
    approvals.mark_shown(db, slug)
    return ids


# ---- handling Caesar's answers --------------------------------------------------------------------
def _find(db: DB, platform: str, hash_prefix: str):
    approvals.init(db)
    return db.conn.execute("SELECT * FROM posts WHERE platform=? AND package_hash LIKE ? ORDER BY updated_at DESC",
                           (platform, hash_prefix + "%")).fetchone()


def _authorised(tg: Telegram, who: dict) -> bool:
    return str(who.get("id")) == tg.chat_id


def handle_callback(db: DB, tg: Telegram, cq: dict, uploaders=None):
    if not _authorised(tg, cq.get("from", {})):
        tg.call("answerCallbackQuery", callback_query_id=cq["id"], text="Not allowed")
        return
    try:
        action, code, h = cq["data"].split(":")
        platform = UNCODE[code]
    except (ValueError, KeyError):
        tg.call("answerCallbackQuery", callback_query_id=cq["id"], text="Unknown button")
        return
    row = _find(db, platform, h)
    msg = cq.get("message", {})
    if row is None:
        tg.call("answerCallbackQuery", callback_query_id=cq["id"], text="This version is out of date; use the newest message.")
        return
    who = cq["from"].get("username") or str(cq["from"]["id"])
    if action == "no":
        approvals.skip(db, row["slug"], platform, who)
        tg.call("answerCallbackQuery", callback_query_id=cq["id"], text="Skipped")
        tg.call("editMessageReplyMarkup", chat_id=tg.chat_id, message_id=msg.get("message_id"),
                reply_markup={"inline_keyboard": []})
        tg.send(f"Skipped {NAMES[platform]} for {row['slug']}.", reply_to_message_id=msg.get("message_id"))
        return
    try:
        approvals.approve(db, row["slug"], platform, h, by=f"telegram:{who}")
    except Exception as e:   # noqa: BLE001
        tg.call("answerCallbackQuery", callback_query_id=cq["id"], text=str(e)[:190])
        return
    tg.call("answerCallbackQuery", callback_query_id=cq["id"], text=f"Approved. Posting to {NAMES[platform]}...")
    tg.call("editMessageReplyMarkup", chat_id=tg.chat_id, message_id=msg.get("message_id"),
            reply_markup={"inline_keyboard": []})
    res = publisher.publish_one(db, row["slug"], platform, uploaders)
    if res["ok"]:
        tg.send(f"Live on {NAMES[platform]}: {res['url']}", reply_to_message_id=msg.get("message_id"))
    else:
        tg.send(f"Not posted to {NAMES[platform]}: {res['error']}", reply_to_message_id=msg.get("message_id"))


def handle_edit(db: DB, tg: Telegram, message: dict):
    """A reply to a platform message replaces its text, then re-sends it for review."""
    if not _authorised(tg, message.get("from", {})):
        return
    reply_to = (message.get("reply_to_message") or {}).get("message_id")
    text = (message.get("text") or "").strip()
    if not reply_to or not text:
        if text.lower() in ("/status", "status"):
            tg.send(status_text(db))
        return
    approvals.init(db)
    row = db.conn.execute("SELECT * FROM posts WHERE review_msg_id=?", (reply_to,)).fetchone()
    if row is None:
        return
    slug, platform = row["slug"], row["platform"]
    if row["status"] in approvals.LIVE:
        tg.send(f"{NAMES[platform]} is already posted; edit it in the app.", reply_to_message_id=message["message_id"])
        return
    pkg = package.load_package(slug)
    f = pkg["platforms"][platform]
    if text.lower().startswith("title:") and platform in ("youtube", "facebook"):
        f["title"] = text[6:].strip()[:100 if platform == "youtube" else 255]
    elif platform == "tiktok":
        f["caption"] = text[:2200]
    else:
        f["description"] = text
    f["hash"] = package.platform_hash(slug, platform, f, pkg["video"]["sha256"], pkg["cover"]["sha256"])
    pkg["checks"] = package.checks(pkg)
    pkg["ok"] = all(c["ok"] for c in pkg["checks"])
    out = settings.out_dir / slug / "publish"
    (out / "package.json").write_text(json.dumps(pkg, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "review.md").write_text(package.review_markdown(pkg), encoding="utf-8")
    approvals.register(db, pkg)
    tg.call("editMessageReplyMarkup", chat_id=tg.chat_id, message_id=reply_to, reply_markup={"inline_keyboard": []})
    send_review(db, slug, tg, platforms=(platform,))


def status_text(db: DB) -> str:
    approvals.init(db)
    rs = approvals.rows(db)
    if not rs:
        return "Nothing packaged yet."
    return "\n".join(f"{r['slug']} · {NAMES[r['platform']]}: {r['status']}"
                     + (f" {r['remote_url']}" if r["remote_url"] else "") for r in rs)


def _offset_file() -> Path:
    return settings.data_dir / "telegram_offset.txt"


def poll(db: DB, tg: Telegram | None = None, once: bool = False, uploaders=None):
    tg = tg or Telegram()
    f = _offset_file()
    offset = int(f.read_text()) if f.exists() else None
    while True:
        updates = tg.call("getUpdates", offset=offset, timeout=0 if once else 50,
                          allowed_updates=["message", "callback_query"])
        for u in updates:
            offset = u["update_id"] + 1
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(str(offset))
            try:
                if "callback_query" in u:
                    handle_callback(db, tg, u["callback_query"], uploaders)
                elif "message" in u:
                    handle_edit(db, tg, u["message"])
            except Exception:   # noqa: BLE001  keep the bot alive
                log.exception("update %s failed", u.get("update_id"))
        if once and not updates:
            return
        if not updates and not once:
            time.sleep(1)
