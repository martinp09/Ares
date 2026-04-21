from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.session_journal import SessionCompactionState, SessionMemorySummary
from app.models.sessions import SessionRecord, SessionStatus, SessionTimelineEntry


class SessionsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        agent_id: str,
        agent_revision_id: str,
        org_id: str,
        business_id: str,
        environment: str,
        initial_message: str | None = None,
    ) -> SessionRecord:
        now = utc_now()
        timeline = [
            SessionTimelineEntry(
                id=generate_id("sev"),
                event_type="session_created",
                payload={"agent_revision_id": agent_revision_id},
                created_at=now,
            )
        ]
        if initial_message:
            timeline.append(
                SessionTimelineEntry(
                    id=generate_id("sev"),
                    event_type="message",
                    payload={"role": "operator", "message": initial_message},
                    created_at=now,
                )
            )

        session = SessionRecord(
            id=generate_id("ses"),
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            org_id=org_id,
            business_id=business_id,
            environment=environment,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            timeline=timeline,
        )
        with self.client.transaction() as store:
            store.sessions[session.id] = session
        return session

    def get(self, session_id: str) -> SessionRecord | None:
        with self.client.transaction() as store:
            return store.sessions.get(session_id)

    def get_memory_summary(self, session_id: str) -> SessionMemorySummary | None:
        with self.client.transaction() as store:
            summary = store.session_memory_summaries.get(session_id)
            return deepcopy(summary) if summary is not None else None

    def upsert_memory_summary(self, summary: SessionMemorySummary) -> SessionMemorySummary:
        with self.client.transaction() as store:
            session = store.sessions.get(summary.session_id)
            if session is None:
                raise ValueError("Session not found")
            stored_summary = summary.model_copy(deep=True)
            store.session_memory_summaries[summary.session_id] = stored_summary
            session.compaction = SessionCompactionState(
                summary_version=stored_summary.summary_version,
                compacted_turn_count=stored_summary.compacted_turn_count,
                compacted_through_turn_id=stored_summary.compacted_through_turn_id,
                compacted_through_turn_number=stored_summary.compacted_through_turn_number,
                source_event_count=stored_summary.source_event_count,
                last_compacted_at=stored_summary.updated_at,
            )
            session.updated_at = stored_summary.updated_at
            store.sessions[summary.session_id] = session
            return stored_summary

    def append_event(self, session_id: str, *, event_type: str, payload: dict | None = None) -> SessionRecord | None:
        with self.client.transaction() as store:
            session = store.sessions.get(session_id)
            if session is None:
                return None
            event = SessionTimelineEntry(
                id=generate_id("sev"),
                event_type=event_type,
                payload=payload or {},
                created_at=utc_now(),
            )
            session.timeline.append(event)
            session.updated_at = event.created_at
            store.sessions[session_id] = session
            return session

    def append_timeline_entry(self, session_id: str, entry: SessionTimelineEntry) -> SessionRecord | None:
        with self.client.transaction() as store:
            session = store.sessions.get(session_id)
            if session is None:
                return None
            session.timeline.append(entry.model_copy(deep=True))
            session.updated_at = entry.created_at
            store.sessions[session_id] = session
            return session
