from app.db.leads import LeadsRepository
from app.models.leads import LeadRecord, LeadSource
from app.services.run_service import reset_control_plane_state

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def _seed_lead() -> str:
    lead = LeadsRepository().upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            external_key="harris-probate-api-543678",
            first_name="Jane",
            last_name="Applicant",
            phone="7135550101",
            property_address="123 Main St, Houston, TX",
            probate_case_number="543678",
            raw_payload={
                "county": "harris",
                "contact_candidates": [{"name": "Jane Applicant", "role": "applicant"}],
            },
        )
    )
    assert lead.id is not None
    return lead.id


def test_promote_lead_endpoint_creates_deal_detail_and_preserves_no_send_gates(client) -> None:
    reset_control_plane_state()
    lead_id = _seed_lead()

    response = client.post(
        "/deals/promote/lead",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_id": lead_id,
            "source_lane": "harris_probate",
            "strategy_lane": "curative_title",
            "promotion_reason": "keep-now probate lead",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["deal"]["source_record_id"] == lead_id
    assert body["deal"]["source_lane"] == "harris_probate"
    assert body["deal"]["strategy_lane"] == "curative_title"
    assert body["deal"]["no_send"] is True
    assert body["deal"]["provider_sends_enabled"] is False
    assert body["tasks"]
    assert body["document_requirements"]
    assert body["audit_events"][0]["event_type"] == "deal_promoted"


def test_promote_lead_endpoint_is_idempotent(client) -> None:
    reset_control_plane_state()
    lead_id = _seed_lead()
    payload = {
        "business_id": "limitless",
        "environment": "dev",
        "lead_id": lead_id,
        "source_lane": "harris_probate",
        "strategy_lane": "curative_title",
    }

    first = client.post("/deals/promote/lead", json=payload, headers=AUTH_HEADERS)
    second = client.post("/deals/promote/lead", json=payload, headers=AUTH_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["deal"]["id"] == second.json()["deal"]["id"]
    assert len(second.json()["audit_events"]) == 1


def test_deal_list_detail_stage_and_fire_list_endpoints(client) -> None:
    reset_control_plane_state()
    lead_id = _seed_lead()
    promoted = client.post(
        "/deals/promote/lead",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_id": lead_id,
            "source_lane": "harris_probate",
            "strategy_lane": "curative_title",
        },
        headers=AUTH_HEADERS,
    )
    assert promoted.status_code == 200
    deal_id = promoted.json()["deal"]["id"]

    listed = client.get(
        "/deals?business_id=limitless&environment=dev&strategy_lane=curative_title",
        headers=AUTH_HEADERS,
    )
    assert listed.status_code == 200
    assert listed.json()["deals"][0]["id"] == deal_id

    detail = client.get(f"/deals/{deal_id}", headers=AUTH_HEADERS)
    assert detail.status_code == 200
    assert detail.json()["deal"]["id"] == deal_id

    blocked = client.post(
        f"/deals/{deal_id}/stage",
        json={"target_stage": "under_contract", "reason": "seller said yes"},
        headers=AUTH_HEADERS,
    )
    assert blocked.status_code == 422
    assert "missing required document evidence" in blocked.json()["detail"]

    moved = client.post(
        f"/deals/{deal_id}/stage",
        json={"target_stage": "contact_ready", "reason": "ready for review", "manual_override": True},
        headers=AUTH_HEADERS,
    )
    assert moved.status_code == 200
    assert moved.json()["deal"]["stage"] == "contact_ready"

    fire_list = client.get("/deals/fire-list?business_id=limitless&environment=dev", headers=AUTH_HEADERS)
    assert fire_list.status_code == 200
    assert {item["item_type"] for item in fire_list.json()["items"]} >= {"document", "provider_gate"}


def test_promote_lead_endpoint_rejects_no_send_false(client) -> None:
    reset_control_plane_state()
    lead_id = _seed_lead()

    response = client.post(
        "/deals/promote/lead",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_id": lead_id,
            "source_lane": "harris_probate",
            "strategy_lane": "curative_title",
            "no_send": False,
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 422
    assert "no-send only" in response.json()["detail"]


def test_missing_lead_promotion_returns_404(client) -> None:
    reset_control_plane_state()

    response = client.post(
        "/deals/promote/lead",
        json={
            "business_id": "limitless",
            "environment": "dev",
            "lead_id": "lead_missing",
            "source_lane": "harris_probate",
            "strategy_lane": "curative_title",
        },
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 404
