from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Email(BaseModel):
    id: str
    thread_id: Optional[str] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None
    subject: Optional[str] = None
    snippet: Optional[str] = None
    date_iso: Optional[str] = None


