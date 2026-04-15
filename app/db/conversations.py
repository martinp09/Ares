from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, resolve_tenant
from app.models.commands import generate_id
from app.models.conversations import ConversationRecord


class ConversationsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def get_or_create(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        channel: str,
    ) -> ConversationRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._get_or_create_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                channel=channel,
            )
        with self.client.transaction() as store:
            conversation_rows: dict[str, ConversationRecord] = getattr(
                store, "marketing_conversation_rows", {}
            )
            conversation_keys: dict[tuple[str, str, str, str], str] = getattr(
                store, "marketing_conversation_keys", {}
            )
            setattr(store, "marketing_conversation_rows", conversation_rows)
            setattr(store, "marketing_conversation_keys", conversation_keys)

            dedupe_key = (business_id, environment, contact_id, channel)
            existing_id = conversation_keys.get(dedupe_key)
            if existing_id is not None:
                return conversation_rows[existing_id]

            record = ConversationRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                channel=channel,
                provider_thread_id=generate_id("cnv"),
            )
            conversation_rows[record.provider_thread_id] = record
            conversation_keys[dedupe_key] = record.provider_thread_id
            return record

    def _get_or_create_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        channel: str,
    ) -> ConversationRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        contact_rows = fetch_rows(
            "contacts",
            params={
                "select": "id",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "external_contact_id": f"eq.{contact_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not contact_rows:
            raise RuntimeError(f"Contact not found for conversation: {contact_id}")
        contact_pk = int(contact_rows[0]["id"])
        rows = fetch_rows(
            "conversations",
            params={
                "select": "external_conversation_id,status",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "contact_id": f"eq.{contact_pk}",
                "channel": f"eq.{channel}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if rows:
            row = rows[0]
            return ConversationRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                channel=channel,
                provider_thread_id=str(row.get("external_conversation_id") or ""),
                status=str(row.get("status") or "open"),
            )
        external_id = generate_id("cnv")
        inserted = insert_rows(
            "conversations",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "contact_id": contact_pk,
                    "channel": channel,
                    "external_conversation_id": external_id,
                }
            ],
            select="external_conversation_id,status",
            settings=self.settings,
        )[0]
        return ConversationRecord(
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            channel=channel,
            provider_thread_id=str(inserted.get("external_conversation_id") or external_id),
            status=str(inserted.get("status") or "open"),
        )
