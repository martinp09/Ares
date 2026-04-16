from __future__ import annotations

from app.db.audit import AuditRepository
from app.models.audit import AuditAppendRequest, AuditRecord


class AuditService:
    def __init__(self, audit_repository: AuditRepository | None = None) -> None:
        self.audit_repository = audit_repository or AuditRepository()

    def append_event(self, request: AuditAppendRequest | None = None, **kwargs: object) -> AuditRecord:
        if request is None:
            request = AuditAppendRequest.model_validate(kwargs)
        elif kwargs:
            raise TypeError("append_event accepts either an AuditAppendRequest or keyword fields, not both")
        return self.audit_repository.append(
            event_type=request.event_type,
            summary=request.summary,
            org_id=request.org_id,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            agent_id=request.agent_id,
            agent_revision_id=request.agent_revision_id,
            session_id=request.session_id,
            run_id=request.run_id,
            actor_id=request.actor_id,
            actor_type=request.actor_type,
            metadata=request.metadata,
        )

    def list_events(
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
        events = self.audit_repository.list(
            org_id=org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            session_id=session_id,
            run_id=run_id,
            resource_type=resource_type,
            resource_id=resource_id,
            event_type=event_type,
            limit=limit,
        )
        return [event.model_copy(update={"metadata": self._scrub_sensitive_data(event.metadata)}) for event in events]

    @staticmethod
    def _scrub_sensitive_data(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: "[redacted]" if isinstance(key, str) and AuditService._looks_sensitive(key) else AuditService._scrub_sensitive_data(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [AuditService._scrub_sensitive_data(item) for item in value]
        if isinstance(value, tuple):
            return tuple(AuditService._scrub_sensitive_data(item) for item in value)
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


audit_service = AuditService()
