from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.commands import router as commands_router
from app.api.release_management import router as release_management_router
from app.api.replays import router as replays_router
from app.db.client import STORE
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, actor_id: str, actor_type: str = "user", org_id: str = "org_internal") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def build_client() -> TestClient:
    app = FastAPI()
    app.include_router(agents_router)
    app.include_router(commands_router)
    app.include_router(approvals_router)
    app.include_router(release_management_router)
    app.include_router(replays_router)
    return TestClient(app)


def create_published_agent(client, *, release_channel: str = "internal") -> tuple[str, str]:
    created = client.post(
        "/agents",
        json={
            "name": "Replay Agent",
            "config": {"prompt": "Replay through the adapter seam"},
            "host_adapter_kind": "trigger_dev",
            "host_adapter_config": {"queue": "priority"},
            "release_channel": release_channel,
        },
        headers=AUTH_HEADERS,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200
    return agent_id, revision_id


def supersede_published_revision(client, agent_id: str, revision_id: str) -> str:
    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=AUTH_HEADERS,
    )
    assert clone_response.status_code == 200
    next_revision_id = clone_response.json()["revisions"][-1]["id"]
    publish_response = client.post(
        f"/agents/{agent_id}/revisions/{next_revision_id}/publish",
        headers=AUTH_HEADERS,
    )
    assert publish_response.status_code == 200
    revisions = {revision["id"]: revision for revision in publish_response.json()["revisions"]}
    assert revisions[revision_id]["state"] == "deprecated"
    assert revisions[next_revision_id]["state"] == "published"
    return next_revision_id


def test_safe_autonomous_run_can_be_replayed_without_new_approval() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030",
            "payload": {"topic": "san antonio landlords"},
        },
        headers=AUTH_HEADERS,
    )
    run_id = command_response.json()["run_id"]

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "new market context"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["requires_approval"] is False
    assert body["parent_run_id"] == run_id
    assert body["child_run_id"] is not None


