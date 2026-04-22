from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_mission_control_surfaces_secret_health_audit_and_usage(client) -> None:
    reset_control_plane_state()

    agent_response = client.post(
        "/agents",
        json={
            "name": "Mission Control Agent",
            "config": {"prompt": "Observe governance"},
            "compatibility_metadata": {"requires_secrets": ["textgrid_auth_token"]},
        },
        headers=AUTH_HEADERS,
    )
    assert agent_response.status_code == 200
    revision_id = agent_response.json()["revisions"][0]["id"]

    secret_response = client.post(
        "/secrets",
        json={"name": "textgrid_auth_token", "secret_value": "tok-12345"},
        headers=AUTH_HEADERS,
    )
    assert secret_response.status_code == 200
    secret_id = secret_response.json()["id"]
    binding_response = client.post(
        f"/secrets/{secret_id}/bindings",
        json={"agent_revision_id": revision_id, "binding_name": "textgrid_auth_token"},
        headers=AUTH_HEADERS,
    )
    assert binding_response.status_code == 200

    audit_response = client.post(
        "/audit",
        json={
            "event_type": "secret_accessed",
            "summary": "Accessed secret metadata",
            "org_id": "org_internal",
            "resource_type": "secret",
            "resource_id": secret_id,
        },
        headers=AUTH_HEADERS,
    )
    assert audit_response.status_code == 200

    usage_response = client.post(
        "/usage",
        json={
            "kind": "tool_call",
            "org_id": "org_internal",
            "agent_id": agent_response.json()["agent"]["id"],
            "agent_revision_id": revision_id,
            "count": 2,
        },
        headers=AUTH_HEADERS,
    )
    assert usage_response.status_code == 200

    secrets_listing = client.get("/mission-control/settings/secrets", headers=AUTH_HEADERS)
    assert secrets_listing.status_code == 200
    secrets_body = secrets_listing.json()
    assert secrets_body["secrets"][0]["value_redacted"] == "[redacted]"
    assert secrets_body["secrets"][0]["binding_count"] == 1

    audit_listing = client.get("/mission-control/audit?org_id=org_internal", headers=AUTH_HEADERS)
    assert audit_listing.status_code == 200
    assert audit_listing.json()["events"][0]["event_type"] == "secret_accessed"

    usage_listing = client.get("/mission-control/usage?org_id=org_internal", headers=AUTH_HEADERS)
    assert usage_listing.status_code == 200
    assert usage_listing.json()["summary"]["total_count"] == 2


def test_mission_control_surfaces_autonomy_visibility_read_model(client) -> None:
    reset_control_plane_state()

    safe_command = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-autonomy-safe",
            "payload": {"topic": "harris probate"},
        },
        headers=AUTH_HEADERS,
    )
    assert safe_command.status_code == 201
    active_run_id = safe_command.json()["run_id"]

    approval_command = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "propose_launch",
            "idempotency_key": "cmd-autonomy-approval",
            "payload": {"campaign_id": "camp-visibility"},
        },
        headers=AUTH_HEADERS,
    )
    assert approval_command.status_code == 201
    approval_id = approval_command.json()["approval_id"]
    assert approval_id is not None

    failed_command = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "run_market_research",
            "idempotency_key": "cmd-autonomy-failed",
            "payload": {"topic": "dallas probate"},
        },
        headers=AUTH_HEADERS,
    )
    assert failed_command.status_code == 201
    failed_run_id = failed_command.json()["run_id"]

    mark_failed = client.post(
        f"/trigger/callbacks/runs/{failed_run_id}/failed",
        json={
            "trigger_run_id": "trg-autonomy-failed",
            "error_classification": "tool_error",
            "error_message": "step timed out",
        },
        headers=AUTH_HEADERS,
    )
    assert mark_failed.status_code == 200

    visibility = client.get("/mission-control/autonomy-visibility", headers=AUTH_HEADERS)
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["current_phase"] == "phase1_lead_wedge"
    assert body["active_run"]["id"] == active_run_id
    assert body["pending_approval_count"] == 1
    assert body["pending_approvals"][0]["id"] == approval_id
    assert body["failed_steps"][0]["run_id"] == failed_run_id
    assert body["failed_steps"][0]["step"] == "run_market_research"
    assert body["lead_quality"] == 0.0
    assert body["confidence"] == 0.0
    assert body["next_action"] == "await_human_approval"


