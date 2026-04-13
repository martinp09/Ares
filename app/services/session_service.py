from __future__ import annotations

from app.db.agents import AgentsRepository
from app.db.sessions import SessionsRepository
from app.models.agents import AgentRevisionState
from app.models.sessions import SessionAppendEventRequest, SessionCreateRequest, SessionRecord


class SessionService:
    def __init__(
        self,
        sessions_repository: SessionsRepository | None = None,
        agents_repository: AgentsRepository | None = None,
    ) -> None:
        self.sessions_repository = sessions_repository or SessionsRepository()
        self.agents_repository = agents_repository or AgentsRepository()

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


session_service = SessionService()
