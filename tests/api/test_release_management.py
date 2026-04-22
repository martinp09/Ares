from app.db.client import STORE
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
