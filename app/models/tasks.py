from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskRecord(BaseModel):
    id: str
    run_id: str
    title: str
    status: TaskStatus
    created_at: datetime
