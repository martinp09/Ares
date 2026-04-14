from app.db.approvals import ApprovalsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.approvals import approval_record_from_row


def build_repository() -> ApprovalsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return ApprovalsRepository(client)


def test_new_approval_defaults_to_pending() -> None:
    repository = build_repository()

    approval = repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="publish_campaign",
        payload_snapshot={"campaign_id": "camp-1"},
    )

    assert approval.status == "pending"
    assert approval.actor_id is None
    assert approval.approved_at is None


def test_approving_row_stores_actor_id_and_approved_at() -> None:
    repository = build_repository()
    approval = repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="publish_campaign",
        payload_snapshot={"campaign_id": "camp-1"},
    )

    approved = repository.approve(approval.id, actor_id="hermes-operator")

    assert approved is not None
    assert approved.status == "approved"
    assert approved.actor_id == "hermes-operator"
    assert approved.approved_at is not None


def test_fetching_missing_approval_returns_none() -> None:
    repository = build_repository()

    assert repository.get("apr_missing") is None


def test_approval_repository_registers_runtime_to_sql_identity_mapping() -> None:
    store = InMemoryControlPlaneStore()
    repository = ApprovalsRepository(InMemoryControlPlaneClient(store))

    approval = repository.create(
        command_id="cmd_123",
        business_id=1,
        environment="dev",
        command_type="publish_campaign",
        payload_snapshot={"campaign_id": "camp-1"},
    )

    assert store.approval_runtime_to_sql_id[approval.id] == 1


def test_approval_row_mapping_bridges_decided_at_and_approved_by_drift() -> None:
    row = {
        "id": 13,
        "runtime_id": "apr_runtime_13",
        "command_runtime_id": "cmd_runtime_9",
        "business_id": 1,
        "environment": "dev",
        "command_type": "publish_campaign",
        "status": "approved",
        "payload_snapshot": {"campaign_id": "camp-1"},
        "created_at": "2026-04-13T18:00:00+00:00",
        "decided_at": "2026-04-13T18:05:00+00:00",
        "approved_by": "hermes-operator",
    }

    approval = approval_record_from_row(row)

    assert approval.id == "apr_runtime_13"
    assert approval.command_id == "cmd_runtime_9"
    assert approval.approved_at is not None
    assert approval.actor_id == "hermes-operator"
