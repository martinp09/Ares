from app.db.automation_runs import AutomationRunsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.models.automation_runs import AutomationRunRecord


def build_repository() -> AutomationRunsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return AutomationRunsRepository(client)


def test_create_same_idempotency_key_returns_deduped_run() -> None:
    repository = build_repository()

    first = repository.create(
        AutomationRunRecord(
            business_id="limitless",
            environment="dev",
            workflow_name="lead-routing",
            idempotency_key="run-001",
        )
    )
    second = repository.create(
        AutomationRunRecord(
            business_id="limitless",
            environment="dev",
            workflow_name="lead-routing",
            idempotency_key="run-001",
        )
    )

    assert first.id == second.id
    assert second.deduped is True


def test_create_does_not_collide_across_workflows() -> None:
    repository = build_repository()

    first = repository.create(
        AutomationRunRecord(
            business_id="limitless",
            environment="dev",
            workflow_name="lead-routing",
            idempotency_key="run-002",
        )
    )
    second = repository.create(
        AutomationRunRecord(
            business_id="limitless",
            environment="dev",
            workflow_name="suppression-sync",
            idempotency_key="run-002",
        )
    )

    assert first.id != second.id
