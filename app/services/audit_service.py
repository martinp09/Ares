from __future__ import annotations

from app.core.config import DEFAULT_INTERNAL_ORG_ID, get_settings
from app.db.audit import AuditRepository
from app.models.actors import ActorContext
from app.models.audit import AuditAppendRequest, AuditRecord
from app.services._control_plane_runtime import resolve_repository_for_active_backend


class AuditService:
    def __init__(self, audit_repository: AuditRepository | None = None) -> None:
        self.audit_repository = audit_repository or AuditRepository()

    def _audit_repository(self) -> AuditRepository:
        self.audit_repository = resolve_repository_for_active_backend(
            self.audit_repository,
            factory=lambda client: AuditRepository(client=client),
        )
        return self.audit_repository

    @staticmethod
    def _resolve_request_org_id(request_org_id: str | None, *, actor_org_id: str | None = None) -> str | None:
        if actor_org_id is None:
            return request_org_id
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

    @staticmethod
    def _resolve_actor_field(request_value: str | None, *, actor_value: str | None, field_name: str) -> str | None:
        if actor_value is None:
            return request_value
        if request_value is None:
            return actor_value
        if request_value != actor_value:
            raise ValueError(f"{field_name} must match actor context")
        return actor_value

    def _normalize_append_request(
        self,
        request: AuditAppendRequest,
        *,
        actor_context: ActorContext | None = None,
    ) -> AuditAppendRequest:
        if actor_context is not None:
            normalized = request.model_copy(
                update={
                    "org_id": self._resolve_request_org_id(request.org_id, actor_org_id=actor_context.org_id),
                    "actor_id": self._resolve_actor_field(
                        request.actor_id,
                        actor_value=actor_context.actor_id,
                        field_name="Actor id",
                    ),
                    "actor_type": self._resolve_actor_field(
                        request.actor_type,
                        actor_value=str(actor_context.actor_type),
                        field_name="Actor type",
                    ),
                }
            )
        else:
            settings = get_settings()
            normalized = request.model_copy(
                update={
                    "org_id": request.org_id or settings.default_org_id,
                    "actor_id": request.actor_id or settings.default_actor_id,
                    "actor_type": request.actor_type or settings.default_actor_type,
                }
            )
        return normalized.model_copy(update={"metadata": self._scrub_sensitive_data(normalized.metadata)})

    @staticmethod
    def _scrub_record(record: AuditRecord) -> AuditRecord:
        return record.model_copy(update={"metadata": AuditService._scrub_sensitive_data(record.metadata)})

    def append_event(
        self,
        request: AuditAppendRequest | None = None,
        *,
        actor_context: ActorContext | None = None,
        **kwargs: object,
    ) -> AuditRecord:
        if request is None:
            request = AuditAppendRequest.model_validate(kwargs)
        elif kwargs:
            raise TypeError("append_event accepts either an AuditAppendRequest or keyword fields, not both")
        request = self._normalize_append_request(request, actor_context=actor_context)
        repository = self._audit_repository()
        record = repository.append(
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
        return self._scrub_record(record)

    def list_events(
        self,
        *,
        org_id: str | None = None,
        actor_org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> list[AuditRecord]:
        effective_org_id = self._resolve_list_org_id(org_id, actor_org_id=actor_org_id)
        repository = self._audit_repository()
        events = repository.list(
            org_id=effective_org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            session_id=session_id,
            run_id=run_id,
            resource_type=resource_type,
            resource_id=resource_id,
            event_type=event_type,
            limit=limit,
        )
        return [self._scrub_record(event) for event in events]

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
