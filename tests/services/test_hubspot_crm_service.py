from app.core.config import Settings
from app.models.crm_records import CrmRecord, CrmRecordStatus, CrmRecordType
from app.models.hubspot_crm import HubSpotCustomizationRequest, HubSpotRecordSyncRequest
from app.services.hubspot_crm_service import HubSpotCrmService, build_ares_hubspot_pipeline


class FakeHubSpotClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict]] = []

    def upsert_property(self, object_type: str, property_name: str, payload: dict) -> dict:
        self.calls.append(("upsert_property", object_type, {"property_name": property_name, **payload}))
        return {"status": "created", "property": {"name": property_name}}

    def upsert_pipeline_by_label(self, object_type: str, payload: dict) -> dict:
        self.calls.append(("upsert_pipeline_by_label", object_type, payload))
        return {"status": "created", "pipeline": {"id": "pipeline_ares", "label": payload["label"]}}

    def upsert_object_by_property(self, object_type: str, *, lookup_property: str, lookup_value: str, properties: dict) -> dict:
        self.calls.append(
            (
                "upsert_object_by_property",
                object_type,
                {"lookup_property": lookup_property, "lookup_value": lookup_value, "properties": properties},
            )
        )
        return {"status": "created", "object": {"id": f"{object_type}_123"}, "matched_by": lookup_property}


def _record() -> CrmRecord:
    return CrmRecord(
        business_id="limitless",
        environment="prod",
        record_type=CrmRecordType.CONTACT,
        status=CrmRecordStatus.NEEDS_SKIP_TRACE,
        identity_key="harris-hot18:0123456789012",
        display_name="Maria Lopez",
        owner_name="Maria Lopez",
        property_address="123 Main St, Houston, TX",
        mailing_address="PO Box 12, Houston, TX",
        phone="713-555-0101",
        facts={
            "source_lane": "curative_title",
            "operator_lane": "a_pull_docs_first",
            "county": "Harris",
            "hctax_account": "0123456789012",
            "probate_case_number": "PR-123456",
            "total_amount_due": "6500.25",
            "delinquent_years": 3,
            "market_value": 250000,
            "debt_to_value_pct": 2.6,
            "title_flags": ["estate_owner", "tax_suit_or_litigation"],
            "next_action": "Pull probate letters before outreach.",
        },
        raw_payload={"source": "harris_hot_title_packet"},
    )


def test_hubspot_customization_dry_run_builds_ares_real_estate_properties_without_provider_calls() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(settings=Settings(_env_file=None), hubspot_client=fake)  # type: ignore[arg-type]

    response = service.configure_crm(HubSpotCustomizationRequest())

    assert response.dry_run is True
    assert response.status == "skipped"
    property_names = {definition["name"] for definition in response.request_payload["properties"]}
    assert {
        "ares_source_lane",
        "ares_skiptrace_status",
        "ares_hctax_account",
        "ares_probate_case_number",
        "ares_document_pull_status",
    }.issubset(property_names)
    assert response.request_payload["deal_pipeline"]["label"] == "Ares Acquisition Pipeline"
    follow_up_property = next(
        definition for definition in response.request_payload["properties"] if definition["name"] == "ares_follow_up_permission"
    )
    assert follow_up_property["type"] == "bool"
    assert follow_up_property["fieldType"] == "booleancheckbox"
    assert fake.calls == []


def test_hubspot_customization_live_gate_applies_properties_and_pipeline() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            hubspot_provider_live_writes_enabled=True,
            hubspot_access_token="hubspot_test_token",
        ),
        hubspot_client=fake,  # type: ignore[arg-type]
    )

    response = service.configure_crm(HubSpotCustomizationRequest(dry_run_only=False, operator_approval=True))

    assert response.dry_run is False
    assert response.status == "applied"
    assert any(call[0] == "upsert_property" and call[2]["property_name"] == "ares_external_key" for call in fake.calls)
    assert fake.calls[-1][0] == "upsert_pipeline_by_label"
    assert fake.calls[-1][2]["label"] == "Ares Acquisition Pipeline"


def test_hubspot_customization_missing_hubspot_gate_stays_dry_run_without_provider_calls() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            hubspot_provider_live_writes_enabled=False,
            hubspot_access_token="hubspot_test_token",
        ),
        hubspot_client=fake,  # type: ignore[arg-type]
    )

    response = service.configure_crm(HubSpotCustomizationRequest(dry_run_only=False))

    assert response.dry_run is True
    assert response.status == "skipped"
    assert "HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=true" in response.missing_config
    assert fake.calls == []


