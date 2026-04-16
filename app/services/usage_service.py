from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime

from app.db.usage import UsageRepository
from app.models.usage import UsageBucketRecord, UsageCreateRequest, UsageEventKind, UsageRecord, UsageResponse, UsageSummaryRecord


class UsageService:
    def __init__(self, usage_repository: UsageRepository | None = None) -> None:
        self.usage_repository = usage_repository or UsageRepository()

    def record_usage(self, request: UsageCreateRequest) -> UsageRecord:
        return self.usage_repository.record(
            kind=request.kind,
            org_id=request.org_id,
            agent_id=request.agent_id,
            agent_revision_id=request.agent_revision_id,
            source_kind=request.source_kind,
            count=request.count,
            metadata=request.metadata,
        )

    def list_usage(
        self,
        *,
        org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        kind: UsageEventKind | None = None,
        source_kind: str | None = None,
        limit: int | None = None,
    ) -> UsageResponse:
        all_events = self.usage_repository.list(
            org_id=org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
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
            org_id=org_id or "org_internal",
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
            events=[event.model_copy(update={"metadata": self._scrub_sensitive_data(event.metadata)}) for event in events],
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
