"""Post every approved platform entry. Never called from the production workflow.

For each `posts` row in APPROVED:
  1. reload out/<slug>/publish/package.json and recompute the platform hash from the files on disk,
  2. require it to equal the hash the human approved,
  3. claim the row (APPROVED -> POSTING, atomic, so a double click or two bots can't post twice),
  4. upload, then mark POSTED with the remote id, or FAILED with the error.
"""
from __future__ import annotations

import importlib
import logging

from ..database import DB
from . import approvals, package
from .platforms import NotConfigured

log = logging.getLogger("factory.publishing")


def uploader(platform: str):
    return importlib.import_module(f"factory.publishing.platforms.{platform}")


def publish_one(db: DB, slug: str, platform: str, uploaders: dict | None = None) -> dict:
    row = approvals.get(db, slug, platform)
    if row is None or row["status"] != "APPROVED":
        return {"slug": slug, "platform": platform, "ok": False, "error": "not approved"}
    try:
        pkg = package.load_package(slug)
        h = package.verify(pkg, platform)
        if h != row["approved_hash"]:
            raise ValueError("the package changed after it was approved")
    except Exception as e:   # noqa: BLE001
        approvals.failed(db, slug, platform, f"refused before upload: {e}")
        return {"slug": slug, "platform": platform, "ok": False, "error": str(e)}
    if not approvals.claim(db, slug, platform):
        return {"slug": slug, "platform": platform, "ok": False, "error": "already being posted"}
    mod = (uploaders or {}).get(platform) or uploader(platform)
    try:
        rid, url = mod.post(pkg)
    except NotConfigured as e:
        approvals.failed(db, slug, platform, str(e))
        return {"slug": slug, "platform": platform, "ok": False, "error": str(e), "setup_needed": True}
    except Exception as e:   # noqa: BLE001
        log.exception("%s/%s upload failed", slug, platform)
        approvals.failed(db, slug, platform, f"{type(e).__name__}: {e}")
        return {"slug": slug, "platform": platform, "ok": False,
                "error": f"{e}. Check the platform before approving again, in case it went through."}
    approvals.posted(db, slug, platform, str(rid), url)
    log.info("%s live on %s: %s", slug, platform, url)
    return {"slug": slug, "platform": platform, "ok": True, "id": rid, "url": url}


def publish_approved(db: DB, uploaders: dict | None = None) -> list[dict]:
    approvals.init(db)
    return [publish_one(db, r["slug"], r["platform"], uploaders) for r in approvals.rows(db, status="APPROVED")]
