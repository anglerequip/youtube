"""Posting slots for the autopilot: how many videos a day, and when they go out.

Caesar (2026-11-20): four videos a day, fully hands-free. The rate is one setting, so it can be
changed without touching code (AUTOPILOT_VIDEOS_PER_DAY=2 or 3 or 4). Slot times are Stockholm local
time, converted to UTC for YouTube's publishAt.

    python -m factory.autopilot schedule --count 8           # next 8 slots at the configured rate
    AUTOPILOT_VIDEOS_PER_DAY=2 python -m factory.autopilot schedule --count 4
"""
from __future__ import annotations

import os
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Stockholm")
DEFAULT_PER_DAY = 4

# Local (Stockholm) posting hours for each daily rate. Four a day: 08, 12, 17, 21 (Caesar's standing plan).
SLOT_HOURS: dict[int, tuple[int, ...]] = {
    1: (12,),
    2: (12, 20),
    3: (10, 16, 21),
    4: (8, 12, 17, 21),
}


def videos_per_day() -> int:
    """The configured rate. Anything not in SLOT_HOURS falls back to the default with a clear error."""
    raw = os.environ.get("AUTOPILOT_VIDEOS_PER_DAY", str(DEFAULT_PER_DAY)).strip()
    try:
        n = int(raw)
    except ValueError as e:
        raise ValueError(f"AUTOPILOT_VIDEOS_PER_DAY must be a whole number, got {raw!r}") from e
    if n not in SLOT_HOURS:
        raise ValueError(f"AUTOPILOT_VIDEOS_PER_DAY must be one of {sorted(SLOT_HOURS)}, got {n}")
    return n


def next_slots(after: datetime, count: int, per_day: int | None = None) -> list[datetime]:
    """The next `count` posting slots strictly after `after` (an aware datetime), as UTC datetimes."""
    if after.tzinfo is None:
        raise ValueError("after must be timezone-aware")
    hours = SLOT_HOURS[per_day or videos_per_day()]
    local = after.astimezone(TZ)
    day = local.date()
    out: list[datetime] = []
    while len(out) < count:
        for h in hours:
            slot = datetime.combine(day, time(h, 0), tzinfo=TZ).astimezone(timezone.utc)
            if slot > after and (not out or slot > out[-1]):
                out.append(slot)
                if len(out) == count:
                    break
        day += timedelta(days=1)
    return out


def rfc3339(dt: datetime) -> str:
    """YouTube publishAt format: 2026-11-25T08:00:00Z."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
