from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.commands import (
    CommandsRepository,
    command_policy_from_sql_policy_result,
    command_policy_to_sql_policy_result,
    command_record_from_row,
    command_status_from_sql_status,
    command_status_to_sql_status,
)
from app.models.commands import CommandPolicy, CommandStatus


def build_repository() -> CommandsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return CommandsRepository(client)


def test_create_same_command_twice_returns_same_command_row() -> None:
    repository = build_repository()

    first = repository.create(
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-001",
        payload={"topic": "houston tired landlords"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    second = repository.create(
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-001",
        payload={"topic": "houston tired landlords"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    assert first.id == second.id
    assert first.deduped is False
    assert second.deduped is True


def test_different_environment_does_not_collide_with_same_idempotency_key() -> None:
    repository = build_repository()

    first = repository.create(
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-002",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    second = repository.create(
        business_id=1,
        environment="prod",
        command_type="run_market_research",
        idempotency_key="cmd-002",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    assert first.id != second.id
    assert second.deduped is False


def test_different_command_type_does_not_collide_with_same_idempotency_key() -> None:
    repository = build_repository()

    first = repository.create(
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-003",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    second = repository.create(
        business_id=1,
        environment="dev",
        command_type="create_campaign_brief",
        idempotency_key="cmd-003",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    assert first.id != second.id
    assert second.deduped is False


def test_repository_returns_normalized_command_shape_with_deduped_support() -> None:
    repository = build_repository()

    command = repository.create(
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-004",
        payload={"topic": "dallas wholesalers"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    assert command.model_dump().keys() >= {
        "id",
        "business_id",
        "environment",
        "command_type",
        "idempotency_key",
        "payload",
        "policy",
        "status",
        "approval_id",
        "run_id",
        "deduped",
        "created_at",
    }
    assert command.deduped is False


def test_command_repository_registers_runtime_to_sql_identity_mapping() -> None:
    store = InMemoryControlPlaneStore()
    repository = CommandsRepository(InMemoryControlPlaneClient(store))

    command = repository.create(
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-005",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    duplicate = repository.create(
        business_id=1,
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-005",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )

    assert store.command_runtime_to_sql_id[command.id] == 1
    assert store.command_runtime_to_sql_id[duplicate.id] == 1


def test_command_sql_compatibility_mappings_cover_status_and_policy_drift() -> None:
    assert command_status_to_sql_status(CommandStatus.ACCEPTED) == "queued"
    assert command_status_to_sql_status(CommandStatus.AWAITING_APPROVAL) == "approval_required"
    assert command_status_from_sql_status("approval_required") == CommandStatus.AWAITING_APPROVAL

    assert command_policy_to_sql_policy_result(CommandPolicy.FORBIDDEN) == "blocked"
    assert command_policy_from_sql_policy_result("blocked") == CommandPolicy.FORBIDDEN


def test_command_row_mapping_prefers_runtime_compatibility_columns() -> None:
    row = {
        "id": 7,
        "runtime_id": "cmd_runtime_7",
        "business_id": 1,
        "environment": "dev",
        "command_type": "run_market_research",
        "payload": {"topic": "houston tired landlords"},
        "idempotency_key": "cmd-006",
        "runtime_policy": "safe_autonomous",
        "runtime_status": "accepted",
        "created_at": "2026-04-13T18:00:00+00:00",
    }

    command = command_record_from_row(row)

    assert command.id == "cmd_runtime_7"
    assert command.policy == CommandPolicy.SAFE_AUTONOMOUS
    assert command.status == CommandStatus.ACCEPTED
