from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.audit import AuditRecord
from app.models.commands import generate_id


class AuditRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def append(
        self,
        *,
        event_type: str,
        summary: str,
        org_id: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
        metadata: dict[str, object] | None = None,
        created_at=None,
    ) -> AuditRecord:
        record = AuditRecord(
            id=generate_id("audit"),
            event_type=event_type,
            summary=summary,
            org_id=org_id,
            resource_type=resource_type,
            resource_id=resource_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            session_id=session_id,
            run_id=run_id,
            actor_id=actor_id,
            actor_type=actor_type,
            metadata=dict(metadata or {}),
            created_at=created_at or utc_now(),
        )
        with self.client.transaction() as store:
            store.audit_events[record.id] = record
        return record

    def list(
        self,
        *,
        org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AuditRecord]:
        with self.client.transaction() as store:
            events = list(store.audit_events.values())
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
        if resource_type is not None:
            events = [event for event in events if event.resource_type == resource_type]
        if resource_id is not None:
            events = [event for event in events if event.resource_id == resource_id]
        if event_type is not None:
            events = [event for event in events if event.event_type == event_type]
        events.sort(key=lambda event: (event.created_at, event.id), reverse=True)
        if limit is not None:
            events = events[:limit]
        return events
