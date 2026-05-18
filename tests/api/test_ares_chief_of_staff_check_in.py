from __future__ import annotations

import json
from pathlib import Path

from app.db.leads import LeadsRepository
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def seed_chief_of_staff_api_lead(repository: LeadsRepository, *, business_id: str = "cos-api-business") -> None:
    repository.upsert(
        LeadRecord(
            id="lead_cos_api_john_seller",
            business_id=business_id,
            environment="prod",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.READY,
            first_name="John",
            last_name="Seller",
            email="john.seller@example.com",
            phone="+17135550100",
            property_address="123 Main St, Houston, TX",
            mailing_address="PO Box 1, Houston, TX",
            probate_case_number="2026-11111",
            score=91,
            raw_payload={
                "county": "Harris",
                "tax_delinquent": True,
                "estate_of": False,
                "lead_temperature": "hot",
                "title_friction": {"status": "clear"},
            },
        ),
        dedupe_key=f"{business_id}:john-seller",
    )


def test_chief_of_staff_check_in_is_trigger_safe_no_send_and_redacted(client) -> None:
    business_id = "cos-api-safe"
    seed_chief_of_staff_api_lead(LeadsRepository(), business_id=business_id)

    response = client.post(
        "/ares-chief-of-staff/internal/check-in",
        headers=AUTH_HEADERS,
        json={
            "business_id": business_id,
            "environment": "prod",
            "limit": 3,
            "write_artifacts": False,
            "idempotency_key": "cos-api-safe-2026-05-18",
        },
    )

    assert response.status_code == 200
    body = response.json()
    rendered = json.dumps(body, sort_keys=True)

    assert body["kind"] == "ares_chief_of_staff_check_in_v1"
    assert body["status"] == "completed"
    assert body["input_lead_count"] == 1
    assert body["queue_counts"]["hot"] == 1
    assert body["queue_counts"]["contact_ready"] == 1
    assert body["manager_action_item_count"] >= 1
    assert body["artifacts"] == {}
    assert body["slack_notification"] == {"status": "not_requested"}
    assert body["no_send"] is True
    assert body["provider_sends_enabled"] is False
    assert body["outreach_allowed"] is False
    assert body["live_source_calls_attempted"] is False
    assert body["provider_writes_attempted"] is False
    assert body["trigger_safe_summary"]["redaction"] == "counts_only_no_lead_pii"

    for forbidden in (
        "John Seller",
        "john.seller@example.com",
        "+17135550100",
        "123 Main St",
        "2026-11111",
        "lead_cos_api_john_seller",
    ):
        assert forbidden not in rendered


def test_chief_of_staff_check_in_rejects_unsafe_runtime_flags(client) -> None:
    unsafe_payloads = [
        {"no_send": False},
        {"provider_sends_enabled": True},
        {"live_source_calls": True},
        {"live_provider_writes": True},
        {"outreach_allowed": True},
    ]

    for override in unsafe_payloads:
        payload = {
            "business_id": "cos-api-unsafe",
            "environment": "prod",
            "write_artifacts": False,
            **override,
        }
        response = client.post("/ares-chief-of-staff/internal/check-in", headers=AUTH_HEADERS, json=payload)
        assert response.status_code == 422
        assert "input" not in response.text


def test_chief_of_staff_check_in_blocks_slack_without_employee_slack_gate(client, tmp_path: Path, monkeypatch) -> None:
    business_id = "cos-api-slack-gate"
    seed_chief_of_staff_api_lead(LeadsRepository(), business_id=business_id)
    monkeypatch.setenv("ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED", "false")

    response = client.post(
        "/ares-chief-of-staff/internal/check-in",
        headers=AUTH_HEADERS,
        json={
            "business_id": business_id,
            "environment": "prod",
            "limit": 2,
            "artifact_root": str(tmp_path),
            "write_artifacts": True,
            "send_slack": True,
            "idempotency_key": "cos-api-slack-gate-2026-05-18",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["artifacts"]["brief_json"].endswith("brief.json")
    assert Path(body["artifacts"]["brief_json"]).exists()
    assert body["slack_notification"] == {"status": "blocked_by_chief_of_staff_slack_gate"}
    assert body["trigger_safe_summary"]["slack_requested"] is True
    assert body["trigger_safe_summary"]["slack_allowed"] is False
