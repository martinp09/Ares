import json

import pytest

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.provider_links import ProviderLinksRepository
from app.models.provider_links import ProviderObjectLink
from app.services.instantly_enrollment_service import InstantlyEnrollmentService


class ExplodingClient:
    def bulk_add_leads(self, *args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("provider call was not allowed")


class ExplodingLinks:
    def get_by_ares_object(self, *args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("provider link read was not allowed")

    def upsert_link(self, *args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("provider link write was not allowed")


class FakeInstantlyClient:
    def __init__(self, response=None, exc=None):
        self.response = response if response is not None else [{"items": []}]
        self.exc = exc
        self.calls = []

    def bulk_add_leads(self, leads, **kwargs):
        self.calls.append({"leads": leads, **kwargs})
        if self.exc:
            raise self.exc
        return self.response


def settings(**overrides):
    defaults = {
        "provider_live_sends_enabled": False,
        "instantly_provider_live_enrollment_enabled": False,
        "instantly_api_key": None,
        "control_plane_backend": "memory",
        "lead_machine_backend": "memory",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def record(record_id="crm_1", email="jane@example.com", verification_status="valid", status="active", sync_hash="hash_1", **extra):
    return {
        "id": record_id,
        "email": email,
        "phone": "7135550100",
        "first_name": "Jane",
        "last_name": "Seller",
        "display_name": "Jane Seller",
        "status": status,
        "verification_status": verification_status,
        "sync_hash": sync_hash,
        "custom_variables": {"source_lane": "probate"},
        **extra,
    }


def live_settings(**overrides):
    return settings(
        provider_live_sends_enabled=True,
        instantly_provider_live_enrollment_enabled=True,
        instantly_api_key="test-key",
        **overrides,
    )


def memory_links():
    return ProviderLinksRepository(client=InMemoryControlPlaneClient(InMemoryControlPlaneStore()), settings=live_settings(), force_memory=True)


def test_preview_returns_eligible_and_excluded_without_provider_or_link_calls_or_token() -> None:
    service = InstantlyEnrollmentService(settings=settings(), client=ExplodingClient(), provider_links=ExplodingLinks())

    result = service.preview_enrollment(
        records=[record("crm_1"), record("crm_2", email="", verification_status="valid")],
        instantly_campaign_id="inst_camp_1",
    )

    assert result["dry_run"] is True
    assert result["would_call_provider"] is False
    assert result["eligible_count"] == 1
    assert result["excluded_count"] == 1
    assert result["results"][0]["action"] == "enroll"
    assert result["results"][1]["reason"] == "missing email"


@pytest.mark.parametrize(
    ("svc_settings", "message"),
    [
        (live_settings(), "operator approval"),
        (settings(instantly_provider_live_enrollment_enabled=True, instantly_api_key="test-key"), "Provider live sends are disabled"),
        (settings(provider_live_sends_enabled=True, instantly_api_key="test-key"), "Instantly live enrollment is disabled"),
        (settings(provider_live_sends_enabled=True, instantly_provider_live_enrollment_enabled=True, instantly_api_key=None), "API key is required"),
    ],
)
def test_apply_preflight_gates_before_provider_or_link_calls(svc_settings, message) -> None:
    service = InstantlyEnrollmentService(settings=svc_settings, client=ExplodingClient(), provider_links=ExplodingLinks())

    with pytest.raises(RuntimeError) as excinfo:
        service.apply_enrollment(
            business_id="biz",
            environment="dev",
            records=[record()],
            operator_approval="operator approval" not in message,
            instantly_campaign_id="inst_camp_1",
        )

    assert message in str(excinfo.value)


def test_apply_excludes_missing_email_bad_verification_and_suppressed_archived_without_provider_call() -> None:
    fake_client = FakeInstantlyClient()
    service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=memory_links())

    result = service.apply_enrollment(
        business_id="biz",
        environment="dev",
        records=[
            record("missing_email", email=""),
            record("invalid", verification_status="invalid"),
            record("unknown", verification_status="unknown"),
            {**record("missing_verification"), "verification_status": None, "facts": {}, "raw_payload": {}},
            record("suppressed", status="suppressed"),
            record("archived", status="archived"),
        ],
        operator_approval=True,
        instantly_campaign_id="inst_camp_1",
    )

    assert fake_client.calls == []
    assert result["excluded_count"] == 6
    reasons = {item["record_id"]: item["reason"] for item in result["results"]}
    assert reasons["missing_email"] == "missing email"
    assert reasons["invalid"] == "email verification status is invalid"
    assert reasons["unknown"] == "email verification status is unknown"
    assert reasons["missing_verification"] == "missing email verification status"
    assert reasons["suppressed"] == "record status is suppressed"
    assert reasons["archived"] == "record status is archived"


def test_apply_success_calls_bulk_add_once_with_provider_target_and_creates_links() -> None:
    links = memory_links()
    fake_client = FakeInstantlyClient(response=[{"items": [{"email": "jane@example.com", "id": "lead_1"}]}])
    service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=links)

    result = service.apply_enrollment(
        business_id="biz",
        environment="dev",
        records=[record(campaign_id="internal_campaign")],
        operator_approval=True,
        instantly_campaign_id="inst_camp_1",
        campaign_id="internal_campaign",
    )

    assert len(fake_client.calls) == 1
    assert fake_client.calls[0]["campaign_id"] == "inst_camp_1"
    assert fake_client.calls[0]["list_id"] is None
    assert fake_client.calls[0]["leads"][0]["email"] == "jane@example.com"
    assert fake_client.calls[0]["leads"][0]["custom_variables"]["source_lane"] == "probate"
    assert result["results"][0]["provider_object_id"] == "lead_1"
    assert result["enrolled_count"] == 1
    assert result["submitted_count"] == 1
    assert result["provider_batch_result"] == {
        "type": "list",
        "top_level_count_fields": {},
        "top_level_collection_lengths": {"items": 1},
        "per_lead_id_count": 1,
        "omitted_raw_payload": True,
    }
    link = links.get_by_ares_object(
        business_id="biz",
        environment="dev",
        provider="instantly",
        ares_object_type="crm_record",
        ares_object_id="crm_1",
        provider_object_type="lead",
    )
    assert link is not None
    assert link.provider_object_id == "lead_1"
    assert link.sync_hash == "hash_1"


def test_apply_uses_instantly_list_id_and_does_not_treat_internal_campaign_id_as_provider_campaign_id() -> None:
    fake_client = FakeInstantlyClient(response=[{"items": [{"email": "jane@example.com", "lead_id": "lead_1"}]}])
    service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=memory_links())

    result = service.apply_enrollment(
        business_id="biz",
        environment="dev",
        records=[record()],
        operator_approval=True,
        instantly_list_id="inst_list_1",
        campaign_id="internal_campaign",
    )

    assert fake_client.calls[0]["campaign_id"] is None
    assert fake_client.calls[0]["list_id"] == "inst_list_1"
    assert result["target"]["campaign_id"] == "internal_campaign"
    assert result["target"]["instantly_campaign_id"] is None


def test_apply_existing_link_skips_provider_call_and_link_write_regardless_of_sync_hash() -> None:
    for existing_sync_hash, record_sync_hash in (("hash_1", "hash_1"), (None, "hash_2"), ("old_hash", "hash_2")):
        links = memory_links()
        links.upsert_link(
            ProviderObjectLink(
                business_id="biz",
                environment="dev",
                provider="instantly",
                provider_object_type="lead",
                provider_object_id="lead_existing",
                ares_object_type="crm_record",
                ares_object_id="crm_1",
                sync_hash=existing_sync_hash,
            )
        )
        fake_client = FakeInstantlyClient()
        service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=links)

        result = service.apply_enrollment(
            business_id="biz",
            environment="dev",
            records=[record(sync_hash=record_sync_hash)],
            operator_approval=True,
            instantly_campaign_id="inst_camp_1",
        )

        assert fake_client.calls == []
        assert result["skipped_count"] == 1
        assert result["submitted_count"] == 0
        assert result["enrolled_count"] == 0
        assert result["results"][0]["provider_object_id"] == "lead_existing"


