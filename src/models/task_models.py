from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class Task(BaseModel):
    id: str
    name: str
    due_iso: Optional[str] = None
    area: Optional[str] = None
    done: Optional[bool] = None
    url: Optional[str] = None


