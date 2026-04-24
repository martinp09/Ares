import pytest

from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def audit_headers(*, org_id: str = "org_internal", actor_id: str = "ares-runtime", actor_type: str = "service") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }


def test_audit_api_derives_actor_context_scopes_reads_and_scrubs_metadata(client) -> None:
    reset_control_plane_state()

    alpha_headers = audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user")
    beta_headers = audit_headers(org_id="org_beta", actor_id="actor_beta", actor_type="service")

    alpha_response = client.post(
        "/audit",
        json={
            "event_type": "secret_created",
            "summary": "Created secret",
            "resource_type": "secret",
            "resource_id": "sec_alpha",
            "metadata": {
                "secret_value": "super-secret",
                "nested": {"access_token": "nested-secret"},
                "safe": "kept",
            },
        },
        headers=alpha_headers,
    )
    beta_response = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Read secret metadata",
            "resource_type": "secret",
            "resource_id": "sec_beta",
            "metadata": {"safe": "visible"},
        },
        headers=beta_headers,
    )

    assert alpha_response.status_code == 200
    assert beta_response.status_code == 200
    alpha_body = alpha_response.json()
    assert alpha_body["org_id"] == "org_alpha"
    assert alpha_body["actor_id"] == "actor_alpha"
    assert alpha_body["actor_type"] == "user"
    assert alpha_body["metadata"] == {
        "secret_value": "[redacted]",
        "nested": {"access_token": "[redacted]"},
        "safe": "kept",
    }

    listing = client.get("/audit", headers=alpha_headers)
    assert listing.status_code == 200
    events = listing.json()["events"]
    assert [event["org_id"] for event in events] == ["org_alpha"]
    assert [event["actor_id"] for event in events] == ["actor_alpha"]
    assert events[0]["metadata"] == alpha_body["metadata"]

    mismatched_listing = client.get("/audit?org_id=org_beta", headers=alpha_headers)
    assert mismatched_listing.status_code == 422
    assert mismatched_listing.json()["detail"] == "Org id must match actor context"


@pytest.mark.parametrize(
    ("payload", "detail"),
    [
        ({"org_id": "org_beta"}, "Org id must match actor context"),
        ({"actor_id": "actor_beta"}, "Actor id must match actor context"),
        ({"actor_type": "service"}, "Actor type must match actor context"),
    ],
)
def test_audit_api_rejects_conflicting_actor_context_fields(client, payload: dict[str, str], detail: str) -> None:
    reset_control_plane_state()

    response = client.post(
        "/audit",
        json={
            "event_type": "secret_created",
            "summary": "Created secret",
            **payload,
        },
        headers=audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user"),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == detail


def test_runtime_actions_append_audit_events(client) -> None:
    reset_control_plane_state()

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-audit-publish",
            "payload": {"campaign_id": "camp-audit"},
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    approval_id = command_response.json()["approval_id"]

    approval_response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "ops-audit"},
        headers=AUTH_HEADERS,
    )
    assert approval_response.status_code == 200
    run_id = approval_response.json()["run_id"]

    started_response = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={"trigger_run_id": "trg-audit-started"},
        headers=AUTH_HEADERS,
    )
    completed_response = client.post(
        f"/trigger/callbacks/runs/{run_id}/completed",
        json={"trigger_run_id": "trg-audit-completed"},
        headers=AUTH_HEADERS,
    )
    replay_response = client.post(
        f"/replays/{run_id}",
        json={"reason": "audit replay"},
        headers=audit_headers(actor_id="ops-replay", actor_type="user"),
    )

    assert started_response.status_code == 200
    assert completed_response.status_code == 200
    assert replay_response.status_code == 409

    listing = client.get("/audit", headers=AUTH_HEADERS)
    assert listing.status_code == 200
    events = listing.json()["events"]
    event_types = [event["event_type"] for event in events]
    assert "hermes_command_invoked" in event_types
    assert "approval_created" in event_types
    assert "approval_approved" in event_types
    assert "run_created" in event_types
    assert "trigger_run_started" in event_types
    assert "trigger_run_completed" in event_types
    assert "replay_requested" in event_types

    replay_events = [event for event in events if event["event_type"] == "replay_requested"]
    assert replay_events[0]["run_id"] == run_id
    assert replay_events[0]["actor_id"] == "ops-replay"


def test_repeated_approval_does_not_duplicate_approval_approved_audit(client) -> None:
    reset_control_plane_state()

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-audit-approval-repeat",
            "payload": {"campaign_id": "camp-repeat"},
        },
        headers=AUTH_HEADERS,
    )
    approval_id = command_response.json()["approval_id"]

    first = client.post(f"/approvals/{approval_id}/approve", json={"actor_id": "ops-1"}, headers=AUTH_HEADERS)
    second = client.post(f"/approvals/{approval_id}/approve", json={"actor_id": "ops-2"}, headers=AUTH_HEADERS)
    assert first.status_code == 200
    assert second.status_code == 200

    listing = client.get("/audit?event_type=approval_approved", headers=AUTH_HEADERS)
    assert listing.status_code == 200
    events = listing.json()["events"]
    assert len(events) == 1
    assert events[0]["resource_id"] == approval_id
    assert events[0]["actor_id"] == "ops-1"


