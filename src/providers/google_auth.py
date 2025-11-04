from __future__ import annotations

import os
from pathlib import Path
from typing import List

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import logging

logger = logging.getLogger(__name__)


SCOPES: List[str] = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_credentials() -> Credentials:
    # Allow overriding token location via env; default to repo root cwd
    token_path = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
    token_path = str(Path(token_path))
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Require a Desktop application client (Installed App) config
            if not os.path.exists("client_secret.json"):
                raise RuntimeError(
                    "Missing client_secret.json. Create a Google OAuth 'Desktop app' client and place client_secret.json in repo root."
                )
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Ensure directory exists
        Path(token_path).parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, "w") as token:
            token.write(creds.to_json())
        logger.info("Google token saved to %s", token_path)
    return creds


