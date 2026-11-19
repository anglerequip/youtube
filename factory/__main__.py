"""Command line.

  python -m factory produce <slug> [--previews] [--force] [--tts kokoro|elevenlabs]
  python -m factory status                show every video and its state
  python -m factory history <slug>        state changes for one video
  python -m factory qc <slug>             re-run quality checks on an existing render
  python -m factory qa <slug> [--video f] [--no-inspect]
                                          all QA layers + release gate on an existing render
                                          (writes out/<slug>/qa/report.md and the review packet)
  python -m factory qa-gate <slug>        re-run the gate once an independent critique.json exists;
                                          moves QC_FAILED -> QUALITY_CHECKED only if it now passes

Publishing (separate workflow, docs/PUBLISHING.md). A package is built automatically when a video
passes QA. Nothing posts without Caesar tapping Post for that platform, on a Post/Skip card in the
project chat (default) or in Telegram (optional).
  python -m factory package <slug> [--video f] [--send]   build out/<slug>/publish/ (title, captions, cover)
  python -m factory review <slug>         send the package to Telegram for approval
  python -m factory bot [--once]          handle Approve / Skip / edits from Telegram and post approved items
  python -m factory publish               retry posting rows already approved (hash re-checked)
  python -m factory posts [<slug>]        per-platform status
  python -m factory publish-auth youtube|tiktok   one-time sign-in
  python -m factory publish-check         test each platform's credentials (posts nothing)
  python -m factory post <slug> <platform> --hash H --by WHO
                                          post one platform after Caesar tapped Post on the card showing hash H
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# Windows Python defaults to cp1252 for text files, which cannot write "≈" or "°" (crashed the review
# packet on Caesar's PC). Re-run in UTF-8 mode once, so every read_text/write_text is UTF-8 everywhere.
if os.name == "nt" and not sys.flags.utf8_mode and __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", "-m", "factory", *sys.argv[1:]]))

from .configuration import settings


def _logging():
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.data_dir / "factory.log", encoding="utf-8"),
    ])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="factory")
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("produce", help="render and quality-check one storyboard")
    pr.add_argument("slug")
    pr.add_argument("--previews", action="store_true", help="save a PNG every 2s to out/<slug>/previews")
    pr.add_argument("--force", action="store_true", help="ignore cached voice/visual steps")
    pr.add_argument("--tts", default=None)
    sub.add_parser("status")
    h = sub.add_parser("history")
    h.add_argument("slug")
    q = sub.add_parser("qc")
    q.add_argument("slug")
    qa_ = sub.add_parser("qa")
    qa_.add_argument("slug")
    qa_.add_argument("--video", default=None)
    qa_.add_argument("--no-inspect", action="store_true")
    qg = sub.add_parser("qa-gate")
    qg.add_argument("slug")
    pk = sub.add_parser("package")
    pk.add_argument("slug")
    pk.add_argument("--video", default=None)
    pk.add_argument("--send", action="store_true")
    rv = sub.add_parser("review")
    rv.add_argument("slug")
    bt = sub.add_parser("bot")
    bt.add_argument("--once", action="store_true")
    sub.add_parser("publish")
    ps = sub.add_parser("posts")
    ps.add_argument("slug", nargs="?")
    pa = sub.add_parser("publish-auth")
    pa.add_argument("platform", choices=["youtube", "tiktok"])
    sub.add_parser("publish-check")
    po = sub.add_parser("post", help="approve one platform for the exact package Caesar tapped Post on, then post it")
    po.add_argument("slug")
    po.add_argument("platform", choices=["youtube", "tiktok", "facebook"])
    po.add_argument("--hash", required=True, help="the 8+ character package hash shown on the approval card")
    po.add_argument("--by", required=True, help="who approved, e.g. 'Caesar via project chat card'")
    args = p.parse_args(argv)
    _logging()

    from .database import DB
    db = DB()
    if args.cmd == "produce":
        from .production import produce
        res = produce(args.slug, db=db, provider=args.tts, previews=args.previews, force=args.force)
        print(f"\n{'QC PASSED' if res['qc_passed'] else 'QC FAILED'}: {res['video']} ({res['duration']:.1f}s) "
              f"timings={res['timings']}")
        if res["qc_passed"]:
            _auto_package(db, args.slug)
        return 0 if res["qc_passed"] else 2
    if args.cmd == "status":
        for r in db.conn.execute("SELECT slug, state, duration_s, youtube_id, updated_at FROM videos ORDER BY slug"):
            yt = f" https://youtu.be/{r['youtube_id']}" if r["youtube_id"] else ""
            print(f"{r['state']:<18} {r['slug']:<30} {r['duration_s'] or 0:5.1f}s  {r['updated_at']}{yt}")
        return 0
    if args.cmd == "history":
        for r in db.history(args.slug):
            print(f"{r['at']}  {r['from_state'] or '-':<18} -> {r['to_state']:<18} {(r['note'] or '')[:80]}")
        return 0
    if args.cmd == "qc":
        from . import quality_control
        from .storyboard_engine import load
        sb = load(args.slug)
        Sim = sb.load_sim_class()
        passed, checks = quality_control.run_all(sb, Sim.self_checks() if hasattr(Sim, "self_checks") else None)
        print(quality_control.summarize(checks))
        return 0 if passed else 2
    if args.cmd in ("qa", "qa-gate"):
        from pathlib import Path
        from . import qa
        from .storyboard_engine import load
        sb = load(args.slug)
        video = Path(getattr(args, "video", None) or sb.final_video)
        verdict, rep, _ = qa.run(sb, video, inspect=not getattr(args, "no_inspect", False))
        print(rep.with_suffix(".md").read_text())
        row = db.get(sb.slug) if hasattr(db, "get") else None
        ok = verdict["state"] == "READY_FOR_RELEASE" or verdict["verdict"] == "deliver"
        if args.cmd == "qa-gate" and ok and row and row["state"] == "QC_FAILED":
            from .production import sha256_file
            if row["video_sha256"] == sha256_file(video):
                note = (f"release gate passed, score {verdict['score']}" if verdict["verdict"] == "approve" else
                        f"review round cap reached (round {verdict['review_round']}), score {verdict['score']}, "
                        f"{verdict['blockers']} blocker(s): for Caesar to decide")
                db.transition(sb.slug, "QUALITY_CHECKED", note=note)
                _auto_package(db, sb.slug)
        return 0 if ok else 2
    if args.cmd in ("package", "review", "bot", "publish", "posts", "publish-auth", "publish-check", "post"):
        return _publishing(db, args)
    return 1


def _auto_package(db, slug: str) -> None:
    """After QA passes: build the publishing package and, if Telegram is set up, send it for review.
    This never posts anything."""
    import os
    try:
        from .publishing import approvals, package
        pkg = package.build(slug)
        approvals.register(db, pkg)
        print(f"Publishing package: {settings.out_dir / slug / 'publish' / 'review.md'}")
        if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
            from .publishing import telegram
            telegram.send_review(db, slug)
            print("Sent to Telegram for approval.")
    except Exception as e:   # noqa: BLE001  packaging must never break production
        logging.getLogger("factory").warning("publishing package not built for %s: %s", slug, e)


def _publishing(db, args) -> int:
    from .publishing import PLATFORMS, approvals, package, publisher, telegram
    approvals.init(db)
    if args.cmd == "package":
        pkg = package.build(args.slug, video=args.video)
        approvals.register(db, pkg)
        print((settings.out_dir / args.slug / "publish" / "review.md").read_text(encoding="utf-8"))
        if args.send:
            telegram.send_review(db, args.slug)
            print("Sent to Telegram for approval.")
        return 0 if pkg["ok"] else 2
    if args.cmd == "review":
        telegram.send_review(db, args.slug)
        print("Sent to Telegram for approval.")
        return 0
    if args.cmd == "bot":
        print("Listening to Telegram. Ctrl+C to stop." if not args.once else "Handling waiting Telegram updates.")
        telegram.poll(db, once=args.once)
        return 0
    if args.cmd == "publish":
        res = publisher.publish_approved(db)
        for r in res:
            print(f"{r['slug']:<28} {r['platform']:<9} {'LIVE ' + str(r.get('url')) if r['ok'] else 'NOT POSTED: ' + r['error']}")
        return 0 if all(r["ok"] for r in res) else 2
    if args.cmd == "posts":
        for r in approvals.rows(db, slug=args.slug):
            print(f"{r['slug']:<28} {r['platform']:<9} {r['status']:<10} {r['remote_url'] or r['last_error'] or ''}")
        return 0
    if args.cmd == "post":
        # Only run this after Caesar tapped "Post" for this platform on an approval card that showed
        # this exact hash. The hash ties the approval to the video, cover and text Caesar saw.
        approvals.register(db, package.load_package(args.slug))
        try:
            approvals.approve(db, args.slug, args.platform, args.hash, by=args.by)
        except Exception as e:   # noqa: BLE001
            print(f"NOT APPROVED: {e}")
            return 2
        r = publisher.publish_one(db, args.slug, args.platform)
        print(f"LIVE {r['url']}" if r["ok"] else f"NOT POSTED: {r['error']}")
        return 0 if r["ok"] else 2
    if args.cmd == "publish-auth":
        print(publisher.uploader(args.platform).authorize())
        return 0
    if args.cmd == "publish-check":
        ok = True
        for p in PLATFORMS:
            try:
                print(publisher.uploader(p).check())
            except Exception as e:   # noqa: BLE001
                ok = False
                print(f"{p}: NOT READY: {e}")
        try:
            telegram.Telegram().call("getMe")
            print("Telegram: bot token works")
        except Exception as e:   # noqa: BLE001
            ok = False
            print(f"telegram: NOT READY: {e}")
        return 0 if ok else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
