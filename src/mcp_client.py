from __future__ import annotations

import json
import logging
from typing import List, Dict, Any, Optional
import httpx

from src.models.calendar_models import CalendarEvent
from src.models.email_models import Email
from src.models.task_models import Task

logger = logging.getLogger(__name__)


class MCPClient:
    """HTTP client for Vercel-hosted MCP server."""

    def __init__(self, server_url: str, timeout: int = 60):
        """
        Initialize MCP client.

        Args:
            server_url: Base URL of the Vercel MCP server (e.g., https://your-server.vercel.app/api/mcp)
            timeout: Request timeout in seconds
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool via HTTP."""
        try:
            response = self.client.post(
                self.server_url,
                json={
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise RuntimeError(f"MCP server error: {data['error']}")
            return data.get("result", {})
        except httpx.HTTPError as e:
            logger.error("MCP HTTP error: %s", e)
            raise
        except Exception as e:
            logger.error("MCP call failed: %s", e)
            raise

    def _extract_text_content(self, result: Dict[str, Any]) -> str:
        """Extract text content from MCP result."""
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "text":
                return item.get("text", "")
        return ""

    def _extract_data_content(self, result: Dict[str, Any]) -> tuple[bytes, str]:
        """Extract binary data content from MCP result."""
        content = result.get("content", [])
        for item in content:
            if item.get("type") == "data":
                import base64
                data = base64.b64decode(item.get("data", ""))
                mime_type = item.get("mimeType", "application/octet-stream")
                return data, mime_type
        raise ValueError("No data content found in MCP result")

    def get_calendar_events(
        self, calendar_id: str, time_min: str, time_max: str
    ) -> List[CalendarEvent]:
        """Fetch calendar events from Google Calendar."""
        result = self._call_tool(
            "get_calendar_events",
            {
                "calendar_id": calendar_id,
                "time_min": time_min,
                "time_max": time_max,
            },
        )
        text = self._extract_text_content(result)
        events_data = json.loads(text)
        return [CalendarEvent(**event) for event in events_data]

    def get_gmail_messages(
        self, query: str, important_senders: List[str], max_results: int
    ) -> List[Email]:
        """Search and fetch Gmail messages."""
        result = self._call_tool(
            "get_gmail_messages",
            {
                "query": query,
                "important_senders": important_senders,
                "max_results": max_results,
            },
        )
        text = self._extract_text_content(result)
        emails_data = json.loads(text)
        return [Email(**email) for email in emails_data]

    def get_notion_tasks(
        self,
        api_key: str,
        database_id: str,
        today_start_iso: str,
        today_end_iso: str,
        days_ahead: int,
        tz: str,
    ) -> tuple[List[Task], List[Task], List[Task]]:
        """Query Notion tasks (returns today, overdue, upcoming)."""
        result = self._call_tool(
            "get_notion_tasks",
            {
                "api_key": api_key,
                "database_id": database_id,
                "today_start_iso": today_start_iso,
                "today_end_iso": today_end_iso,
                "days_ahead": days_ahead,
                "tz": tz,
            },
        )
        text = self._extract_text_content(result)
        tasks_data = json.loads(text)
        today = [Task(**task) for task in tasks_data.get("today", [])]
        overdue = [Task(**task) for task in tasks_data.get("overdue", [])]
        upcoming = [Task(**task) for task in tasks_data.get("upcoming", [])]
        return today, overdue, upcoming

    def generate_voice_script(
        self,
        tz: str,
        user_name: str,
        today_events: List[Dict[str, Any]],
        tasks_today: List[Dict[str, Any]],
        emails: List[Dict[str, Any]],
    ) -> str:
        """Generate voice script using OpenAI."""
        result = self._call_tool(
            "generate_voice_script",
            {
                "tz": tz,
                "user_name": user_name,
                "today_events": today_events,
                "tasks_today": tasks_today,
                "emails": emails,
            },
        )
        return self._extract_text_content(result)

    def synthesize_speech(
        self, text: str, voice_id: Optional[str] = None, model_id: Optional[str] = None
    ) -> bytes:
        """Synthesize speech using ElevenLabs. Returns MP3 audio bytes."""
        result = self._call_tool(
            "synthesize_speech",
            {
                "text": text,
                "voice_id": voice_id,
                "model_id": model_id,
            },
        )
        audio_data, _ = self._extract_data_content(result)
        return audio_data

    def post_to_slack(
        self, user_id: Optional[str] = None, channel: Optional[str] = None, text: str = ""
    ) -> bool:
        """Post a message to Slack."""
        result = self._call_tool(
            "post_to_slack",
            {
                "user_id": user_id,
                "channel": channel,
                "text": text,
            },
        )
        text_content = self._extract_text_content(result)
        result_data = json.loads(text_content)
        return result_data.get("success", False)

    def upload_file_to_slack(
        self,
        user_id: str,
        file_path: str,
        title: str,
        initial_comment: Optional[str] = None,
    ) -> bool:
        """Upload a file to Slack."""
        import base64
        from pathlib import Path

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path_obj, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")

        result = self._call_tool(
            "upload_file_to_slack",
            {
                "user_id": user_id,
                "file_data": file_data,
                "filename": file_path_obj.name,
                "title": title,
                "initial_comment": initial_comment,
            },
        )
        text_content = self._extract_text_content(result)
        result_data = json.loads(text_content)
        return result_data.get("success", False)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

