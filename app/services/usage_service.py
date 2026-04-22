from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.db.agents import AgentsRepository
from app.db.sessions import SessionsRepository
from app.db.usage import UsageRepository
from app.models.actors import ActorContext
from app.models.usage import UsageBucketRecord, UsageCreateRequest, UsageEventKind, UsageRecord, UsageResponse, UsageSummaryRecord


class UsageService:
    def __init__(
        self,
        usage_repository: UsageRepository | None = None,
        agents_repository: AgentsRepository | None = None,
        sessions_repository: SessionsRepository | None = None,
    ) -> None:
        self.usage_repository = usage_repository or UsageRepository()
        self.agents_repository = agents_repository or AgentsRepository()
        self.sessions_repository = sessions_repository or SessionsRepository()

    @staticmethod
    def _resolve_request_org_id(request_org_id: str | None, *, actor_org_id: str | None = None) -> str:
        if actor_org_id is None:
            return request_org_id or DEFAULT_INTERNAL_ORG_ID
        if request_org_id in (None, DEFAULT_INTERNAL_ORG_ID):
            return actor_org_id
        if request_org_id != actor_org_id:
            raise ValueError("Org id must match actor context")
        return actor_org_id

    @staticmethod
    def _resolve_list_org_id(request_org_id: str | None, *, actor_org_id: str | None = None) -> str | None:
        if actor_org_id is not None and request_org_id is not None and request_org_id != actor_org_id:
            raise ValueError("Org id must match actor context")
        return actor_org_id or request_org_id

    def _normalize_record_request(
        self,
        request: UsageCreateRequest,
        *,
        actor_context: ActorContext | None = None,
    ) -> UsageCreateRequest:
        org_id = self._resolve_request_org_id(
            request.org_id,
            actor_org_id=actor_context.org_id if actor_context is not None else None,
        )
        agent_id = request.agent_id
        agent_revision_id = request.agent_revision_id

        if agent_revision_id is not None:
            revision = self.agents_repository.get_revision(agent_revision_id)
            if revision is None:
                raise ValueError("Agent revision not found")
            agent = self.agents_repository.get_agent(revision.agent_id)
            if agent is None:
                raise ValueError("Owning agent not found")
            if agent_id is not None and agent_id != agent.id:
                raise ValueError("Agent id must match agent revision")
            if org_id != agent.org_id:
                raise ValueError("Org id must match agent revision org")
            agent_id = agent.id

        if request.session_id is not None:
            session = self.sessions_repository.get(request.session_id)
            if session is None:
                raise ValueError("Session not found")
            if org_id != session.org_id:
                raise ValueError("Org id must match session")
            if agent_revision_id is not None and agent_revision_id != session.agent_revision_id:
                raise ValueError("Agent revision id must match session")
            if agent_id is not None and agent_id != session.agent_id:
                raise ValueError("Agent id must match session")
            org_id = session.org_id
            agent_id = session.agent_id
            agent_revision_id = session.agent_revision_id

        return request.model_copy(
            update={
                "org_id": org_id,
                "agent_id": agent_id,
                "agent_revision_id": agent_revision_id,
                "metadata": self._scrub_sensitive_data(request.metadata),
            }
        )

    @staticmethod
    def _scrub_record(record: UsageRecord) -> UsageRecord:
        return record.model_copy(update={"metadata": UsageService._scrub_sensitive_data(record.metadata)})

    def record_usage(self, request: UsageCreateRequest, *, actor_context: ActorContext | None = None) -> UsageRecord:
        request = self._normalize_record_request(request, actor_context=actor_context)
        record = self.usage_repository.record(
            kind=request.kind,
            org_id=request.org_id,
            agent_id=request.agent_id,
            agent_revision_id=request.agent_revision_id,
            session_id=request.session_id,
            run_id=request.run_id,
            source_kind=request.source_kind,
            count=request.count,
            metadata=request.metadata,
        )
        return self._scrub_record(record)

    def list_usage(
        self,
        *,
        org_id: str | None = None,
        actor_org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        kind: UsageEventKind | None = None,
        source_kind: str | None = None,
        limit: int | None = None,
    ) -> UsageResponse:
        effective_org_id = self._resolve_list_org_id(org_id, actor_org_id=actor_org_id)
        all_events = self.usage_repository.list(
            org_id=effective_org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            session_id=session_id,
            run_id=run_id,
            kind=kind,
            source_kind=source_kind,
            limit=None,
        )
        events = all_events if limit is None else all_events[:limit]
        by_kind = Counter({event.kind.value: 0 for event in all_events})
        by_source: dict[str, int] = defaultdict(int)
        by_agent: dict[str, int] = defaultdict(int)
        source_last: dict[str, datetime] = {}
        agent_last: dict[str, datetime] = {}
        total = 0
        for event in all_events:
            by_kind[event.kind.value] += event.count
            total += event.count
            if event.source_kind is not None:
                by_source[event.source_kind] += event.count
                source_last[event.source_kind] = max(source_last.get(event.source_kind, event.created_at), event.created_at)
            if event.agent_id is not None:
                by_agent[event.agent_id] += event.count
                agent_last[event.agent_id] = max(agent_last.get(event.agent_id, event.created_at), event.created_at)

        return UsageResponse(
            org_id=effective_org_id or DEFAULT_INTERNAL_ORG_ID,
            agent_id=agent_id,
            summary=UsageSummaryRecord(
                total_count=total,
                by_kind=dict(sorted(by_kind.items())),
                by_source_kind=[
                    UsageBucketRecord(key=key, label=key, count=count, last_used_at=source_last.get(key))
                    for key, count in sorted(by_source.items())
                ],
                by_agent=[
                    UsageBucketRecord(key=key, label=key, count=count, last_used_at=agent_last.get(key))
                    for key, count in sorted(by_agent.items())
                ],
                updated_at=datetime.now(UTC),
            ),
            events=[self._scrub_record(event) for event in events],
        )

    @staticmethod
    def _scrub_sensitive_data(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: "[redacted]" if isinstance(key, str) and UsageService._looks_sensitive(key) else UsageService._scrub_sensitive_data(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [UsageService._scrub_sensitive_data(item) for item in value]
        if isinstance(value, tuple):
            return tuple(UsageService._scrub_sensitive_data(item) for item in value)
        return value

    @staticmethod
    def _looks_sensitive(key: str) -> bool:
        normalized = key.lower()
        markers = (
            "secret",
            "secretvalue",
            "token",
            "password",
            "passphrase",
            "apikey",
            "api_key",
            "clientsecret",
            "client_secret",
            "webhooksecret",
            "webhook_secret",
            "privatekey",
            "private_key",
            "authorization",
            "credential",
            "passwd",
            "authtoken",
            "access_token",
            "refresh_token",
        )
        return any(marker in normalized for marker in markers)


usage_service = UsageService()
