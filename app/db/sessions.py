from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.db.client import ControlPlaneClient, SupabaseControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.sessions import SessionRecord, SessionStatus, SessionTimelineEntry


def session_event_from_row(row: Mapping[str, Any]) -> SessionTimelineEntry:
    raw_payload = row.get("payload")
    payload = dict(raw_payload) if isinstance(raw_payload, Mapping) else {}
    return SessionTimelineEntry(
        id=str(row.get("runtime_id") or row["id"]),
        event_type=str(row["event_type"]),
        payload=payload,
        created_at=row["created_at"],
    )


def session_record_from_row(row: Mapping[str, Any], timeline: list[SessionTimelineEntry]) -> SessionRecord:
    return SessionRecord(
        id=str(row.get("runtime_id") or row["id"]),
        agent_id=str(row["agent_id"]),
        agent_revision_id=str(row["agent_revision_id"]),
        business_id=str(row["business_id"]),
        environment=str(row["environment"]),
        status=SessionStatus(str(row["status"])),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        timeline=timeline,
    )


class SessionsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def _select_supabase_timeline(self, session_id: str) -> list[SessionTimelineEntry]:
        rows = self._supabase_client().select(
            "agent_session_events",
            columns="id,runtime_id,session_runtime_id,event_type,payload,created_at",
            filters={"session_runtime_id": session_id},
            order="created_at.asc",
        )
        return [session_event_from_row(row) for row in rows]

    def _select_supabase_session(self, session_id: str) -> SessionRecord | None:
        rows = self._supabase_client().select(
            "agent_sessions",
            columns="id,runtime_id,agent_id,agent_revision_id,business_id,environment,status,created_at,updated_at",
            filters={"runtime_id": session_id},
            limit=1,
        )
        if not rows:
            return None
        timeline = self._select_supabase_timeline(session_id)
        return session_record_from_row(rows[0], timeline)

    def create(
        self,
        *,
        agent_id: str,
        agent_revision_id: str,
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
            business_id=business_id,
            environment=environment,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            timeline=timeline,
        )

        if self._is_supabase():
            session_rows = self._supabase_client().insert(
                "agent_sessions",
                rows=[
                    {
                        "runtime_id": session.id,
                        "agent_id": session.agent_id,
                        "agent_revision_id": session.agent_revision_id,
                        "business_id": session.business_id,
                        "environment": session.environment,
                        "status": session.status.value,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    }
                ],
                columns="id,runtime_id,agent_id,agent_revision_id,business_id,environment,status,created_at,updated_at",
            )
            if not session_rows:
                raise RuntimeError("Supabase session insert failed without returning a row")

            event_rows = self._supabase_client().insert(
                "agent_session_events",
                rows=[
                    {
                        "runtime_id": entry.id,
                        "session_runtime_id": session.id,
                        "event_type": entry.event_type,
                        "payload": entry.payload,
                        "created_at": entry.created_at.isoformat(),
                    }
                    for entry in timeline
                ],
                columns="id,runtime_id,session_runtime_id,event_type,payload,created_at",
            )
            if not event_rows:
                raise RuntimeError(f"Supabase session event insert failed for runtime_id '{session.id}'")

            loaded = self._select_supabase_session(session.id)
            if loaded is None:
                raise RuntimeError(f"Supabase session load failed for runtime_id '{session.id}' after insert")
            return loaded

        with self.client.transaction() as store:
            store.sessions[session.id] = session
        return session

    def get(self, session_id: str) -> SessionRecord | None:
        if self._is_supabase():
            return self._select_supabase_session(session_id)
        with self.client.transaction() as store:
            return store.sessions.get(session_id)

    def append_event(self, session_id: str, *, event_type: str, payload: dict | None = None) -> SessionRecord | None:
        if self._is_supabase():
            session = self._select_supabase_session(session_id)
            if session is None:
                return None

            event = SessionTimelineEntry(
                id=generate_id("sev"),
                event_type=event_type,
                payload=payload or {},
                created_at=utc_now(),
            )
            event_rows = self._supabase_client().insert(
                "agent_session_events",
                rows=[
                    {
                        "runtime_id": event.id,
                        "session_runtime_id": session_id,
                        "event_type": event.event_type,
                        "payload": event.payload,
                        "created_at": event.created_at.isoformat(),
                    }
                ],
                columns="id,runtime_id,session_runtime_id,event_type,payload,created_at",
            )
            if not event_rows:
                raise RuntimeError(f"Supabase session event append failed for runtime_id '{session_id}'")

            updated_rows = self._supabase_client().update(
                "agent_sessions",
                values={"updated_at": event.created_at.isoformat()},
                filters={"runtime_id": session_id},
                columns=(
                    "id,runtime_id,agent_id,agent_revision_id,business_id,environment,status,created_at,updated_at"
                ),
            )
            if not updated_rows:
                raise RuntimeError(f"Supabase session update failed for runtime_id '{session_id}'")

            return self._select_supabase_session(session_id)

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
