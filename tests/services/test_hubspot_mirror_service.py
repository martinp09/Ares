import pytest

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.provider_links import ProviderLinksRepository
from app.models.provider_links import ProviderObjectLink
from app.services.hubspot_mirror_service import HubSpotMirrorService


class ExplodingClient:
    def __getattr__(self, name: str):
        raise AssertionError(f"provider should not be called: {name}")


class FakeHubSpotCustomizationClient:
    def __init__(self, *, groups=None, properties=None, pipelines=None) -> None:
        self.groups = groups or {"contacts": [], "deals": [], "companies": []}
        self.properties = properties or {"contacts": [], "deals": [], "companies": []}
        self.pipelines = pipelines or []
        self.calls: list[tuple[str, str]] = []

    def list_property_groups(self, object_type: str) -> dict:
        self.calls.append(("list_property_groups", object_type))
        return {"results": list(self.groups.get(object_type, []))}

    def create_property_group(self, object_type: str, payload: dict) -> dict:
        self.calls.append(("create_property_group", object_type))
        created = {**payload, "id": f"group_{object_type}_{payload['name']}"}
        self.groups.setdefault(object_type, []).append(created)
        return created

    def list_properties(self, object_type: str) -> dict:
        self.calls.append(("list_properties", object_type))
        return {"results": list(self.properties.get(object_type, []))}

    def create_property(self, object_type: str, payload: dict) -> dict:
        self.calls.append(("create_property", object_type))
        created = {**payload, "id": f"prop_{object_type}_{payload['name']}"}
        self.properties.setdefault(object_type, []).append(created)
        return created

    def list_pipelines(self, object_type: str = "deals") -> dict:
        self.calls.append(("list_pipelines", object_type))
        return {"results": list(self.pipelines)}

    def create_pipeline(self, object_type: str, payload: dict) -> dict:
        self.calls.append(("create_pipeline", object_type))
        created = {**payload, "id": "pipeline_ares"}
        self.pipelines.append(created)
        return created

    def create_pipeline_stage(self, object_type: str, pipeline_id: str, payload: dict) -> dict:
        self.calls.append(("create_pipeline_stage", pipeline_id))
        created = {**payload, "id": f"stage_{payload['stageId']}"}
        for pipeline in self.pipelines:
            if pipeline.get("id") == pipeline_id:
                pipeline.setdefault("stages", []).append(created)
        return created


class FakeHubSpotRecordClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | str]] = []
        self.next_id = 1

    def create_object(self, object_type: str, payload: dict) -> dict:
        self.calls.append(("create_object", object_type, payload))
        provider_id = f"hs_{object_type}_{self.next_id}"
        self.next_id += 1
        return {"id": provider_id, "properties": payload.get("properties", {})}

    def update_object(self, object_type: str, record_id: str, payload: dict) -> dict:
        self.calls.append(("update_object", object_type, record_id))
        return {"id": record_id, "properties": payload.get("properties", {})}


class ExplodingRecordClient(FakeHubSpotRecordClient):
    def create_object(self, object_type: str, payload: dict) -> dict:
        raise RuntimeError(
            "Authorization: Bearer hs-secret-token token=plain123 "
            "url=https://example.com/hook?secret=super-secret&api_key=key123"
        )

    def update_object(self, object_type: str, record_id: str, payload: dict) -> dict:
        raise RuntimeError(
            "Authorization: Bearer hs-secret-token token=plain123 "
            "url=https://example.com/hook?secret=super-secret&api_key=key123"
        )


class CountingProviderLinksRepository(ProviderLinksRepository):
    def __init__(self) -> None:
        super().__init__(client=InMemoryControlPlaneClient(InMemoryControlPlaneStore()), force_memory=True)
        self.upsert_calls = 0
        self.lookup_calls = 0

    def upsert_link(self, link: ProviderObjectLink) -> ProviderObjectLink:
        self.upsert_calls += 1
        return super().upsert_link(link)

    def get_by_ares_object(self, **kwargs):
        self.lookup_calls += 1
        return super().get_by_ares_object(**kwargs)


