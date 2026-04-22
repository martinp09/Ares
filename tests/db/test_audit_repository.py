from datetime import UTC, datetime, timedelta

import pytest

from app.db.audit import AuditRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.models.audit import AuditRecord


def build_repository() -> AuditRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return AuditRepository(client)


def test_audit_records_append_only_and_return_newest_first() -> None:
    repository = build_repository()
    earlier = datetime(2026, 4, 16, 18, 0, tzinfo=UTC)
    later = earlier + timedelta(minutes=5)

    first = repository.append(
        event_type="agent_created",
        summary="Created agent",
        org_id="org_limitless",
        agent_id="agt_1",
        created_at=earlier,
    )
    second = repository.append(
        event_type="agent_published",
        summary="Published revision",
        org_id="org_limitless",
        agent_id="agt_1",
        agent_revision_id="rev_1",
        created_at=later,
    )

    events = repository.list(org_id="org_limitless")

    assert first.id != second.id
    assert [event.event_type for event in events] == ["agent_published", "agent_created"]
    assert events[0].agent_revision_id == "rev_1"
    assert events[1].agent_id == "agt_1"


def test_audit_records_with_identical_timestamps_return_latest_append_first(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = build_repository()
    created_at = datetime(2026, 4, 16, 18, 0, tzinfo=UTC)
    generated_ids = iter(["audit_zzz_first", "audit_aaa_second"])
    monkeypatch.setattr("app.db.audit.generate_id", lambda prefix: next(generated_ids))

    repository.append(
        event_type="agent_created",
        summary="Created agent",
        org_id="org_limitless",
        created_at=created_at,
    )
    repository.append(
        event_type="agent_published",
        summary="Published revision",
        org_id="org_limitless",
        created_at=created_at,
    )

    events = repository.list(org_id="org_limitless")

    assert [event.event_type for event in events] == ["agent_published", "agent_created"]


def test_audit_records_with_identical_timestamps_keep_latest_append_first_after_persisted_reload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = InMemoryControlPlaneStore()
    repository = AuditRepository(InMemoryControlPlaneClient(store))
    created_at = datetime(2026, 4, 16, 18, 0, tzinfo=UTC)
    generated_ids = iter(["audit_zzz_first", "audit_aaa_second"])
    monkeypatch.setattr("app.db.audit.generate_id", lambda prefix: next(generated_ids))

    first = repository.append(
        event_type="agent_created",
        summary="Created agent",
        org_id="org_limitless",
        created_at=created_at,
    )
    second = repository.append(
        event_type="agent_published",
        summary="Published revision",
        org_id="org_limitless",
        created_at=created_at,
    )

    payloads = sorted(
        [first.model_dump(mode="json"), second.model_dump(mode="json")],
        key=lambda payload: payload["updated_at"],
    )
    hydrated_store = InMemoryControlPlaneStore()
    for payload in payloads:
        record = AuditRecord.model_validate(payload)
        hydrated_store.audit_events[record.id] = record
    hydrated_repository = AuditRepository(InMemoryControlPlaneClient(hydrated_store))

    events = hydrated_repository.list(org_id="org_limitless")

    assert first.updated_at < second.updated_at
    assert [event.event_type for event in events] == ["agent_published", "agent_created"]
