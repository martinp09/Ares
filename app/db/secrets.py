from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.secrets import SecretBindingRecord, SecretRecord


class SecretsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create_secret(self, *, org_id: str, name: str, secret_value: str, description: str | None = None) -> SecretRecord:
        now = utc_now()
        lookup_key = (org_id, name)
        with self.client.transaction() as store:
            existing_id = store.secret_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.secrets[existing_id]
                updated = existing.model_copy(update={"description": description, "secret_value": secret_value, "updated_at": now})
                store.secrets[existing_id] = updated
                return updated

            record = SecretRecord(
                id=generate_id("sec"),
                org_id=org_id,
                name=name,
                description=description,
                secret_value=secret_value,
                created_at=now,
                updated_at=now,
            )
            store.secrets[record.id] = record
            store.secret_keys[lookup_key] = record.id
            return record

    def get_secret(self, secret_id: str) -> SecretRecord | None:
        with self.client.transaction() as store:
            return store.secrets.get(secret_id)

    def get_secret_by_name(self, *, org_id: str, name: str) -> SecretRecord | None:
        with self.client.transaction() as store:
            secret_id = store.secret_keys.get((org_id, name))
            if secret_id is None:
                return None
            return store.secrets.get(secret_id)

    def list_secrets(self, *, org_id: str | None = None) -> list[SecretRecord]:
        with self.client.transaction() as store:
            secrets = list(store.secrets.values())
        if org_id is not None:
            secrets = [secret for secret in secrets if secret.org_id == org_id]
        secrets.sort(key=lambda secret: (secret.name, secret.created_at))
        return secrets

    def bind_secret(self, *, secret_id: str, agent_revision_id: str, binding_name: str) -> SecretBindingRecord:
        now = utc_now()
        with self.client.transaction() as store:
            secret = store.secrets.get(secret_id)
            if secret is None:
                raise ValueError("Secret not found")
            lookup_key = (agent_revision_id, binding_name)
            existing_id = store.secret_binding_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.secret_bindings[existing_id]
                updated = existing.model_copy(update={"secret_id": secret_id, "updated_at": now})
                store.secret_bindings[existing_id] = updated
                return updated

            record = SecretBindingRecord(
                id=generate_id("sbind"),
                org_id=secret.org_id,
                secret_id=secret_id,
                agent_revision_id=agent_revision_id,
                binding_name=binding_name,
                created_at=now,
                updated_at=now,
            )
            store.secret_bindings[record.id] = record
            store.secret_binding_keys[lookup_key] = record.id
            return record

    def list_bindings(self, *, agent_revision_id: str) -> list[SecretBindingRecord]:
        with self.client.transaction() as store:
            bindings = [binding for binding in store.secret_bindings.values() if binding.agent_revision_id == agent_revision_id]
        bindings.sort(key=lambda binding: (binding.binding_name, binding.created_at))
        return bindings

    def list_bindings_for_secret(self, secret_id: str) -> list[SecretBindingRecord]:
        with self.client.transaction() as store:
            bindings = [binding for binding in store.secret_bindings.values() if binding.secret_id == secret_id]
        bindings.sort(key=lambda binding: (binding.binding_name, binding.created_at))
        return bindings