def test_mission_control_autonomy_visibility_shows_bounded_execution_review(client) -> None:
    reset_control_plane_state()

    execute = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "action_budget": 5,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                    "tax": [
                        {
                            "property_address": "123 Main St, Houston, TX",
                            "owner_name": "Estate of Jane Doe",
                        }
                    ],
                }
            },
        },
        headers=AUTH_HEADERS,
    )
    assert execute.status_code == 200
    run_id = execute.json()["run_id"]

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["execution_review"]["run_id"] == run_id
    assert body["execution_review"]["state"] == "completed"
    assert body["execution_review"]["lead_count"] == 1
    assert body["execution_review"]["failure_count"] == 0
    assert body["execution_review"]["high_risk_policy_checks"][0]["tool_name"] == "send_outreach"
    assert body["execution_review"]["high_risk_policy_checks"][0]["decision"] == "require_approval"
    assert body["execution_review"]["high_risk_policy_checks"][0]["requires_human_approval"] is True
    assert body["execution_review"]["workflow_eval"]["exception_count"] == 0
    assert body["execution_review"]["drift_detection"]["detected"] is False
    assert "High-risk steps (send, contract, disposition) require hard approval before execution." in body["execution_review"][
        "major_decisions"
    ]
    assert body["execution_review"]["major_failures"] == []
    assert body["execution_review"]["ranked_leads"][0]["tier"] == "PROBATE_WITH_VERIFIED_TAX"


def test_mission_control_autonomy_visibility_surfaces_execution_drift_and_failures(client) -> None:
    reset_control_plane_state()

    baseline = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "action_budget": 5,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [{"property_address": "123 Main St, Houston, TX", "owner_name": "Estate of Jane Doe"}],
                    "tax": [{"property_address": "123 Main St, Houston, TX", "owner_name": "Estate of Jane Doe"}],
                }
            },
        },
        headers=AUTH_HEADERS,
    )
    assert baseline.status_code == 200

    shifted = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "action_budget": 5,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [],
                    "tax": [],
                }
            },
        },
        headers=AUTH_HEADERS,
    )
    assert shifted.status_code == 200

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["execution_review"]["lead_count"] == 0
    assert body["execution_review"]["drift_detection"]["detected"] is True
    assert "Lead count changed from 1 to 0." in body["execution_review"]["drift_detection"]["reason"]


def test_mission_control_autonomy_visibility_surfaces_guarded_autonomous_operator(client) -> None:
    reset_control_plane_state()

    operator_run = client.post(
        "/ares/operator/run",
        json={
            "objective_id": "objective-probate-harris-01",
            "objective_status": "approved",
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "county_payloads": {
                "harris": {
                    "probate": [
                        {
                            "property_address": "321 Main St, Houston, TX",
                            "owner_name": "Estate of John Doe",
                        }
                    ],
                    "tax": [
                        {
                            "property_address": "321 Main St, Houston, TX",
                            "owner_name": "Estate of John Doe",
                        }
                    ],
                }
            },
            "response_events": ["positive_reply"],
        },
        headers=AUTH_HEADERS,
    )
    assert operator_run.status_code == 200

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["current_phase"] == "phase5_guarded_operator"
    assert body["autonomous_operator"]["objective_id"] == "objective-probate-harris-01"
    assert body["autonomous_operator"]["agent_name"] == "ares_guarded_operator"
    assert body["autonomous_operator"]["policy_checks"][0]["tool_name"] == "send_outreach"
    assert body["autonomous_operator"]["policy_checks"][0]["decision"] == "require_approval"
    assert body["autonomous_operator"]["escalation_required"] is True
    assert body["next_action"] == "review_operator_escalation"


