from __future__ import annotations

from dataclasses import dataclass, field
from urllib import error, parse, request
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import Settings, get_settings
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


def _ingest_site_event_in_memory(event: SiteEventRecord) -> SiteEventIngestResponse:
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


def _supabase_headers(settings: Settings, *, prefer: str | None = None) -> dict[str, str]:
    if not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for site event persistence")

    headers = {
        "Content-Type": "application/json",
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _site_events_endpoint(settings: Settings) -> str:
    if not settings.supabase_url:
        raise RuntimeError("SUPABASE_URL is required for site event persistence")
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/site_events"


def _fetch_existing_site_event(event: SiteEventRecord, settings: Settings) -> dict | None:
    query = parse.urlencode(
        {
            "select": "id,event_name",
            "business_id": f"eq.{event.business_id}",
            "environment": f"eq.{event.environment}",
            "idempotency_key": f"eq.{event.idempotency_key}",
        }
    )
    req = request.Request(
        f"{_site_events_endpoint(settings)}?{query}",
        headers=_supabase_headers(settings),
        method="GET",
    )
    with request.urlopen(req, timeout=5) as response:
        rows = json.loads(response.read().decode("utf-8"))
    return rows[0] if rows else None


def _ingest_site_event_in_supabase(event: SiteEventRecord, settings: Settings) -> SiteEventIngestResponse:
    payload = json.dumps(
        [
            {
                "business_id": event.business_id,
                "environment": event.environment,
                "contact_id": None,
                "conversation_id": None,
                "visitor_id": event.visitor_id,
                "session_id": event.session_id,
                "event_name": event.event_name,
                "event_source": "website",
                "idempotency_key": event.idempotency_key,
                "payload": event.payload,
                "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
            }
        ]
    ).encode("utf-8")
    req = request.Request(
        f"{_site_events_endpoint(settings)}?select=id,event_name",
        data=payload,
        headers=_supabase_headers(settings, prefer="resolution=ignore-duplicates,return=representation"),
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=5) as response:
            rows = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:  # pragma: no cover - networked failure path
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Failed to persist site event: {detail}") from exc

    if rows:
        row = rows[0]
        return SiteEventIngestResponse(
            event_id=str(row["id"]),
            event_name=row["event_name"],
            deduped=False,
        )

    existing = _fetch_existing_site_event(event, settings)
    if existing is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Site event insert returned no row and no existing record was found")

    return SiteEventIngestResponse(
        event_id=str(existing["id"]),
        event_name=existing["event_name"],
        deduped=True,
    )


def ingest_site_event(event: SiteEventRecord) -> SiteEventIngestResponse:
    settings = get_settings()
    if settings.site_events_backend == "memory":
        return _ingest_site_event_in_memory(event)
    return _ingest_site_event_in_supabase(event, settings)


def list_ingested_site_events() -> list[SiteEventRecord]:
    return [
        _SITE_EVENTS.events_by_idempotency_key[key][1].model_copy(deep=True)
        for key in _SITE_EVENTS.ordered_keys
    ]


def reset_site_event_ingestion_state() -> None:
    _SITE_EVENTS.events_by_idempotency_key.clear()
    _SITE_EVENTS.ordered_keys.clear()
