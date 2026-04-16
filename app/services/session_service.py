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

    def create_session(self, request: SessionCreateRequest, *, org_id: str | None = None) -> SessionRecord:
        revision = self.agents_repository.get_revision(request.agent_revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        agent = self.agents_repository.get_agent(revision.agent_id)
        effective_org_id = org_id or request.org_id
        if agent is None or agent.org_id != effective_org_id:
            raise ValueError("Agent revision not found")
        if revision.state == AgentRevisionState.ARCHIVED:
            raise ValueError("Cannot create a session from an archived revision")
        if revision.state != AgentRevisionState.PUBLISHED:
            raise ValueError("Cannot create a session from an unpublished revision")
        if request.business_id != agent.business_id or request.environment != agent.environment:
            raise ValueError("Session scope must match the owning agent scope")
        return self.sessions_repository.create(
            agent_id=revision.agent_id,
            agent_revision_id=revision.id,
            org_id=effective_org_id,
            business_id=agent.business_id,
            environment=agent.environment,
            initial_message=request.initial_message,
        )

    def get_session(self, session_id: str, *, org_id: str | None = None) -> SessionRecord | None:
        session = self.sessions_repository.get(session_id)
        if session is None or (org_id is not None and session.org_id != org_id):
            return None
        return session

    def append_event(self, session_id: str, request: SessionAppendEventRequest, *, org_id: str | None = None) -> SessionRecord | None:
        session = self.get_session(session_id, org_id=org_id)
        if session is None:
            return None
        return self.sessions_repository.append_event(
            session_id,
            event_type=request.event_type,
            payload=request.payload,
        )

    def append_turn_event(self, session_id: str, request: SessionAppendEventRequest, *, org_id: str | None = None) -> SessionRecord | None:
        return self.append_event(session_id, request, org_id=org_id)

    def get_session_journal(self, session_id: str, *, org_id: str | None = None):
        session = self.get_session(session_id, org_id=org_id)
        if session is None:
            return None
        return self.compaction_service.get_session_journal(session_id)


session_service = SessionService()
