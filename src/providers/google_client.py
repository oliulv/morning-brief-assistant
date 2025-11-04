from __future__ import annotations

import json
import logging
import os
from typing import List
from googleapiclient.discovery import build

from src.models.calendar_models import CalendarEvent
from src.config import Settings
from src.providers.google_auth import get_credentials


logger = logging.getLogger(__name__)


def get_events(calendar_id: str, time_min: str, time_max: str) -> List[CalendarEvent]:
    try:
        creds = get_credentials()
        service = build("calendar", "v3", credentials=creds)
        events_result = (
            service.events()
            .list(calendarId=calendar_id, timeMin=time_min, timeMax=time_max, singleEvents=True, orderBy="startTime")
            .execute()
        )
        items = events_result.get("items", [])
        logger.info("Calendar fetched %d events between %s and %s for calendar %s", len(items), time_min, time_max, calendar_id)
        if not items:
            logger.warning("Calendar returned 0 events. Consider verifying GOOGLE_CALENDAR_ID and timezone window.")
        results: List[CalendarEvent] = []
        for e in items:
            start = e.get("start", {})
            end = e.get("end", {})
            start_iso = start.get("dateTime") or (start.get("date") + "T00:00:00")
            end_iso = end.get("dateTime") or (end.get("date") + "T00:00:00")
            all_day = "date" in start or "date" in end
            location = e.get("location")
            meeting_link = None
            # Try to detect common conferencing links
            hangout_link = e.get("hangoutLink")
            if hangout_link:
                meeting_link = hangout_link
            else:
                conference = e.get("conferenceData", {}).get("entryPoints", [])
                for ep in conference:
                    if ep.get("uri"):
                        meeting_link = ep["uri"]
                        break
            results.append(
                CalendarEvent(
                    id=e.get("id", ""),
                    title=e.get("summary", "(No title)"),
                    start_iso=start_iso,
                    end_iso=end_iso,
                    all_day=all_day,
                    location=location,
                    meeting_link=meeting_link,
                )
            )
        return results
    except Exception as exc:  # noqa: BLE001
        logger.error("Calendar fetch failed: %s", exc)
        return []