def test_hubspot_customization_live_gate_requires_operator_approval_before_provider_calls() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            hubspot_provider_live_writes_enabled=True,
            hubspot_access_token="hubspot_test_token",
        ),
        hubspot_client=fake,  # type: ignore[arg-type]
    )

    try:
        service.configure_crm(HubSpotCustomizationRequest(dry_run_only=False))
    except RuntimeError as exc:
        assert "operator_approval=true" in str(exc)
    else:
        raise AssertionError("Expected missing operator approval to raise")
    assert fake.calls == []


def test_hubspot_customization_live_gate_requires_token_before_provider_calls() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            hubspot_provider_live_writes_enabled=True,
            hubspot_access_token=None,
        ),
        hubspot_client=fake,  # type: ignore[arg-type]
    )

    try:
        service.configure_crm(HubSpotCustomizationRequest(dry_run_only=False, operator_approval=True))
    except RuntimeError as exc:
        assert "HUBSPOT_ACCESS_TOKEN or HUBSPOT_PERSONAL_KEY" in str(exc)
    else:
        raise AssertionError("Expected missing HubSpot token to raise")
    assert fake.calls == []


def test_hubspot_record_sync_dry_run_maps_title_packet_record_to_contact_and_deal_payloads() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(settings=Settings(_env_file=None), hubspot_client=fake)  # type: ignore[arg-type]

    response = service.sync_record(HubSpotRecordSyncRequest(record=_record()))

    assert response.dry_run is True
    assert response.status == "skipped"
    contact = response.request_payload["contact"]["properties"]
    deal = response.request_payload["deal"]["properties"]
    assert contact["firstname"] == "Maria"
    assert contact["lastname"] == "Lopez"
    assert contact["phone"] == "+17135550101"
    assert contact["ares_skiptrace_status"] == "needs_skiptrace"
    assert deal["ares_external_key"] == "harris-hot18:0123456789012"
    assert deal["ares_hctax_account"] == "0123456789012"
    assert deal["ares_probate_case_number"] == "PR-123456"
    assert deal["ares_delinquent_tax_amount"] == 6500.25
    assert deal["ares_title_flags"] == "estate_owner, tax_suit_or_litigation"
    assert fake.calls == []


def test_hubspot_record_sync_live_gate_upserts_contact_by_phone_and_deal_by_ares_external_key() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            hubspot_provider_live_writes_enabled=True,
            hubspot_access_token="hubspot_test_token",
            hubspot_default_pipeline_id="pipeline_ares",
            hubspot_default_deal_stage_id="needs_skiptrace",
        ),
        hubspot_client=fake,  # type: ignore[arg-type]
    )

    response = service.sync_record(HubSpotRecordSyncRequest(record=_record(), dry_run_only=False, operator_approval=True))

    assert response.dry_run is False
    assert response.status == "synced"
    assert fake.calls[0][0] == "upsert_object_by_property"
    assert fake.calls[0][1] == "contacts"
    assert fake.calls[0][2]["lookup_property"] == "phone"
    assert fake.calls[1][0] == "upsert_object_by_property"
    assert fake.calls[1][1] == "deals"
    assert fake.calls[1][2]["lookup_property"] == "ares_external_key"
    assert fake.calls[1][2]["properties"]["pipeline"] == "pipeline_ares"
    assert fake.calls[1][2]["properties"]["dealstage"] == "needs_skiptrace"


def test_hubspot_record_sync_live_gate_requires_operator_approval_before_provider_calls() -> None:
    fake = FakeHubSpotClient()
    service = HubSpotCrmService(
        settings=Settings(
            _env_file=None,
            provider_live_sends_enabled=True,
            hubspot_provider_live_writes_enabled=True,
            hubspot_access_token="hubspot_test_token",
            hubspot_default_pipeline_id="pipeline_ares",
            hubspot_default_deal_stage_id="needs_skiptrace",
        ),
        hubspot_client=fake,  # type: ignore[arg-type]
    )

    try:
        service.sync_record(HubSpotRecordSyncRequest(record=_record(), dry_run_only=False))
    except RuntimeError as exc:
        assert "operator_approval=true" in str(exc)
    else:
        raise AssertionError("Expected missing operator approval to raise")
    assert fake.calls == []


def test_ares_hubspot_pipeline_keeps_skiptrace_and_title_review_stages_separate() -> None:
    pipeline = build_ares_hubspot_pipeline()

    stage_ids = [stage.stage_id for stage in pipeline.stages]

    assert stage_ids.index("needs_skiptrace") < stage_ids.index("contact_ready")
    assert stage_ids.index("title_legal_review") > stage_ids.index("seller_heir_interested")
    assert pipeline.stages[-2].closed_won is True
    assert pipeline.stages[-1].closed_lost is True
