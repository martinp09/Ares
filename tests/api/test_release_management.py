import pytest

import app.db.control_plane_store_supabase as control_plane_store_supabase
from app.db.client import STORE
from app.db.release_management import ReleaseManagementRepository
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def org_actor_headers(*, org_id: str, actor_id: str, actor_type: str = "user") -> dict[str, str]:
    return {
        **AUTH_HEADERS,
        "X-Ares-Org-Id": org_id,
        "X-Ares-Actor-Id": actor_id,
        "X-Ares-Actor-Type": actor_type,
    }

def test_release_management_publish_rollback_and_list_events(client) -> None:
    reset_control_plane_state()

    create_response = client.post(
        "/agents",
        json={
            "name": "Release API Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Manage releases"},
            "release_channel": "dogfood",
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert create_response.status_code == 200
    created = create_response.json()
    agent_id = created["agent"]["id"]
    first_revision_id = created["revisions"][0]["id"]

    first_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/publish",
        json={
            "notes": "Initial release",
            "require_passing_evaluation": True,
            "evaluation_summary": {
                "outcome_name": "release_readiness",
                "artifact_type": "agent_revision",
                "artifact_payload": {"revision_id": first_revision_id, "release_channel": "dogfood"},
                "rubric_criteria": ["smoke tests pass", "rollback path validated"],
                "evaluator_result": "ready to promote",
                "passed": True,
                "failure_details": [],
            },
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert first_publish.status_code == 200
    first_body = first_publish.json()
    assert first_body["agent"]["active_revision_id"] == first_revision_id
    assert first_body["event"]["event_type"] == "publish"
    assert first_body["event"]["previous_active_revision_id"] is None
    assert first_body["event"]["target_revision_id"] == first_revision_id
    assert first_body["event"]["release_channel"] == "dogfood"
    assert first_body["event"]["evaluation_summary"] == {
        "outcome_id": first_body["event"]["evaluation_summary"]["outcome_id"],
        "outcome_name": "release_readiness",
        "status": "satisfied",
        "satisfied": True,
        "evaluator_result": "ready to promote",
        "failure_details": [],
        "rubric_criteria": ["smoke tests pass", "rollback path validated"],
        "require_passing_evaluation": True,
        "blocked_promotion": False,
        "rollback_reason": None,
    }
    first_outcome = STORE.outcomes[first_body["event"]["evaluation_summary"]["outcome_id"]]
    assert first_outcome.release_decision is not None
    assert first_outcome.release_decision.action.value == "promotion"
    assert first_outcome.release_decision.require_passing_evaluation is True

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{first_revision_id}/clone",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert clone_response.status_code == 200
    second_revision = max(clone_response.json()["revisions"], key=lambda revision: revision["revision_number"])

    second_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{second_revision['id']}/publish",
        json={"notes": "Promote cloned revision"},
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert second_publish.status_code == 200
    second_body = second_publish.json()
    second_revisions = {revision["id"]: revision for revision in second_body["revisions"]}
    assert second_body["agent"]["active_revision_id"] == second_revision["id"]
    assert second_body["event"]["event_type"] == "publish"
    assert second_body["event"]["previous_active_revision_id"] == first_revision_id
    assert second_revisions[first_revision_id]["state"] == "deprecated"
    assert second_revisions[second_revision["id"]]["state"] == "published"

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/rollback",
        json={
            "notes": "Rollback to known-good revision",
            "rollback_reason": "Operator reported a production regression after promotion",
            "evaluation_summary": {
                "outcome_name": "rollback_assessment",
                "artifact_type": "agent_revision",
                "artifact_payload": {"target_revision_id": first_revision_id},
                "rubric_criteria": ["known good revision exists", "regression isolated"],
                "evaluator_result": "rollback approved",
                "passed": False,
                "failure_details": ["Promoted revision regressed production behavior"],
            },
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert rollback_response.status_code == 200
    rollback_body = rollback_response.json()
    rollback_revisions = {revision["id"]: revision for revision in rollback_body["revisions"]}
    rollback_active_revision_id = rollback_body["agent"]["active_revision_id"]
    assert rollback_active_revision_id != first_revision_id
    assert rollback_body["event"]["event_type"] == "rollback"
    assert rollback_body["event"]["previous_active_revision_id"] == second_revision["id"]
    assert rollback_body["event"]["target_revision_id"] == first_revision_id
    assert rollback_body["event"]["resulting_active_revision_id"] == rollback_active_revision_id
    assert rollback_body["event"]["evaluation_summary"] == {
        "outcome_id": rollback_body["event"]["evaluation_summary"]["outcome_id"],
        "outcome_name": "rollback_assessment",
        "status": "failed",
        "satisfied": False,
        "evaluator_result": "rollback approved",
        "failure_details": ["Promoted revision regressed production behavior"],
        "rubric_criteria": ["known good revision exists", "regression isolated"],
        "require_passing_evaluation": False,
        "blocked_promotion": False,
        "rollback_reason": "Operator reported a production regression after promotion",
    }
    rollback_outcome = STORE.outcomes[rollback_body["event"]["evaluation_summary"]["outcome_id"]]
    assert rollback_outcome.release_decision is not None
    assert rollback_outcome.release_decision.action.value == "rollback"
    assert rollback_outcome.release_decision.rollback_reason == "Operator reported a production regression after promotion"
    assert rollback_revisions[first_revision_id]["state"] == "deprecated"
    assert rollback_revisions[second_revision["id"]]["state"] == "deprecated"
    assert rollback_revisions[rollback_active_revision_id]["state"] == "published"
    assert rollback_revisions[rollback_active_revision_id]["cloned_from_revision_id"] == first_revision_id
    assert len(rollback_body["revisions"]) == 3

    events_response = client.get(
        f"/release-management/agents/{agent_id}/events",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert [event["event_type"] for event in events] == ["publish", "publish", "rollback"]
    assert [event["target_revision_id"] for event in events] == [
        first_revision_id,
        second_revision["id"],
        first_revision_id,
    ]
    assert events[-1]["resulting_active_revision_id"] == rollback_active_revision_id


def test_release_management_deactivate_clears_active_pointer_and_appends_event(client) -> None:
    reset_control_plane_state()

    create_response = client.post(
        "/agents",
        json={
            "name": "Retired Release Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Retire release cleanly"},
            "release_channel": "dogfood",
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert create_response.status_code == 200
    created = create_response.json()
    agent_id = created["agent"]["id"]
    first_revision_id = created["revisions"][0]["id"]

    publish_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/publish",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert publish_response.status_code == 200

    deactivate_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/deactivate",
        json={"notes": "Retire the current production release"},
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert deactivate_response.status_code == 200
    body = deactivate_response.json()
    revisions = {revision["id"]: revision for revision in body["revisions"]}
    assert body["agent"]["active_revision_id"] is None
    assert body["agent"]["lifecycle_status"] == "archived"
    assert revisions[first_revision_id]["state"] == "archived"
    assert body["event"]["event_type"] == "deactivate"
    assert body["event"]["previous_active_revision_id"] == first_revision_id
    assert body["event"]["target_revision_id"] == first_revision_id
    assert body["event"]["resulting_active_revision_id"] is None
    assert body["event"]["release_channel"] == "dogfood"

    events_response = client.get(
        f"/release-management/agents/{agent_id}/events",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert [event["event_type"] for event in events] == ["publish", "deactivate"]
    assert events[-1]["resulting_active_revision_id"] is None


def test_release_management_is_org_scoped_and_rejects_never_published_rollback(client) -> None:
    reset_control_plane_state()

    create_response = client.post(
        "/agents",
        json={
            "name": "Scoped Release Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Scope release history"},
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert create_response.status_code == 200
    created = create_response.json()
    agent_id = created["agent"]["id"]
    first_revision_id = created["revisions"][0]["id"]

    publish_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/publish",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert publish_response.status_code == 200

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{first_revision_id}/clone",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert clone_response.status_code == 200
    draft_revision = max(clone_response.json()["revisions"], key=lambda revision: revision["revision_number"])

    forbidden_org = client.get(
        f"/release-management/agents/{agent_id}/events",
        headers=org_actor_headers(org_id="org_other", actor_id="usr_other"),
    )
    assert forbidden_org.status_code == 404

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{draft_revision['id']}/rollback",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert rollback_response.status_code == 409
    assert rollback_response.json()["detail"] == "Only previously published revisions can be rolled back"


def test_release_management_blocks_promotion_when_failed_evaluation_is_required(client) -> None:
    reset_control_plane_state()

    create_response = client.post(
        "/agents",
        json={
            "name": "Eval Gated Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Require a passing eval before promotion"},
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert create_response.status_code == 200
    created = create_response.json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]

    publish_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{revision_id}/publish",
        json={
            "notes": "Attempt promotion with failing eval",
            "require_passing_evaluation": True,
            "evaluation_summary": {
                "outcome_name": "release_readiness",
                "artifact_type": "agent_revision",
                "artifact_payload": {"revision_id": revision_id},
                "rubric_criteria": ["smoke tests pass"],
                "evaluator_result": "smoke test failed",
                "passed": False,
                "failure_details": ["Trigger callback contract regressed"],
            },
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )

    assert publish_response.status_code == 409
    assert publish_response.json()["detail"] == "Promotion blocked by failed evaluation summary"
    assert STORE.release_event_ids_by_agent.get(agent_id, []) == []
    assert len(STORE.outcomes) == 1
    stored = next(iter(STORE.outcomes.values()))
    assert stored.status.value == "failed"
    assert stored.release_decision is not None
    assert stored.release_decision.action.value == "promotion"
    assert stored.release_decision.require_passing_evaluation is True


def test_invalid_release_transitions_do_not_persist_evaluation_outcomes(client) -> None:
    reset_control_plane_state()

    create_response = client.post(
        "/agents",
        json={
            "name": "Invalid Transition Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Do not persist fake evals"},
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert create_response.status_code == 200
    created = create_response.json()
    agent_id = created["agent"]["id"]
    revision_id = created["revisions"][0]["id"]

    first_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{revision_id}/publish",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert first_publish.status_code == 200
    assert len(STORE.outcomes) == 0

    republish_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{revision_id}/publish",
        json={
            "evaluation_summary": {
                "outcome_name": "release_readiness",
                "artifact_type": "agent_revision",
                "artifact_payload": {"revision_id": revision_id},
                "rubric_criteria": ["smoke tests pass"],
                "evaluator_result": "still active already",
                "passed": True,
                "failure_details": [],
            }
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert republish_response.status_code == 409
    assert republish_response.json()["detail"] == "Revision is already the active published revision"
    assert len(STORE.outcomes) == 0

    missing_publish_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/rev_missing/publish",
        json={
            "evaluation_summary": {
                "outcome_name": "release_readiness",
                "artifact_type": "agent_revision",
                "artifact_payload": {"revision_id": "rev_missing"},
                "rubric_criteria": ["smoke tests pass"],
                "evaluator_result": "missing revision",
                "passed": True,
                "failure_details": [],
            }
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert missing_publish_response.status_code == 404
    assert len(STORE.outcomes) == 0

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{revision_id}/clone",
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert clone_response.status_code == 200
    draft_revision_id = max(clone_response.json()["revisions"], key=lambda revision: revision["revision_number"])["id"]

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{draft_revision_id}/rollback",
        json={
            "rollback_reason": "should fail before storing eval",
            "evaluation_summary": {
                "outcome_name": "rollback_assessment",
                "artifact_type": "agent_revision",
                "artifact_payload": {"target_revision_id": draft_revision_id},
                "rubric_criteria": ["known good revision exists"],
                "evaluator_result": "draft never published",
                "passed": False,
                "failure_details": ["Never published"],
            }
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert rollback_response.status_code == 409
    assert rollback_response.json()["detail"] == "Only previously published revisions can be rolled back"
    assert len(STORE.outcomes) == 0

    missing_rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/rev_missing/rollback",
        json={
            "rollback_reason": "missing revision",
            "evaluation_summary": {
                "outcome_name": "rollback_assessment",
                "artifact_type": "agent_revision",
                "artifact_payload": {"target_revision_id": "rev_missing"},
                "rubric_criteria": ["known good revision exists"],
                "evaluator_result": "missing revision",
                "passed": False,
                "failure_details": ["Missing revision"],
            }
        },
        headers=org_actor_headers(org_id="org_release", actor_id="usr_release"),
    )
    assert missing_rollback_response.status_code == 404
    assert len(STORE.outcomes) == 0


def test_release_management_events_persist_across_supabase_transaction_boundary(client, fake_supabase_control_plane) -> None:
    reset_control_plane_state()
    rows_by_table = fake_supabase_control_plane()

    headers = org_actor_headers(org_id="org_release", actor_id="usr_release")
    create_response = client.post(
        "/agents",
        json={
            "name": "Supabase Release Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Persist release state"},
            "release_channel": "dogfood",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    agent_id = create_body["agent"]["id"]
    first_revision_id = create_body["revisions"][0]["id"]

    first_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/publish",
        json={
            "notes": "Promote into Supabase runtime",
            "require_passing_evaluation": True,
            "evaluation_summary": {
                "outcome_name": "release_readiness",
                "artifact_type": "agent_revision",
                "artifact_payload": {"revision_id": first_revision_id},
                "rubric_criteria": ["smoke tests pass"],
                "evaluator_result": "supabase green",
                "passed": True,
                "failure_details": [],
            },
        },
        headers=headers,
    )
    assert first_publish.status_code == 200
    assert first_publish.json()["event"]["evaluation_summary"] is not None

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{first_revision_id}/clone",
        headers=headers,
    )
    assert clone_response.status_code == 200
    second_revision_id = max(clone_response.json()["revisions"], key=lambda revision: revision["revision_number"])["id"]

    second_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{second_revision_id}/publish",
        headers=headers,
    )
    assert second_publish.status_code == 200

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/rollback",
        json={
            "notes": "Rollback for persistence regression",
            "rollback_reason": "Supabase rollback coverage",
            "evaluation_summary": {
                "outcome_name": "rollback_assessment",
                "artifact_type": "agent_revision",
                "artifact_payload": {"target_revision_id": first_revision_id},
                "rubric_criteria": ["known good revision exists"],
                "evaluator_result": "rollback approved",
                "passed": False,
                "failure_details": ["Expected rollback regression drill"],
            },
        },
        headers=headers,
    )
    assert rollback_response.status_code == 200
    assert rollback_response.json()["event"]["evaluation_summary"] is not None
    rollback_active_revision_id = rollback_response.json()["agent"]["active_revision_id"]

    deactivate_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{rollback_active_revision_id}/deactivate",
        json={"notes": "Retire active release"},
        headers=headers,
    )
    assert deactivate_response.status_code == 200

    events_response = client.get(
        f"/release-management/agents/{agent_id}/events",
        headers=headers,
    )
    assert events_response.status_code == 200
    events = events_response.json()["events"]
    assert [event["event_type"] for event in events] == ["publish", "publish", "rollback", "deactivate"]
    assert events[-1]["resulting_active_revision_id"] is None
    assert len(rows_by_table.get("outcomes_runtime", {})) == 2


def test_release_management_rolls_back_evaluation_outcome_when_transition_fails(client, monkeypatch, fake_supabase_control_plane) -> None:
    reset_control_plane_state()
    rows_by_table = fake_supabase_control_plane()

    headers = org_actor_headers(org_id="org_release", actor_id="usr_release")
    create_response = client.post(
        "/agents",
        json={
            "name": "Supabase Failure Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Force transition failure"},
            "release_channel": "dogfood",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    agent_id = create_body["agent"]["id"]
    revision_id = create_body["revisions"][0]["id"]

    def fail_publish(self, *args, **kwargs):
        raise ValueError("forced transition failure")

    monkeypatch.setattr(ReleaseManagementRepository, "publish_revision", fail_publish)

    publish_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{revision_id}/publish",
        json={
            "notes": "This publish should fail after evaluation creation",
            "evaluation_summary": {
                "outcome_name": "release_readiness",
                "artifact_type": "agent_revision",
                "artifact_payload": {"revision_id": revision_id},
                "rubric_criteria": ["smoke tests pass"],
                "evaluator_result": "simulated failure",
                "passed": True,
                "failure_details": [],
            },
        },
        headers=headers,
    )
    assert publish_response.status_code == 409
    assert publish_response.json()["detail"] == "forced transition failure"
    assert rows_by_table.get("outcomes_runtime", {}) == {}
    assert rows_by_table.get("release_events_runtime", {}) == {}


def test_release_management_restores_supabase_state_when_publish_flush_fails(
    client,
    monkeypatch,
    fake_supabase_control_plane,
) -> None:
    reset_control_plane_state()
    rows_by_table = fake_supabase_control_plane()

    headers = org_actor_headers(org_id="org_release", actor_id="usr_release")
    create_response = client.post(
        "/agents",
        json={
            "name": "Supabase Publish Flush Failure Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Force publish flush failure"},
            "release_channel": "dogfood",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    agent_id = create_body["agent"]["id"]
    revision_id = create_body["revisions"][0]["id"]
    audit_count_before = len(rows_by_table.get("audit_events_runtime", {}))
    original_insert_rows = control_plane_store_supabase.insert_rows
    injected_failure = False

    def fail_after_canonicalized_agent_row(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        nonlocal injected_failure
        if not injected_failure and table == "outcomes_runtime":
            injected_failure = True
            agent_row = dict(rows_by_table["agents_runtime"][agent_id])
            payload = dict(agent_row["payload_json"])
            payload["updated_at"] = str(payload["updated_at"]).replace("+00:00", "Z")
            agent_row["payload_json"] = payload
            agent_row["updated_at"] = str(agent_row["updated_at"]).replace("+00:00", "Z")
            agent_row["db_generated"] = "server-default"
            rows_by_table["agents_runtime"][agent_id] = agent_row
            raise RuntimeError("outcomes_runtime insert failure")
        return original_insert_rows(table, rows, select=select, prefer=prefer, settings=settings)

    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fail_after_canonicalized_agent_row)

    with pytest.raises(RuntimeError, match="outcomes_runtime insert failure"):
        client.post(
            f"/release-management/agents/{agent_id}/revisions/{revision_id}/publish",
            json={
                "notes": "This publish should fail during Supabase flush",
                "evaluation_summary": {
                    "outcome_name": "release_readiness",
                    "artifact_type": "agent_revision",
                    "artifact_payload": {"revision_id": revision_id},
                    "rubric_criteria": ["smoke tests pass"],
                    "evaluator_result": "flush failure",
                    "passed": True,
                    "failure_details": [],
                },
            },
            headers=headers,
        )

    assert rows_by_table.get("outcomes_runtime", {}) == {}
    assert rows_by_table.get("release_events_runtime", {}) == {}
    assert rows_by_table["agents_runtime"][agent_id]["payload_json"]["active_revision_id"] is None
    assert rows_by_table["agent_revisions_runtime"][revision_id]["payload_json"]["state"] == "draft"
    assert len(rows_by_table.get("agent_revisions_runtime", {})) == 1
    assert len(rows_by_table.get("audit_events_runtime", {})) == audit_count_before


def test_release_management_flush_restore_does_not_clobber_newer_same_row_commit(
    client,
    monkeypatch,
    fake_supabase_control_plane,
) -> None:
    reset_control_plane_state()
    rows_by_table = fake_supabase_control_plane()

    headers = org_actor_headers(org_id="org_release", actor_id="usr_release")
    create_response = client.post(
        "/agents",
        json={
            "name": "Supabase Concurrent Publish Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Force concurrent publish rollback race"},
            "release_channel": "dogfood",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    agent_id = create_body["agent"]["id"]
    revision_id = create_body["revisions"][0]["id"]

    original_insert_rows = control_plane_store_supabase.insert_rows
    injected_failure = False

    def fail_after_concurrent_agent_write(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        nonlocal injected_failure
        if not injected_failure and table == "outcomes_runtime":
            injected_failure = True
            agent_row = dict(rows_by_table["agents_runtime"][agent_id])
            payload = dict(agent_row["payload_json"])
            payload["name"] = "Concurrent Winner"
            payload["active_revision_id"] = "rev_concurrent"
            agent_row["payload_json"] = payload
            agent_row["name"] = "Concurrent Winner"
            rows_by_table["agents_runtime"][agent_id] = agent_row
            raise RuntimeError("outcomes_runtime insert failure")
        return original_insert_rows(table, rows, select=select, prefer=prefer, settings=settings)

    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fail_after_concurrent_agent_write)

    with pytest.raises(RuntimeError, match="outcomes_runtime insert failure"):
        client.post(
            f"/release-management/agents/{agent_id}/revisions/{revision_id}/publish",
            json={
                "notes": "This publish should fail during Supabase flush",
                "evaluation_summary": {
                    "outcome_name": "release_readiness",
                    "artifact_type": "agent_revision",
                    "artifact_payload": {"revision_id": revision_id},
                    "rubric_criteria": ["smoke tests pass"],
                    "evaluator_result": "flush failure",
                    "passed": True,
                    "failure_details": [],
                },
            },
            headers=headers,
        )

    assert rows_by_table["agents_runtime"][agent_id]["payload_json"]["name"] == "Concurrent Winner"
    assert rows_by_table["agents_runtime"][agent_id]["payload_json"]["active_revision_id"] == "rev_concurrent"


def test_release_management_rolls_back_evaluation_outcome_when_rollback_transition_fails(
    client,
    monkeypatch,
    fake_supabase_control_plane,
) -> None:
    reset_control_plane_state()
    rows_by_table = fake_supabase_control_plane()

    headers = org_actor_headers(org_id="org_release", actor_id="usr_release")
    create_response = client.post(
        "/agents",
        json={
            "name": "Supabase Rollback Failure Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Force rollback transition failure"},
            "release_channel": "dogfood",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    agent_id = create_body["agent"]["id"]
    first_revision_id = create_body["revisions"][0]["id"]

    first_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/publish",
        headers=headers,
    )
    assert first_publish.status_code == 200

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{first_revision_id}/clone",
        headers=headers,
    )
    assert clone_response.status_code == 200
    second_revision_id = max(clone_response.json()["revisions"], key=lambda revision: revision["revision_number"])["id"]

    second_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{second_revision_id}/publish",
        headers=headers,
    )
    assert second_publish.status_code == 200

    def fail_rollback(self, *args, **kwargs):
        raise ValueError("forced rollback failure")

    monkeypatch.setattr(ReleaseManagementRepository, "rollback_revision", fail_rollback)

    rollback_response = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/rollback",
        json={
            "notes": "This rollback should fail after evaluation creation",
            "rollback_reason": "forced rollback failure",
            "evaluation_summary": {
                "outcome_name": "rollback_assessment",
                "artifact_type": "agent_revision",
                "artifact_payload": {"target_revision_id": first_revision_id},
                "rubric_criteria": ["known good revision exists"],
                "evaluator_result": "simulated rollback failure",
                "passed": False,
                "failure_details": ["Rollback transition exploded"],
            },
        },
        headers=headers,
    )
    assert rollback_response.status_code == 409
    assert rollback_response.json()["detail"] == "forced rollback failure"
    assert rows_by_table.get("outcomes_runtime", {}) == {}
    assert len(rows_by_table.get("release_events_runtime", {})) == 2


def test_release_management_restores_supabase_state_when_rollback_flush_fails(
    client,
    fake_supabase_control_plane,
) -> None:
    reset_control_plane_state()
    rows_by_table = fake_supabase_control_plane()

    headers = org_actor_headers(org_id="org_release", actor_id="usr_release")
    create_response = client.post(
        "/agents",
        json={
            "name": "Supabase Rollback Flush Failure Agent",
            "business_id": "limitless",
            "environment": "prod",
            "config": {"prompt": "Force rollback flush failure"},
            "release_channel": "dogfood",
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    agent_id = create_body["agent"]["id"]
    first_revision_id = create_body["revisions"][0]["id"]

    first_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/publish",
        headers=headers,
    )
    assert first_publish.status_code == 200

    clone_response = client.post(
        f"/agents/{agent_id}/revisions/{first_revision_id}/clone",
        headers=headers,
    )
    assert clone_response.status_code == 200
    second_revision_id = max(clone_response.json()["revisions"], key=lambda revision: revision["revision_number"])["id"]

    second_publish = client.post(
        f"/release-management/agents/{agent_id}/revisions/{second_revision_id}/publish",
        headers=headers,
    )
    assert second_publish.status_code == 200
    revision_states_before = {
        row_id: row["payload_json"]["state"]
        for row_id, row in rows_by_table.get("agent_revisions_runtime", {}).items()
    }

    fake_supabase_control_plane(reset=False, fail_on_insert={"release_events_runtime": 1})

    with pytest.raises(RuntimeError, match="release_events_runtime insert failure"):
        client.post(
            f"/release-management/agents/{agent_id}/revisions/{first_revision_id}/rollback",
            json={
                "notes": "This rollback should fail during Supabase flush",
                "rollback_reason": "flush failure",
                "evaluation_summary": {
                    "outcome_name": "rollback_assessment",
                    "artifact_type": "agent_revision",
                    "artifact_payload": {"target_revision_id": first_revision_id},
                    "rubric_criteria": ["known good revision exists"],
                    "evaluator_result": "flush failure",
                    "passed": False,
                    "failure_details": ["Rollback flush exploded"],
                },
            },
            headers=headers,
        )

    assert len(rows_by_table.get("release_events_runtime", {})) == 2
    assert rows_by_table.get("outcomes_runtime", {}) == {}
    assert rows_by_table["agents_runtime"][agent_id]["payload_json"]["active_revision_id"] == second_revision_id
    assert {
        row_id: row["payload_json"]["state"]
        for row_id, row in rows_by_table.get("agent_revisions_runtime", {}).items()
    } == revision_states_before
