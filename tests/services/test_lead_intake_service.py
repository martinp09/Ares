from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.services.lead_intake_service import LeadIntakeRequest, LeadIntakeService


def build_service() -> tuple[LeadIntakeService, LeadsRepository, LeadEventsRepository]:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    leads = LeadsRepository(client)
    events = LeadEventsRepository(client)
    return LeadIntakeService(leads_repository=leads, lead_events_repository=events), leads, events


def test_intake_lead_creates_canonical_lead_and_event() -> None:
    service, leads, events = build_service()

    result = service.intake_lead(
        LeadIntakeRequest(
            business_id="limitless",
            environment="dev",
            source="manual",
            source_record_id="lp_123",
            campaign_key="lease-option",
            first_name="Maya",
            last_name="Garcia",
            phone="+15551234567",
            email="maya@example.com",
            property_address="123 Main St",
            county="Harris",
            status="ready",
            pipeline_stage="new_inbound",
            priority="high",
            metadata={"utm_source": "site"},
        )
    )

    assert result.status == "created"
    assert result.queued is False
    assert result.failed_side_effects == []
    stored = leads.get(result.lead.id or "")
    assert stored is not None
    assert stored.email == "maya@example.com"
    assert stored.lifecycle_status == "ready"
    assert stored.raw_payload["source"] == "manual"
    assert stored.raw_payload["source_record_id"] == "lp_123"
    assert stored.raw_payload["county"] == "Harris"
    assert stored.external_key == "manual:lp_123"
    lead_events = events.list_for_lead(result.lead.id or "")
    assert [event.event_type for event in lead_events] == ["lead.intake.created"]
    assert lead_events[0].payload["campaign_key"] == "lease-option"


def test_intake_lead_returns_deduped_for_same_source_record() -> None:
    service, leads, events = build_service()
    request = LeadIntakeRequest(
        business_id="limitless",
        environment="dev",
        source="manual",
        source_record_id="lp_123",
        phone="+15551234567",
        first_name="Maya",
    )

    first = service.intake_lead(request)
    second = service.intake_lead(request)

    assert first.status == "created"
    assert second.status == "deduped"
    assert first.lead.id == second.lead.id
    assert len(leads.list(business_id="limitless", environment="dev")) == 1
    assert len(events.list_for_lead(first.lead.id or "")) == 1


def test_intake_lead_namespaces_source_record_identity_by_source() -> None:
    service, leads, _ = build_service()

    landing = service.intake_lead(
        LeadIntakeRequest(
            business_id="limitless",
            environment="dev",
            source="manual",
            source_record_id="123",
            phone="+15550000001",
        )
    )
    import_row = service.intake_lead(
        LeadIntakeRequest(
            business_id="limitless",
            environment="dev",
            source="instantly_import",
            source_record_id="123",
            phone="+15550000002",
        )
    )

    assert landing.lead.id != import_row.lead.id
    assert len(leads.list(business_id="limitless", environment="dev")) == 2


def test_intake_lead_requires_deterministic_identity() -> None:
    service, _, _ = build_service()

    try:
        service.intake_lead(
            LeadIntakeRequest(
                business_id="limitless",
                environment="dev",
                source="manual",
            )
        )
    except ValueError as exc:
        assert "dedupe_key" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_intake_lead_rejects_unknown_canonical_source() -> None:
    service, _, _ = build_service()

    try:
        service.intake_lead(
            LeadIntakeRequest(
                business_id="limitless",
                environment="dev",
                source="landing_page",
                source_record_id="lp_123",
            )
        )
    except ValueError as exc:
        assert "unsupported lead source" in str(exc)
    else:
        raise AssertionError("expected ValueError")
