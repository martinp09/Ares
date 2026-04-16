from __future__ import annotations

from app.db.client import ControlPlaneClient
from app.db.sessions import SessionsRepository
from app.db.turn_events import TurnEventsRepository
from app.models.providers import ProviderCapability
from app.models.turns import TurnEventRecord, TurnRecord, TurnResumeRequest, TurnStartRequest
from app.models.sessions import SessionTimelineEntry
from app.services.compaction_service import CompactionService
from app.services.permission_service import PermissionService
from app.services.session_service import SessionService


class TurnRunnerService:
    def __init__(
        self,
        sessions_repository: SessionsRepository | None = None,
        turn_events_repository: TurnEventsRepository | None = None,
        session_service: SessionService | None = None,
        compaction_service: CompactionService | None = None,
        permission_service: PermissionService | None = None,
        client: ControlPlaneClient | None = None,
    ) -> None:
        self.sessions_repository = sessions_repository or SessionsRepository(client)
        self.turn_events_repository = turn_events_repository or TurnEventsRepository(client)
        self.session_service = session_service or SessionService(self.sessions_repository, None)
        self.compaction_service = compaction_service or CompactionService(self.sessions_repository, self.turn_events_repository)
        self.permission_service = permission_service or PermissionService()

    def start_turn(self, session_id: str, request: TurnStartRequest) -> TurnRecord:
        session = self.session_service.get_session(session_id)
        if session is None:
            raise ValueError("Session not found")
        if request.tool_calls and not self.permission_service.has_revision_capability(
            session.agent_revision_id, ProviderCapability.TOOL_CALLS
        ):
            raise ValueError("Agent revision does not support tool calls")
        turn, _ = self.turn_events_repository.create_turn(
            session_id=session_id,
            agent_id=session.agent_id,
            agent_revision_id=session.agent_revision_id,
            request=request,
            on_event=lambda event: self._append_session_timeline_event(session_id, event),
        )
        self.compaction_service.refresh_session_summary(session_id)
        return turn

    def resume_turn(self, session_id: str, turn_id: str, request: TurnResumeRequest) -> TurnRecord:
        session = self.session_service.get_session(session_id)
        if session is None:
            raise ValueError("Session not found")
        turn = self.turn_events_repository.get_turn(turn_id)
        if turn is None:
            raise ValueError("Turn not found")
        if turn.session_id != session_id:
            raise ValueError("Turn does not belong to session")
        if request.tool_results and not self.permission_service.has_revision_capability(
            session.agent_revision_id, ProviderCapability.TOOL_CALLS
        ):
            raise ValueError("Agent revision does not support tool calls")
        resumed_turn, _ = self.turn_events_repository.resume_turn(
            turn_id,
            request,
            on_event=lambda event: self._append_session_timeline_event(session_id, event),
        )
        self.compaction_service.refresh_session_summary(session_id)
        return resumed_turn

    def get_turn(self, turn_id: str) -> TurnRecord | None:
        return self.turn_events_repository.get_turn(turn_id)

    def get_turn_events(self, turn_id: str) -> list[TurnEventRecord]:
        return self.turn_events_repository.get_turn_events(turn_id)

    def replay_turn(self, turn_id: str) -> TurnRecord | None:
        return self.turn_events_repository.replay_turn(turn_id)

    def _append_session_timeline_event(self, session_id: str, event: TurnEventRecord) -> None:
        with self.sessions_repository.client.transaction() as store:
            session = store.sessions.get(session_id)
            if session is None:
                raise ValueError("Session not found")
            session.timeline.append(
                SessionTimelineEntry(
                    id=event.id,
                    event_type=event.event_type.value,
                    payload={"turn_id": event.turn_id, **event.payload},
                    created_at=event.created_at,
                )
            )
            session.updated_at = event.created_at
            store.sessions[session_id] = session


turn_runner_service = TurnRunnerService()
