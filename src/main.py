from __future__ import annotations

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from src.config import Settings
from src.models.calendar_models import CalendarEvent
from src.models.email_models import Email
from src.models.task_models import Task
from src.providers.google_client import get_events as cal_get_events
from src.providers.gmail_client import search_messages as gmail_search
from src.providers.notion_client import query_tasks as notion_query
from src.providers.slack_client import SlackClient
from src.summarizer import make_summary
from src.utils.dates import today_range_iso, weekday_name, pretty_time
from src.providers.google_auth import get_credentials
from src.providers.llm_openai import rewrite_for_voice, generate_voice_script


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("morning-brief-assistant")


def _safe_fetch_calendar(settings: Settings, start_iso: str, end_iso: str) -> List[CalendarEvent]:
    try:
        return cal_get_events(settings.google_calendar_id, start_iso, end_iso)
    except Exception as exc:  # noqa: BLE001
        logger.error("Calendar provider failed: %s", exc)
        return []


def _safe_fetch_gmail(settings: Settings) -> List[Email]:
    try:
        return gmail_search(settings.gmail_query, settings.important_senders, settings.gmail_max)
    except Exception as exc:  # noqa: BLE001
        logger.error("Gmail provider failed: %s", exc)
        return []


def _safe_fetch_notion(settings: Settings, today_start: str, today_end: str) -> Tuple[List[Task], List[Task], List[Task]]:
    try:
        if not settings.notion_api_key or not settings.notion_task_database_id:
            return [], [], []
        return notion_query(
            settings.notion_api_key,
            settings.notion_task_database_id,
            settings.tz,
            settings.days_ahead,
            today_start,
            today_end,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Notion provider failed: %s", exc)
        return [], [], []


def main() -> int:
    settings = Settings.load()
    slack = SlackClient(settings.slack_bot_token)

    today_start, today_end = today_range_iso(settings.tz)

    # Ensure Google credentials are created/refreshed once before any threaded calls
    try:
        get_credentials()
    except Exception as exc:  # noqa: BLE001
        logger.error("Google auth initialization failed: %s", exc)

    # Fetch concurrently where possible
    futures = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures[pool.submit(_safe_fetch_calendar, settings, today_start, today_end)] = "today_events"
        futures[pool.submit(_safe_fetch_gmail, settings)] = "emails"
        futures[pool.submit(_safe_fetch_notion, settings, today_start, today_end)] = "notion"

        results = {
            "today_events": [],
            "emails": [],
            "tasks_today": [],
        }
        for f in as_completed(futures):
            key = futures[f]
            try:
                val = f.result()
            except Exception as exc:  # noqa: BLE001
                logger.error("Fetch failed for %s: %s", key, exc)
                continue
            if key == "notion":
                t_today, _t_overdue, _t_upcoming = val
                results["tasks_today"] = t_today
            else:
                results[key] = val

    summary = make_summary(
        tz=settings.tz,
        today_events=results["today_events"],
        tasks_today=results["tasks_today"],
        emails=results["emails"],
    )

    print(summary)

    posted = False
    if settings.slack_user_id:
        posted = slack.post_dm(settings.slack_user_id, summary)
    if not posted and settings.slack_fallback_channel:
        posted = slack.post_channel(settings.slack_fallback_channel, summary)
    # Try ElevenLabs TTS and upload audio, but do not fail the run if it breaks
    try:
        from pathlib import Path
        from src.providers.tts_elevenlabs import ElevenTTS

        # If OPENAI_API_KEY is present, generate a warmer voice script from structured data
        voice_text = None
        if settings.openai_api_key:
            # Prepare structured data for the LLM - EXCLUDE done tasks
            today_events_llm = [
                {
                    "title": e.title,
                    "time": ("All day" if e.all_day else pretty_time(e.start_iso, settings.tz)),
                    "weekday": ("" if e.all_day else weekday_name(e.start_iso, settings.tz)),
                    "location": e.location,
                    "link": e.meeting_link,
                }
                for e in results["today_events"]
            ]
            # Filter out done tasks BEFORE sending to LLM
            tasks_today_llm = [
                {"name": t.name, "area": t.area}
                for t in results["tasks_today"]
                if not t.done
            ]
            # Log area distribution for debugging
            area_counts = {}
            for t in tasks_today_llm:
                area = t.get("area") or "None"
                area_counts[area] = area_counts.get(area, 0) + 1
            logger.info("Tasks by area for LLM: %s", area_counts)
            emails_llm = [
                {"from": (e.from_name or e.from_email or ""), "subject": (e.subject or "")}
                for e in results["emails"][:3]
            ]
            logger.info("Generating voice script with OpenAI (today events: %d, tasks: %d, emails: %d)", len(today_events_llm), len(tasks_today_llm), len(emails_llm))
            voice_text = generate_voice_script(
                tz=settings.tz,
                user_name="Oliver",
                today_events=today_events_llm,
                tasks_today=tasks_today_llm,
                emails=emails_llm,
                slack_mentions=[],  # Slack mentions removed - we're posting to Slack anyway
                upcoming_events=[],
                upcoming_tasks=[],
            )
            if not voice_text:
                logger.warning("OpenAI voice script generation returned empty, falling back to rewrite_for_voice")
                voice_text = rewrite_for_voice(summary, user_name="Oliver", tz_label=settings.tz)
            else:
                logger.info("Using OpenAI-generated voice script for ElevenLabs")
        else:
            logger.info("OPENAI_API_KEY not set, using rewrite_for_voice fallback")
            voice_text = rewrite_for_voice(summary, user_name="Oliver", tz_label=settings.tz)
        tts = ElevenTTS(mock=settings.mock_elevenlabs)
        outfile = Path("out/audio/daily-brief.mp3")
        tts.synth(voice_text, outfile)
        if settings.slack_user_id:
            slack.upload_dm_file(
                settings.slack_user_id,
                str(outfile),
                title="Daily Brief (Audio)",
                initial_comment="🔊 Here’s your morning audio summary.",
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ElevenLabs TTS failed: %s", exc)

    if not posted:
        logger.error("Failed to post summary to Slack")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())


