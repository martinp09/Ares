from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id
from app.models.site_events import SiteEventRecord


class SiteEventIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted"] = "accepted"
    event_id: str = Field(min_length=1)
    event_name: str = Field(min_length=1)


_SITE_EVENTS: list[SiteEventRecord] = []


def ingest_site_event(event: SiteEventRecord) -> SiteEventIngestResponse:
    _SITE_EVENTS.append(event.model_copy(deep=True))
    return SiteEventIngestResponse(
        event_id=generate_id("siteevt"),
        event_name=event.event_name,
    )


def list_ingested_site_events() -> list[SiteEventRecord]:
    return [event.model_copy(deep=True) for event in _SITE_EVENTS]


def reset_site_event_ingestion_state() -> None:
    _SITE_EVENTS.clear()
