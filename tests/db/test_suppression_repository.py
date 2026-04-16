from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.suppression import SuppressionRepository
from app.models.suppression import SuppressionRecord, SuppressionScope, SuppressionSource


def build_repository() -> SuppressionRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return SuppressionRepository(client)


def test_upsert_reuses_scope_key_and_archives_inactive_record() -> None:
    repository = build_repository()

    first = repository.upsert(
        SuppressionRecord(
            business_id="limitless",
            environment="dev",
            email="owner@example.com",
            reason="opt_out",
            source=SuppressionSource.WEBHOOK,
        )
    )
    second = repository.upsert(
        SuppressionRecord(
            business_id="limitless",
            environment="dev",
            email="owner@example.com",
            reason="manual_override",
            source=SuppressionSource.MANUAL,
            active=False,
        )
    )

    assert first.id == second.id
    assert second.active is False
    assert second.archived_at is not None


def test_list_active_filters_out_archived_suppressions() -> None:
    repository = build_repository()
    repository.upsert(
        SuppressionRecord(
            business_id="limitless",
            environment="dev",
            lead_id="lead_123",
            campaign_id="camp_123",
            scope=SuppressionScope.CAMPAIGN,
            reason="reply_received",
            source=SuppressionSource.AUTOMATION,
        )
    )
    repository.upsert(
        SuppressionRecord(
            business_id="limitless",
            environment="dev",
            email="owner@example.com",
            reason="opt_out",
            source=SuppressionSource.WEBHOOK,
            active=False,
        )
    )

    active_records = repository.list_active(business_id="limitless", environment="dev")
    assert len(active_records) == 1
    assert active_records[0].campaign_id == "camp_123"
