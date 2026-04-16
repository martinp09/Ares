from __future__ import annotations

from app.db.secrets import SecretsRepository
from app.models.secrets import (
    SecretBindingCreateRequest,
    SecretBindingRecord,
    SecretCreateRequest,
    SecretRecord,
    SecretSummaryRecord,
)
from app.services.audit_service import audit_service


class SecretService:
    def __init__(self, secrets_repository: SecretsRepository | None = None) -> None:
        self.secrets_repository = secrets_repository or SecretsRepository()

    def create_secret(self, request: SecretCreateRequest) -> SecretSummaryRecord:
        existing_secret = self.secrets_repository.get_secret_by_name(org_id=request.org_id, name=request.name)
        secret = self.secrets_repository.create_secret(
            org_id=request.org_id,
            name=request.name,
            secret_value=request.secret_value,
            description=request.description,
        )
        summary = self._summarize(secret)
        audit_service.append_event(
            event_type="secret_updated" if existing_secret is not None else "secret_created",
            summary=f"{'Updated' if existing_secret is not None else 'Created'} secret {secret.name}",
            org_id=secret.org_id,
            resource_type="secret",
            resource_id=secret.id,
            metadata={"name": secret.name, "binding_count": summary.binding_count},
        )
        return summary

    def list_secrets(self, org_id: str | None = None) -> list[SecretSummaryRecord]:
        secrets = self.secrets_repository.list_secrets(org_id=org_id)
        return [self._summarize(secret) for secret in secrets]

    def bind_secret(self, secret_id: str, request: SecretBindingCreateRequest) -> SecretBindingRecord:
        binding = self.secrets_repository.bind_secret(
            secret_id=secret_id,
            agent_revision_id=request.agent_revision_id,
            binding_name=request.binding_name,
        )
        audit_service.append_event(
            event_type="secret_bound",
            summary=f"Bound secret {binding.binding_name}",
            org_id=binding.org_id,
            resource_type="secret_binding",
            resource_id=binding.id,
            agent_revision_id=binding.agent_revision_id,
            metadata={"secret_id": binding.secret_id, "binding_name": binding.binding_name},
        )
        return binding

    def list_bindings_for_revision(self, agent_revision_id: str):
        return self.secrets_repository.list_bindings(agent_revision_id=agent_revision_id)

    def list_bindings_for_secret(self, secret_id: str):
        return self.secrets_repository.list_bindings_for_secret(secret_id)

    def _summarize(self, secret: SecretRecord) -> SecretSummaryRecord:
        binding_count = len(self.secrets_repository.list_bindings_for_secret(secret.id))
        return SecretSummaryRecord(
            id=secret.id,
            org_id=secret.org_id,
            name=secret.name,
            description=secret.description,
            value_redacted="[redacted]",
            binding_count=binding_count,
            created_at=secret.created_at,
            updated_at=secret.updated_at,
        )


secret_service = SecretService()