def _settings(**overrides) -> Settings:
    return Settings(
        hubspot_access_token=overrides.pop("hubspot_access_token", None),
        provider_live_sends_enabled=overrides.pop("provider_live_sends_enabled", False),
        hubspot_provider_live_writes_enabled=overrides.pop("hubspot_provider_live_writes_enabled", False),
        hubspot_default_pipeline_id=overrides.pop("hubspot_default_pipeline_id", "pipeline_default"),
        hubspot_default_deal_stage_id=overrides.pop("hubspot_default_deal_stage_id", "stage_default"),
        hubspot_owner_id=overrides.pop("hubspot_owner_id", "owner_123"),
        **overrides,
    )


def test_customization_preview_returns_property_group_properties_pipeline_and_no_provider_call() -> None:
    service = HubSpotMirrorService(settings=_settings(), client=ExplodingClient())

    preview = service.build_customization_preview()

    assert preview["provider"] == "hubspot"
    assert preview["dry_run"] is True
    assert preview["would_call_provider"] is False
    assert preview["live_write_enabled"] is False
    assert preview["payloads"]["property_groups"]["contacts"] == [
        {"name": "ares_information", "label": "Ares Information", "displayOrder": 50}
    ]
    contact_property_names = [item["name"] for item in preview["payloads"]["properties"]["contacts"]]
    contact_properties = {item["name"]: item for item in preview["payloads"]["properties"]["contacts"]}
    assert "ares_record_id" in contact_property_names
    assert "ares_next_best_action" in contact_property_names
    assert "ares_probate_case_number" in contact_property_names
    assert contact_properties["ares_mailing_address"]["fieldType"] == "textarea"
    assert contact_properties["ares_heir_candidate_count"]["type"] == "number"
    deal_property_names = [item["name"] for item in preview["payloads"]["properties"]["deals"]]
    deal_properties = {item["name"]: item for item in preview["payloads"]["properties"]["deals"]}
    assert "ares_opportunity_id" in deal_property_names
    assert "ares_sync_hash" in deal_property_names
    assert "ares_heir_candidates_summary" in deal_property_names
    assert deal_properties["ares_heir_candidates_summary"]["fieldType"] == "textarea"
    assert deal_properties["ares_party_count"]["type"] == "number"
    pipeline = preview["payloads"]["pipelines"]["deals"][0]
    assert pipeline["label"] == "Ares Acquisitions"
    assert [stage["label"] for stage in pipeline["stages"]][:3] == ["New Lead", "Data QC", "Needs Skiptrace"]
    assert pipeline["stages"][-2]["label"] == "Closed Won"
    assert pipeline["stages"][-1]["metadata"]["isClosed"] == "true"


