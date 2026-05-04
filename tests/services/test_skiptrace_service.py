from typing import Any

from app.core.config import Settings
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.crm_records import CrmRecordsRepository
from app.models.crm_records import CrmRecord, CrmRecordStatus, CrmRecordType
from app.services.skiptrace_service import SkipTraceLookupInput, TracerfySkipTraceService, parse_property_address


class FakeTracerfyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def instant_address_lookup(self, **payload: Any) -> dict[str, Any]:
        self.calls.append(("address", payload))
        return {
            "hit": True,
            "persons_count": 1,
            "credits_deducted": 5,
            "persons": [
                {
                    "full_name": "Jane Doe",
                    "deceased": False,
                    "property_owner": True,
                    "phones": [{"number": "7135550100", "type": "Mobile", "dnc": False, "rank": 1}],
                    "emails": [{"email": "jane@example.com", "rank": 1}],
                }
            ],
        }

    def instant_apn_lookup(self, **payload: Any) -> dict[str, Any]:
        self.calls.append(("apn", payload))
        return {"hit": False, "persons_count": 0, "credits_deducted": 0, "persons": []}


def test_parse_property_address_extracts_city_state_zip() -> None:
    parsed = parse_property_address("123 Main St, Houston, TX 77002")

    assert parsed.address == "123 Main St"
    assert parsed.city == "Houston"
    assert parsed.state == "TX"
    assert parsed.zip_code == "77002"


def test_tracerfy_skiptrace_enriches_needs_skiptrace_crm_record() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = CrmRecordsRepository(client=client, settings=Settings(), force_memory=True)
    record = repo.upsert_record(
        CrmRecord(
            business_id="biz",
            environment="dev",
            record_type=CrmRecordType.PROPERTY,
            status=CrmRecordStatus.NEEDS_SKIP_TRACE,
            display_name="123 Main",
            owner_name="Jane Doe",
            property_address="123 Main St, Houston, TX 77002",
        )
    )
    fake = FakeTracerfyClient()
    service = TracerfySkipTraceService(settings=Settings(), crm_records_repository=repo, client=fake)

    updated, result = service.enrich_crm_record(record.id or "")

    assert result.provider == "tracerfy"
    assert result.lookup_method == "address"
    assert updated.phone == "7135550100"
    assert updated.email == "jane@example.com"
    assert updated.status == CrmRecordStatus.CLEAN
    assert updated.facts["skiptrace"]["provider"] == "tracerfy"
    assert updated.raw_payload["tracerfy_skiptrace_response"]["credits_deducted"] == 5
    assert fake.calls[-1] == (
        "address",
        {
            "address": "123 Main St",
            "city": "Houston",
            "state": "TX",
            "zip_code": "77002",
            "find_owner": True,
            "first_name": None,
            "last_name": None,
        },
    )


def test_tracerfy_skiptrace_uses_apn_when_present() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = CrmRecordsRepository(client=client, settings=Settings(), force_memory=True)
    record = repo.upsert_record(
        CrmRecord(
            business_id="biz",
            environment="dev",
            record_type=CrmRecordType.PROPERTY,
            status=CrmRecordStatus.NEEDS_SKIP_TRACE,
            display_name="APN record",
            facts={"apn": "1234567890123", "county": "Harris", "state": "TX"},
        )
    )
    fake = FakeTracerfyClient()
    service = TracerfySkipTraceService(settings=Settings(), crm_records_repository=repo, client=fake)

    _, result = service.enrich_crm_record(record.id or "")

    assert result.lookup_method == "apn"
    assert fake.calls[-1] == ("apn", {"parcel_id": "1234567890123", "county": "Harris", "state": "TX"})


def test_explicit_lookup_overrides_record_address() -> None:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    repo = CrmRecordsRepository(client=client, settings=Settings(), force_memory=True)
    record = repo.upsert_record(
        CrmRecord(
            business_id="biz",
            environment="dev",
            record_type=CrmRecordType.PROPERTY,
            status=CrmRecordStatus.NEEDS_SKIP_TRACE,
            display_name="Needs override",
            property_address="unparsed",
        )
    )
    fake = FakeTracerfyClient()
    service = TracerfySkipTraceService(settings=Settings(), crm_records_repository=repo, client=fake)

    service.enrich_crm_record(
        record.id or "",
        lookup=SkipTraceLookupInput(address="456 Oak St", city="Houston", state="TX", zip_code="77003"),
    )

    assert fake.calls[-1][1]["address"] == "456 Oak St"
    assert fake.calls[-1][1]["city"] == "Houston"
