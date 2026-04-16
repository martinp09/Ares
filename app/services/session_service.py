from __future__ import annotations

from app.db.agents import AgentsRepository
from app.db.sessions import SessionsRepository
from app.models.agents import AgentRevisionState
from app.models.sessions import SessionAppendEventRequest, SessionCreateRequest, SessionRecord
from app.services.compaction_service import CompactionService


class SessionService:
    def __init__(
        self,
        sessions_repository: SessionsRepository | None = None,
        agents_repository: AgentsRepository | None = None,
        compaction_service: CompactionService | None = None,
    ) -> None:
        self.sessions_repository = sessions_repository or SessionsRepository()
        self.agents_repository = agents_repository or AgentsRepository()
        self.compaction_service = compaction_service or CompactionService(self.sessions_repository)

    def create_session(self, request: SessionCreateRequest) -> SessionRecord:
        revision = self.agents_repository.get_revision(request.agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        if revision.state == AgentRevisionState.ARCHIVED:
            raise ValueError("Cannot create a session from an archived revision")
        return self.sessions_repository.create(
            agent_id=revision.agent_id,
            agent_revision_id=revision.id,
            business_id=request.business_id,
            environment=request.environment,
            initial_message=request.initial_message,
        )

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self.sessions_repository.get(session_id)

    def append_event(self, session_id: str, request: SessionAppendEventRequest) -> SessionRecord | None:
        return self.sessions_repository.append_event(
            session_id,
            event_type=request.event_type,
            payload=request.payload,
        )

    def append_turn_event(self, session_id: str, request: SessionAppendEventRequest) -> SessionRecord | None:
        return self.append_event(session_id, request)

    def get_session_journal(self, session_id: str):
        return self.compaction_service.get_session_journal(session_id)


session_service = SessionService()
