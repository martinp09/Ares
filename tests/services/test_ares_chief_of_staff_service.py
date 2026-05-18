from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.leads import LeadsRepository
from app.models.ares_chief_of_staff import AresChiefOfStaffBucket
from app.models.leads import LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.slack_notifications import SlackNotificationRoute
from app.services.ares_chief_of_staff_service import AresChiefOfStaffService


class RecordingSlackNotifier:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def notify(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "status": "sent",
            "route": kwargs["route"],
            "dedupe_key": kwargs["dedupe_key"],
            "channel_id": "CCOS",
            "slack_message_ts": "1770000000.000100",
        }


def build_repository() -> LeadsRepository:
    return LeadsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore()))


def seed_leads(repository: LeadsRepository) -> None:
    repository.upsert(
        LeadRecord(
            id="lead_contact_ready_hot",
            business_id="limitless",
            environment="prod",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.READY,
            first_name="John",
            last_name="Seller",
            email="john@example.com",
            phone="+17135550100",
            property_address="123 Main St, Houston, TX",
            mailing_address="PO Box 1, Houston, TX",
            probate_case_number="2026-11111",
            score=88,
            raw_payload={
                "county": "Harris",
                "owner_name": "John Seller",
                "tax_delinquent": True,
                "estate_of": False,
                "lead_temperature": "hot",
                "title_friction": {"status": "clear_enough_for_review"},
            },
        ),
        dedupe_key="lead:contact-ready-hot",
    )
    repository.upsert(
        LeadRecord(
            id="lead_hot_research",
            business_id="limitless",
            environment="prod",
            source=LeadSource.PROBATE_INTAKE,
            lifecycle_status=LeadLifecycleStatus.NEW,
            company_name="Estate of Jane Doe",
            property_address="456 Oak St, Houston, TX",
            probate_case_number="2026-22222",
            score=84,
            raw_payload={
                "county": "Harris",
                "owner_name": "Estate of Jane Doe",
                "decedent_name": "Jane Doe",
                "tax_delinquent": True,
                "estate_of": True,
                "case_detail_status": "postback_only",
                "authority_status": "unclear",
                "title_friction": {"status": "review_needed"},
            },
        ),
        dedupe_key="lead:hot-research",
    )
    repository.upsert(
        LeadRecord(
            id="lead_suppressed",
            business_id="limitless",
            environment="prod",
            source=LeadSource.INSTANTLY_SYNC,
            lifecycle_status=LeadLifecycleStatus.SUPPRESSED,
            email="suppressed@example.com",
            property_address="789 Pine St, Houston, TX",
            score=72,
        ),
        dedupe_key="lead:suppressed",
    )


def test_chief_of_staff_builds_human_queues_without_mutating_leads() -> None:
    repository = build_repository()
    seed_leads(repository)
    service = AresChiefOfStaffService(leads_repository=repository)

    brief = service.build_brief(business_id="limitless", environment="prod", limit=5)

    assert brief.input_lead_count == 3
    assert repository.get("lead_hot_research") is not None
    assert brief.queue_counts[AresChiefOfStaffBucket.HOT.value] == 2
    assert brief.queue_counts[AresChiefOfStaffBucket.CONTACT_READY.value] == 1
    assert brief.queue_counts[AresChiefOfStaffBucket.NEEDS_RESEARCH.value] == 1
    assert brief.queue_counts[AresChiefOfStaffBucket.NEEDS_SKIPTRACE.value] == 1
    assert brief.queue_counts[AresChiefOfStaffBucket.BLOCKED.value] == 1

    contact_ready_ids = {card.lead_id for card in brief.queues[AresChiefOfStaffBucket.CONTACT_READY.value]}
    research_ids = {card.lead_id for card in brief.queues[AresChiefOfStaffBucket.NEEDS_RESEARCH.value]}
    skiptrace_ids = {card.lead_id for card in brief.queues[AresChiefOfStaffBucket.NEEDS_SKIPTRACE.value]}

    assert "lead_contact_ready_hot" in contact_ready_ids
    assert "lead_hot_research" in research_ids
    assert "lead_hot_research" in skiptrace_ids
    assert brief.queues[AresChiefOfStaffBucket.NEEDS_RESEARCH.value][0].next_action == "Resolve authority/title research before seller outreach."
    assert any("No seller outreach" in item for item in brief.safety_boundaries)


def test_chief_of_staff_writes_artifacts_and_slack_digest_without_contact_pii(tmp_path: Path) -> None:
    repository = build_repository()
    seed_leads(repository)
    notifier = RecordingSlackNotifier()
    service = AresChiefOfStaffService(leads_repository=repository, slack_notifier=notifier)

    result = service.run_digest(
        business_id="limitless",
        environment="prod",
        limit=2,
        artifact_root=tmp_path,
        send_slack=True,
        idempotency_key="chief-of-staff:2026-05-18",
    )

    assert result.artifacts["brief_json"].endswith("brief.json")
    assert result.artifacts["brief_markdown"].endswith("brief.md")
    assert result.artifacts["hot_csv"].endswith("hot_leads.csv")
    assert Path(result.artifacts["brief_json"]).exists()
    assert Path(result.artifacts["brief_markdown"]).read_text(encoding="utf-8").startswith("# Ares Chief of Staff Brief")
    payload = json.loads(Path(result.artifacts["brief_json"]).read_text(encoding="utf-8"))
    assert payload["kind"] == "ares_chief_of_staff_brief_v0"
    assert payload["queue_counts"]["hot"] == 2

    assert len(notifier.calls) == 1
    call = notifier.calls[0]
    assert call["route"] == SlackNotificationRoute.CHIEF_OF_STAFF_DIGEST
    assert call["dedupe_key"] == "chief-of-staff:2026-05-18"
    assert "john@example.com" not in call["text"]
    assert "+17135550100" not in call["text"]
    assert call["payload"]["safety"]["seller_outreach_sent"] is False
    assert result.slack_notification["status"] == "sent"
