from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.commands import CommandsRepository
from app.models.commands import CommandPolicy, CommandStatus


def build_repository() -> CommandsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return CommandsRepository(client)


def test_create_same_command_twice_returns_same_command_row() -> None:
    repository = build_repository()

    first = repository.create(
        business_id="limitless",
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-001",
        payload={"topic": "houston tired landlords"},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    second = repository.create(
        business_id="limitless",
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
        business_id="limitless",
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-002",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    second = repository.create(
        business_id="limitless",
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
        business_id="limitless",
        environment="dev",
        command_type="run_market_research",
        idempotency_key="cmd-003",
        payload={},
        policy=CommandPolicy.SAFE_AUTONOMOUS,
        status=CommandStatus.ACCEPTED,
    )
    second = repository.create(
        business_id="limitless",
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
        business_id="limitless",
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