def test_mission_control_autonomy_visibility_classifies_planner_only_scope_as_phase2(client) -> None:
    reset_control_plane_state()

    plan_response = client.post(
        "/ares/plans",
        json={
            "goal": "Plan probate outreach in Dallas county.",
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )
    assert plan_response.status_code == 200

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["current_phase"] == "phase2_planner"
    assert body["next_action"] == "review_planner_output"
    assert body["planner_review"]["goal"] == "Plan probate outreach in Dallas county."


def test_mission_control_prefers_newer_execution_review_over_stale_operator_snapshot(client) -> None:
    reset_control_plane_state()

    operator_run = client.post(
        "/ares/operator/run",
        json={
            "objective_id": "objective-probate-harris-stale-check",
            "objective_status": "approved",
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "county_payloads": {
                "harris": {
                    "probate": [{"property_address": "321 Main St, Houston, TX", "owner_name": "Estate of John Doe"}],
                    "tax": [{"property_address": "321 Main St, Houston, TX", "owner_name": "Estate of John Doe"}],
                }
            },
            "response_events": ["positive_reply"],
        },
        headers=AUTH_HEADERS,
    )
    assert operator_run.status_code == 200

    execute = client.post(
        "/ares/execution/run",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "action_budget": 5,
            "retry_limit": 1,
            "approved_tools": ["county_fetch"],
            "county_payloads": {
                "harris": {
                    "probate": [{"property_address": "123 Main St, Houston, TX", "owner_name": "Estate of Jane Doe"}],
                    "tax": [{"property_address": "123 Main St, Houston, TX", "owner_name": "Estate of Jane Doe"}],
                }
            },
        },
        headers=AUTH_HEADERS,
    )
    assert execute.status_code == 200
    execution_run_id = execute.json()["run_id"]

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["current_phase"] == "phase3_bounded_executor"
    assert body["execution_review"]["run_id"] == execution_run_id
    assert body["next_action"] != "review_operator_escalation"


def test_autonomy_visibility_updated_at_matches_displayed_snapshot_freshness(client) -> None:
    reset_control_plane_state()

    operator_run = client.post(
        "/ares/operator/run",
        json={
            "objective_id": "objective-probate-harris-freshness-check",
            "objective_status": "approved",
            "business_id": "limitless",
            "environment": "dev",
            "market": "texas",
            "counties": ["harris"],
            "county_payloads": {
                "harris": {
                    "probate": [{"property_address": "321 Main St, Houston, TX", "owner_name": "Estate of John Doe"}],
                    "tax": [{"property_address": "321 Main St, Houston, TX", "owner_name": "Estate of John Doe"}],
                }
            },
            "response_events": ["positive_reply"],
        },
        headers=AUTH_HEADERS,
    )
    assert operator_run.status_code == 200

    approval_command = client.post(
        "/commands",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "command_type": "propose_launch",
            "idempotency_key": "cmd-autonomy-freshness-approval",
            "payload": {"campaign_id": "camp-freshness"},
        },
        headers=AUTH_HEADERS,
    )
    assert approval_command.status_code == 201

    visibility = client.get(
        "/mission-control/autonomy-visibility?business_id=limitless&environment=dev",
        headers=AUTH_HEADERS,
    )
    assert visibility.status_code == 200
    body = visibility.json()

    assert body["current_phase"] == "phase5_guarded_operator"
    assert body["pending_approval_count"] == 1
    assert body["updated_at"] == body["autonomous_operator"]["generated_at"]


def test_reset_control_plane_state_clears_file_backed_operator_runtime_state(client) -> None:
    reset_control_plane_state()

    payload = {
        "objective_id": "objective-reset-runtime-state",
        "objective_status": "approved",
        "business_id": "limitless",
        "environment": "dev",
        "market": "texas",
        "counties": ["harris"],
        "county_payloads": {
            "harris": {
                "probate": [{"property_address": "321 Main St, Houston, TX", "owner_name": "Estate of John Doe"}],
                "tax": [{"property_address": "321 Main St, Houston, TX", "owner_name": "Estate of John Doe"}],
            }
        },
        "response_events": ["positive_reply"],
    }
    first = client.post("/ares/operator/run", json=payload, headers=AUTH_HEADERS)
    assert first.status_code == 200
    first_counts = first.json()["memory_counts"]

    reset_control_plane_state()

    second = client.post("/ares/operator/run", json=payload, headers=AUTH_HEADERS)
    assert second.status_code == 200
    second_counts = second.json()["memory_counts"]

    assert second_counts == first_counts
