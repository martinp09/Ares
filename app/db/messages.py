from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, resolve_tenant
from app.models.messages import MessageDirection, MessageRecord, MessageStatus


class MessagesRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
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
