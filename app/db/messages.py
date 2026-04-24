from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, resolve_tenant
from app.models.messages import MessageDirection, MessageRecord, MessageStatus


class MessagesRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ):
        self.client = client or get_control_plane_client()
        self._force_memory = False if force_memory is None else force_memory
        self.settings = settings or get_settings()

    def append_outbound(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        conversation_id: str,
        channel: str,
        provider: str | None,
        body: str,
        external_message_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MessageRecord:
        return self._append(
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            conversation_id=conversation_id,
            channel=channel,
            provider=provider,
            body=body,
            direction=MessageDirection.OUTBOUND,
            status=MessageStatus.QUEUED,
            external_message_id=external_message_id,
            metadata=metadata,
        )

    def append_inbound(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        conversation_id: str,
        channel: str,
        provider: str | None,
        body: str,
        external_message_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MessageRecord:
        return self._append(
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            conversation_id=conversation_id,
            channel=channel,
            provider=provider,
            body=body,
            direction=MessageDirection.INBOUND,
            status=MessageStatus.RECEIVED,
            external_message_id=external_message_id,
            metadata=metadata,
        )

    def get(self, message_id: str | None) -> MessageRecord | None:
        if not message_id:
            return None
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._get_in_supabase(message_id)
        with self.client.transaction() as store:
            message_rows: dict[str, MessageRecord] = getattr(
                store, "marketing_message_rows", {}
            )
            return message_rows.get(message_id)

    def update_status_by_external_id(
        self,
        *,
        provider: str,
        external_message_id: str,
        status: str,
        metadata: dict[str, object] | None = None,
    ) -> MessageRecord | None:
        normalized_status = MessageStatus(status)
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._update_status_by_external_id_in_supabase(
                provider=provider,
                external_message_id=external_message_id,
                status=normalized_status,
                metadata=metadata,
            )
        with self.client.transaction() as store:
            message_rows: dict[str, MessageRecord] = getattr(
                store, "marketing_message_rows", {}
            )
            message_keys: dict[tuple[str, str, str, str, str], str] = getattr(
                store, "marketing_message_keys", {}
            )
            for key, message_id in message_keys.items():
                key_business_id, key_environment, key_provider, _direction, key_external_id = key
                if key_provider == provider and key_external_id == external_message_id:
                    existing = message_rows.get(message_id)
                    if existing is None:
                        continue
                    updated = existing.model_copy(
                        update={
                            "status": normalized_status,
                            "metadata": {**existing.metadata, **(metadata or {})},
                        }
                    )
                    message_rows[message_id] = updated
                    message_keys[key] = message_id
                    return updated
        return None

    def _append(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        conversation_id: str,
        channel: str,
        provider: str | None,
        body: str,
        direction: MessageDirection,
        status: MessageStatus,
        external_message_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MessageRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._append_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                conversation_id=conversation_id,
                channel=channel,
                provider=provider,
                body=body,
                direction=direction,
                status=status,
                external_message_id=external_message_id,
                metadata=metadata,
            )
        with self.client.transaction() as store:
            message_rows: dict[str, MessageRecord] = getattr(store, "marketing_message_rows", {})
            message_keys: dict[tuple[str, str, str, str, str], str] = getattr(
                store, "marketing_message_keys", {}
            )
            setattr(store, "marketing_message_rows", message_rows)
            setattr(store, "marketing_message_keys", message_keys)
            if external_message_id is not None:
                lookup_key = (
                    business_id,
                    environment,
                    provider or "",
                    direction.value if hasattr(direction, "value") else str(direction),
                    external_message_id,
                )
                existing_id = message_keys.get(lookup_key)
                if existing_id is not None:
                    return message_rows[existing_id]
            record = MessageRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                conversation_id=conversation_id,
                channel=channel,
                direction=direction,
                provider=provider,
                external_message_id=external_message_id,
                body=body,
                status=status,
                metadata=metadata or {},
            )
            message_rows[record.id] = record
            if external_message_id is not None:
                message_keys[lookup_key] = record.id
        return record

    def _append_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        conversation_id: str,
        channel: str,
        provider: str | None,
        body: str,
        direction: MessageDirection,
        status: MessageStatus,
        external_message_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MessageRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        contact_pk = int(
            fetch_rows(
                "contacts",
                params={
                    "select": "id",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "external_contact_id": f"eq.{contact_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )[0]["id"]
        )
        conversation_pk = int(
            fetch_rows(
                "conversations",
                params={
                    "select": "id",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "external_conversation_id": f"eq.{conversation_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )[0]["id"]
        )
        if external_message_id is not None:
            existing_rows = fetch_rows(
                "messages",
                params={
                    "select": "id,created_at,updated_at,status,metadata",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "provider": f"eq.{provider}" if provider is not None else "is.null",
                    "direction": f"eq.{direction.value}",
                    "external_message_id": f"eq.{external_message_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            if existing_rows:
                row = existing_rows[0]
                return MessageRecord(
                    id=f"msg_{row['id']}",
                    business_id=business_id,
                    environment=environment,
                    contact_id=contact_id,
                    conversation_id=conversation_id,
                    channel=channel,
                    direction=direction,
                    provider=provider,
                    external_message_id=external_message_id,
                    body=body,
                    status=MessageStatus(str(row.get("status") or status.value)),
                    metadata=dict(row.get("metadata") or metadata or {}),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        row = insert_rows(
            "messages",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "contact_id": contact_pk,
                    "conversation_id": conversation_pk,
                    "channel": channel,
                    "direction": direction.value,
                    "provider": provider,
                    "external_message_id": external_message_id,
                    "body": body,
                    "status": status.value if hasattr(status, "value") else str(status),
                    "metadata": metadata or {},
                }
            ],
            select="id,status,metadata,created_at,updated_at",
            settings=self.settings,
        )[0]
        return MessageRecord(
            id=f"msg_{row['id']}",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            conversation_id=conversation_id,
            channel=channel,
            direction=direction,
            provider=provider,
            external_message_id=external_message_id,
            body=body,
            status=MessageStatus(str(row.get("status") or status.value)),
            metadata=dict(row.get("metadata") or metadata or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _get_in_supabase(self, message_id: str) -> MessageRecord | None:
        if not message_id.startswith("msg_"):
            return None
        rows = fetch_rows(
            "messages",
            params={"select": "*", "id": f"eq.{message_id.removeprefix('msg_')}", "limit": "1"},
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        return MessageRecord(
            id=f"msg_{row['id']}",
            business_id=str(row["business_id"]),
            environment=str(row["environment"]),
            contact_id=str(row["contact_id"]),
            conversation_id=str(row["conversation_id"]),
            channel=str(row["channel"]),
            direction=MessageDirection(str(row["direction"])),
            provider=row.get("provider"),
            external_message_id=row.get("external_message_id"),
            body=str(row.get("body") or ""),
            status=MessageStatus(str(row.get("status") or "queued")),
            metadata=dict(row.get("metadata") or {}),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _update_status_by_external_id_in_supabase(
        self,
        *,
        provider: str,
        external_message_id: str,
        status: MessageStatus,
        metadata: dict[str, object] | None = None,
    ) -> MessageRecord | None:
        from app.db.marketing_supabase import patch_rows

        rows = fetch_rows(
            "messages",
            params={
                "select": "id,metadata",
                "provider": f"eq.{provider}",
                "external_message_id": f"eq.{external_message_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        updated_metadata = {**dict(row.get("metadata") or {}), **(metadata or {})}
        updated = patch_rows(
            "messages",
            params={"id": f"eq.{row['id']}"},
            row={"status": status.value, "metadata": updated_metadata},
            select="*",
            settings=self.settings,
        )[0]
        return self._get_in_supabase(f"msg_{updated['id']}")