def test_safe_autonomous_replay_preserves_original_command_run_id() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-preserve-original-run",
            "payload": {"topic": "san antonio landlords"},
        },
        headers=AUTH_HEADERS,
    )
    command_body = command_response.json()
    command_id = command_body["id"]
    original_run_id = command_body["run_id"]

    response = client.post(
        f"/replays/{original_run_id}",
        json={"reason": "new market context"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    child_run_id = response.json()["child_run_id"]
    assert child_run_id is not None
    assert STORE.commands[command_id].run_id == original_run_id
    assert STORE.runs[original_run_id].command_id == command_id
    assert STORE.runs[child_run_id].command_id != command_id
    replay_command = STORE.commands[STORE.runs[child_run_id].command_id]
    assert replay_command.run_id == child_run_id
    assert replay_command.payload == {"topic": "san antonio landlords"}


def test_agent_backed_safe_autonomous_replay_dispatches_child_run_through_adapter_seam() -> None:
    reset_control_plane_state()
    client = build_client()
    _, revision_id = create_published_agent(client, release_channel="dogfood")

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay",
            "payload": {"topic": "san antonio landlords"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]

    initial_dispatches = HostAdapterDispatchesRepository().list()
    assert len(initial_dispatches) == 1
    assert initial_dispatches[0].run_id == run_id
    assert initial_dispatches[0].agent_revision_id == revision_id

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "new market context"},
        headers=org_actor_headers(actor_id="ops-42"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["requires_approval"] is False
    assert body["parent_run_id"] == run_id
    assert body["child_run_id"] is not None
    assert body["lineage"]["triggering_actor"] == {
        "org_id": "org_internal",
        "actor_id": "ops-42",
        "actor_type": "user",
    }
    assert body["lineage"]["source"]["agent_id"] == initial_dispatches[0].agent_id
    assert body["lineage"]["source"]["agent_revision_id"] == revision_id
    assert body["lineage"]["source"]["active_revision_id"] == revision_id
    assert body["lineage"]["source"]["revision_state"] == "published"
    assert body["lineage"]["source"]["release_channel"] == "dogfood"
    assert body["lineage"]["source"]["release_event_type"] == "publish"
    assert body["lineage"]["source"]["release_event_id"] is not None
    assert body["lineage"]["replay"]["agent_id"] == initial_dispatches[0].agent_id
    assert body["lineage"]["replay"]["agent_revision_id"] == revision_id
    assert body["lineage"]["replay"]["active_revision_id"] == revision_id
    assert body["lineage"]["replay"]["revision_state"] == "published"
    assert body["lineage"]["replay"]["release_channel"] == "dogfood"
    assert body["lineage"]["replay"]["release_event_type"] == "publish"
    assert body["lineage"]["replay"]["release_event_id"] == body["lineage"]["source"]["release_event_id"]

    dispatches = HostAdapterDispatchesRepository().list()
    assert len(dispatches) == 2
    assert dispatches[1].agent_revision_id == revision_id
    assert dispatches[1].run_id == body["child_run_id"]
    assert dispatches[1].external_reference == body["child_run_id"]
    parent_replay_events = [
        event for event in STORE.runs[run_id].events if event.get("event_type") == "replay_requested"
    ]
    assert len(parent_replay_events) == 1
    assert parent_replay_events[0]["payload"]["child_run_id"] == body["child_run_id"]
    assert parent_replay_events[0]["payload"]["triggering_actor"]["actor_id"] == "ops-42"
    child_lineage_events = [
        event for event in STORE.runs[body["child_run_id"]].events if event.get("event_type") == "replay_lineage_bound"
    ]
    assert len(child_lineage_events) == 1
    assert child_lineage_events[0]["payload"]["parent_run_id"] == run_id
    assert child_lineage_events[0]["payload"]["source"]["agent_revision_id"] == revision_id


def test_agent_backed_safe_autonomous_replay_allows_superseded_deprecated_revision() -> None:
    reset_control_plane_state()
    client = build_client()
    agent_id, revision_id = create_published_agent(client)

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay-deprecated",
            "payload": {"topic": "san antonio landlords"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]

    superseded_revision_id = supersede_published_revision(client, agent_id, revision_id)
    assert superseded_revision_id != revision_id

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "rerun pinned historical release"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["requires_approval"] is False
    assert body["parent_run_id"] == run_id
    assert body["child_run_id"] is not None

    dispatches = HostAdapterDispatchesRepository().list()
    assert len(dispatches) == 2
    assert dispatches[0].agent_revision_id == revision_id
    assert dispatches[1].agent_revision_id == revision_id
    assert dispatches[1].run_id == body["child_run_id"]
    assert dispatches[1].external_reference == body["child_run_id"]


def test_replay_source_context_uses_current_active_revision_for_superseded_source_run() -> None:
    reset_control_plane_state()
    client = build_client()
    agent_id, original_revision_id = create_published_agent(client, release_channel="internal")
    current_active_revision_id = supersede_published_revision(client, agent_id, original_revision_id)

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay-superseded-source",
            "payload": {"topic": "superseded source context"},
            "agent_revision_id": original_revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "inspect source release context"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    lineage = response.json()["lineage"]
    assert lineage["source"]["agent_revision_id"] == original_revision_id
    assert lineage["source"]["revision_state"] == "deprecated"
    assert lineage["source"]["active_revision_id"] == current_active_revision_id
    assert lineage["replay"]["agent_revision_id"] == original_revision_id
    assert lineage["replay"]["active_revision_id"] == current_active_revision_id


def test_agent_backed_safe_autonomous_replay_stays_pinned_to_original_revision_after_clone_based_rollback() -> None:
    reset_control_plane_state()
    client = build_client()
    agent_id, revision_id = create_published_agent(client, release_channel="dogfood")

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay-rollback",
            "payload": {"topic": "san antonio landlords"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]

    superseded_revision_id = supersede_published_revision(client, agent_id, revision_id)
    assert superseded_revision_id != revision_id

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{revision_id}/rollback",
        json={"notes": "return to known-good baseline"},
        headers=AUTH_HEADERS,
    )
    assert rollback_response.status_code == 200
    rollback_body = rollback_response.json()
    rollback_active_revision_id = rollback_body["agent"]["active_revision_id"]
    assert rollback_active_revision_id not in {revision_id, superseded_revision_id}
    assert rollback_body["event"]["target_revision_id"] == revision_id
    assert rollback_body["event"]["resulting_active_revision_id"] == rollback_active_revision_id

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "rerun original historical release"},
        headers=org_actor_headers(actor_id="ops-rollback"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["lineage"]["source"]["agent_revision_id"] == revision_id
    assert body["lineage"]["source"]["active_revision_id"] == revision_id
    assert body["lineage"]["source"]["release_event_type"] == "publish"
    assert body["lineage"]["source"]["release_channel"] == "dogfood"
    assert body["lineage"]["replay"]["agent_revision_id"] == revision_id
    assert body["lineage"]["replay"]["active_revision_id"] == rollback_active_revision_id
    assert body["lineage"]["replay"]["release_event_id"] == rollback_body["event"]["id"]
    assert body["lineage"]["replay"]["release_event_type"] == "rollback"
    assert body["lineage"]["replay"]["release_channel"] == "dogfood"
    dispatches = HostAdapterDispatchesRepository().list()
    assert len(dispatches) == 2
    assert dispatches[0].agent_revision_id == revision_id
    assert dispatches[1].agent_revision_id == revision_id
    assert dispatches[1].agent_revision_id != rollback_active_revision_id
    assert dispatches[1].run_id == body["child_run_id"]


def test_agent_backed_safe_autonomous_replay_fails_cleanly_when_revision_is_no_longer_dispatchable() -> None:
    reset_control_plane_state()
    client = build_client()
    agent_id, revision_id = create_published_agent(client)

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay-archived",
            "payload": {"topic": "san antonio landlords"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]

    superseded_revision_id = supersede_published_revision(client, agent_id, revision_id)
    assert superseded_revision_id != revision_id

    archive_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/archive",
        headers=AUTH_HEADERS,
    )
    assert archive_response.status_code == 200

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "new market context"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Archived revisions cannot be dispatched"
    assert len(STORE.commands) == 1
    assert len(STORE.runs) == 1
    dispatches = HostAdapterDispatchesRepository().list()
    assert len(dispatches) == 1
    assert dispatches[0].run_id == run_id


