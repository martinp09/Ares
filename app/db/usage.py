from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.usage import UsageEventKind, UsageRecord


class UsageRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def record(
        self,
        *,
        kind: UsageEventKind,
        org_id: str,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        source_kind: str | None = None,
        count: int = 1,
        metadata: dict[str, object] | None = None,
        created_at=None,
    ) -> UsageRecord:
        record = UsageRecord(
            id=generate_id("usage"),
            kind=kind,
            org_id=org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            session_id=session_id,
            run_id=run_id,
            source_kind=source_kind,
            count=count,
            metadata=dict(metadata or {}),
            created_at=created_at or utc_now(),
        )
        with self.client.transaction() as store:
            store.usage_events[record.id] = record
        return record

    def list(
        self,
        *,
        org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        kind: UsageEventKind | None = None,
        source_kind: str | None = None,
        limit: int | None = None,
    ) -> list[UsageRecord]:
        with self.client.transaction() as store:
            events = list(store.usage_events.values())
        if org_id is not None:
            events = [event for event in events if event.org_id == org_id]
        if agent_id is not None:
            events = [event for event in events if event.agent_id == agent_id]
        if agent_revision_id is not None:
            events = [event for event in events if event.agent_revision_id == agent_revision_id]
        if session_id is not None:
            events = [event for event in events if event.session_id == session_id]
        if run_id is not None:
            events = [event for event in events if event.run_id == run_id]
        if kind is not None:
            events = [event for event in events if event.kind == kind]
        if source_kind is not None:
            events = [event for event in events if event.source_kind == source_kind]
        events.sort(key=lambda event: (event.created_at, event.id), reverse=True)
        if limit is not None:
            events = events[:limit]
        return events
