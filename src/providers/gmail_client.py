from __future__ import annotations

import logging
import os
from typing import List

from googleapiclient.discovery import build

from src.models.email_models import Email
from src.config import Settings
from src.providers.google_auth import get_credentials


logger = logging.getLogger(__name__)


def search_messages(query: str, important_senders: List[str], max_results: int) -> List[Email]:
    """
    Fetch emails by query, deduplicate by thread_id (one message per thread),
    then apply importance filtering and return top N threads.
    """
    try:
        creds = get_credentials()
        service = build("gmail", "v1", credentials=creds)
        # Fetch more messages to account for thread deduplication
        resp = service.users().messages().list(userId="me", q=query, maxResults=max_results * 10).execute()
        message_ids = [m["id"] for m in resp.get("messages", [])]
        logger.info("Gmail: matched %d messages for query %s", len(message_ids), query)
        if not message_ids:
            logger.warning("Gmail returned 0 messages. Retrying with broader query newer_than:7d (diagnostic)")
            resp = service.users().messages().list(userId="me", q="newer_than:7d", maxResults=max_results * 10).execute()
            message_ids = [m["id"] for m in resp.get("messages", [])]
        
        # Fetch all message metadata
        emails: List[Email] = []
        message_metadata = {}  # id -> metadata dict
        for mid in message_ids:
            try:
                msg = service.users().messages().get(userId="me", id=mid, format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
                headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
                from_header = headers.get("from", "")
                subject = headers.get("subject", "") or "(No subject)"
                date_iso = headers.get("date")
                snippet = (msg.get("snippet") or "").strip()
                from_name = None
                from_email = None
                if "<" in from_header and ">" in from_header:
                    name_part = from_header.split("<")[0].strip().strip('"')
                    email_part = from_header.split("<")[1].split(">")[0].strip()
                    from_name = name_part or None
                    from_email = email_part or None
                else:
                    from_email = from_header or None
                
                thread_id = msg.get("threadId")
                internal_date = msg.get("internalDate")  # Use internalDate for sorting (timestamp)
                
                email_obj = Email(
                    id=mid,
                    thread_id=thread_id,
                    from_name=from_name,
                    from_email=from_email,
                    subject=subject,
                    snippet=snippet,
                    date_iso=date_iso,
                )
                emails.append(email_obj)
                message_metadata[mid] = {
                    "email": email_obj,
                    "internal_date": int(internal_date) if internal_date else 0,
                    "labels": msg.get("labelIds", []),
                }
            except Exception as e:
                logger.warning("Failed to fetch message %s: %s", mid, e)
                continue

        # Deduplicate by thread_id - keep only the most recent message per thread
        thread_to_email: dict[str, Email] = {}
        thread_to_metadata: dict[str, dict] = {}
        for mid, metadata in message_metadata.items():
            email_obj = metadata["email"]
            thread_id = email_obj.thread_id or mid  # Fallback to message ID if no thread
            internal_date = metadata["internal_date"]
            
            # Keep the most recent message per thread
            if thread_id not in thread_to_metadata or internal_date > thread_to_metadata[thread_id]["internal_date"]:
                thread_to_email[thread_id] = email_obj
                thread_to_metadata[thread_id] = metadata
        
        # Now work with unique threads
        unique_threads = list(thread_to_email.values())
        logger.info("Gmail: %d unique threads after deduplication (from %d messages)", len(unique_threads), len(emails))

        # Importance heuristic - apply to thread representatives
        # Only filter if important_senders is configured (non-empty list)
        important: List[Email] = []
        has_important_senders = important_senders and len(important_senders) > 0
        logger.debug("Gmail importance filter: important_senders=%s, has_important_senders=%s", important_senders, has_important_senders)
        
        if has_important_senders:
            senders = {s.lower() for s in important_senders}
            important = [e for e in unique_threads if (e.from_email or "").lower() in senders]
            logger.info("Gmail: %d threads from important senders", len(important))
            # If no important senders matched, fall through to use all threads (don't filter by IMPORTANT)
        
        # If no importance filter matched OR no important_senders configured, use ALL threads
        if not important:
            important = unique_threads
            if has_important_senders:
                logger.info("Gmail: Using all %d threads (important senders configured but none matched)", len(important))
            else:
                logger.info("Gmail: Using all %d threads (no importance filter configured)", len(important))
        
        # Return top N threads (sorted by date, most recent first)
        # Sort by internal date from metadata
        def get_internal_date(email: Email) -> int:
            thread_id = email.thread_id or email.id
            return thread_to_metadata.get(thread_id, {}).get("internal_date", 0)
        
        sorted_important = sorted(
            important,
            key=get_internal_date,
            reverse=True
        )
        
        result = sorted_important[:max_results]
        logger.info("Gmail: returning %d threads (max_results=%d)", len(result), max_results)
        return result
    except Exception as exc:  # noqa: BLE001
        logger.error("Gmail fetch failed: %s", exc)
        return []


