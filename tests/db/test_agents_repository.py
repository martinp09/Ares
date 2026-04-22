import pytest

from app.db.agents import AgentsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.models.agents import AgentLifecycleStatus, AgentRevisionState


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


def test_candidate_and_deprecated_revision_states_are_supported_in_repository_transitions() -> None:
    repository = build_repository()

    agent, first_revision = repository.create_agent(
        business_id="limitless",
        environment="prod",
        name="Lifecycle Repo Agent",
        description=None,
        config={"prompt": "Manage staged launches"},
        release_channel="canary",
    )

    candidate_agent, candidate_revision = repository.promote_revision_to_candidate(agent.id, first_revision.id)
    assert candidate_agent.lifecycle_status == AgentLifecycleStatus.DRAFT
    assert candidate_revision.state == AgentRevisionState.CANDIDATE
    assert candidate_revision.release_channel == "canary"

    published_agent, published_first = repository.publish_revision(agent.id, first_revision.id)
    assert published_agent.active_revision_id == first_revision.id
    assert published_first.state == AgentRevisionState.PUBLISHED

    _, second_revision = repository.clone_revision(agent.id, first_revision.id)
    _, second_candidate = repository.promote_revision_to_candidate(agent.id, second_revision.id)
    assert second_candidate.state == AgentRevisionState.CANDIDATE
    assert second_candidate.release_channel == "canary"

    republished_agent, published_second = repository.publish_revision(agent.id, second_revision.id)
    assert republished_agent.active_revision_id == second_revision.id
    assert published_second.state == AgentRevisionState.PUBLISHED
    assert repository.get_revision(first_revision.id).state == AgentRevisionState.DEPRECATED

    with pytest.raises(ValueError, match="Deprecated revisions cannot be republished"):
        repository.publish_revision(agent.id, first_revision.id)


def test_archiving_latest_published_revision_with_only_deprecated_remaining_marks_agent_deprecated() -> None:
    repository = build_repository()

    agent, first_revision = repository.create_agent(
        business_id="limitless",
        environment="prod",
        name="Archive Repo Agent",
        description=None,
        config={"prompt": "Handle deprecation fallback"},
    )
    repository.publish_revision(agent.id, first_revision.id)
    _, second_revision = repository.clone_revision(agent.id, first_revision.id)
    repository.publish_revision(agent.id, second_revision.id)

    archived_agent, archived_revision = repository.archive_revision(agent.id, second_revision.id)

    assert archived_revision.state == AgentRevisionState.ARCHIVED
    assert archived_agent.active_revision_id is None
    assert archived_agent.lifecycle_status == AgentLifecycleStatus.DEPRECATED
    assert repository.get_revision(first_revision.id).state == AgentRevisionState.DEPRECATED
