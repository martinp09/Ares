from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol

from app.core.config import Settings, get_settings
from app.db.client import utc_now
from app.db.crm_records import CrmRecordsRepository
from app.models.crm_records import CrmRecord, CrmRecordStatus, CrmSourceRecord
from app.providers.tracerfy import TracerfyClient, primary_email_from_trace, primary_phone_from_trace

_STATE_RE = re.compile(r"\b([A-Z]{2})\b(?:\s+(\d{5})(?:-\d{4})?)?\s*$")


class TracerfyLookupClient(Protocol):
    def instant_address_lookup(
        self,
        *,
        address: str,
        city: str,
        state: str,
        zip_code: str | None = None,
        find_owner: bool = True,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict[str, Any]: ...

    def instant_apn_lookup(self, *, parcel_id: str, county: str, state: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class SkipTraceLookupInput:
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    parcel_id: str | None = None
    county: str | None = None
    find_owner: bool = True
    first_name: str | None = None
    last_name: str | None = None


@dataclass(frozen=True, slots=True)
class SkipTraceResult:
    provider: str
    lookup_method: str
    hit: bool
    persons_count: int
    credits_deducted: int
    phone: str | None
    email: str | None
    raw_response: dict[str, Any]


class TracerfySkipTraceService:
    def __init__(
        self,
        *,
        settings: Settings | None = None,
        crm_records_repository: CrmRecordsRepository | None = None,
        client: TracerfyLookupClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.crm_records_repository = crm_records_repository or CrmRecordsRepository(settings=self.settings)
        if client is None:
            if not self.settings.tracerfy_api_key:
                raise RuntimeError("TRACERFY_API_KEY is required for Tracerfy skip tracing")
            client = TracerfyClient(api_key=self.settings.tracerfy_api_key, base_url=self.settings.tracerfy_base_url)
        self.client = client

    def enrich_crm_record(
        self,
        record_id: str,
        *,
        lookup: SkipTraceLookupInput | None = None,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> tuple[CrmRecord, SkipTraceResult]:
        record = self.crm_records_repository.get_record(record_id)
        if record is None:
            raise KeyError(f"CRM record {record_id} not found")
        resolved = self._resolve_lookup(record, lookup)
        result = self.trace(resolved)
        updated = self._apply_result(record, result)
        if updated.status != record.status:
            self.crm_records_repository.append_status_history(
                event=self._status_event(record, updated, actor_id=actor_id, actor_type=actor_type)
            )
        return updated, result

    def trace(self, lookup: SkipTraceLookupInput) -> SkipTraceResult:
        if lookup.parcel_id and lookup.county and lookup.state:
            response = self.client.instant_apn_lookup(parcel_id=lookup.parcel_id, county=lookup.county, state=lookup.state)
            return self._result_from_response(response, lookup_method="apn")
        if not (lookup.address and lookup.city and lookup.state):
            raise ValueError("Tracerfy address lookup requires address, city, and state")
        response = self.client.instant_address_lookup(
            address=lookup.address,
            city=lookup.city,
            state=lookup.state,
            zip_code=lookup.zip_code,
            find_owner=lookup.find_owner,
            first_name=lookup.first_name,
            last_name=lookup.last_name,
        )
        return self._result_from_response(response, lookup_method="address")

    def _resolve_lookup(self, record: CrmRecord, lookup: SkipTraceLookupInput | None) -> SkipTraceLookupInput:
        if lookup is not None:
            return lookup
        facts = record.facts or {}
        parcel_id = self._first_text(facts.get("parcel_id"), facts.get("apn"), facts.get("account_number"))
        county = self._first_text(facts.get("county"), facts.get("property_county"))
        state = self._first_text(facts.get("state"), facts.get("property_state"))
        if parcel_id and county and state:
            return SkipTraceLookupInput(parcel_id=parcel_id, county=county, state=state)
        parsed = parse_property_address(record.property_address or self._first_text(facts.get("property_address")) or "")
        return SkipTraceLookupInput(
            address=self._first_text(facts.get("street_address"), parsed.address),
            city=self._first_text(facts.get("city"), facts.get("property_city"), parsed.city),
            state=self._first_text(facts.get("state"), facts.get("property_state"), parsed.state),
            zip_code=self._first_text(facts.get("zip"), facts.get("zip_code"), facts.get("property_zip"), parsed.zip_code),
            find_owner=True,
        )

    def _apply_result(self, record: CrmRecord, result: SkipTraceResult) -> CrmRecord:
        facts = {
            **record.facts,
            "skiptrace": {
                "provider": result.provider,
                "lookup_method": result.lookup_method,
                "hit": result.hit,
                "persons_count": result.persons_count,
                "credits_deducted": result.credits_deducted,
                "checked_at": utc_now().isoformat(),
            },
        }
        raw_payload = {**record.raw_payload, "tracerfy_skiptrace_response": result.raw_response}
        phone = record.phone or result.phone
        email = record.email or result.email
        status = record.status
        if result.hit and (phone or email) and record.status == CrmRecordStatus.NEEDS_SKIP_TRACE:
            status = CrmRecordStatus.CLEAN
        data_quality_score = _data_quality_score(record.model_copy(update={"phone": phone, "email": email}))
        updated = record.model_copy(
            update={
                "phone": phone,
                "email": email,
                "status": status,
                "facts": facts,
                "raw_payload": raw_payload,
                "data_quality_score": max(record.data_quality_score, data_quality_score),
                "last_activity_at": utc_now(),
                "updated_at": utc_now(),
            }
        )
        self.crm_records_repository.upsert_source_record(
            CrmSourceRecord(
                business_id=record.business_id,
                environment=record.environment,
                source_system="tracerfy",
                source_key=f"skiptrace:{record.id or record.resolved_identity_key()}",
                source_type="skiptrace_result",
                payload=result.raw_response,
                confidence=1.0 if result.hit else 0.0,
            )
        )
        return self.crm_records_repository.upsert_record(updated, dedupe_key=record.resolved_identity_key())

    @staticmethod
    def _result_from_response(response: dict[str, Any], *, lookup_method: str) -> SkipTraceResult:
        return SkipTraceResult(
            provider="tracerfy",
            lookup_method=lookup_method,
            hit=bool(response.get("hit")),
            persons_count=int(response.get("persons_count") or len(response.get("persons") or [])),
            credits_deducted=int(response.get("credits_deducted") or 0),
            phone=primary_phone_from_trace(response),
            email=primary_email_from_trace(response),
            raw_response=response,
        )

    @staticmethod
    def _first_text(*values: Any) -> str | None:
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return None

    @staticmethod
    def _status_event(record: CrmRecord, updated: CrmRecord, *, actor_id: str | None, actor_type: str | None):
        from app.models.crm_records import CrmRecordStatusHistory

        return CrmRecordStatusHistory(
            business_id=updated.business_id,
            environment=updated.environment,
            record_id=updated.id or record.id or "",
            from_status=record.status,
            to_status=updated.status,
            actor_id=actor_id,
            actor_type=actor_type,
            reason="tracerfy skiptrace enrichment",
            metadata={"provider": "tracerfy"},
        )


@dataclass(frozen=True, slots=True)
class ParsedAddress:
    address: str | None
    city: str | None
    state: str | None
    zip_code: str | None


def parse_property_address(value: str) -> ParsedAddress:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) >= 3:
        state_zip = parts[-1].upper()
        match = _STATE_RE.search(state_zip)
        state = match.group(1) if match else None
        zip_code = match.group(2) if match else None
        return ParsedAddress(address=parts[0], city=parts[-2], state=state, zip_code=zip_code)
    return ParsedAddress(address=value.strip() or None, city=None, state=None, zip_code=None)


def _data_quality_score(record: CrmRecord) -> int:
    available_fields = [record.owner_name or record.display_name, record.phone, record.email, record.property_address, record.mailing_address]
    return int((sum(1 for value in available_fields if value) / len(available_fields)) * 100)
