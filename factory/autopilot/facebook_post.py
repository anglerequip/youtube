"""Cloud Facebook queue: posts ONE reel a day to the CounterPhysical Page, with no PC.

Caesar (2026-11-21): "queue everything we've ever made that's not already on Facebook, including new
videos". Rules agreed in the project thread "Find out why Facebook reels disappeared":
  * at most one reel per Stockholm calendar day, going live at 18:00 Stockholm time. GitHub runs the
    "hourly" schedule only every 6-10 hours, so the job uploads whenever it runs and lets Facebook
    publish the reel at 18:00 (video_state SCHEDULED); a run between 18:00 and 22:00 posts at once;
  * at least 18 h between two reels (Meta locked the developer account on 2026-11-20 after five
    API reels in about 12 hours, so the queue is deliberately slow);
  * never the same video twice (content/ledger/facebook.jsonl records every reel on the Page).

Queue layout (one folder per video, oldest `queued_at` goes first):
  autopilot_queue_facebook/<slug>/package.json  {"title", "description", "queued_at" (RFC 3339 UTC),
                                                  "is_ai_generated": true}
  autopilot_queue_facebook/<slug>/video.mp4
New videos join automatically: cloud_post.py moves each folder here after its YouTube upload.
After a successful reel the folder is deleted (Caesar's clean-up rule) and the reel is logged.

Runs inside GitHub Actions (.github/workflows/publish.yml). Secrets: FACEBOOK_PAGE_ID and
FACEBOOK_PAGE_TOKEN. Nothing here prints a secret value.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "autopilot_queue_facebook"
LOG = ROOT / "content" / "ledger" / "facebook.jsonl"
TZ = ZoneInfo("Europe/Stockholm")
SLOT_HOUR = 18              # local Stockholm hour from which the day's reel may go out
MIN_GAP = timedelta(hours=18)
LEAD = timedelta(minutes=20)    # Facebook wants a scheduled time at least 10 min ahead
LATEST_HOUR = 22                # after 22:00 Stockholm, wait for tomorrow's 18:00 instead
GRAPH = "https://graph.facebook.com"
RUPLOAD = "https://rupload.facebook.com/video-upload"
VERSION = os.environ.get("FACEBOOK_GRAPH_VERSION", "v25.0")


def posted() -> dict[str, dict]:
    """slug -> latest log line for every reel already on the Page."""
    out: dict[str, dict] = {}
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                out[d["slug"]] = d
    return out


def log_post(slug: str, reel_id: str, when: datetime, how: str = "cloud queue") -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"slug": slug, "reel_id": reel_id, "posted_at": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "how": how}) + "\n")


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def next_slot(now: datetime, log: dict[str, dict]) -> tuple[datetime | None, str]:
    """When should the next reel go live? Returns (time, reason); time None = nothing to do now.

    A time later than `now` means "upload now, Facebook publishes it then"."""
    times = [_ts(d["posted_at"]) for d in log.values() if d.get("posted_at")]
    last = max(times) if times else None
    if last and last > now:
        return None, f"a reel is already scheduled for {last.astimezone(TZ):%a %d %b %H:%M} Stockholm"
    days = {t.astimezone(TZ).date() for t in times}
    local = now.astimezone(TZ)
    for add in range(4):
        day = (local + timedelta(days=add)).date()
        slot = datetime(day.year, day.month, day.day, SLOT_HOUR, tzinfo=TZ)
        if day in days:
            continue
        if slot - now < LEAD:                    # too close to (or past) 18:00 to schedule
            if add == 0 and local.hour < LATEST_HOUR and (not last or now - last >= MIN_GAP):
                return now, "posting now (18:00 slot already passed today)"
            continue
        if last and slot - last < MIN_GAP:
            continue
        return slot.astimezone(timezone.utc), f"scheduling for {slot:%a %d %b %H:%M} Stockholm"
    return None, "no open slot in the next days"


def queue_folders() -> list[Path]:
    folders = [p for p in QUEUE.glob("*") if (p / "package.json").exists() and (p / "video.mp4").exists()]

    def key(p: Path):
        pkg = json.loads((p / "package.json").read_text(encoding="utf-8"))
        return (pkg.get("queued_at", "9999"), p.name)
    return sorted(folders, key=key)


def enqueue(src: Path, pkg: dict, now: datetime | None = None) -> Path | None:
    """Move a finished video folder (video.mp4 [+ cover.jpg]) into the Facebook queue.

    Returns the new folder, or None when that video is already on Facebook or already queued."""
    slug = src.name
    if slug in posted() or (QUEUE / slug).exists():
        return None
    now = now or datetime.now(timezone.utc)
    dst = QUEUE / slug
    dst.mkdir(parents=True)
    shutil.move(str(src / "video.mp4"), dst / "video.mp4")
    if (src / "cover.jpg").exists():
        shutil.move(str(src / "cover.jpg"), dst / "cover.jpg")
    fb = {"title": pkg["title"][:255], "description": pkg.get("description", ""),
          "queued_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
          "is_ai_generated": bool(pkg.get("contains_synthetic_media", True))}
    (dst / "package.json").write_text(json.dumps(fb, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dst


def _ok(r, what: str) -> dict:
    d = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in d:
        err = d.get("error", d)
        if isinstance(err, dict):
            err = {k: err.get(k) for k in ("message", "type", "code", "error_subcode") if k in err}
        raise RuntimeError(f"Facebook {what}: HTTP {r.status_code} {err}")
    return d


def post_reel(folder: Path, page: str, token: str, at: datetime | None = None) -> str:
    """Upload and publish one reel through the Graph API Reels endpoints. Returns the reel id."""
    import requests
    pkg = json.loads((folder / "package.json").read_text(encoding="utf-8"))
    video = folder / "video.mp4"
    start = _ok(requests.post(f"{GRAPH}/{VERSION}/{page}/video_reels",
                              data={"upload_phase": "start", "access_token": token}, timeout=60), "start")
    vid = start["video_id"]
    with video.open("rb") as fh:
        _ok(requests.post(f"{RUPLOAD}/{VERSION}/{vid}", data=fh, timeout=900, headers={
            "Authorization": f"OAuth {token}", "offset": "0", "file_size": str(video.stat().st_size)}), "upload")
    finish = {"upload_phase": "finish", "video_id": vid, "video_state": "PUBLISHED", "access_token": token,
              "title": pkg["title"], "description": pkg.get("description", "")}
    if pkg.get("is_ai_generated", True):
        finish["is_ai_generated"] = "true"
    if at is not None:
        finish["video_state"] = "SCHEDULED"
        finish["scheduled_publish_time"] = str(int(at.timestamp()))
    _ok(requests.post(f"{GRAPH}/{VERSION}/{page}/video_reels", data=finish, timeout=60), "finish")
    if at is not None:      # Facebook publishes it later; nothing to wait for now
        return vid
    for _ in range(90):      # wait until Facebook has actually published it, not just received it
        try:                 # after "finish" the reel exists: a flaky status call must not cause a re-post
            st = _ok(requests.get(f"{GRAPH}/{VERSION}/{vid}", params={"fields": "status", "access_token": token},
                                  timeout=30), "status").get("status", {})
        except Exception as e:   # noqa: BLE001
            print(f"note: status check for {folder.name} failed ({type(e).__name__}); reel {vid} was submitted")
            break
        if st.get("video_status") == "error":
            raise RuntimeError(f"Facebook processing failed: {st}")
        if st.get("publishing_phase", {}).get("status") == "complete" or st.get("video_status") == "published":
            break
        time.sleep(10)
    else:
        print(f"note: {folder.name} still processing after 15 min; Facebook will finish publishing it")
    return vid


def run(dry_run: bool = False, now: datetime | None = None, now_slug: str = "") -> int:
    """Post the day's reel. `now_slug` (from a manual run, Caesar's explicit ask) posts that queued
    video immediately and skips the daily slot rule; it still refuses anything already on Facebook."""
    now = now or datetime.now(timezone.utc)
    log = posted()
    for f in queue_folders():           # drop anything that is already on the Page
        if f.name in log:
            print(f"removing {f.name} from the Facebook queue: already on Facebook ({log[f.name]['reel_id']})")
            if not dry_run:
                shutil.rmtree(f)
    folders = [f for f in queue_folders() if f.name not in log]
    if not folders:
        print("Facebook queue is empty")
        return 0
    if now_slug:
        picked = [f for f in folders if f.name == now_slug]
        if not picked:
            print(f"{now_slug} is not waiting in the Facebook queue (or is already on Facebook); nothing posted")
            return 1
        folders, when, why = picked, now, "posted now on request"
    else:
        when, why = next_slot(now, log)
    print(f"Facebook queue: {len(folders)} waiting, next {folders[0].name}; {why}")
    if when is None or dry_run:
        return 0
    page, token = os.environ.get("FACEBOOK_PAGE_ID"), os.environ.get("FACEBOOK_PAGE_TOKEN")
    if not page or not token:
        print("FACEBOOK_PAGE_ID / FACEBOOK_PAGE_TOKEN secrets are missing; nothing posted")
        return 1
    f = folders[0]
    try:
        vid = post_reel(f, page, token, at=when if when > now else None)
    except Exception as e:   # noqa: BLE001  keep the folder so the next run retries it
        print(f"FAILED {f.name}: {type(e).__name__}: {str(e)[:300]}")
        return 1
    if when > now:
        print(f"scheduled {f.name} for {when.astimezone(TZ):%a %d %b %H:%M} Stockholm: https://www.facebook.com/reel/{vid}")
        log_post(f.name, vid, when, how="cloud queue, scheduled on Facebook")
    else:
        print(f"posted {f.name}: https://www.facebook.com/reel/{vid}")
        log_post(f.name, vid, now)
    shutil.rmtree(f)
    return 0


if __name__ == "__main__":
    sys.exit(run(dry_run="--dry-run" in sys.argv, now_slug=os.environ.get("FACEBOOK_POST_NOW", "").strip()))
