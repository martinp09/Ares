from __future__ import annotations

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
from app.models.lead_events import ProviderWebhookReceiptRecord


class ProviderWebhooksRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ):
        self.client = client or get_control_plane_client()
        self._force_memory = False if force_memory is None else force_memory
        self.settings = settings or get_settings()

    def record(self, receipt: ProviderWebhookReceiptRecord, *, replay_key: str | None = None) -> ProviderWebhookReceiptRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._record_in_supabase(receipt, replay_key=replay_key)
        resolved_key = replay_key or receipt.replay_key()
        lookup_key = (receipt.business_id, receipt.environment, receipt.provider, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.provider_webhook_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.provider_webhooks[existing_id]
                return existing.model_copy(update={"deduped": True})

            receipt_id = receipt.id or generate_stable_id("wh", receipt.business_id, receipt.environment, receipt.provider, resolved_key)
            created = receipt.model_copy(update={"id": receipt_id})
            store.provider_webhooks[receipt_id] = created
            store.provider_webhook_keys[lookup_key] = receipt_id
            return created

    def get(self, receipt_id: str) -> ProviderWebhookReceiptRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(receipt_id, "wh")
            if row_id is None:
                return None
            rows = fetch_rows("provider_webhooks", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.provider_webhooks.get(receipt_id)

    def mark_processed(self, receipt_id: str, *, lead_event_id: str | None = None) -> ProviderWebhookReceiptRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(receipt_id, "wh")
            if row_id is None:
                return None
            rows = patch_rows(
                "provider_webhooks",
                params={"id": f"eq.{row_id}"},
                row={
                    "processed": True,
                    "processed_at": utc_now().isoformat(),
                    "lead_event_id": row_id_from_external_id(lead_event_id, "levt"),
                },
                select="*",
                settings=self.settings,
            )
            return self._record_from_supabase(rows[0]) if rows else None
        processed_at = utc_now()
        with self.client.transaction() as store:
            receipt = store.provider_webhooks.get(receipt_id)
            if receipt is None:
                return None
            updated = receipt.model_copy(update={"processed": True, "processed_at": processed_at, "lead_event_id": lead_event_id})
            store.provider_webhooks[receipt_id] = updated
            return updated

    def _record_in_supabase(self, receipt: ProviderWebhookReceiptRecord, *, replay_key: str | None = None) -> ProviderWebhookReceiptRecord:
        tenant = resolve_tenant(receipt.business_id, receipt.environment, settings=self.settings)
        resolved_key = replay_key or receipt.replay_key()
        rows = fetch_rows(
            "provider_webhooks",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "provider": f"eq.{receipt.provider}",
                "idempotency_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if rows:
            return self._record_from_supabase(rows[0], deduped=True)
        payload = receipt.model_dump(mode="json", exclude={"id", "business_id", "environment", "received_at", "processed_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["idempotency_key"] = resolved_key
        payload["lead_event_id"] = row_id_from_external_id(receipt.lead_event_id, "levt")
        row = insert_rows("provider_webhooks", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict, *, deduped: bool = False) -> ProviderWebhookReceiptRecord:
        allowed_fields = set(ProviderWebhookReceiptRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("wh", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("lead_event_id") is not None:
            payload["lead_event_id"] = external_id("levt", row["lead_event_id"])
        payload["deduped"] = deduped or bool(row.get("deduped"))
        return ProviderWebhookReceiptRecord.model_validate(payload)
