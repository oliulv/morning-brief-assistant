from __future__ import annotations

from datetime import datetime, timedelta
from typing import Tuple

import pytz


def get_timezone(tz_name: str) -> pytz.BaseTzInfo:
    return pytz.timezone(tz_name)


def today_range_iso(tz_name: str) -> Tuple[str, str]:
    tz = get_timezone(tz_name)
    now = datetime.now(tz)
    start = tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def next_n_days_range_iso(tz_name: str, days: int) -> Tuple[str, str]:
    tz = get_timezone(tz_name)
    now = datetime.now(tz)
    start = tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
    end = start + timedelta(days=days)
    return start.isoformat(), end.isoformat()


def pretty_day_header(tz_name: str) -> str:
    tz = get_timezone(tz_name)
    now = datetime.now(tz)
    # Example: Mon 3 Nov
    return now.strftime("%a %-d %b") if hasattr(now, "strftime") else now.strftime("%a %d %b")


def pretty_time(dt_iso: str, tz_name: str) -> str:
    tz = get_timezone(tz_name)
    dt = datetime.fromisoformat(dt_iso)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    return dt.astimezone(tz).strftime("%H:%M")


def weekday_name(dt_iso: str, tz_name: str) -> str:
    tz = get_timezone(tz_name)
    dt = datetime.fromisoformat(dt_iso)
    if dt.tzinfo is None:
        dt = tz.localize(dt)
    return dt.astimezone(tz).strftime("%A")


