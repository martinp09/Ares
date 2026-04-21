from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_ares_plans_route_returns_planner_contract(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/ares/plans",
        json={
            "goal": "Find probate plus tax delinquent leads in Harris and Travis counties.",
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()

    assert body["business_id"] == "limitless"
    assert body["environment"] == "dev"
    assert body["goal"] == "Find probate plus tax delinquent leads in Harris and Travis counties."
    assert "Approval required before any side-effecting step" in body["explanation"]
    assert body["plan"]["source_lanes"] == ["probate", "tax_delinquent"]
    assert body["plan"]["counties"] == ["harris", "travis"]
    assert body["plan"]["steps"][-1]["action_type"] == "side_effecting"
    assert body["plan"]["steps"][-1]["requires_approval"] is True
    assert body["generated_at"]


def test_mission_control_autonomy_visibility_surfaces_latest_planner_output(client) -> None:
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

    assert body["planner_review"]["goal"] == "Plan probate outreach in Dallas county."
    assert body["planner_review"]["business_id"] == "limitless"
    assert body["planner_review"]["environment"] == "dev"
    assert body["planner_review"]["plan"]["counties"] == ["dallas"]
    assert body["planner_review"]["plan"]["source_lanes"] == ["probate"]


def test_ares_plans_route_rejects_whitespace_only_goal(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/ares/plans",
        json={
            "goal": "   ",
            "business_id": "limitless",
            "environment": "dev",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
