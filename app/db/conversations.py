from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, resolve_tenant
from app.models.commands import generate_id
from app.models.conversations import ConversationRecord


class ConversationsRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ):
        self.client = client or get_control_plane_client()
        self._force_memory = False if force_memory is None else force_memory
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
            row_id = conversation_keys.get(dedupe_key)
            if row_id is not None:
                return conversation_rows[row_id]

            record = ConversationRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                channel=channel,
                provider_thread_id=provider_thread_id or generate_id("cnv"),
            )
            row_id = generate_id("cnvrow")
            conversation_rows[row_id] = record
            conversation_keys[dedupe_key] = row_id
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
            for record in conversation_rows.values():
                if (
                    record.business_id == business_id
                    and record.environment == environment
                    and record.channel == channel
                    and record.provider_thread_id == provider_thread_id
                ):
                    return record
            return None

    def find_all_by_provider_thread(
        self,
        *,
        channel: str,
        provider_thread_id: str,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[ConversationRecord]:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            params = {
                "select": "external_conversation_id,status,contact_id,business_id,environment,channel",
                "channel": f"eq.{channel}",
                "external_conversation_id": f"eq.{provider_thread_id}",
            }
            if business_id is not None:
                params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
            rows = fetch_rows(
                "conversations",
                params=params,
                settings=self.settings,
            )
            records: list[ConversationRecord] = []
            for row in rows:
                contact_pk = row.get("contact_id")
                contact_rows = fetch_rows(
                    "contacts",
                    params={
                        "select": "external_contact_id",
                        "business_id": f"eq.{row['business_id']}",
                        "environment": f"eq.{row['environment']}",
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
                records.append(
                    ConversationRecord(
                        business_id=str(row["business_id"]),
                        environment=str(row["environment"]),
                        contact_id=contact_external_id,
                        channel=str(row.get("channel") or channel),
                        provider_thread_id=str(row.get("external_conversation_id") or provider_thread_id),
                        status=str(row.get("status") or "open"),
                    )
                )
            return records
        with self.client.transaction() as store:
            conversation_rows: dict[str, ConversationRecord] = getattr(
                store, "marketing_conversation_rows", {}
            )
            return [
                record
                for record in conversation_rows.values()
                if record.channel == channel
                and record.provider_thread_id == provider_thread_id
                and (business_id is None or record.business_id == business_id)
                and (environment is None or record.environment == environment)
            ]

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
