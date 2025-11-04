from __future__ import annotations

from typing import List

from src.providers.slack_client import SlackClient


def fetch_recent_mentions_snippets(slack: SlackClient, user_id: str, hours: int = 24, max_items: int = 3) -> List[str]:
    mentions = slack.get_recent_mentions(user_id=user_id, hours=hours)
    lines: List[str] = []
    for m in mentions[:max_items]:
        who = m.get("user") or "someone"
        channel = m.get("channel") or "DM"
        text = (m.get("text") or "").replace("\n", " ").strip()
        lines.append(f"{who} in {channel} — {text}")
    return lines


