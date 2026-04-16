from datetime import UTC, datetime, timedelta

from app.db.audit import AuditRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore


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
