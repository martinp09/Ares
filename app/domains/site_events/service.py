from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.commands import generate_id
from app.models.site_events import SiteEventRecord


class SiteEventIngestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted"] = "accepted"
    event_id: str = Field(min_length=1)
    event_name: str = Field(min_length=1)
    deduped: bool = False


@dataclass
class SiteEventStore:
    events_by_idempotency_key: dict[str, tuple[str, SiteEventRecord]] = field(default_factory=dict)
    ordered_keys: list[str] = field(default_factory=list)


_SITE_EVENTS = SiteEventStore()


def ingest_site_event(event: SiteEventRecord) -> SiteEventIngestResponse:
    existing = _SITE_EVENTS.events_by_idempotency_key.get(event.idempotency_key)
    if existing is not None:
        event_id, stored_event = existing
        return SiteEventIngestResponse(
            event_id=event_id,
            event_name=stored_event.event_name,
            deduped=True,
        )

    event_id = generate_id("siteevt")
    _SITE_EVENTS.events_by_idempotency_key[event.idempotency_key] = (event_id, event.model_copy(deep=True))
    _SITE_EVENTS.ordered_keys.append(event.idempotency_key)
    return SiteEventIngestResponse(
        event_id=event_id,
        event_name=event.event_name,
    )


def list_ingested_site_events() -> list[SiteEventRecord]:
    return [
        _SITE_EVENTS.events_by_idempotency_key[key][1].model_copy(deep=True)
        for key in _SITE_EVENTS.ordered_keys
    ]


def reset_site_event_ingestion_state() -> None:
    _SITE_EVENTS.events_by_idempotency_key.clear()
    _SITE_EVENTS.ordered_keys.clear()
