# src/providers/openai_voice.py

from __future__ import annotations

import json
import logging
import os
from typing import Optional

"""
OpenAI integration for crafting a world-class *spoken* script
that ElevenLabs will voice. The model turns structured data
into a single, natural paragraph (no bullets) with:
- Greeting that addresses the user as GOAT (configurable)
- Clear mention of today's day/date in Europe/Oslo
- 24-hour times (e.g., 09:30)
- Grouped Notion tasks by Area (skips done)
- Short, tasteful humor and an original one-liner "quote"
- 30–70 seconds target read time
- Focus ONLY on today - no future references
If OpenAI isn't configured, falls back gracefully.
"""

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_TZ = os.getenv("TZ", "Europe/Oslo")
DEFAULT_NICKNAME = os.getenv("USER_NICKNAME", "GOAT")
VOICE_MIN_SECS = int(os.getenv("VOICE_MIN_SECS", "45"))
VOICE_MAX_SECS = int(os.getenv("VOICE_MAX_SECS", "70"))


def _openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # type: ignore
    except Exception:
        return None
    return OpenAI(api_key=api_key)


def rewrite_for_voice(
    summary_text: str,
    user_name: str = DEFAULT_NICKNAME,
    tz_label: str = DEFAULT_TZ,
    model: Optional[str] = None,
) -> str:
    """
    Quick pass to convert an existing textual summary into a spoken script.
    If OPENAI isn't available, returns the summary_text unchanged.
    """
    client = _openai_client()
    if not client:
        return summary_text

    model_id = model or DEFAULT_MODEL

    system = (
        "You are a world-class personal assistant crafting a short VOICE NOTE. "
        "Speak naturally, no bullet points, no section headers, no emoji. "
        "Address the user as GOAT. Use 24-hour times for Europe/Oslo. "
        "Aim for {min}-{max} seconds of spoken audio. Keep sentences short; "
        "vary rhythm with commas and brief pauses. Never read raw URLs; say 'Zoom link' or 'map link'. "
        "End with a single, original, witty one-liner (not a famous quote)."
    ).format(min=VOICE_MIN_SECS, max=VOICE_MAX_SECS)

    user_prompt = (
        f"User nickname: {user_name}\n"
        f"Timezone: {tz_label}\n"
        "Rewrite the following text as a natural spoken briefing (not a list):\n\n"
        + summary_text
    )

    try:
        resp = client.chat.completions.create(
            model=model_id,
            temperature=0.3,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content.strip() if resp.choices else summary_text
    except Exception as e:
        logger.error("OpenAI rewrite_for_voice failed: %s", e)
        return summary_text


def generate_voice_script(
    tz: str,
    user_name: str,
    today_events: list[dict],
    tasks_today: list[dict],
    emails: list[dict],
    slack_mentions: list[str],
    upcoming_events: list[dict],
    upcoming_tasks: list[dict],
    model: Optional[str] = None,
) -> str:
    """
    Primary generator: turns structured agenda + tasks + comms into
    a polished, human-sounding script tailored for ElevenLabs TTS.

    Expected keys (robust to missing fields):
      - Events: {title, start, end, location, link, all_day, source}
      - Tasks:  {title, area, due, priority, done, url}
      - Emails: {from, subject}
    """
    client = _openai_client()
    if not client:
        logger.warning("OPENAI_API_KEY not set; skipping voice script generation")
        return ""

    model_id = model or DEFAULT_MODEL
    nickname = DEFAULT_NICKNAME if not user_name else ("GOAT" if user_name.lower() == "oliver" else user_name)

    # SYSTEM PROMPT: style + constraints + “understanding”
    system = f"""
You are a world-class personal assistant creating a {VOICE_MIN_SECS}–{VOICE_MAX_SECS} second VOICE NOTE.
Speak to the user as “{nickname}”.

STYLE:
- Warm, crisp, competent; a hint of playful wit.
- Natural speech only: no headings, no bullets, no emoji, no dictation artifacts.
- 24-hour times for Europe/Oslo (e.g., 09:05, 16:30). Say the day and date up front.
- Don’t read raw URLs; say “Zoom link”, “calendar link”, or “location link”.
- End with ONE original, funny but tasteful one-liner (not a famous quote, 6–14 words).

INTELLIGENCE:
- CRITICAL: Group ALL Notion tasks by their Area property. Say "For [Area name], you have: [list tasks]". If area is null/empty, group those as "Other tasks: [list]".
- Do NOT mention dates for tasks due today - they're due TODAY, no need to say the date.
- Skip any tasks with done=true.
- Notice back-to-back events; suggest a travel/water/coffee buffer if sensible.
- Collapse noise: keep top 2–3 from Emails unless empty.
- If a section is empty, acknowledge briefly and move on.
- Prefer specifics that matter (time, title, who, where) over generic filler.
- DO NOT mention upcoming events or tasks - only focus on TODAY.

LENGTH:
- Target {VOICE_MIN_SECS}–{VOICE_MAX_SECS} seconds. Keep sentences short and flowing.
"""

    # USER PROMPT: pass structured JSON with gentle instructions
    user_payload = {
        "user_nickname": nickname,
        "timezone": tz or DEFAULT_TZ,
        "today_events": today_events,
        "tasks_today": tasks_today,
        "upcoming_events": upcoming_events,
        "upcoming_tasks": upcoming_tasks,
        "emails_top": emails,
        "slack_mentions_top": slack_mentions,
        "instructions": {
            "calendar": "Say 'Today you have…' then list briefly with 24-hour times and titles; include location/link only if useful.",
            "back_to_back": "If two events are adjacent or locations differ, suggest a short buffer.",
            "tasks": "MANDATORY: Group ALL tasks by their 'area' field. Say 'For [Area name], you have: [task 1], [task 2]'. If area is null/empty, say 'Other tasks: [list]'. Do NOT mention dates for tasks due today - they're due TODAY. Skip tasks with done=true. Never mention upcoming tasks or events.",
            "emails": "Name top 2–3 senders + brief subject gist.",
            "tone": "Natural voice, slight humor, never overdo it. Focus ONLY on today - no future references.",
        },
    }

    try:
        logger.info("Calling OpenAI to generate voice script with model %s", model_id)
        resp = client.chat.completions.create(
            model=model_id,
            temperature=0.35,
            messages=[
                {"role": "system", "content": system.strip()},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
            ],
        )
        if resp.choices and resp.choices[0].message.content:
            voice_text = resp.choices[0].message.content.strip()

            # Soft guardrail: if it looks way too long, lightly trim.
            # (ElevenLabs reads ~140–160 wpm; we aim ~120–180 words.)
            max_chars = int(os.getenv("VOICE_MAX_CHARS", "1200"))  # ~150–180 words
            if len(voice_text) > max_chars:
                # Keep opening and final one-liner; trim middle
                parts = voice_text.split(". ")
                head = ". ".join(parts[:6])  # ~ first 6 sentences
                tail = parts[-1] if parts else ""
                voice_text = f"{head}. … {tail}".strip(". ") + "."
            logger.info("OpenAI generated voice script (%d chars)", len(voice_text))
            return voice_text

        logger.error("OpenAI returned empty response for voice script")
        return ""
    except Exception as e:
        logger.error("OpenAI API call failed: %s", e)
        return ""
