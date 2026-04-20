from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.lead_machine_supabase import (
    external_id,
    fetch_rows,
    insert_rows,
    lead_machine_backend_enabled,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.commands import generate_stable_id
from app.models.lead_events import LeadEventRecord


class LeadEventsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = False
        self.settings = settings or get_settings()

    def append(self, record: LeadEventRecord, *, replay_key: str | None = None) -> LeadEventRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._append_in_supabase(record, replay_key=replay_key)
        resolved_key = replay_key or record.replay_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.lead_event_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.lead_events[existing_id]
                return existing.model_copy(update={"deduped": True})
            event_id = record.id or generate_stable_id("levt", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": event_id})
            store.lead_events[event_id] = created
            store.lead_event_keys[lookup_key] = event_id
            store.lead_event_ids_by_lead.setdefault(record.lead_id, []).append(event_id)
            return created

    def get(self, event_id: str) -> LeadEventRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(event_id, "levt")
            if row_id is None:
                return None
            rows = fetch_rows("lead_events", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.lead_events.get(event_id)

    def list(self, *, business_id: str | None = None, environment: str | None = None, lead_id: str | None = None, campaign_id: str | None = None) -> list[LeadEventRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params = {"select": "*", "order": "event_timestamp.asc"}
            if business_id and business_id.isdigit():
                params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
            if lead_id is not None:
                row_id = row_id_from_external_id(lead_id, "lead")
                params["lead_id"] = f"eq.{row_id}"
            if campaign_id is not None:
                row_id = row_id_from_external_id(campaign_id, "camp")
                params["campaign_id"] = f"eq.{row_id}"
            return [self._record_from_supabase(row) for row in fetch_rows("lead_events", params=params, settings=self.settings)]
        with self.client.transaction() as store:
            events = list(store.lead_events.values())
        if business_id is not None:
            events = [event for event in events if event.business_id == business_id]
        if environment is not None:
            events = [event for event in events if event.environment == environment]
        if lead_id is not None:
            events = [event for event in events if event.lead_id == lead_id]
        if campaign_id is not None:
            events = [event for event in events if event.campaign_id == campaign_id]
        events.sort(key=lambda record: (record.event_timestamp, record.received_at, record.id or ""))
        return events

    def list_for_lead(self, lead_id: str) -> list[LeadEventRecord]:
        return self.list(lead_id=lead_id)

    def _append_in_supabase(self, record: LeadEventRecord, *, replay_key: str | None = None) -> LeadEventRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        resolved_key = replay_key or record.replay_key()
        rows = fetch_rows(
            "lead_events",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "idempotency_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if rows:
            return self._record_from_supabase(rows[0], deduped=True)
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["lead_id"] = row_id_from_external_id(record.lead_id, "lead")
        payload["campaign_id"] = row_id_from_external_id(record.campaign_id, "camp")
        payload["automation_run_id"] = row_id_from_external_id(record.automation_run_id, "run")
        payload["provider_receipt_id"] = row_id_from_external_id(record.provider_receipt_id, "wh")
        payload["source_event_id"] = row_id_from_external_id(record.source_event_id, "levt")
        payload["idempotency_key"] = resolved_key
        row = insert_rows("lead_events", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict, *, deduped: bool = False) -> LeadEventRecord:
        allowed_fields = set(LeadEventRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("levt", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["lead_id"] = external_id("lead", row["lead_id"])
        if row.get("campaign_id") is not None:
            payload["campaign_id"] = external_id("camp", row["campaign_id"])
        if row.get("automation_run_id") is not None:
            payload["automation_run_id"] = external_id("run", row["automation_run_id"])
        if row.get("provider_receipt_id") is not None:
            payload["provider_receipt_id"] = external_id("wh", row["provider_receipt_id"])
        if row.get("source_event_id") is not None:
            payload["source_event_id"] = external_id("levt", row["source_event_id"])
        payload["deduped"] = deduped or bool(row.get("deduped"))
        return LeadEventRecord.model_validate(payload)
