from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_stable_id
from app.models.lead_events import ProviderWebhookReceiptRecord


class ProviderWebhooksRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def record(self, receipt: ProviderWebhookReceiptRecord, *, replay_key: str | None = None) -> ProviderWebhookReceiptRecord:
        resolved_key = replay_key or receipt.replay_key()
        lookup_key = (receipt.business_id, receipt.environment, receipt.provider, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.provider_webhook_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.provider_webhooks[existing_id]
                return existing.model_copy(update={"deduped": True})

            receipt_id = receipt.id or generate_stable_id(
                "wh",
                receipt.business_id,
                receipt.environment,
                receipt.provider,
                resolved_key,
            )
            created = receipt.model_copy(update={"id": receipt_id})
            store.provider_webhooks[receipt_id] = created
            store.provider_webhook_keys[lookup_key] = receipt_id
            return created

    def get(self, receipt_id: str) -> ProviderWebhookReceiptRecord | None:
        with self.client.transaction() as store:
            return store.provider_webhooks.get(receipt_id)

    def mark_processed(
        self,
        receipt_id: str,
        *,
        lead_event_id: str | None = None,
    ) -> ProviderWebhookReceiptRecord | None:
        processed_at = utc_now()
        with self.client.transaction() as store:
            receipt = store.provider_webhooks.get(receipt_id)
            if receipt is None:
                return None
            updated = receipt.model_copy(
                update={
                    "processed": True,
                    "processed_at": processed_at,
                    "lead_event_id": lead_event_id,
                }
            )
            store.provider_webhooks[receipt_id] = updated
            return updated
