from datetime import UTC, datetime, timedelta

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.usage import UsageRepository
from app.models.usage import UsageEventKind


def build_repository() -> UsageRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return UsageRepository(client)


def test_usage_records_append_and_filter_by_org_and_agent() -> None:
    repository = build_repository()
    base_time = datetime(2026, 4, 16, 18, 0, tzinfo=UTC)

    repository.record(
        kind=UsageEventKind.RUN,
        org_id="org_limitless",
        agent_id="agt_1",
        agent_revision_id="rev_1",
        count=1,
        created_at=base_time,
    )
    repository.record(
        kind=UsageEventKind.TOOL_CALL,
        org_id="org_limitless",
        agent_id="agt_1",
        agent_revision_id="rev_1",
        count=2,
        created_at=base_time + timedelta(minutes=1),
    )
    repository.record(
        kind=UsageEventKind.PROVIDER_CALL,
        org_id="org_other",
        agent_id="agt_2",
        agent_revision_id="rev_2",
        count=3,
        created_at=base_time + timedelta(minutes=2),
    )

    events = repository.list(org_id="org_limitless", agent_id="agt_1")

    assert [event.kind for event in events] == [UsageEventKind.TOOL_CALL, UsageEventKind.RUN]
    assert [event.count for event in events] == [2, 1]