def test_record_sync_preview_builds_contact_deal_company_payloads_without_provider_call() -> None:
    service = HubSpotMirrorService(settings=_settings(), client=ExplodingClient())

    preview = service.build_record_sync_preview(
        [
            {
                "id": "crm_1",
                "record_type": "contact_record",
                "display_name": "Jane Seller",
                "property_address": "123 Main St, Houston, TX",
                "mailing_address": "PO Box 123, Houston TX 77001",
                "source": "harris_probate",
                "source_run_id": "harris_probate_2026_04_28",
                "record_status": "active",
                "phone": "7135550100",
                "email": "jane@example.com",
                "contact_role": "Applicant",
                "contact_address": "PO Box 123, Houston TX 77001",
                "opportunity_id": "opp_1",
                "county": "Harris",
                "hcad_account": "0012340000001",
                "hctax_account": "0012340000001",
                "hcad_owner_names": "Estate of Jane Seller",
                "probate_case_number": "543678",
                "probate_court_number": "1",
                "probate_file_date": "2026-04-20",
                "probate_status": "Open",
                "probate_filing_type": "APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP",
                "estate_name": "IN THE ESTATE OF: JANE SELLER, DECEASED",
                "decedent_name": "Jane Seller",
                "best_contact_name": "Jane Applicant",
                "best_contact_role": "Applicant",
                "best_contact_address": "PO Box 123, Houston TX 77001",
                "heir_candidate_count": 5,
                "heir_candidates_summary": "Jane Applicant (Applicant); John Heir (Respondent)",
                "heir_status": "candidate_identified_relationship_pending",
                "heir_confidence": "medium_high_candidate_contact",
                "heir_next_gate": "Pull/OCR application to confirm relationship and authority.",
                "party_count": 7,
                "event_count": 7,
                "priority_tier": "HOT",
                "priority_flags": ["heirship", "applicant_address"],
                "tax_overlay_status": "tax_overlay_soft_no_signal",
                "tax_overlay_query": "Jane Seller",
                "tax_overlay_candidate_hit_count": 0,
                "lead_score": 83,
                "campaign_id": "camp_1",
                "next_best_action": "Review title packet",
            },
            {
                "id": "crm_2",
                "record_type": "entity_record",
                "display_name": "Seller Trust",
                "entity_role": "estate_entity",
                "source_lane": "probate",
                "property_address": "456 Oak St, Houston, TX",
            },
        ]
    )

    assert preview["would_call_provider"] is False
    assert preview["payloads"]["contacts"] == [
        {
            "properties": {
                "firstname": "Jane",
                "lastname": "Seller",
                "email": "jane@example.com",
                "phone": "7135550100",
                "address": "PO Box 123",
                "city": "Houston",
                "state": "TX",
                "zip": "77001",
                "country": "United States",
                "ares_record_id": "crm_1",
                "ares_source_lane": "harris_probate",
                "ares_contact_role": "Applicant",
                "ares_contact_address": "PO Box 123, Houston TX 77001",
                "ares_property_address": "123 Main St, Houston, TX",
                "ares_contact_status": "active",
                "ares_mailing_address": "PO Box 123, Houston TX 77001",
                "ares_probate_case_number": "543678",
                "ares_decedent_name": "Jane Seller",
                "ares_estate_name": "IN THE ESTATE OF: JANE SELLER, DECEASED",
                "ares_best_contact_name": "Jane Applicant",
                "ares_best_contact_role": "Applicant",
                "ares_best_contact_address": "PO Box 123, Houston TX 77001",
                "ares_heir_candidate_count": 5,
                "ares_heir_candidates_summary": "Jane Applicant (Applicant); John Heir (Respondent)",
                "ares_heir_status": "candidate_identified_relationship_pending",
                "ares_heir_confidence": "medium_high_candidate_contact",
                "ares_heir_next_gate": "Pull/OCR application to confirm relationship and authority.",
                "ares_priority_tier": "HOT",
                "ares_next_best_action": "Review title packet",
                "hubspot_owner_id": "owner_123",
            }
        }
    ]
    assert preview["payloads"]["companies"][0]["properties"] == {
        "name": "Seller Trust",
        "ares_entity_id": "crm_2",
        "ares_entity_role": "estate_entity",
        "ares_source_lane": "probate",
        "hubspot_owner_id": "owner_123",
    }
    first_deal = preview["payloads"]["deals"][0]["properties"]
    assert first_deal["dealname"] == "123 Main St, Houston, TX"
    assert first_deal["pipeline"] == "pipeline_default"
    assert first_deal["dealstage"] == "stage_default"
    assert first_deal["ares_primary_record_id"] == "crm_1"
    assert first_deal["ares_opportunity_id"] == "opp_1"
    assert first_deal["ares_lead_score"] == 83
    assert first_deal["ares_mailing_address"] == "PO Box 123, Houston TX 77001"
    assert first_deal["ares_probate_case_number"] == "543678"
    assert first_deal["ares_probate_filing_type"] == "APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP"
    assert first_deal["ares_best_contact_name"] == "Jane Applicant"
    assert first_deal["ares_best_contact_role"] == "Applicant"
    assert first_deal["ares_heir_candidate_count"] == 5
    assert first_deal["ares_heir_candidates_summary"] == "Jane Applicant (Applicant); John Heir (Respondent)"
    assert first_deal["ares_party_count"] == 7
    assert first_deal["ares_event_count"] == 7
    assert first_deal["ares_priority_flags"] == "heirship; applicant_address"
    assert first_deal["ares_tax_overlay_status"] == "tax_overlay_soft_no_signal"
    assert first_deal["ares_tax_overlay_query"] == "Jane Seller"
    assert first_deal["ares_tax_overlay_candidate_hit_count"] == 0


