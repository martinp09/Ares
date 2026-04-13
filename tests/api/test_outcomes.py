from copy import deepcopy

from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_evaluating_outcome_stores_rubric_criteria_and_evaluator_result(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/outcomes",
        json={
            "outcome_name": "campaign_brief_quality",
            "artifact_type": "campaign_brief",
            "artifact_payload": {"headline": "Win more listings"},
            "rubric_criteria": ["clear audience", "specific CTA"],
            "evaluator_result": "missing CTA detail",
            "passed": False,
            "failure_details": ["CTA was too vague"],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["rubric_criteria"] == ["clear audience", "specific CTA"]
    assert body["evaluator_result"] == "missing CTA detail"


def test_failed_rubric_stores_failure_details_without_mutating_original_artifact(client) -> None:
    reset_control_plane_state()
    artifact = {"headline": "Win more listings", "cta": "Call us"}
    original_artifact = deepcopy(artifact)

    response = client.post(
        "/outcomes",
        json={
            "outcome_name": "campaign_brief_quality",
            "artifact_type": "campaign_brief",
            "artifact_payload": artifact,
            "rubric_criteria": ["clear audience", "specific CTA"],
            "evaluator_result": "audience segment missing",
            "passed": False,
            "failure_details": ["No audience segment"],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["failure_details"] == ["No audience segment"]
    assert artifact == original_artifact
    assert body["artifact_payload"] == original_artifact


def test_passed_rubric_marks_outcome_as_satisfied(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/outcomes",
        json={
            "outcome_name": "campaign_brief_quality",
            "artifact_type": "campaign_brief",
            "artifact_payload": {"headline": "Win more listings", "cta": "Schedule a call"},
            "rubric_criteria": ["clear audience", "specific CTA"],
            "evaluator_result": "criteria satisfied",
            "passed": True,
            "failure_details": [],
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "satisfied"
    assert body["satisfied"] is True
