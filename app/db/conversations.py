from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, patch_rows, resolve_tenant
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
        provider_thread_id: str | None = None,
    ) -> ConversationRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._get_or_create_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                channel=channel,
                provider_thread_id=provider_thread_id,
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
                existing = conversation_rows[existing_id]
                if provider_thread_id and existing.provider_thread_id != provider_thread_id:
                    existing = existing.model_copy(update={"provider_thread_id": provider_thread_id})
                    conversation_rows[existing_id] = existing
                return existing

            record = ConversationRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                channel=channel,
                provider_thread_id=provider_thread_id or generate_id("cnv"),
            )
            conversation_rows[record.provider_thread_id] = record
            conversation_keys[dedupe_key] = record.provider_thread_id
            return record

    def find_by_provider_thread(
        self,
        *,
        business_id: str,
        environment: str,
        channel: str,
        provider_thread_id: str,
    ) -> ConversationRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._find_by_provider_thread_in_supabase(
                business_id=business_id,
                environment=environment,
                channel=channel,
                provider_thread_id=provider_thread_id,
            )
        with self.client.transaction() as store:
            conversation_rows: dict[str, ConversationRecord] = getattr(
                store, "marketing_conversation_rows", {}
            )
            record = conversation_rows.get(provider_thread_id)
            if record is None:
                return None
            if record.business_id != business_id or record.environment != environment or record.channel != channel:
                return None
            return record

    def _get_or_create_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        channel: str,
        provider_thread_id: str | None = None,
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
            row_external_id = str(row.get("external_conversation_id") or "")
            if provider_thread_id and provider_thread_id != row_external_id:
                updated_row = patch_rows(
                    "conversations",
                    params={
                        "business_id": f"eq.{tenant.business_pk}",
                        "environment": f"eq.{tenant.environment}",
                        "contact_id": f"eq.{contact_pk}",
                        "channel": f"eq.{channel}",
                    },
                    row={"external_conversation_id": provider_thread_id},
                    select="external_conversation_id,status",
                    settings=self.settings,
                )[0]
                row_external_id = str(updated_row.get("external_conversation_id") or row_external_id)
            return ConversationRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                channel=channel,
                provider_thread_id=row_external_id,
                status=str(row.get("status") or "open"),
            )
        external_id = provider_thread_id or generate_id("cnv")
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

    def _find_by_provider_thread_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        channel: str,
        provider_thread_id: str,
    ) -> ConversationRecord | None:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        rows = fetch_rows(
            "conversations",
            params={
                "select": "external_conversation_id,status,contact_id",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "channel": f"eq.{channel}",
                "external_conversation_id": f"eq.{provider_thread_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        contact_pk = row.get("contact_id")
        contact_rows = fetch_rows(
            "contacts",
            params={
                "select": "external_contact_id",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "id": f"eq.{contact_pk}",
                "limit": "1",
            },
            settings=self.settings,
        )
        contact_external_id = (
            str(contact_rows[0].get("external_contact_id") or f"ctc_{contact_pk}")
            if contact_rows
            else f"ctc_{contact_pk}"
        )
        return ConversationRecord(
            business_id=business_id,
            environment=environment,
            contact_id=contact_external_id,
            channel=channel,
            provider_thread_id=str(row.get("external_conversation_id") or provider_thread_id),
            status=str(row.get("status") or "open"),
        )
