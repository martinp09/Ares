import pytest

from app.db.agents import AgentsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.release_management import ReleaseManagementRepository
from app.models.agents import AgentRevisionState
from app.models.release_management import ReleaseEventType


def build_repositories() -> tuple[AgentsRepository, ReleaseManagementRepository]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return AgentsRepository(client), ReleaseManagementRepository(client)


def test_publish_and_rollback_append_immutable_release_events_and_move_active_pointer() -> None:
    agents_repository, release_repository = build_repositories()

    agent, first_revision = agents_repository.create_agent(
        business_id="limitless",
        environment="prod",
        name="Release Repo Agent",
        description=None,
        config={"prompt": "Handle release transitions"},
        release_channel="canary",
    )

    published_agent, published_first, first_event = release_repository.publish_revision(
        agent.id,
        first_revision.id,
        actor_id="usr_release",
        actor_type="user",
        notes="Initial production publish",
    )

    assert published_agent.active_revision_id == first_revision.id
    assert published_first.state == AgentRevisionState.PUBLISHED
    assert first_event.event_type == ReleaseEventType.PUBLISH
    assert first_event.previous_active_revision_id is None
    assert first_event.target_revision_id == first_revision.id
    assert first_event.resulting_active_revision_id == first_revision.id
    assert first_event.release_channel == "canary"

    _, second_revision = agents_repository.clone_revision(agent.id, first_revision.id)
    promoted_agent, promoted_second, second_event = release_repository.publish_revision(
        agent.id,
        second_revision.id,
        actor_id="usr_release",
        actor_type="user",
        notes="Promote cloned revision",
    )

    assert promoted_agent.active_revision_id == second_revision.id
    assert promoted_second.state == AgentRevisionState.PUBLISHED
    assert second_event.event_type == ReleaseEventType.PUBLISH
    assert second_event.previous_active_revision_id == first_revision.id
    assert agents_repository.get_revision(first_revision.id).state == AgentRevisionState.DEPRECATED

    first_revision_after_publish = agents_repository.get_revision(first_revision.id)
    rolled_back_agent, rolled_back_revision, rollback_event = release_repository.rollback_revision(
        agent.id,
        first_revision.id,
        actor_id="usr_release",
        actor_type="user",
        notes="Rollback to known-good revision",
    )

    assert rolled_back_agent.active_revision_id == rolled_back_revision.id
    assert rolled_back_revision.id != first_revision.id
    assert rolled_back_revision.state == AgentRevisionState.PUBLISHED
    assert rolled_back_revision.cloned_from_revision_id == first_revision.id
    assert rolled_back_revision.revision_number == 3
    assert rolled_back_revision.published_at is not None
    assert rollback_event.event_type == ReleaseEventType.ROLLBACK
    assert rollback_event.previous_active_revision_id == second_revision.id
    assert rollback_event.target_revision_id == first_revision.id
    assert rollback_event.resulting_active_revision_id == rolled_back_revision.id
    assert agents_repository.get_revision(first_revision.id).published_at == first_revision_after_publish.published_at
    assert agents_repository.get_revision(first_revision.id).state == AgentRevisionState.DEPRECATED
    assert agents_repository.get_revision(second_revision.id).state == AgentRevisionState.DEPRECATED
    revisions = agents_repository.list_revisions(agent.id)
    assert [revision.revision_number for revision in revisions] == [1, 2, 3]

    events = release_repository.list_events(agent.id)
    assert [event.event_type for event in events] == [
        ReleaseEventType.PUBLISH,
        ReleaseEventType.PUBLISH,
        ReleaseEventType.ROLLBACK,
    ]
    assert events[0].target_revision_id == first_revision.id
    assert events[1].target_revision_id == second_revision.id
    assert events[2].target_revision_id == first_revision.id
    assert events[2].resulting_active_revision_id == rolled_back_revision.id


def test_rollback_rejects_revisions_that_were_never_published() -> None:
    agents_repository, release_repository = build_repositories()

    agent, first_revision = agents_repository.create_agent(
        business_id="limitless",
        environment="prod",
        name="Release Validation Agent",
        description=None,
        config={"prompt": "Protect rollback invariants"},
    )
    release_repository.publish_revision(
        agent.id,
        first_revision.id,
        actor_id="usr_release",
        actor_type="user",
    )
    _, draft_revision = agents_repository.clone_revision(agent.id, first_revision.id)

    with pytest.raises(ValueError, match="Only previously published revisions can be rolled back"):
        release_repository.rollback_revision(
            agent.id,
            draft_revision.id,
            actor_id="usr_release",
            actor_type="user",
        )