def test_record_sync_preview_preserves_zero_lead_score_without_falling_back() -> None:
    service = HubSpotMirrorService(settings=_settings(), client=ExplodingClient())

    preview = service.build_record_sync_preview(
        [
            {
                "id": "crm_zero",
                "display_name": "Zero Score",
                "lead_score": 0,
                "data_quality_score": 72,
            }
        ]
    )

    assert preview["payloads"]["deals"][0]["properties"]["ares_lead_score"] == 0


def test_record_sync_preview_omits_empty_sequence_values_instead_of_clearing_hubspot() -> None:
    service = HubSpotMirrorService(settings=_settings(), client=ExplodingClient())

    preview = service.build_record_sync_preview(
        [
            {
                "id": "crm_empty_sequence",
                "display_name": "Empty Sequence",
                "priority_flags": [],
            }
        ]
    )

    assert "ares_priority_flags" not in preview["payloads"]["deals"][0]["properties"]


def test_missing_live_write_gate_fails_before_provider_call() -> None:
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_access_token="token"),
        client=ExplodingClient(),
    )

    with pytest.raises(RuntimeError, match="live writes are disabled"):
        service.build_record_sync_preview([], dry_run=False)


def test_missing_token_fails_before_provider_call_when_live_gate_enabled() -> None:
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token=None),
        client=ExplodingClient(),
    )

    with pytest.raises(RuntimeError, match="access token is required"):
        service.build_customization_preview(dry_run=False)


def test_live_apply_rejected_after_gate_without_provider_call() -> None:
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token="token"),
        client=ExplodingClient(),
    )

    with pytest.raises(RuntimeError, match="apply-sync"):
        service.build_record_sync_preview([], dry_run=False)


def test_customization_apply_rejects_missing_operator_approval_before_provider_call() -> None:
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token="token"),
        client=ExplodingClient(),
    )

    with pytest.raises(RuntimeError, match="operator approval"):
        service.apply_customization(operator_approval=False)


def test_customization_apply_rejects_global_gate_before_provider_call() -> None:
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=False, hubspot_provider_live_writes_enabled=True, hubspot_access_token="token"),
        client=ExplodingClient(),
    )

    with pytest.raises(RuntimeError, match="Provider live sends are disabled"):
        service.apply_customization(operator_approval=True)


def test_customization_apply_rejects_hubspot_gate_before_provider_call() -> None:
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=False, hubspot_access_token="token"),
        client=ExplodingClient(),
    )

    with pytest.raises(RuntimeError, match="HubSpot live writes are disabled"):
        service.apply_customization(operator_approval=True)


def test_customization_apply_rejects_missing_token_before_provider_call() -> None:
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token=None),
        client=ExplodingClient(),
    )

    with pytest.raises(RuntimeError, match="access token is required"):
        service.apply_customization(operator_approval=True)


def test_customization_apply_creates_missing_groups_properties_and_pipeline_with_fake_client() -> None:
    fake_client = FakeHubSpotCustomizationClient()
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token="token"),
        client=fake_client,
    )

    result = service.apply_customization(operator_approval=True)

    assert result["live_applied"] is True
    assert result["property_groups_created"]["contacts"][0]["name"] == "ares_information"
    assert any(item["name"] == "ares_record_id" for item in result["properties_created"]["contacts"])
    assert result["pipeline_created"] == {"label": "Ares Acquisitions", "id": "pipeline_ares"}
    assert result["stages_created"][0]["label"] == "New Lead"
    expected_property_count = sum(len(items) for items in service._customization_payloads()["properties"].values())
    assert result["mutation_count"] == 3 + expected_property_count + 1
    assert ("create_pipeline", "deals") in fake_client.calls


