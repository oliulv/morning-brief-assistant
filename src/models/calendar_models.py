from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    id: str
    title: str
    start_iso: str
    end_iso: str
    all_day: bool = Field(default=False)
    location: Optional[str] = None
    meeting_link: Optional[str] = None


