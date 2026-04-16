from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.models.lead_events import ProviderWebhookReceiptRecord


def build_repository() -> ProviderWebhooksRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return ProviderWebhooksRepository(client)


def test_record_same_replay_key_returns_deduped_receipt() -> None:
    repository = build_repository()

    first = repository.record(
        ProviderWebhookReceiptRecord(
            business_id="limitless",
            environment="dev",
            provider="instantly",
            event_type="reply_received",
            idempotency_key="wh-001",
        )
    )
    second = repository.record(
        ProviderWebhookReceiptRecord(
            business_id="limitless",
            environment="dev",
            provider="instantly",
            event_type="reply_received",
            idempotency_key="wh-001",
        )
    )

    assert first.id == second.id
    assert second.deduped is True


def test_mark_processed_sets_processed_metadata() -> None:
    repository = build_repository()
    receipt = repository.record(
        ProviderWebhookReceiptRecord(
            business_id="limitless",
            environment="dev",
            provider="instantly",
            event_type="email_sent",
            idempotency_key="wh-002",
        )
    )

    processed = repository.mark_processed(receipt.id or "", lead_event_id="levt_123")

    assert processed is not None
    assert processed.processed is True
    assert processed.lead_event_id == "levt_123"