def test_safe_autonomous_replay_prevalidates_once_before_creating_replay_command(monkeypatch) -> None:
    from app.services.run_service import run_service

    reset_control_plane_state()
    client = build_client()
    _, revision_id = create_published_agent(client)

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay-single-validate",
            "payload": {"topic": "single validation only"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]
    initial_command_ids = set(STORE.commands)

    call_count = {"count": 0}
    original_validate = run_service.agent_execution_service.validate_dispatchable

    def flaky_validate(agent_revision_id: str) -> None:
        call_count["count"] += 1
        if call_count["count"] > 1:
            raise ValueError("synthetic second validation failure")
        original_validate(agent_revision_id)

    monkeypatch.setattr(run_service.agent_execution_service, "validate_dispatchable", flaky_validate)

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "prove single validation"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    assert call_count["count"] == 1
    assert len(set(STORE.commands) - initial_command_ids) == 1


def test_safe_autonomous_replay_rolls_back_replay_command_and_run_when_dispatch_fails_after_persistence(monkeypatch) -> None:
    from app.services.run_service import run_service

    reset_control_plane_state()
    client = build_client()
    _, revision_id = create_published_agent(client)

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-030-agent-replay-dispatch-failure",
            "payload": {"topic": "dispatch failure rollback"},
            "agent_revision_id": revision_id,
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]
    initial_command_ids = set(STORE.commands)
    initial_run_ids = set(STORE.runs)
    initial_dispatch_count = len(HostAdapterDispatchesRepository().list())

    original_dispatch = run_service.agent_execution_service.dispatch_revision

    def failing_dispatch(*args, **kwargs):
        raise ValueError("synthetic dispatch failure after run creation")

    monkeypatch.setattr(run_service.agent_execution_service, "dispatch_revision", failing_dispatch)

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "prove rollback on dispatch failure"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "synthetic dispatch failure after run creation"
    assert set(STORE.commands) == initial_command_ids
    assert set(STORE.runs) == initial_run_ids
    assert len(HostAdapterDispatchesRepository().list()) == initial_dispatch_count

    monkeypatch.setattr(run_service.agent_execution_service, "dispatch_revision", original_dispatch)


def test_side_effecting_run_replay_requires_reapproval() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-031",
            "payload": {"campaign_id": "camp-3"},
        },
        headers=AUTH_HEADERS,
    )
    approval_id = command_response.json()["approval_id"]
    approval_response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "ops-1"},
        headers=AUTH_HEADERS,
    )
    run_id = approval_response.json()["run_id"]

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "rerun delivery"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 409
    body = response.json()
    assert body["requires_approval"] is True
    assert body["approval_id"] is not None


def test_side_effecting_replay_records_no_child_run_until_approval() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-031-side-effect-audit",
            "payload": {"campaign_id": "camp-4"},
        },
        headers=AUTH_HEADERS,
    )
    approval_id = command_response.json()["approval_id"]
    approval_response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "ops-1"},
        headers=AUTH_HEADERS,
    )
    run_id = approval_response.json()["run_id"]
    run_ids_before_replay = set(STORE.runs)

    response = client.post(
        f"/replays/{run_id}",
        json={"reason": "rerun delivery"},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 409
    body = response.json()
    assert body["child_run_id"] is None
    assert body["requires_approval"] is True
    assert set(STORE.runs) == run_ids_before_replay
    parent_replay_events = [
        event for event in STORE.runs[run_id].events if event.get("event_type") == "replay_requested"
    ]
    assert parent_replay_events[-1]["payload"]["requires_approval"] is True


def test_side_effecting_replay_records_approval_created_audit() -> None:
    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-031-replay-approval-audit",
            "payload": {"campaign_id": "camp-5"},
        },
        headers=AUTH_HEADERS,
    )
    approval_response = client.post(
        f"/approvals/{command_response.json()['approval_id']}/approve",
        json={"actor_id": "ops-1"},
        headers=AUTH_HEADERS,
    )
    run_id = approval_response.json()["run_id"]

    response = client.post(f"/replays/{run_id}", json={"reason": "audit approval"}, headers=AUTH_HEADERS)

    assert response.status_code == 409
    replay_approval_id = response.json()["approval_id"]
    approval_created_events = [
        event
        for event in STORE.audit_events.values()
        if event.event_type == "approval_created" and event.resource_id == replay_approval_id
    ]
    assert len(approval_created_events) == 1


