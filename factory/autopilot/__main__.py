"""python -m factory.autopilot ledger list|check|add|status ...  (no PC or credentials needed)"""
from __future__ import annotations

import argparse
import json
import sys

from .ledger import Ledger, Topic, slugify


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="factory.autopilot")
    sub = p.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("schedule", help="next posting slots at the configured rate (AUTOPILOT_VIDEOS_PER_DAY)")
    sc.add_argument("--count", type=int, default=4)
    sc.add_argument("--per-day", type=int, default=None, help="override the rate for this call only")
    lg = sub.add_parser("ledger", help="the topic ledger")
    ls = lg.add_subparsers(dest="action", required=True)
    l1 = ls.add_parser("list"); l1.add_argument("--status")
    for name in ("check", "add"):
        c = ls.add_parser(name)
        c.add_argument("core_claim")
        c.add_argument("--title", default="")
        c.add_argument("--area", default="")
        c.add_argument("--keywords", default="", help="comma separated")
        c.add_argument("--follows", default="")
        c.add_argument("--id", default="")
        c.add_argument("--status", default="idea")
    st = ls.add_parser("status"); st.add_argument("id"); st.add_argument("status"); st.add_argument("--reason", default="")
    a = p.parse_args(argv)
    if a.cmd == "schedule":
        from datetime import datetime, timezone
        from .schedule import TZ, next_slots, rfc3339, videos_per_day
        per_day = a.per_day or videos_per_day()
        for dt in next_slots(datetime.now(timezone.utc), a.count, per_day):
            print(rfc3339(dt), dt.astimezone(TZ).strftime("%a %H:%M Stockholm"))
        return 0
    led = Ledger()
    if a.action == "list":
        for t in led.topics().values():
            if not a.status or t.status == a.status:
                print(f"{t.status:13} {t.id:32} {t.title or t.core_claim}")
        return 0
    if a.action == "status":
        print(json.dumps(led.set_status(a.id, a.status, a.reason).__dict__, ensure_ascii=False))
        return 0
    t = Topic(id=a.id or slugify(a.title or a.core_claim), core_claim=a.core_claim, title=a.title, area=a.area,
              keywords=[k.strip() for k in a.keywords.split(",") if k.strip()], follows=a.follows, status=a.status)
    res = led.check(t) if a.action == "check" else led.add(t)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 1 if res["verdict"] == "duplicate" else 0


if __name__ == "__main__":
    sys.exit(main())
