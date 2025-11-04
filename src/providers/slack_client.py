from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict
import os

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self, token: str | None):
        self.token = token
        self.client = WebClient(token=token) if token else None

    def _ensure_dm_channel(self, user_id: str) -> str | None:
        if not self.client:
            return None
        im = self.client.conversations_open(users=[user_id])
        return im["channel"]["id"]

    def post_dm(self, user_id: str, text: str) -> bool:
        if not self.client:
            logger.warning("Slack client not configured")
            return False
        try:
            channel_id = self._ensure_dm_channel(user_id)
            self.client.chat_postMessage(channel=channel_id, text=text)
            return True
        except SlackApiError as e:
            logger.error("Slack DM failed: %s", e)
            return False

    def post_channel(self, channel: str, text: str) -> bool:
        if not self.client:
            logger.warning("Slack client not configured")
            return False
        try:
            self.client.chat_postMessage(channel=channel, text=text)
            return True
        except SlackApiError as e:
            logger.error("Slack channel post failed: %s", e)
            return False

    def get_recent_mentions(self, user_id: str, hours: int = 24) -> List[Dict]:
        if not self.client:
            return []
        try:
            cutoff_ts = (datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp()
            results: List[Dict] = []
            types = ["im", "mpim", "public_channel", "private_channel"]
            for conv_type in types:
                cursor = None
                while True:
                    resp = self.client.conversations_list(Types=conv_type, cursor=cursor, limit=200)
                    channels = resp.get("channels", [])
                    for ch in channels:
                        chan_id = ch.get("id")
                        try:
                            hist_cursor = None
                            while True:
                                hist = self.client.conversations_history(channel=chan_id, cursor=hist_cursor, oldest=cutoff_ts, limit=200)
                                for m in hist.get("messages", []):
                                    text = m.get("text", "") or ""
                                    if f"<@{user_id}>" in text:
                                        results.append({
                                            "channel": ch.get("name") or chan_id,
                                            "text": text,
                                            "user": m.get("user"),
                                        })
                                hist_cursor = hist.get("response_metadata", {}).get("next_cursor")
                                if not hist_cursor:
                                    break
                        except SlackApiError:
                            continue
                    cursor = resp.get("response_metadata", {}).get("next_cursor")
                    if not cursor:
                        break
            return results[:10]
        except SlackApiError as e:
            logger.warning("Slack mentions fetch failed: %s", e)
            return []

    def upload_dm_file(self, user_id: str, file_path: str, title: str, initial_comment: str | None = None) -> bool:
        if not self.client:
            logger.warning("Slack client not configured")
            return False
        try:
            channel_id = self._ensure_dm_channel(user_id)
            with open(file_path, "rb") as f:
                self.client.files_upload_v2(
                    channel=channel_id,
                    file=f,
                    title=title,
                    initial_comment=initial_comment or "",
                    filename=os.path.basename(file_path),
                )
            return True
        except SlackApiError as e:
            logger.error("Slack file upload failed: %s", e)
            return False


