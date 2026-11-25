from datetime import datetime, timezone

import pytest

from factory.autopilot.schedule import SLOT_HOURS, TZ, next_slots, rfc3339, videos_per_day


def utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


def test_four_a_day_slots_are_08_12_17_21_stockholm(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_VIDEOS_PER_DAY", raising=False)
    got = next_slots(utc(2026, 11, 25, 6, 0), 4)          # 07:00 Stockholm, before the first slot
    local = [d.astimezone(TZ).strftime("%H:%M") for d in got]
    assert local == ["08:00", "12:00", "17:00", "21:00"]
    assert all(d.astimezone(TZ).date().isoformat() == "2026-11-25" for d in got)


def test_next_slot_is_strictly_after_now():
    now = utc(2026, 11, 25, 7, 0)                          # exactly 08:00 Stockholm
    first = next_slots(now, 1, per_day=4)[0]
    assert first.astimezone(TZ).strftime("%H:%M") == "12:00"


def test_slots_roll_over_to_next_days_without_gaps():
    got = next_slots(utc(2026, 11, 25, 21, 30), 8, per_day=4)
    assert len(got) == 8 and got == sorted(got) and len(set(got)) == 8
    assert got[0].astimezone(TZ).day == 26 and got[0].astimezone(TZ).hour == 8


@pytest.mark.parametrize("per_day", sorted(SLOT_HOURS))
def test_each_rate_gives_that_many_slots_per_day(per_day):
    got = next_slots(utc(2026, 11, 25, 0, 0), per_day * 3, per_day=per_day)
    days = {d.astimezone(TZ).date() for d in got}
    assert len(days) == 3
    assert all(len([d for d in got if d.astimezone(TZ).date() == day]) == per_day for day in days)


def test_rate_comes_from_env_and_rejects_bad_values(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_VIDEOS_PER_DAY", "2")
    assert videos_per_day() == 2
    monkeypatch.setenv("AUTOPILOT_VIDEOS_PER_DAY", "7")
    with pytest.raises(ValueError):
        videos_per_day()
    monkeypatch.setenv("AUTOPILOT_VIDEOS_PER_DAY", "four")
    with pytest.raises(ValueError):
        videos_per_day()


def test_naive_datetime_is_refused():
    with pytest.raises(ValueError):
        next_slots(datetime(2026, 11, 25, 7, 0), 1, per_day=4)


def test_rfc3339_is_utc_z_format():
    assert rfc3339(utc(2026, 11, 25, 7, 0)) == "2026-11-25T07:00:00Z"
