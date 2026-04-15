from app.db.approvals import ApprovalsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore


def build_repository() -> ApprovalsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return ApprovalsRepository(client)


def test_new_approval_defaults_to_pending() -> None:
    repository = build_repository()

    approval = repository.create(
        command_id="cmd_123",
        business_id="limitless",
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
        business_id="limitless",
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
