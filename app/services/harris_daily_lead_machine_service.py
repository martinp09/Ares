from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date, datetime
import re
from typing import Any

from app.core.config import Settings, get_settings
from app.db.crm_records import CrmRecordsRepository
from app.models.crm_records import (
    CrmRecord,
    CrmRecordSourceMembership,
    CrmRecordStatus,
    CrmRecordType,
    CrmSourceRecord,
)
from app.models.probate_leads import ProbateHCADMatchStatus, ProbateLeadRecord
from app.services.harris_probate_intake_service import HarrisProbateIntakeService
from app.services.probate_hcad_match_service import ProbateHCADMatchService
from app.services.probate_lead_score_service import ProbateLeadScoreService
from app.services.probate_write_path_service import ProbateWritePathService, probate_write_path_service


class HarrisDailyLeadMachineService:
    """Dry-run/import foundation for the Harris daily probate + Estate Of lead machine.

    This service intentionally avoids provider sends. Slack is represented as a
    readiness/skip status until a Slack bot token is configured, and Vercel is not
    part of this local runtime path.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        probate_write_path: ProbateWritePathService | None = None,
        crm_records_repository: CrmRecordsRepository | None = None,
        probate_intake_service: HarrisProbateIntakeService | None = None,
        hcad_match_service: ProbateHCADMatchService | None = None,
        score_service: ProbateLeadScoreService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.probate_write_path = probate_write_path or probate_write_path_service
        self.crm_records_repository = crm_records_repository or CrmRecordsRepository(settings=self.settings)
        self.probate_intake_service = probate_intake_service or HarrisProbateIntakeService()
        self.hcad_match_service = hcad_match_service or ProbateHCADMatchService()
        self.score_service = score_service or ProbateLeadScoreService()

    def run_daily_import(
        self,
        *,
        business_id: str,
        environment: str,
        run_date: date,
        probate_records: Iterable[Mapping[str, Any]] = (),
        hcad_estate_of_records: Iterable[Mapping[str, Any]] = (),
        dry_run: bool = True,
        keep_only: bool = True,
    ) -> dict[str, Any]:
        probate_payloads = [dict(record) for record in probate_records]
        estate_payloads = [dict(record) for record in hcad_estate_of_records]
        qc_warnings: list[dict[str, Any]] = []

        hcad_candidates_by_case = _hcad_candidates_by_case(probate_payloads)
        probate_preview = self._preview_probate(
            probate_payloads,
            hcad_candidates_by_case=hcad_candidates_by_case,
            keep_only=keep_only,
            qc_warnings=qc_warnings,
        )
        if dry_run:
            probate_result = probate_preview
        else:
            write_result = self.probate_write_path.intake_probate_cases(
                business_id=business_id,
                environment=environment,
                payloads=probate_payloads,
                hcad_candidates_by_case=hcad_candidates_by_case,
                keep_only=keep_only,
            )
            probate_result = {
                "received_count": write_result["received_count"],
                "processed_count": write_result["processed_count"],
                "keep_now_count": write_result["keep_now_count"],
                "bridged_count": write_result["bridged_count"],
                "lead_ids": write_result["lead_ids"],
                "records": write_result["records"],
            }

        estate_preview = self._process_estate_of_records(
            business_id=business_id,
            environment=environment,
            records=estate_payloads,
            dry_run=dry_run,
            qc_warnings=qc_warnings,
        )
        counts = {
            "probate_received": len(probate_payloads),
            "probate_keep_now": probate_result["keep_now_count"],
            "probate_bridged": probate_result["bridged_count"],
            "estate_of_received": len(estate_payloads),
            "estate_of_candidates": estate_preview["candidate_count"],
            "estate_of_imported": estate_preview["imported_count"],
            "qc_warning_count": len(qc_warnings),
            "provider_send_count": 0,
        }
        return {
            "run_key": f"harris-daily-lead-machine:{run_date.isoformat()}",
            "run_date": run_date.isoformat(),
            "dry_run": dry_run,
            "live_send_policy": "no_provider_sends_or_slack_posts_from_daily_import",
            "counts": counts,
            "probate": probate_result,
            "estate_of": estate_preview,
            "qc_warnings": qc_warnings,
            "notifications": [self._daily_digest_notification_status(counts)],
        }

    def _preview_probate(
        self,
        payloads: list[dict[str, Any]],
        *,
        hcad_candidates_by_case: Mapping[str, Iterable[Mapping[str, Any]]],
        keep_only: bool,
        qc_warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        keep_now_count = 0
        for payload in payloads:
            record = self.probate_intake_service.normalize_case(payload)
            enriched = self._enrich_probate_preview(record, payload, hcad_candidates_by_case=hcad_candidates_by_case)
            if enriched.keep_now:
                keep_now_count += 1
            if enriched.hcad_match_status == ProbateHCADMatchStatus.MULTIPLE:
                qc_warnings.append(
                    {
                        "code": "probate_hcad_multiple_candidates",
                        "source": "harris_county_probate",
                        "source_key": enriched.case_number,
                        "message": "Probate case has multiple top-ranked HCAD candidates and requires match QC.",
                    }
                )
            if keep_only and not enriched.keep_now:
                continue
            records.append(
                {
                    "case_number": enriched.case_number,
                    "keep_now": enriched.keep_now,
                    "lead_score": enriched.lead_score,
                    "hcad_match_status": str(enriched.hcad_match_status),
                    "contact_confidence": str(enriched.contact_confidence),
                    "bridged_lead_id": None,
                }
            )
        return {
            "received_count": len(payloads),
            "processed_count": len(records),
            "keep_now_count": keep_now_count if not keep_only else len(records),
            "bridged_count": 0,
            "lead_ids": [],
            "records": records,
        }

    def _enrich_probate_preview(
        self,
        record: ProbateLeadRecord,
        payload: Mapping[str, Any],
        *,
        hcad_candidates_by_case: Mapping[str, Iterable[Mapping[str, Any]]],
    ) -> ProbateLeadRecord:
        candidates = list(hcad_candidates_by_case.get(record.case_number, []))
        matched = self.hcad_match_service.match_lead(record, candidates) if candidates else record
        overlay_updates = ProbateWritePathService._overlay_updates(payload)
        if overlay_updates:
            matched = ProbateLeadRecord.model_validate({**matched.model_dump(mode="python"), **overlay_updates})
        return self.score_service.score_lead(matched)

    def _process_estate_of_records(
        self,
        *,
        business_id: str,
        environment: str,
        records: list[dict[str, Any]],
        dry_run: bool,
        qc_warnings: list[dict[str, Any]],
    ) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        imported_ids: list[str] = []
        source_record_ids: list[str] = []
        excluded_count = 0
        seen_keys: set[str] = set()
        for raw in records:
            normalized = _normalize_estate_of_record(raw)
            source_key = normalized["source_key"]
            if source_key in seen_keys:
                qc_warnings.append(
                    {
                        "code": "estate_of_duplicate_in_payload",
                        "source": "hcad_estate_of",
                        "source_key": source_key,
                        "message": "Duplicate Estate Of source record in the same daily payload was ignored after the first row.",
                    }
                )
                continue
            seen_keys.add(source_key)
            if not normalized["eligible"]:
                excluded_count += 1
                qc_warnings.append(
                    {
                        "code": "estate_of_false_positive_excluded",
                        "source": "hcad_estate_of",
                        "source_key": source_key,
                        "message": normalized["exclusion_reason"],
                    }
                )
                continue
            selected_contacts, hidden_contact_count = _cap_contacts(raw)
            if hidden_contact_count:
                qc_warnings.append(
                    {
                        "code": "estate_of_contact_cap_applied",
                        "source": "hcad_estate_of",
                        "source_key": source_key,
                        "message": "More than two contact candidates were provided; only the top two are surfaced.",
                        "hidden_contact_count": hidden_contact_count,
                    }
                )
            if normalized["tax_overlay_status"] == "tax_overlay_ambiguous":
                qc_warnings.append(
                    {
                        "code": "estate_of_tax_overlay_ambiguous",
                        "source": "hcad_estate_of",
                        "source_key": source_key,
                        "message": "Tax overlay is ambiguous and should be reviewed before promotion.",
                    }
                )
            record_status = _estate_record_status(normalized, selected_contacts)
            row = {
                "source_key": source_key,
                "owner_name": normalized["owner_name"],
                "property_address": normalized["property_address"],
                "hcad_account": normalized["hcad_account"],
                "tax_delinquent": normalized["tax_delinquent"],
                "tax_overlay_status": normalized["tax_overlay_status"],
                "selected_contact_count": len(selected_contacts),
                "additional_contacts_hidden": hidden_contact_count > 0,
                "status": record_status.value,
                "record_id": None,
                "source_record_id": None,
            }
            if not dry_run:
                source_record = self.crm_records_repository.upsert_source_record(
                    CrmSourceRecord(
                        business_id=business_id,
                        environment=environment,
                        source_system="hcad_estate_of",
                        source_key=source_key,
                        source_type="estate_of_tax_delinquency_candidate",
                        payload=raw,
                        extracted_at=_parse_datetime(raw.get("extracted_at") or raw.get("verified_at")),
                        confidence=normalized["source_confidence"],
                    )
                )
                crm_record = self.crm_records_repository.upsert_record(
                    CrmRecord(
                        business_id=business_id,
                        environment=environment,
                        record_type=CrmRecordType.TAX_DELINQUENCY
                        if normalized["tax_delinquent"]
                        else CrmRecordType.PROPERTY,
                        status=record_status,
                        identity_key=f"hcad_estate_of:{source_key}",
                        display_name=normalized["display_name"],
                        owner_name=normalized["owner_name"],
                        property_address=normalized["property_address"],
                        mailing_address=normalized["mailing_address"],
                        tags=normalized["tags"],
                        data_quality_score=normalized["data_quality_score"],
                        source_record_ids=[source_record.id or ""],
                        facts={
                            "source_lane": "hcad_estate_of",
                            "hcad_account": normalized["hcad_account"],
                            "tax_account": normalized["tax_account"],
                            "tax_overlay_status": normalized["tax_overlay_status"],
                            "tax_delinquent": normalized["tax_delinquent"],
                            "delinquent_amount": normalized["delinquent_amount"],
                            "delinquent_years": normalized["delinquent_years"],
                            "selected_contacts": selected_contacts,
                            "selected_contact_count": len(selected_contacts),
                            "additional_contacts_hidden": hidden_contact_count > 0,
                            "hidden_contact_count": hidden_contact_count,
                            "qc_status": _estate_qc_status(normalized, selected_contacts),
                        },
                        raw_payload={"hcad_estate_of_record": raw},
                    )
                )
                self.crm_records_repository.add_source_membership(
                    CrmRecordSourceMembership(
                        business_id=business_id,
                        environment=environment,
                        record_id=crm_record.id or "",
                        source_record_id=source_record.id,
                        source_system="hcad_estate_of",
                        source_key=source_key,
                        list_name="daily_harris_estate_of",
                        metadata={"source_lane": "hcad_estate_of", "run_source": "harris_daily_lead_machine"},
                    )
                )
                row["record_id"] = crm_record.id
                row["source_record_id"] = source_record.id
                if crm_record.id:
                    imported_ids.append(crm_record.id)
                if source_record.id:
                    source_record_ids.append(source_record.id)
            rows.append(row)
        return {
            "received_count": len(records),
            "candidate_count": len(rows),
            "excluded_count": excluded_count,
            "imported_count": len(imported_ids),
            "record_ids": imported_ids,
            "source_record_ids": source_record_ids,
            "records": rows,
        }

    def _daily_digest_notification_status(self, counts: Mapping[str, Any]) -> dict[str, Any]:
        if self.settings.slack_bot_token:
            return {
                "type": "daily_digest",
                "status": "ready_not_sent",
                "reason": "Slack token is configured, but this endpoint records import readiness only and does not post live Slack messages.",
                "channel_id": self.settings.slack_channel_leads,
                "counts": dict(counts),
            }
        return {
            "type": "daily_digest",
            "status": "skipped_missing_token",
            "reason": "SLACK_BOT_TOKEN is not configured; import completed without Slack post.",
            "counts": dict(counts),
        }


_estate_include_pattern = re.compile(r"\b(ESTATE OF|EST OF|ESTATE|DECEASED)\b", re.IGNORECASE)
_estate_false_positive_pattern = re.compile(
    r"\b(REAL ESTATE|LLC|INC|CORP|CORPORATION|LTD|LP|LLP|TRUST|TRUSTEE|BANK|HOLDINGS|PARTNERS)\b",
    re.IGNORECASE,
)
_whitespace_pattern = re.compile(r"\s+")


def _hcad_candidates_by_case(payloads: Iterable[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    candidates_by_case: dict[str, list[Mapping[str, Any]]] = {}
    for payload in payloads:
        case_number = str(payload.get("case_number") or payload.get("cause_number") or "").strip()
        candidates = payload.get("hcad_candidates") or []
        if case_number and isinstance(candidates, list) and candidates:
            candidates_by_case[case_number] = [candidate for candidate in candidates if isinstance(candidate, Mapping)]
    return candidates_by_case


def _normalize_estate_of_record(record: Mapping[str, Any]) -> dict[str, Any]:
    owner_name = _text(record.get("owner_name") or record.get("owner"))
    property_address = _text(record.get("property_address") or record.get("site_address") or record.get("situs_address"))
    mailing_address = _text(record.get("mailing_address") or record.get("mail_to"))
    hcad_account = _account(record.get("hcad_account") or record.get("account") or record.get("acct"))
    tax_account = _account(record.get("tax_account") or record.get("hctax_account"))
    source_key = hcad_account or _source_key_from_address(property_address) or _source_key_from_address(mailing_address) or _slug(owner_name) or "unknown"
    tax_overlay_status = _tax_overlay_status(record)
    tax_delinquent = bool(
        record.get("tax_delinquent")
        or record.get("is_delinquent")
        or tax_overlay_status == "tax_overlay_verified_delinquent"
    )
    delinquent_amount = _number(record.get("delinquent_amount") or record.get("amount_owed"))
    delinquent_years = _number(record.get("delinquent_years") or record.get("est_years_delinquent"))
    eligible = bool(owner_name and _estate_include_pattern.search(owner_name))
    exclusion_reason = "Owner name does not contain an Estate Of / deceased signal."
    if eligible and _estate_false_positive_pattern.search(owner_name):
        eligible = False
        exclusion_reason = "Owner name matched an entity/REAL ESTATE false-positive exclusion."
    tags = ["source:hcad_estate_of"]
    if tax_delinquent:
        tags.append("tax:delinquent")
    if tax_overlay_status == "tax_overlay_ambiguous":
        tags.append("qc:tax_ambiguous")
    data_quality_score = 45
    if hcad_account:
        data_quality_score += 15
    if property_address:
        data_quality_score += 10
    if tax_delinquent:
        data_quality_score += 15
    if mailing_address:
        data_quality_score += 5
    data_quality_score = min(data_quality_score, 100)
    display_parts = [part for part in (owner_name, property_address or hcad_account) if part]
    return {
        "source_key": source_key,
        "eligible": eligible,
        "exclusion_reason": exclusion_reason,
        "owner_name": owner_name,
        "property_address": property_address,
        "mailing_address": mailing_address,
        "hcad_account": hcad_account,
        "tax_account": tax_account,
        "tax_overlay_status": tax_overlay_status,
        "tax_delinquent": tax_delinquent,
        "delinquent_amount": delinquent_amount,
        "delinquent_years": delinquent_years,
        "display_name": " — ".join(display_parts) if display_parts else source_key,
        "tags": tags,
        "data_quality_score": data_quality_score,
        "source_confidence": 0.85 if hcad_account else 0.65,
    }


def _estate_record_status(normalized: Mapping[str, Any], selected_contacts: list[dict[str, Any]]) -> CrmRecordStatus:
    if normalized["tax_overlay_status"] == "tax_overlay_ambiguous":
        return CrmRecordStatus.INCOMPLETE
    if normalized["tax_delinquent"] and selected_contacts:
        return CrmRecordStatus.CLEAN
    if normalized["tax_delinquent"]:
        return CrmRecordStatus.NEEDS_SKIP_TRACE
    return CrmRecordStatus.NEW


def _estate_qc_status(normalized: Mapping[str, Any], selected_contacts: list[dict[str, Any]]) -> str:
    if normalized["tax_overlay_status"] == "tax_overlay_ambiguous":
        return "needs_tax_qc"
    if not selected_contacts:
        return "needs_contact_qc"
    return "ready_for_operator_review"


def _tax_overlay_status(record: Mapping[str, Any]) -> str:
    value = _text(record.get("tax_overlay_status") or record.get("verification_status"))
    if value:
        return value
    if record.get("tax_delinquent") or record.get("is_delinquent"):
        return "tax_overlay_verified_delinquent"
    if record.get("tax_overlay_ambiguous") or record.get("ambiguous"):
        return "tax_overlay_ambiguous"
    return "tax_overlay_unknown"


def _cap_contacts(record: Mapping[str, Any]) -> tuple[list[dict[str, Any]], int]:
    raw_contacts = record.get("selected_contacts") or record.get("contact_candidates") or []
    if not isinstance(raw_contacts, list):
        return [], 0
    contacts = [dict(contact) for contact in raw_contacts if isinstance(contact, Mapping)]
    return contacts[:2], max(0, len(contacts) - 2)


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _account(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    digits = re.sub(r"\D+", "", text)
    return digits or text


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = _whitespace_pattern.sub(" ", str(value).strip())
    return text or None


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = re.sub(r"[^0-9.\-]+", "", str(value))
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _source_key_from_address(value: str | None) -> str | None:
    if not value:
        return None
    return _slug(value)


def _slug(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return normalized or None


harris_daily_lead_machine_service = HarrisDailyLeadMachineService()
