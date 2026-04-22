import pytest

from app.db.agents import AgentsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.models.agents import AgentLifecycleStatus


def build_repository() -> AgentsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return AgentsRepository(client)


def test_create_agent_rejects_non_draft_lifecycle_status_at_repository_boundary() -> None:
    repository = build_repository()

    with pytest.raises(ValueError, match="lifecycle_status='draft'"):
        repository.create_agent(
            business_id="limitless",
            environment="dev",
            name="Broken Repo Agent",
            description=None,
            lifecycle_status=AgentLifecycleStatus.ACTIVE,
            config={"prompt": "Should fail"},
        )