def test_replay_observability_failure_does_not_fail_committed_replay(monkeypatch) -> None:
    from app.services.runtime_observability_service import runtime_observability_service

    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-031-replay-audit-failure",
            "payload": {"topic": "audit failure should not duplicate"},
        },
        headers=AUTH_HEADERS,
    )
    run_id = command_response.json()["run_id"]

    def fail_replay_audit(*args, **kwargs) -> None:
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(runtime_observability_service, "record_replay_requested", fail_replay_audit)

    response = client.post(f"/replays/{run_id}", json={"reason": "nonfatal audit"}, headers=AUTH_HEADERS)

    assert response.status_code == 201
    body = response.json()
    assert body["child_run_id"] is not None
    assert body["child_run_id"] in STORE.runs


def test_replay_run_created_observability_failure_does_not_orphan_child_run(monkeypatch) -> None:
    from app.services.runtime_observability_service import runtime_observability_service

    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-031-replay-run-audit-failure",
            "payload": {"topic": "run audit failure should not orphan"},
        },
        headers=AUTH_HEADERS,
    )
    run_id = command_response.json()["run_id"]

    def fail_run_created(*args, **kwargs) -> None:
        raise RuntimeError("synthetic run audit failure")

    monkeypatch.setattr(runtime_observability_service, "record_run_created", fail_run_created)

    response = client.post(f"/replays/{run_id}", json={"reason": "nonfatal run audit"}, headers=AUTH_HEADERS)

    assert response.status_code == 201
    child_run_id = response.json()["child_run_id"]
    child_run = STORE.runs[child_run_id]
    assert child_run.command_id in STORE.commands
    assert STORE.commands[child_run.command_id].run_id == child_run_id


def test_side_effecting_replay_approval_audit_failure_does_not_fail_replay(monkeypatch) -> None:
    from app.services.runtime_observability_service import runtime_observability_service

    reset_control_plane_state()
    client = build_client()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-031-replay-approval-audit-failure",
            "payload": {"campaign_id": "camp-audit-failure"},
        },
        headers=AUTH_HEADERS,
    )
    approval_response = client.post(
        f"/approvals/{command_response.json()['approval_id']}/approve",
        json={"actor_id": "ops-1"},
        headers=AUTH_HEADERS,
    )
    run_id = approval_response.json()["run_id"]

    def fail_approval_audit(*args, **kwargs) -> None:
        raise RuntimeError("synthetic approval audit failure")

    monkeypatch.setattr(runtime_observability_service, "record_approval_created", fail_approval_audit)

    response = client.post(f"/replays/{run_id}", json={"reason": "nonfatal approval audit"}, headers=AUTH_HEADERS)

    assert response.status_code == 409
    replay_approval_id = response.json()["approval_id"]
    assert replay_approval_id in STORE.approvals
    replay_command_id = STORE.approvals[replay_approval_id].command_id
    assert replay_command_id in STORE.commands
    assert STORE.commands[replay_command_id].approval_id == replay_approval_id


def test_agent_backed_side_effecting_replay_approval_preserves_agent_scope() -> None:
    reset_control_plane_state()
    client = build_client()
    agent_id, revision_id = create_published_agent(client)
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-031-agent-replay-approval-scope",
            "payload": {"campaign_id": "camp-agent-replay"},
            "agent_revision_id": revision_id,
        },
        headers=org_actor_headers(actor_id="ops-alpha", org_id="org_internal"),
    )
    approval_response = client.post(
        f"/approvals/{command_response.json()['approval_id']}/approve",
        json={"actor_id": "ops-1"},
        headers=AUTH_HEADERS,
    )
    run_id = approval_response.json()["run_id"]
    replay_response = client.post(f"/replays/{run_id}", json={"reason": "agent scoped replay"}, headers=AUTH_HEADERS)
    assert replay_response.status_code == 409

    approved_replay = client.post(
        f"/approvals/{replay_response.json()['approval_id']}/approve",
        json={"actor_id": "ops-2"},
        headers=AUTH_HEADERS,
    )

    assert approved_replay.status_code == 200
    child_run_id = approved_replay.json()["run_id"]
    child_run_events = [
        event
        for event in STORE.audit_events.values()
        if event.event_type == "run_created" and event.run_id == child_run_id
    ]
    assert len(child_run_events) == 1
    assert child_run_events[0].agent_id == agent_id
    assert child_run_events[0].agent_revision_id == revision_id