def test_apply_no_eligible_records_means_no_provider_call() -> None:
    fake_client = FakeInstantlyClient()
    service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=memory_links())

    result = service.apply_enrollment(
        business_id="biz",
        environment="dev",
        records=[record("bad", verification_status="undeliverable")],
        operator_approval=True,
        instantly_campaign_id="inst_camp_1",
    )

    assert fake_client.calls == []
    assert result["eligible_count"] == 0
    assert any("No eligible" in warning for warning in result["warnings"])


def test_apply_sanitizes_provider_errors() -> None:
    fake_client = FakeInstantlyClient(exc=RuntimeError("Authorization: Bearer abc123 token=rawsecret"))
    service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=memory_links())

    result = service.apply_enrollment(
        business_id="biz",
        environment="dev",
        records=[record()],
        operator_approval=True,
        instantly_campaign_id="inst_camp_1",
    )

    serialized = json.dumps(result, sort_keys=True).lower()
    assert "abc123" not in serialized
    assert "rawsecret" not in serialized
    assert "bearer [redacted]" in serialized
    assert result["error_count"] == 1


def test_apply_does_not_create_link_when_response_has_no_per_lead_id() -> None:
    links = memory_links()
    fake_client = FakeInstantlyClient(response=[{"status": "ok"}])
    service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=links)

    result = service.apply_enrollment(
        business_id="biz",
        environment="dev",
        records=[record()],
        operator_approval=True,
        instantly_campaign_id="inst_camp_1",
    )

    assert result["results"][0]["action"] == "submitted_unlinked"
    assert result["results"][0].get("provider_object_id") is None
    assert result["submitted_count"] == 1
    assert result["enrolled_count"] == 0
    assert "per-lead id" in result["results"][0]["reason"]
    assert links.get_by_ares_object(
        business_id="biz",
        environment="dev",
        provider="instantly",
        ares_object_type="crm_record",
        ares_object_id="crm_1",
        provider_object_type="lead",
    ) is None


def test_apply_provider_batch_summary_omits_raw_echoed_contact_payload() -> None:
    links = memory_links()
    fake_client = FakeInstantlyClient(
        response={
            "status": "ok",
            "accepted_count": 1,
            "data": [
                {
                    "email": "jane@example.com",
                    "phone": "7135550100",
                    "id": "lead_1",
                    "provider_internal": {"echo": "do-not-leak"},
                }
            ],
        }
    )
    service = InstantlyEnrollmentService(settings=live_settings(), client=fake_client, provider_links=links)

    result = service.apply_enrollment(
        business_id="biz",
        environment="dev",
        records=[record()],
        operator_approval=True,
        instantly_campaign_id="inst_camp_1",
    )

    assert result["provider_batch_result"] == {
        "type": "dict",
        "top_level_count_fields": {"accepted_count": 1},
        "top_level_collection_lengths": {"data": 1},
        "per_lead_id_count": 1,
        "omitted_raw_payload": True,
    }
    serialized_batch_summary = json.dumps(result["provider_batch_result"], sort_keys=True).lower()
    assert "jane@example.com" not in serialized_batch_summary
    assert "7135550100" not in serialized_batch_summary
    assert "do-not-leak" not in serialized_batch_summary
    assert result["results"][0]["email"] == "jane@example.com"