def test_customization_apply_idempotent_existing_path_skips_and_creates_missing_stage_only() -> None:
    existing_stage = {"label": "New Lead", "id": "stage_new_lead"}
    fake_client = FakeHubSpotCustomizationClient(
        groups={object_type: [{"name": "ares_information"}] for object_type in ("contacts", "deals", "companies")},
        properties={
            "contacts": [{"name": "ares_record_id"}],
            "deals": [{"name": "ares_opportunity_id"}],
            "companies": [{"name": "ares_entity_id"}],
        },
        pipelines=[{"id": "pipeline_existing", "label": "Ares Acquisitions", "stages": [existing_stage]}],
    )
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token="token"),
        client=fake_client,
    )

    result = service.apply_customization(operator_approval=True)

    assert result["pipeline_created"] is None
    assert result["pipeline_existing"] == {"label": "Ares Acquisitions", "id": "pipeline_existing"}
    assert result["stages_skipped"] == [{"label": "New Lead", "id": "stage_new_lead"}]
    assert all(item["name"] == "ares_information" for items in result["property_groups_skipped"].values() for item in items)
    assert any(item["name"] == "ares_record_id" for item in result["properties_skipped"]["contacts"])
    assert ("create_pipeline", "deals") not in fake_client.calls
    assert ("create_pipeline_stage", "pipeline_existing") in fake_client.calls


def test_customization_apply_reuses_single_existing_pipeline_when_portal_limit_blocks_new_pipeline() -> None:
    probe_service = HubSpotMirrorService(settings=_live_settings(), client=ExplodingClient())
    payloads = probe_service._customization_payloads()
    fake_client = FakeHubSpotCustomizationClient(
        groups={object_type: list(payloads["property_groups"][object_type]) for object_type in ("contacts", "deals", "companies")},
        properties={object_type: list(payloads["properties"][object_type]) for object_type in ("contacts", "deals", "companies")},
        pipelines=[{"id": "default", "label": "Sales Pipeline", "stages": [{"label": "Closed Won", "id": "closedwon"}]}],
    )
    service = HubSpotMirrorService(settings=_live_settings(), client=fake_client)

    result = service.apply_customization(operator_approval=True)

    assert result["pipeline_created"] is None
    assert result["pipeline_existing"] == {"label": "Sales Pipeline", "id": "default"}
    assert result["stages_skipped"] == [{"label": "Closed Won", "id": "closedwon"}]
    assert len(result["stages_created"]) == 11
    assert result["mutation_count"] == 11
    assert result["warnings"] == [
        "HubSpot portal already has its maximum deal-pipeline count; reused the existing deal pipeline and added missing Ares stages."
    ]
    assert ("create_pipeline", "deals") not in fake_client.calls
    assert ("create_pipeline_stage", "default") in fake_client.calls


def test_dry_run_preview_does_not_require_token() -> None:
    service = HubSpotMirrorService(settings=_settings(hubspot_access_token=None), client=ExplodingClient())

    preview = service.build_record_sync_preview([])

    assert preview["dry_run"] is True
    assert preview["would_call_provider"] is False


def _live_settings() -> Settings:
    return _settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token="token")


def _sample_records() -> list[dict]:
    return [
        {
            "id": "crm_contact_1",
            "record_type": "contact_record",
            "display_name": "Jane Seller",
            "email": "jane@example.com",
            "phone": "7135550100",
            "property_address": "123 Main St",
            "opportunity_id": "opp_1",
            "sync_hash": "hash_contact",
        },
        {
            "id": "crm_entity_1",
            "record_type": "entity_record",
            "display_name": "Seller Trust",
            "entity_role": "estate_entity",
            "property_address": "456 Oak St",
        },
    ]


def test_record_apply_rejects_missing_operator_approval_before_provider_call_and_link_write() -> None:
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(settings=_live_settings(), client=ExplodingClient(), provider_links=links)

    with pytest.raises(RuntimeError, match="operator approval"):
        service.apply_record_sync(business_id="biz", environment="dev", records=_sample_records(), operator_approval=False)

    assert links.lookup_calls == 0
    assert links.upsert_calls == 0


