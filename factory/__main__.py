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
"""
from __future__ import annotations

import argparse
import logging
import sys

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
    args = p.parse_args(argv)
    _logging()

    from .database import DB
    db = DB()
    if args.cmd == "produce":
        from .production import produce
        res = produce(args.slug, db=db, provider=args.tts, previews=args.previews, force=args.force)
        print(f"\n{'QC PASSED' if res['qc_passed'] else 'QC FAILED'}: {res['video']} ({res['duration']:.1f}s) "
              f"timings={res['timings']}")
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
        if args.cmd == "qa-gate" and verdict["state"] == "READY_FOR_RELEASE" and row and row["state"] == "QC_FAILED":
            from .production import sha256_file
            if row["video_sha256"] == sha256_file(video):
                db.transition(sb.slug, "QUALITY_CHECKED", note=f"release gate passed, score {verdict['score']}")
        return 0 if verdict["state"] == "READY_FOR_RELEASE" else 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
