from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.lead_machine_supabase import (
    external_id,
    fetch_rows,
    insert_rows,
    lead_machine_backend_enabled,
    patch_rows,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.commands import generate_stable_id
from app.models.title_packets import TitlePacketPriority, TitlePacketRecord, TitlePacketStatus


class TitlePacketsRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ):
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        if force_memory is None:
            self._force_memory = client is not None and getattr(client, "backend", "memory") != "supabase"
        else:
            self._force_memory = force_memory

    def upsert(self, record: TitlePacketRecord, *, dedupe_key: str | None = None) -> TitlePacketRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record, dedupe_key=dedupe_key)
        now = utc_now()
        resolved_key = dedupe_key or record.identity_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.title_packet_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.title_packets[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.title_packets[existing_id] = updated
                return updated

            packet_id = record.id or generate_stable_id("tpkt", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": packet_id, "updated_at": now})
            store.title_packets[packet_id] = created
            store.title_packet_keys[lookup_key] = packet_id
            return created

    def get(self, packet_id: str) -> TitlePacketRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(packet_id, "tpkt")
            if row_id is None:
                return None
            rows = fetch_rows("title_packets", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.title_packets.get(packet_id)

    def get_by_key(self, *, business_id: str, environment: str, dedupe_key: str) -> TitlePacketRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            rows = fetch_rows(
                "title_packets",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "identity_key": f"eq.{dedupe_key}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            packet_id = store.title_packet_keys.get((business_id, environment, dedupe_key))
            if packet_id is None:
                return None
            return store.title_packets.get(packet_id)

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        lead_id: str | None = None,
        status: TitlePacketStatus | None = None,
    ) -> list[TitlePacketRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._list_in_supabase(
                business_id=business_id,
                environment=environment,
                lead_id=lead_id,
                status=status,
            )
        with self.client.transaction() as store:
            records = list(store.title_packets.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        if lead_id is not None:
            records = [record for record in records if record.lead_id == lead_id]
        if status is not None:
            records = [record for record in records if record.status == status]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records

    def _upsert_in_supabase(self, record: TitlePacketRecord, *, dedupe_key: str | None = None) -> TitlePacketRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        resolved_key = dedupe_key or record.identity_key()
        existing = fetch_rows(
            "title_packets",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "identity_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        payload = self._payload_for_supabase(record, business_pk=tenant.business_pk, environment=tenant.environment)
        payload["identity_key"] = resolved_key
        if existing:
            row = patch_rows(
                "title_packets",
                params={"id": f"eq.{existing[0]['id']}"},
                row=payload,
                select="*",
                settings=self.settings,
            )[0]
            return self._record_from_supabase(row)
        provided_id = row_id_from_external_id(record.id, "tpkt")
        if provided_id is not None:
            payload["id"] = provided_id
        row = insert_rows("title_packets", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    def _list_in_supabase(
        self,
        *,
        business_id: str | None,
        environment: str | None,
        lead_id: str | None,
        status: TitlePacketStatus | None,
    ) -> list[TitlePacketRecord]:
        params = {"select": "*", "order": "created_at.asc,id.asc"}
        if business_id is not None and environment is not None:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            params["business_id"] = f"eq.{tenant.business_pk}"
            params["environment"] = f"eq.{tenant.environment}"
        elif business_id is not None and business_id.isdigit():
            params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
        elif environment is not None:
            params["environment"] = f"eq.{environment}"
        if lead_id is not None:
            params["lead_id"] = f"eq.{row_id_from_external_id(lead_id, 'lead')}"
        if status is not None:
            params["status"] = f"eq.{status.value}"
        return [self._record_from_supabase(row) for row in fetch_rows("title_packets", params=params, settings=self.settings)]

    @staticmethod
    def _payload_for_supabase(record: TitlePacketRecord, *, business_pk: int, environment: str) -> dict[str, Any]:
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["lead_id"] = row_id_from_external_id(record.lead_id, "lead")
        payload["status"] = record.status.value
        payload["priority"] = record.priority.value
        return payload

    @staticmethod
    def _record_from_supabase(row: dict[str, Any]) -> TitlePacketRecord:
        allowed_fields = set(TitlePacketRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("tpkt", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("lead_id") is not None:
            payload["lead_id"] = external_id("lead", row["lead_id"])
        if row.get("status") is not None:
            payload["status"] = TitlePacketStatus(str(row["status"]))
        if row.get("priority") is not None:
            payload["priority"] = TitlePacketPriority(str(row["priority"]))
        return TitlePacketRecord.model_validate(payload)