def test_record_apply_rejects_global_gate_before_provider_call_and_link_write() -> None:
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=False, hubspot_provider_live_writes_enabled=True, hubspot_access_token="token"),
        client=ExplodingClient(),
        provider_links=links,
    )

    with pytest.raises(RuntimeError, match="Provider live sends are disabled"):
        service.apply_record_sync(business_id="biz", environment="dev", records=_sample_records(), operator_approval=True)

    assert links.lookup_calls == 0
    assert links.upsert_calls == 0


def test_record_apply_rejects_hubspot_gate_before_provider_call_and_link_write() -> None:
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=False, hubspot_access_token="token"),
        client=ExplodingClient(),
        provider_links=links,
    )

    with pytest.raises(RuntimeError, match="HubSpot live writes are disabled"):
        service.apply_record_sync(business_id="biz", environment="dev", records=_sample_records(), operator_approval=True)

    assert links.lookup_calls == 0
    assert links.upsert_calls == 0


def test_record_apply_rejects_missing_token_before_provider_call_and_link_write() -> None:
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(
        settings=_settings(provider_live_sends_enabled=True, hubspot_provider_live_writes_enabled=True, hubspot_access_token=None),
        client=ExplodingClient(),
        provider_links=links,
    )

    with pytest.raises(RuntimeError, match="access token is required"):
        service.apply_record_sync(business_id="biz", environment="dev", records=_sample_records(), operator_approval=True)

    assert links.lookup_calls == 0
    assert links.upsert_calls == 0


def test_record_apply_create_path_uses_fake_client_and_stores_provider_links() -> None:
    fake_client = FakeHubSpotRecordClient()
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(settings=_live_settings(), client=fake_client, provider_links=links)

    result = service.apply_record_sync(business_id="biz", environment="dev", records=_sample_records(), operator_approval=True)

    assert result["live_applied"] is True
    assert result["created_count"] == 4
    assert result["updated_count"] == 0
    assert result["failed_count"] == 0
    assert [(call[0], call[1]) for call in fake_client.calls] == [
        ("create_object", "contacts"),
        ("create_object", "deals"),
        ("create_object", "companies"),
        ("create_object", "deals"),
    ]
    assert [item["object_type"] for item in result["results"]] == ["contact", "deal", "company", "deal"]
    assert result["results"][0]["ares_object_type"] == "crm_record"
    assert result["results"][0]["ares_object_id"] == "crm_contact_1"
    assert result["results"][1]["ares_object_type"] == "opportunity"
    assert result["results"][1]["ares_object_id"] == "opp_1"
    assert result["results"][2]["ares_object_type"] == "crm_record"
    assert result["results"][2]["ares_object_id"] == "crm_entity_1"
    assert links.upsert_calls == 4
    assert links.get_by_ares_object(
        business_id="biz",
        environment="dev",
        provider="hubspot",
        ares_object_type="opportunity",
        ares_object_id="opp_1",
        provider_object_type="deal",
    ).provider_object_id == result["results"][1]["provider_object_id"]


def test_record_apply_update_path_uses_existing_provider_links_instead_of_create() -> None:
    fake_client = FakeHubSpotRecordClient()
    links = CountingProviderLinksRepository()
    links.upsert_link(
        ProviderObjectLink(
            business_id="biz",
            environment="dev",
            provider="hubspot",
            provider_object_type="contact",
            provider_object_id="hs_contact_existing",
            ares_object_type="crm_record",
            ares_object_id="crm_contact_1",
        )
    )
    links.upsert_link(
        ProviderObjectLink(
            business_id="biz",
            environment="dev",
            provider="hubspot",
            provider_object_type="deal",
            provider_object_id="hs_deal_existing",
            ares_object_type="opportunity",
            ares_object_id="opp_1",
        )
    )
    links.upsert_calls = 0
    service = HubSpotMirrorService(settings=_live_settings(), client=fake_client, provider_links=links)

    result = service.apply_record_sync(business_id="biz", environment="dev", records=[_sample_records()[0]], operator_approval=True)

    assert result["created_count"] == 0
    assert result["updated_count"] == 2
    assert links.upsert_calls == 2
    assert fake_client.calls == [
        ("update_object", "contacts", "hs_contact_existing"),
        ("update_object", "deals", "hs_deal_existing"),
    ]
    assert [item["provider_object_id"] for item in result["results"]] == ["hs_contact_existing", "hs_deal_existing"]


