from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def test_skill_api_registers_lists_and_fetches_records(client) -> None:
    reset_control_plane_state()

    create_response = client.post(
        "/skills",
        json={
            "name": "lead_triage",
            "description": "Route incoming leads",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "required_tools": ["lookup_title"],
        },
        headers=AUTH_HEADERS,
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["name"] == "lead_triage"
    assert created["required_tools"] == ["lookup_title"]

    list_response = client.get("/skills", headers=AUTH_HEADERS)
    assert list_response.status_code == 200
    assert [skill["id"] for skill in list_response.json()] == [created["id"]]

    get_response = client.get(f"/skills/{created['id']}", headers=AUTH_HEADERS)
    assert get_response.status_code == 200
    assert get_response.json()["description"] == "Route incoming leads"


def test_skill_api_returns_404_for_missing_skill(client) -> None:
    reset_control_plane_state()

    response = client.get("/skills/skl_missing", headers=AUTH_HEADERS)
    assert response.status_code == 404
    assert response.json()["detail"] == "Skill not found"
