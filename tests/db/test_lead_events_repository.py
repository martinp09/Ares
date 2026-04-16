from datetime import UTC, datetime

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.models.lead_events import LeadEventRecord


def build_repository() -> LeadEventsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return LeadEventsRepository(client)


def test_append_same_replay_key_returns_deduped_event() -> None:
    repository = build_repository()
    first = repository.append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_123",
            event_type="reply_received",
            idempotency_key="evt-001",
        )
    )
    second = repository.append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_123",
            event_type="reply_received",
            idempotency_key="evt-001",
        )
    )

    assert first.id == second.id
    assert second.deduped is True


def test_list_for_lead_orders_by_event_timestamp() -> None:
    repository = build_repository()
    later = datetime(2026, 4, 16, 17, 0, 5, tzinfo=UTC)
    earlier = datetime(2026, 4, 16, 17, 0, 1, tzinfo=UTC)
    repository.append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_123",
            event_type="email_sent",
            idempotency_key="evt-002",
            event_timestamp=later,
        )
    )
    repository.append(
        LeadEventRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_123",
            event_type="reply_received",
            idempotency_key="evt-003",
            event_timestamp=earlier,
        )
    )

    events = repository.list_for_lead("lead_123")
    assert [event.event_type for event in events] == ["reply_received", "email_sent"]