def test_record_apply_update_path_skips_when_existing_sync_hash_matches() -> None:
    fake_client = FakeHubSpotRecordClient()
    links = CountingProviderLinksRepository()
    links.upsert_link(
        ProviderObjectLink(
            business_id="biz",
            environment="dev",
            provider="hubspot",
            provider_object_type="contact",
            provider_object_id="hs_contact_existing",
            ares_object_type="crm_record",
            ares_object_id="crm_contact_1",
            sync_hash="hash_contact",
        )
    )
    links.upsert_link(
        ProviderObjectLink(
            business_id="biz",
            environment="dev",
            provider="hubspot",
            provider_object_type="deal",
            provider_object_id="hs_deal_existing",
            ares_object_type="opportunity",
            ares_object_id="opp_1",
            sync_hash="hash_contact",
        )
    )
    links.upsert_calls = 0
    service = HubSpotMirrorService(settings=_live_settings(), client=fake_client, provider_links=links)

    result = service.apply_record_sync(business_id="biz", environment="dev", records=[_sample_records()[0]], operator_approval=True)

    assert result["created_count"] == 0
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 2
    assert links.upsert_calls == 0
    assert fake_client.calls == []
    assert [item["action"] for item in result["results"]] == ["skip", "skip"]
    assert [item["provider_object_id"] for item in result["results"]] == ["hs_contact_existing", "hs_deal_existing"]


def test_record_apply_result_errors_are_sanitized_for_client_exceptions() -> None:
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(settings=_live_settings(), client=ExplodingRecordClient(), provider_links=links)

    result = service.apply_record_sync(
        business_id="biz",
        environment="dev",
        records=[{"id": "crm_contact_1", "display_name": "Jane Seller", "email": "jane@example.com"}],
        operator_approval=True,
    )

    assert result["failed_count"] == 2
    serialized = str(result)
    assert "hs-secret-token" not in serialized
    assert "plain123" not in serialized
    assert "super-secret" not in serialized
    assert "key123" not in serialized
    assert "Bearer [redacted]" in serialized


def test_entity_record_without_email_or_phone_does_not_emit_contact_matching_warning() -> None:
    service = HubSpotMirrorService(settings=_settings(), client=ExplodingClient())

    preview = service.build_record_sync_preview([
        {"id": "crm_entity_1", "record_type": "entity_record", "display_name": "Seller Trust", "property_address": "456 Oak St"}
    ])

    assert preview["warnings"] == []


def test_record_apply_empty_records_returns_zero_counts_and_no_provider_call() -> None:
    fake_client = FakeHubSpotRecordClient()
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(settings=_live_settings(), client=fake_client, provider_links=links)

    result = service.apply_record_sync(business_id="biz", environment="dev", records=[], operator_approval=True)

    assert result["created_count"] == 0
    assert result["updated_count"] == 0
    assert result["skipped_count"] == 0
    assert result["failed_count"] == 0
    assert result["results"] == []
    assert "No HubSpot record sync items" in result["warnings"][0]
    assert fake_client.calls == []
    assert links.lookup_calls == 0
    assert links.upsert_calls == 0


def test_dry_run_preview_still_does_not_call_provider_or_write_links() -> None:
    links = CountingProviderLinksRepository()
    service = HubSpotMirrorService(settings=_settings(hubspot_access_token=None), client=ExplodingClient(), provider_links=links)

    preview = service.build_record_sync_preview(_sample_records())

    assert preview["dry_run"] is True
    assert preview["would_call_provider"] is False
    assert links.lookup_calls == 0
    assert links.upsert_calls == 0