def test_agent_backed_trigger_audit_stays_scoped_to_agent_org(client) -> None:
    reset_control_plane_state()

    headers = audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user")
    created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Alpha Audit Agent",
            "config": {"prompt": "Track audit"},
            "host_adapter_kind": "trigger_dev",
        },
        headers=headers,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=headers)
    assert publish_response.status_code == 200

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-audit-agent-org",
            "payload": {"topic": "org-scoped runtime audit"},
            "agent_revision_id": revision_id,
        },
        headers=headers,
    )
    assert command_response.status_code == 201
    run_id = command_response.json()["run_id"]
    started_response = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={"trigger_run_id": "trg-audit-agent-org"},
        headers=AUTH_HEADERS,
    )
    assert started_response.status_code == 200

    alpha_listing = client.get("/audit", headers=headers)
    internal_listing = client.get("/audit", headers=AUTH_HEADERS)
    assert alpha_listing.status_code == 200
    assert internal_listing.status_code == 200
    alpha_events = alpha_listing.json()["events"]
    assert "trigger_run_started" in [event["event_type"] for event in alpha_events]
    assert {event["agent_id"] for event in alpha_events if event["agent_id"] is not None} == {agent_id}
    assert {event["agent_revision_id"] for event in alpha_events if event["agent_revision_id"] is not None} == {revision_id}
    assert "trigger_run_started" not in [event["event_type"] for event in internal_listing.json()["events"]]


def test_agent_backed_approval_audit_and_run_observability_stay_scoped_to_agent_org(client) -> None:
    reset_control_plane_state()

    headers = audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user")
    created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Alpha Approval Agent",
            "config": {"prompt": "Track approval audit"},
            "host_adapter_kind": "trigger_dev",
        },
        headers=headers,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=headers)
    assert publish_response.status_code == 200

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-audit-agent-approval-org",
            "payload": {"campaign_id": "camp-agent-approval"},
            "agent_revision_id": revision_id,
        },
        headers=headers,
    )
    assert command_response.status_code == 201
    approval_id = command_response.json()["approval_id"]
    approval_response = client.post(f"/approvals/{approval_id}/approve", json={"actor_id": "ops-alpha"}, headers=headers)
    assert approval_response.status_code == 200

    alpha_listing = client.get("/audit", headers=headers)
    internal_listing = client.get("/audit", headers=AUTH_HEADERS)
    assert alpha_listing.status_code == 200
    assert internal_listing.status_code == 200
    alpha_events = [
        event
        for event in alpha_listing.json()["events"]
        if event["event_type"] in {"hermes_command_invoked", "approval_created", "approval_approved", "run_created"}
    ]
    assert [event["event_type"] for event in alpha_events] == [
        "run_created",
        "approval_approved",
        "approval_created",
        "hermes_command_invoked",
    ]
    assert {event["agent_id"] for event in alpha_events} == {agent_id}
    assert {event["agent_revision_id"] for event in alpha_events} == {revision_id}
    assert not [
        event
        for event in internal_listing.json()["events"]
        if event["event_type"] in {"approval_created", "approval_approved", "run_created"}
    ]


def test_deduped_command_observability_uses_persisted_agent_scope(client) -> None:
    reset_control_plane_state()

    alpha_headers = audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user")
    beta_headers = audit_headers(org_id="org_beta", actor_id="actor_beta", actor_type="user")
    alpha_created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Alpha Dedup Agent",
            "config": {"prompt": "Original scope"},
            "host_adapter_kind": "trigger_dev",
        },
        headers=alpha_headers,
    ).json()
    beta_created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Beta Dedup Agent",
            "config": {"prompt": "Retry scope"},
            "host_adapter_kind": "trigger_dev",
        },
        headers=beta_headers,
    ).json()
    alpha_revision_id = alpha_created["revisions"][0]["id"]
    beta_revision_id = beta_created["revisions"][0]["id"]
    assert client.post(f"/agents/{alpha_created['agent']['id']}/revisions/{alpha_revision_id}/publish", headers=alpha_headers).status_code == 200
    assert client.post(f"/agents/{beta_created['agent']['id']}/revisions/{beta_revision_id}/publish", headers=beta_headers).status_code == 200

    payload = {
        "business_id": "limitless",
        "environment": "dev",
        "command_type": "run_market_research",
        "idempotency_key": "cmd-audit-dedup-agent-scope",
        "payload": {"topic": "dedupe scope"},
    }
    first = client.post("/commands", json={**payload, "agent_revision_id": alpha_revision_id}, headers=alpha_headers)
    retry = client.post("/commands", json={**payload, "agent_revision_id": beta_revision_id}, headers=beta_headers)

    assert first.status_code == 201
    assert retry.status_code == 200
    alpha_listing = client.get("/audit?event_type=hermes_command_invoked", headers=alpha_headers)
    beta_listing = client.get("/audit?event_type=hermes_command_invoked", headers=beta_headers)
    assert len(alpha_listing.json()["events"]) == 2
    assert {event["agent_revision_id"] for event in alpha_listing.json()["events"]} == {alpha_revision_id}
    assert beta_listing.json()["events"] == []


