from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    mcp_server_url: str

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
    def _strip_env(key: str, default: str | None = None) -> str | None:
        """Get env var and strip whitespace/newlines (common issue with GitHub secrets)."""
        val = os.getenv(key)
        if val is None:
            return default
        stripped = val.strip()
        return stripped if stripped else default

    @staticmethod
    def load() -> "Settings":
        mcp_server_url = Settings._strip_env("MCP_SERVER_URL")
        if not mcp_server_url:
            raise ValueError("MCP_SERVER_URL environment variable is required")

        slack_bot_token = Settings._strip_env("SLACK_BOT_TOKEN")
        slack_user_id = Settings._strip_env("SLACK_USER_ID")
        slack_fallback_channel = Settings._strip_env("SLACK_FALLBACK_CHANNEL")

        notion_api_key = Settings._strip_env("NOTION_API_KEY")
        notion_task_database_id = Settings._strip_env("NOTION_TASK_DATABASE_ID")

        google_calendar_id = Settings._strip_env("GOOGLE_CALENDAR_ID") or "primary"
        google_oauth_client_id = Settings._strip_env("GOOGLE_OAUTH_CLIENT_ID")
        google_oauth_client_secret = Settings._strip_env("GOOGLE_OAUTH_CLIENT_SECRET")

        gmail_query = Settings._strip_env("GMAIL_QUERY") or "label:INBOX newer_than:1d"
        important_senders_str = Settings._strip_env("IMPORTANT_SENDERS") or ""
        important_senders = [s.strip() for s in important_senders_str.split(",") if s.strip()]
        gmail_max_str = Settings._strip_env("GMAIL_MAX") or "5"
        try:
            gmail_max = int(gmail_max_str)
        except ValueError:
            gmail_max = 5

        days_ahead_str = Settings._strip_env("DAYS_AHEAD") or "14"
        try:
            days_ahead = int(days_ahead_str)
        except ValueError:
            days_ahead = 14
        tz = Settings._strip_env("TZ") or "Europe/Oslo"

        openai_api_key = Settings._strip_env("OPENAI_API_KEY")
        elevenlabs_api_key = Settings._strip_env("ELEVENLABS_API_KEY")
        elevenlabs_voice_id = Settings._strip_env("ELEVENLABS_VOICE_ID")
        elevenlabs_model_id = Settings._strip_env("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2"
        mock_elevenlabs = (Settings._strip_env("MOCK_ELEVENLABS") or "false").lower() in {"1", "true", "yes"}
        debug_providers = (Settings._strip_env("DEBUG_PROVIDERS") or "false").lower() in {"1", "true", "yes"}

        return Settings(
            mcp_server_url=mcp_server_url,
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


