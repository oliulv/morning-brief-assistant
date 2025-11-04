from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple

from src.models.calendar_models import CalendarEvent
from src.models.email_models import Email
from src.models.task_models import Task
from src.utils.dates import pretty_day_header, pretty_time
from src.utils.formatting import section


def _events_lines(events: List[CalendarEvent], tz: str) -> List[str]:
    lines: List[str] = []
    # Back-to-back detection
    events_sorted = sorted(events, key=lambda e: e.start_iso)
    for idx, e in enumerate(events_sorted):
        if e.all_day:
            start_str = "All day"
        else:
            start_str = pretty_time(e.start_iso, tz)
        loc_part = e.location or e.meeting_link
        loc = f" → {loc_part}" if loc_part else ""
        lines.append(f"{start_str} → {e.title}{loc}")
        if idx > 0 and not e.all_day:
            # simplistic back-to-back hint
            prev_end = events_sorted[idx - 1].end_iso
            if prev_end and pretty_time(prev_end, tz) == start_str:
                lines[-1] += " (back-to-back — plan travel buffer)"
    return lines


def _tasks_lines(today: List[Task], overdue: List[Task], max_today: int = 5, max_overdue: int = 3) -> Tuple[List[str], List[str]]:
    def fmt(t: Task) -> str:
        area = f" ({t.area})" if t.area else ""
        return f"{t.name}{area}"

    t_lines = [fmt(t) for t in today[:max_today]]
    o_lines = [fmt(t) for t in overdue[:max_overdue]]
    return t_lines, o_lines


def _emails_lines(emails: List[Email], max_items: int = 3) -> List[str]:
    lines = []
    for e in emails[:max_items]:
        who = e.from_name or e.from_email or "Unknown"
        subject = e.subject or "(No subject)"
        lines.append(f"{who} — {subject}")
    return lines


def _slack_lines(mentions: List[str], max_items: int = 3) -> List[str]:
    return mentions[:max_items]


def make_summary(
    tz: str,
    today_events: List[CalendarEvent],
    tasks_today: List[Task],
    emails: List[Email],
) -> str:
    header = f"Good morning, Oliver — {pretty_day_header(tz)}"

    today_sec = section("🗓️ Today", _events_lines(today_events, tz))
    tasks_today_lines, _ = _tasks_lines(tasks_today, [])
    tasks_today_sec = section("🧰 Tasks Today", tasks_today_lines)
    inbox_sec = section("📥 Inbox Today", _emails_lines(emails))

    parts = [header, "", today_sec, "", tasks_today_sec, "", inbox_sec]
    return "\n".join(p for p in parts if p is not None)