def test_command_observability_failure_does_not_strand_command(monkeypatch, client) -> None:
    from app.services.runtime_observability_service import runtime_observability_service

    reset_control_plane_state()

    def fail_command_audit(*args, **kwargs) -> None:
        raise RuntimeError("synthetic command audit failure")

    monkeypatch.setattr(runtime_observability_service, "record_command_invoked", fail_command_audit)

    response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-audit-command-failure",
            "payload": {"topic": "nonfatal command audit"},
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["run_id"] is not None


def test_approval_observability_failure_does_not_block_approval_flow(monkeypatch, client) -> None:
    from app.services.runtime_observability_service import runtime_observability_service

    reset_control_plane_state()

    def fail_approval_audit(*args, **kwargs) -> None:
        raise RuntimeError("synthetic approval audit failure")

    monkeypatch.setattr(runtime_observability_service, "record_approval_created", fail_approval_audit)
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-audit-approval-create-failure",
            "payload": {"campaign_id": "camp-create-failure"},
        },
        headers=AUTH_HEADERS,
    )
    assert command_response.status_code == 201
    approval_id = command_response.json()["approval_id"]
    assert approval_id is not None

    monkeypatch.setattr(runtime_observability_service, "record_approval_created", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime_observability_service, "record_approval_approved", fail_approval_audit)
    approval_response = client.post(
        f"/approvals/{approval_id}/approve",
        json={"actor_id": "ops-audit-failure"},
        headers=AUTH_HEADERS,
    )
    assert approval_response.status_code == 200
    assert approval_response.json()["run_id"] is not None


def test_trigger_lifecycle_observability_failure_still_acknowledges_callback(monkeypatch, client) -> None:
    from app.services.runtime_observability_service import runtime_observability_service

    reset_control_plane_state()
    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-audit-trigger-failure",
            "payload": {"topic": "nonfatal trigger audit"},
        },
        headers=AUTH_HEADERS,
    )
    run_id = command_response.json()["run_id"]

    def fail_trigger_audit(*args, **kwargs) -> None:
        raise RuntimeError("synthetic trigger audit failure")

    monkeypatch.setattr(runtime_observability_service, "record_trigger_lifecycle", fail_trigger_audit)

    started_response = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={"trigger_run_id": "trg-audit-failure"},
        headers=AUTH_HEADERS,
    )

    assert started_response.status_code == 200
    assert started_response.json()["status"] == "in_progress"


def test_agent_backed_approved_run_trigger_lifecycle_uses_command_agent_scope(client) -> None:
    reset_control_plane_state()

    headers = audit_headers(org_id="org_alpha", actor_id="actor_alpha", actor_type="user")
    created = client.post(
        "/agents",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "name": "Alpha Trigger Approval Agent",
            "config": {"prompt": "Track trigger approval audit"},
            "host_adapter_kind": "trigger_dev",
        },
        headers=headers,
    ).json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]
    publish_response = client.post(f"/agents/{agent_id}/revisions/{revision_id}/publish", headers=headers)
    assert publish_response.status_code == 200

    command_response = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "publish_campaign",
            "idempotency_key": "cmd-audit-agent-approved-trigger",
            "payload": {"campaign_id": "camp-agent-trigger"},
            "agent_revision_id": revision_id,
        },
        headers=headers,
    )
    approval_response = client.post(
        f"/approvals/{command_response.json()['approval_id']}/approve",
        json={"actor_id": "ops-alpha"},
        headers=headers,
    )
    assert approval_response.status_code == 200
    run_id = approval_response.json()["run_id"]
    started_response = client.post(
        f"/trigger/callbacks/runs/{run_id}/started",
        json={"trigger_run_id": "trg-agent-approved"},
        headers=AUTH_HEADERS,
    )
    assert started_response.status_code == 200

    alpha_listing = client.get("/audit?event_type=trigger_run_started", headers=headers)
    internal_listing = client.get("/audit?event_type=trigger_run_started", headers=AUTH_HEADERS)
    assert alpha_listing.status_code == 200
    assert internal_listing.status_code == 200
    assert len(alpha_listing.json()["events"]) == 1
    assert alpha_listing.json()["events"][0]["agent_id"] == agent_id
    assert alpha_listing.json()["events"][0]["agent_revision_id"] == revision_id
    assert internal_listing.json()["events"] == []
