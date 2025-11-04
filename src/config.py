from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    slack_bot_token: Optional[str]
    slack_user_id: Optional[str]
    slack_fallback_channel: Optional[str]

    notion_api_key: Optional[str]
    notion_task_database_id: Optional[str]

    google_calendar_id: str
    google_oauth_client_id: Optional[str]
    google_oauth_client_secret: Optional[str]

    gmail_query: str
    important_senders: List[str]
    gmail_max: int

    days_ahead: int
    tz: str

    openai_api_key: Optional[str]
    elevenlabs_api_key: Optional[str]
    elevenlabs_voice_id: Optional[str]
    elevenlabs_model_id: Optional[str]
    mock_elevenlabs: bool
    debug_providers: bool

    @staticmethod
    def load() -> "Settings":
        slack_bot_token = os.getenv("SLACK_BOT_TOKEN")
        slack_user_id = os.getenv("SLACK_USER_ID")
        slack_fallback_channel = os.getenv("SLACK_FALLBACK_CHANNEL")

        notion_api_key = os.getenv("NOTION_API_KEY")
        notion_task_database_id = os.getenv("NOTION_TASK_DATABASE_ID")

        google_calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        google_oauth_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        google_oauth_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

        gmail_query = os.getenv("GMAIL_QUERY", "label:INBOX newer_than:1d")
        important_senders_str = os.getenv("IMPORTANT_SENDERS", "")
        important_senders = [s.strip() for s in important_senders_str.split(",") if s.strip()]
        gmail_max = int(os.getenv("GMAIL_MAX", "5"))

        days_ahead = int(os.getenv("DAYS_AHEAD", "14"))
        tz = os.getenv("TZ", "Europe/Oslo")

        openai_api_key = os.getenv("OPENAI_API_KEY")
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        elevenlabs_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
        elevenlabs_model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
        mock_elevenlabs = os.getenv("MOCK_ELEVENLABS", "false").lower() in {"1", "true", "yes"}
        debug_providers = os.getenv("DEBUG_PROVIDERS", "false").lower() in {"1", "true", "yes"}

        return Settings(
            slack_bot_token=slack_bot_token,
            slack_user_id=slack_user_id,
            slack_fallback_channel=slack_fallback_channel,
            notion_api_key=notion_api_key,
            notion_task_database_id=notion_task_database_id,
            google_calendar_id=google_calendar_id,
            google_oauth_client_id=google_oauth_client_id,
            google_oauth_client_secret=google_oauth_client_secret,
            gmail_query=gmail_query,
            important_senders=important_senders,
            gmail_max=gmail_max,
            days_ahead=days_ahead,
            tz=tz,
            openai_api_key=openai_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            elevenlabs_voice_id=elevenlabs_voice_id,
            elevenlabs_model_id=elevenlabs_model_id,
            mock_elevenlabs=mock_elevenlabs,
            debug_providers=debug_providers,
        )


