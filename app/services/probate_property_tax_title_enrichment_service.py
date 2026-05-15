from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.models.probate_leads import ProbateLeadRecord
from app.services.probate_hcad_match_service import ProbateHCADMatchService
from app.services.probate_lead_score_service import ProbateLeadScoreService
from app.services.tax_overlay_service import TaxOverlayResult, TaxOverlayStatus


class ProbatePropertyTaxTitleEnrichmentService:
    """No-send property/tax/title enrichment gate for probate-autopilot rows.

    This service intentionally consumes only supplied local candidates/snapshots.
    Live CAD, tax, and land-record calls are separate future provider gates.
    """

    def __init__(
        self,
        *,
        hcad_match_service: ProbateHCADMatchService | None = None,
        score_service: ProbateLeadScoreService | None = None,
        settings: Settings | None = None,
        cad_client: Any | None = None,
        tax_client: Any | None = None,
        land_record_client: Any | None = None,
    ) -> None:
        self.hcad_match_service = hcad_match_service or ProbateHCADMatchService()
        self.score_service = score_service or ProbateLeadScoreService()
        self.settings = settings or get_settings()
        self.cad_client = cad_client
        self.tax_client = tax_client
        self.land_record_client = land_record_client

    def run_enrichment(
        self,
        *,
        business_id: str,
        environment: str,
        keep_now_rows: list[Mapping[str, Any]],
        hcad_candidates_by_case: Mapping[str, list[Mapping[str, Any]]] | None = None,
        tax_overlays_by_case: Mapping[str, TaxOverlayResult | Mapping[str, Any]] | None = None,
        tax_overlays_by_account: Mapping[str, TaxOverlayResult | Mapping[str, Any]] | None = None,
        land_record_rows_by_case: Mapping[str, list[Mapping[str, Any]]] | None = None,
        live_cad_calls: bool = False,
        live_tax_calls: bool = False,
        live_land_record_calls: bool = False,
        enrichment_approval: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._validate_live_enrichment_gates(
            live_cad_calls=live_cad_calls,
            live_tax_calls=live_tax_calls,
            live_land_record_calls=live_land_record_calls,
            enrichment_approval=enrichment_approval,
        )

        hcad_candidates_by_case = hcad_candidates_by_case or {}
        tax_overlays_by_case = tax_overlays_by_case or {}
        tax_overlays_by_account = tax_overlays_by_account or {}
        land_record_rows_by_case = land_record_rows_by_case or {}

        enriched_records: list[ProbateLeadRecord] = []
        property_match_completed_count = 0
        property_match_unmatched_count = 0
        tax_overlay_completed_count = 0
        tax_overlay_ambiguous_count = 0
        title_friction_completed_count = 0
        title_friction_review_count = 0

        for row in keep_now_rows:
            record = _lead_from_row(row)
            case_key = _case_key(record.case_number)
            candidates = list(hcad_candidates_by_case.get(record.case_number) or hcad_candidates_by_case.get(case_key) or [])
            if live_cad_calls and not candidates:
                candidates = self._fetch_live_cad_candidates(record=record, source_row=row)
            record = self.hcad_match_service.match_lead(record, candidates)
            property_match = {
                "status": str(record.hcad_match_status),
                "hcad_acct": record.hcad_acct,
                "matched_candidate_count": record.matched_candidate_count,
                "contact_confidence": str(record.contact_confidence),
                "live_calls_attempted": bool(live_cad_calls),
            }
            if record.hcad_acct:
                property_match_completed_count += 1
            else:
                property_match_unmatched_count += 1

            tax_overlay = _lookup_tax_overlay(
                record=record,
                case_key=case_key,
                tax_overlays_by_case=tax_overlays_by_case,
                tax_overlays_by_account=tax_overlays_by_account,
            )
            if live_tax_calls and tax_overlay is None:
                tax_overlay = self._fetch_live_tax_overlay(record=record, source_row=row)
            tax_payload = _tax_payload(tax_overlay, live_calls_attempted=bool(live_tax_calls))
            if tax_payload["status"] != str(TaxOverlayStatus.NOT_CHECKED):
                tax_overlay_completed_count += 1
            if tax_payload["status"] == str(TaxOverlayStatus.AMBIGUOUS):
                tax_overlay_ambiguous_count += 1

            land_rows = list(land_record_rows_by_case.get(record.case_number) or land_record_rows_by_case.get(case_key) or [])
            if live_land_record_calls and not land_rows:
                land_rows = self._fetch_live_land_records(record=record, source_row=row)
            title_friction = _title_friction_payload(land_rows, live_calls_attempted=bool(live_land_record_calls))
            if title_friction["status"] != "not_checked":
                title_friction_completed_count += 1
            if title_friction["next_action"] in {"needs_document_image_review", "needs_land_record_review"}:
                title_friction_review_count += 1

            pain_stack = dict(record.pain_stack)
            pain_stack["property_match"] = property_match
            pain_stack["tax_overlay"] = tax_payload
            pain_stack["title_friction"] = title_friction
            tax_delinquent = bool(
                tax_payload.get("status") == str(TaxOverlayStatus.VERIFIED_DELINQUENT)
                and tax_payload.get("is_delinquent") is True
            )
            estate_of = bool(record.estate_of or _contains_estate_of(row) or _contains_estate_of(record.model_dump(mode="json")))
            record = record.model_copy(
                update={
                    "tax_delinquent": tax_delinquent,
                    "estate_of": estate_of,
                    "pain_stack": pain_stack,
                    "raw_payload": {
                        **record.raw_payload,
                        "probate_property_tax_title_enrichment": {
                            "business_id": business_id,
                            "environment": environment,
                            "no_send": True,
                            "provider_sends_enabled": False,
                            "live_cad_calls_attempted": bool(live_cad_calls),
                            "live_tax_calls_attempted": bool(live_tax_calls),
                            "live_land_record_calls_attempted": bool(live_land_record_calls),
                        },
                    },
                }
            )
            enriched_records.append(self.score_service.score_lead(record))

        return {
            "business_id": business_id,
            "environment": environment,
            "received_count": len(keep_now_rows),
            "enriched_count": len(enriched_records),
            "property_match_completed_count": property_match_completed_count,
            "property_match_unmatched_count": property_match_unmatched_count,
            "tax_overlay_completed_count": tax_overlay_completed_count,
            "tax_overlay_ambiguous_count": tax_overlay_ambiguous_count,
            "title_friction_completed_count": title_friction_completed_count,
            "title_friction_review_count": title_friction_review_count,
            "hubspot_mirror_blocked_until_approval_count": len(enriched_records),
            "outbound_blocked_until_explicit_approval_count": len(enriched_records),
            "no_send": True,
            "provider_sends_enabled": False,
            "outbound_allowed": False,
            "live_cad_calls_attempted": bool(live_cad_calls),
            "live_tax_calls_attempted": bool(live_tax_calls),
            "live_land_record_calls_attempted": bool(live_land_record_calls),
            "records": [record.model_dump(mode="json") for record in enriched_records],
        }

    def _validate_live_enrichment_gates(
        self,
        *,
        live_cad_calls: bool,
        live_tax_calls: bool,
        live_land_record_calls: bool,
        enrichment_approval: Mapping[str, Any] | None,
    ) -> None:
        if not (live_cad_calls or live_tax_calls or live_land_record_calls):
            return
        if not isinstance(enrichment_approval, Mapping) or enrichment_approval.get("approved") is not True:
            raise RuntimeError("live probate enrichment requires enrichment_approval.approved=true")
        if enrichment_approval.get("no_send") is not True or enrichment_approval.get("provider_sends_enabled") is not False:
            raise RuntimeError("live probate enrichment requires enrichment_approval.no_send=true and provider_sends_enabled=false")
        if live_cad_calls and not self.settings.lead_machine_live_cad_calls_enabled:
            raise RuntimeError("live CAD calls are disabled; set LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED=true")
        if live_tax_calls and not self.settings.lead_machine_live_tax_calls_enabled:
            raise RuntimeError("live tax calls are disabled; set LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED=true")
        if live_land_record_calls and not self.settings.lead_machine_live_land_record_calls_enabled:
            raise RuntimeError("live land-record calls are disabled; set LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED=true")
        if live_cad_calls and self.cad_client is None:
            raise RuntimeError("live CAD calls require a registered public CAD client")
        if live_tax_calls and self.tax_client is None:
            raise RuntimeError("live tax calls require a registered public tax client")
        if live_land_record_calls and self.land_record_client is None:
            raise RuntimeError("live land-record calls require a registered public land-record client")

    def _fetch_live_cad_candidates(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        result = _call_live_client(self.cad_client, "fetch_candidates", record=record, source_row=source_row)
        return [item for item in result if isinstance(item, Mapping)] if isinstance(result, list) else []

    def _fetch_live_tax_overlay(
        self,
        *,
        record: ProbateLeadRecord,
        source_row: Mapping[str, Any],
    ) -> TaxOverlayResult | Mapping[str, Any] | None:
        result = _call_live_client(self.tax_client, "fetch_tax_overlay", record=record, source_row=source_row)
        return result if isinstance(result, (TaxOverlayResult, Mapping)) else None

    def _fetch_live_land_records(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        result = _call_live_client(self.land_record_client, "fetch_land_records", record=record, source_row=source_row)
        return [item for item in result if isinstance(item, Mapping)] if isinstance(result, list) else []


def _lead_from_row(row: Mapping[str, Any]) -> ProbateLeadRecord:
    raw = row.get("raw") if isinstance(row.get("raw"), Mapping) else {}
    source = {**raw, **row}
    file_date = _parse_date(source.get("file_date"))
    return ProbateLeadRecord(
        case_number=str(source.get("case_number") or "").strip(),
        file_date=file_date,
        court_number=_text_or_none(source.get("court_number")),
        status=_text_or_none(source.get("status")),
        filing_type=str(source.get("filing_type") or "").strip(),
        filing_subtype=_text_or_none(source.get("filing_subtype")),
        estate_name=_text_or_none(source.get("estate_name") or source.get("style")),
        decedent_name=_text_or_none(source.get("decedent_name")),
        keep_now=bool(source.get("keep_now", True)),
        owner_name=_text_or_none(source.get("owner_name") or source.get("owner")),
        mailing_address=_text_or_none(source.get("mailing_address") or source.get("mail_to")),
        property_address=_text_or_none(source.get("property_address") or source.get("site_address") or source.get("situs_address")),
        pain_stack=dict(source.get("pain_stack") or {}) if isinstance(source.get("pain_stack"), Mapping) else {},
        raw_payload={"source_row": dict(row)},
    )


def _lookup_tax_overlay(
    *,
    record: ProbateLeadRecord,
    case_key: str,
    tax_overlays_by_case: Mapping[str, TaxOverlayResult | Mapping[str, Any]],
    tax_overlays_by_account: Mapping[str, TaxOverlayResult | Mapping[str, Any]],
) -> TaxOverlayResult | Mapping[str, Any] | None:
    if record.hcad_acct:
        direct = tax_overlays_by_account.get(record.hcad_acct) or tax_overlays_by_account.get(record.hcad_acct.lstrip("0"))
        if direct is not None:
            return direct
    return tax_overlays_by_case.get(record.case_number) or tax_overlays_by_case.get(case_key)


def _tax_payload(result: TaxOverlayResult | Mapping[str, Any] | None, *, live_calls_attempted: bool = False) -> dict[str, Any]:
    if result is None:
        return {
            "status": str(TaxOverlayStatus.NOT_CHECKED),
            "is_delinquent": None,
            "amount_owed": None,
            "account": None,
            "confidence": "none",
            "live_calls_attempted": live_calls_attempted,
        }
    payload = result.model_dump(mode="json") if isinstance(result, TaxOverlayResult) else dict(result)
    return {
        "status": str(payload.get("status") or TaxOverlayStatus.NOT_CHECKED),
        "is_delinquent": payload.get("is_delinquent"),
        "amount_owed": payload.get("amount_owed"),
        "prior_years_owed": payload.get("prior_years_owed"),
        "current_year_owed": payload.get("current_year_owed"),
        "estimated_years_delinquent": payload.get("estimated_years_delinquent"),
        "tax_value": payload.get("tax_value"),
        "taxes_under_suit": payload.get("taxes_under_suit"),
        "account": payload.get("account"),
        "search_method": payload.get("search_method"),
        "confidence": payload.get("confidence") or "low",
        "parser_warnings": payload.get("parser_warnings") or [],
        "live_calls_attempted": live_calls_attempted,
    }


def _title_friction_payload(rows: list[Mapping[str, Any]], *, live_calls_attempted: bool = False) -> dict[str, Any]:
    if not rows:
        return {
            "status": "not_checked",
            "instrument_count": 0,
            "high_value_instrument_types": [],
            "party_count": 0,
            "friction_flags": {},
            "confidence": "none",
            "source_refs": [],
            "next_action": "needs_land_record_review",
            "live_calls_attempted": live_calls_attempted,
        }
    instrument_types = [_instrument_type(row) for row in rows]
    flags = {
        "affidavit_of_heirship": any("AFFIDAVIT" in item and "HEIR" in item for item in instrument_types),
        "probate_recorded": any("PROBATE" in item for item in instrument_types),
        "deed_after_death": any("DEED" in item for item in instrument_types),
        "lien_or_tax_suit": any("LIEN" in item or "TAX SUIT" in item or "JUDGMENT" in item for item in instrument_types),
        "trustee_or_foreclosure": any("TRUSTEE" in item or "FORECLOSURE" in item for item in instrument_types),
        "life_estate_or_tod": any("LIFE ESTATE" in item or "TRANSFER ON DEATH" in item or "TOD" in item for item in instrument_types),
    }
    high_value = sorted({item for item in instrument_types if item and any(flag for flag in flags.values())})
    source_refs = [_source_ref(row) for row in rows]
    source_refs = [ref for ref in source_refs if ref]
    party_names = {_text_or_none(row.get(key)) for row in rows for key in ("grantor", "grantee", "party", "person_name")}
    party_names.discard(None)
    review_needed = any(flags.values())
    return {
        "status": "needs_document_image_review" if review_needed else "soft_signal",
        "instrument_count": len(rows),
        "high_value_instrument_types": high_value,
        "party_count": len(party_names),
        "friction_flags": flags,
        "confidence": "medium" if review_needed else "low",
        "source_refs": source_refs[:10],
        "next_action": "needs_document_image_review" if review_needed else "needs_land_record_review",
        "live_calls_attempted": live_calls_attempted,
    }


def _instrument_type(row: Mapping[str, Any]) -> str:
    return str(row.get("instrument_type") or row.get("doc_type") or row.get("document_type") or row.get("type") or "").strip().upper()


def _source_ref(row: Mapping[str, Any]) -> str | None:
    return _text_or_none(row.get("instrument_number") or row.get("document_number") or row.get("file_number") or row.get("source_ref"))


def _call_live_client(client: Any, method_name: str, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> Any:
    method = getattr(client, method_name, None)
    if method is None:
        raise RuntimeError(f"registered live enrichment client is missing {method_name}")
    return method(record=record, source_row=source_row)


def _case_key(value: str) -> str:
    return value.strip().casefold()


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _contains_estate_of(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_contains_estate_of(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_estate_of(item) for item in value)
    return "ESTATE OF" in str(value or "").upper()
