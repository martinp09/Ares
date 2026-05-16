from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Mapping, Sequence

from app.core.config import Settings, get_settings

CASE_DETAIL_ENRICHMENT_VERSION = "probate_case_detail_enrichment_v1"
_PRIMARY_CONTACT_CAP = 2
_HARRIS_CASE_DETAIL_PATHS = (
    "/applications/websearch/casedetail.aspx",
    "/applications/websearch/courtcasedetail.aspx",
)
_ALLOWED_CASE_DETAIL_HOSTS = {
    "www.cclerk.hctx.net": _HARRIS_CASE_DETAIL_PATHS,
    "cclerk.hctx.net": _HARRIS_CASE_DETAIL_PATHS,
    "odyssey.mctx.org": ("/county/casedetail.aspx",),
}


class ProbateCaseDetailEnrichmentService:
    """No-send case-detail evidence extraction for probate autopilot keep-now rows.

    This service turns case-detail pages or structured detail payloads into
    parties/events/document evidence and contact-candidate packets. It never
    treats an applicant/heir/executor as a confirmed seller and never performs
    provider sends, CRM writes, skiptrace spend, SMS, or calls.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        case_detail_client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.case_detail_client = case_detail_client or PublicProbateCaseDetailClient()

    def run_enrichment(
        self,
        *,
        business_id: str,
        environment: str,
        keep_now_rows: list[Mapping[str, Any]],
        case_details_by_case: Mapping[str, Mapping[str, Any]] | None = None,
        live_case_detail_calls: bool = False,
        case_detail_approval: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._validate_live_case_detail_gates(
            live_case_detail_calls=live_case_detail_calls,
            case_detail_approval=case_detail_approval,
        )
        details_by_case = case_details_by_case or {}
        records: list[dict[str, Any]] = []
        detail_completed_count = 0
        detail_incomplete_count = 0
        detail_blocked_count = 0
        party_count = 0
        event_count = 0
        document_reference_count = 0
        contact_candidate_count = 0
        primary_contact_candidate_count = 0
        attorney_count = 0
        hearing_clue_count = 0
        publication_clue_count = 0
        live_attempted = False

        for row in keep_now_rows:
            source_row = dict(row)
            case_number = _text_or_none(source_row.get("case_number")) or ""
            detail_payload = _lookup_detail(details_by_case, case_number)
            row_live_attempted = False
            if detail_payload is None and live_case_detail_calls:
                row_live_attempted = True
                live_attempted = True
                detail_payload = self._fetch_live_case_detail(source_row)

            case_detail = normalize_case_detail_payload(
                detail_payload,
                source_row=source_row,
                business_id=business_id,
                environment=environment,
                live_case_detail_calls_attempted=row_live_attempted,
            )
            status = case_detail["status"]
            if status == "completed":
                detail_completed_count += 1
            elif status == "blocked":
                detail_blocked_count += 1
            else:
                detail_incomplete_count += 1

            party_count += len(case_detail["parties"])
            event_count += len(case_detail["events"])
            document_reference_count += len(case_detail["document_references"])
            contact_candidate_count += len(case_detail["contact_candidates"])
            primary_contact_candidate_count += len(case_detail["primary_contact_candidates"])
            attorney_count += case_detail["attorney_count"]
            hearing_clue_count += case_detail["hearing_clue_count"]
            publication_clue_count += case_detail["publication_clue_count"]

            pain_stack = dict(source_row.get("pain_stack") or {}) if isinstance(source_row.get("pain_stack"), Mapping) else {}
            pain_stack["case_detail"] = _case_detail_pain_stack(case_detail)
            enriched_row = {
                **source_row,
                "case_detail": case_detail,
                "contact_candidates": case_detail["primary_contact_candidates"],
                "all_contact_candidate_evidence": case_detail["contact_candidates"],
                "pain_stack": pain_stack,
            }
            primary = case_detail["primary_contact_candidates"]
            if primary and not _text_or_none(enriched_row.get("mailing_address")):
                address = _text_or_none(primary[0].get("address"))
                if address:
                    enriched_row["mailing_address"] = address
            records.append(enriched_row)

        status = _summary_status(
            received_count=len(keep_now_rows),
            completed=detail_completed_count,
            incomplete=detail_incomplete_count,
            blocked=detail_blocked_count,
        )
        return {
            "business_id": business_id,
            "environment": environment,
            "status": status,
            "received_count": len(keep_now_rows),
            "detail_completed_count": detail_completed_count,
            "detail_incomplete_count": detail_incomplete_count,
            "detail_blocked_count": detail_blocked_count,
            "party_count": party_count,
            "event_count": event_count,
            "document_reference_count": document_reference_count,
            "contact_candidate_count": contact_candidate_count,
            "primary_contact_candidate_count": primary_contact_candidate_count,
            "attorney_count": attorney_count,
            "hearing_clue_count": hearing_clue_count,
            "publication_clue_count": publication_clue_count,
            "no_send": True,
            "provider_sends_enabled": False,
            "outbound_allowed": False,
            "live_case_detail_calls_attempted": live_attempted,
            "records": records,
        }

    def _validate_live_case_detail_gates(
        self,
        *,
        live_case_detail_calls: bool,
        case_detail_approval: Mapping[str, Any] | None,
    ) -> None:
        if not live_case_detail_calls:
            return
        if not isinstance(case_detail_approval, Mapping) or case_detail_approval.get("approved") is not True:
            raise RuntimeError("live probate case-detail enrichment requires case_detail_approval.approved=true")
        if case_detail_approval.get("no_send") is not True or case_detail_approval.get("provider_sends_enabled") is not False:
            raise RuntimeError("live probate case-detail enrichment requires case_detail_approval.no_send=true and provider_sends_enabled=false")
        if not self.settings.lead_machine_live_case_detail_calls_enabled:
            raise RuntimeError("live case-detail calls are disabled; set LEAD_MACHINE_LIVE_CASE_DETAIL_CALLS_ENABLED=true")
        if self.case_detail_client is None or getattr(self.case_detail_client, "fetch_case_detail", None) is None:
            raise RuntimeError("live case-detail calls require a registered public case-detail client")

    def _fetch_live_case_detail(self, source_row: Mapping[str, Any]) -> Mapping[str, Any] | None:
        url = _case_detail_url(source_row)
        if not url:
            if _text_or_none(source_row.get("case_detail_postback_target")):
                return {
                    "status": "incomplete",
                    "incomplete_reason": "case_detail_postback_only",
                    "warnings": ["case_detail_postback_only"],
                }
            return {
                "status": "incomplete",
                "incomplete_reason": "case_detail_url_missing",
                "warnings": ["case_detail_url_missing"],
            }
        if not _is_allowed_public_case_detail_url(url):
            return {
                "status": "blocked",
                "source_url": url,
                "warnings": ["case_detail_url_not_allowed"],
            }
        try:
            result = self.case_detail_client.fetch_case_detail(source_row=source_row)
        except Exception as exc:  # noqa: BLE001 - public county detail pages can expire/block; preserve evidence state.
            return {
                "status": "blocked",
                "source_url": url,
                "warnings": [f"case_detail_fetch_failed:{type(exc).__name__}"],
            }
        return result if isinstance(result, Mapping) else None


class PublicProbateCaseDetailClient:
    """Read-only public case-detail fetcher for rows that already expose a detail URL."""

    def fetch_case_detail(self, *, source_row: Mapping[str, Any]) -> Mapping[str, Any]:
        url = _case_detail_url(source_row)
        if not url:
            raise RuntimeError("source row does not include case_detail_url")
        if not _is_allowed_public_case_detail_url(url):
            raise RuntimeError("case_detail_url is outside the approved public probate detail host allowlist")
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AresProbateAutopilot/1.0)"})
        with urllib.request.urlopen(request, timeout=45) as response:  # noqa: S310 - public county portals only.
            body = response.read().decode("utf-8", errors="replace")
        return {"html": body, "source_url": url}


def normalize_case_detail_payload(
    payload: Mapping[str, Any] | None,
    *,
    source_row: Mapping[str, Any],
    business_id: str,
    environment: str,
    live_case_detail_calls_attempted: bool,
) -> dict[str, Any]:
    case_number = _text_or_none(source_row.get("case_number"))
    county = _normalize_county(source_row.get("county"))
    if payload is None:
        return _incomplete_detail(
            source_row=source_row,
            business_id=business_id,
            environment=environment,
            reason="case_detail_not_available",
            live_case_detail_calls_attempted=live_case_detail_calls_attempted,
        )

    explicit_status = _text_or_none(payload.get("status"))
    if explicit_status == "blocked":
        return _blocked_detail(
            source_row=source_row,
            payload=payload,
            business_id=business_id,
            environment=environment,
            live_case_detail_calls_attempted=live_case_detail_calls_attempted,
        )

    html_payload = _text_or_none(payload.get("html") or payload.get("html_text"))
    parsed = parse_case_detail_html(html_payload, county=county, case_number=case_number, source_url=_source_url(payload, source_row)) if html_payload else {}
    parties = _normalize_parties(_structured_list(payload, "parties", "party_rows") or parsed.get("parties") or [])
    events = _normalize_events(_structured_list(payload, "events", "event_rows") or parsed.get("events") or [])
    documents = _normalize_documents(
        _structured_list(payload, "document_references", "documents", "docs", "document_rows")
        or parsed.get("document_references")
        or []
    )
    warnings = _string_list(payload.get("warnings")) + _string_list(parsed.get("warnings"))
    source_url = _source_url(payload, source_row) or _text_or_none(parsed.get("source_url"))
    contact_candidates = _contact_candidates(parties)
    primary_candidates = contact_candidates[:_PRIMARY_CONTACT_CAP]
    hearing_clues = _clue_count(events, documents, tokens=("HEARING", "SETTING"))
    publication_clues = _clue_count(events, documents, tokens=("PUBLICATION", "NOTICE"))
    attorney_count = _attorney_count(parties)
    if parties or events or documents:
        status = "completed"
        incomplete_reason = None
    else:
        status = "incomplete"
        incomplete_reason = explicit_status or "case_detail_empty"
    return {
        "version": CASE_DETAIL_ENRICHMENT_VERSION,
        "business_id": business_id,
        "environment": environment,
        "case_number": case_number,
        "county": county,
        "status": status,
        "incomplete_reason": incomplete_reason,
        "source_url": source_url,
        "parties": parties,
        "events": events,
        "document_references": documents,
        "contact_candidates": contact_candidates,
        "primary_contact_candidates": primary_candidates,
        "extra_contact_candidate_count": max(0, len(contact_candidates) - len(primary_candidates)),
        "party_count": len(parties),
        "event_count": len(events),
        "document_reference_count": len(documents),
        "contact_candidate_count": len(contact_candidates),
        "primary_contact_candidate_count": len(primary_candidates),
        "attorney_count": attorney_count,
        "hearing_clue_count": hearing_clues,
        "publication_clue_count": publication_clues,
        "warnings": warnings,
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
        "live_case_detail_calls_attempted": live_case_detail_calls_attempted,
    }


def parse_case_detail_html(
    html_text: str | None,
    *,
    county: str | None = None,
    case_number: str | None = None,
    source_url: str | None = None,
) -> dict[str, Any]:
    if not html_text:
        return {"parties": [], "events": [], "document_references": [], "warnings": ["empty_case_detail_html"]}
    parser = _TableParser()
    parser.feed(html_text)
    parties: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    for table in parser.tables:
        rows = _table_dicts(table)
        if not rows:
            continue
        table_kind = _classify_table(rows)
        if table_kind == "party":
            parties.extend(_party_from_row(row) for row in rows)
        elif table_kind == "event":
            events.extend(_event_from_row(row) for row in rows)
        elif table_kind == "document":
            documents.extend(_document_from_row(row) for row in rows)
    return {
        "case_number": case_number,
        "county": county,
        "source_url": source_url,
        "parties": [item for item in parties if item.get("name") or item.get("role")],
        "events": [item for item in events if item.get("event_type") or item.get("date")],
        "document_references": [item for item in documents if item.get("document_type") or item.get("document_number")],
        "warnings": [],
    }


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None
        self._cell_tag: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_tag = tag
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell_parts is not None and self._row is not None:
            self._row.append(_clean_text(" ".join(self._cell_parts)))
            self._cell_parts = None
            self._cell_tag = None
        elif tag == "tr" and self._table is not None and self._row is not None:
            if any(cell for cell in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _table_dicts(table: list[list[str]]) -> list[dict[str, str]]:
    if len(table) < 2:
        return []
    headers = [_normalize_header(cell) or f"column_{idx}" for idx, cell in enumerate(table[0], start=1)]
    rows: list[dict[str, str]] = []
    for raw_row in table[1:]:
        row: dict[str, str] = {}
        for index, header in enumerate(headers):
            row[header] = raw_row[index] if index < len(raw_row) else ""
        rows.append(row)
    return rows


def _classify_table(rows: list[dict[str, str]]) -> str | None:
    headers = " ".join(rows[0]).lower()
    if "document" in headers or "doc" in headers or "filing" in headers:
        return "document"
    if "event" in headers or "hearing" in headers or "result" in headers:
        return "event"
    if "party" in headers or ("name" in headers and ("role" in headers or "type" in headers or "attorney" in headers)):
        return "party"
    return None


def _party_from_row(row: Mapping[str, str]) -> dict[str, Any]:
    role = _first_header_text(row, "party_type", "party", "role", "type")
    name = _first_header_text(row, "name", "party_name", "person")
    attorney = _first_header_text(row, "attorney", "attorney_name")
    address = _first_header_text(row, "address", "mailing_address")
    return {"role": _canonical_role(role), "raw_role": role, "name": name, "address": address, "attorney_name": attorney}


def _event_from_row(row: Mapping[str, str]) -> dict[str, Any]:
    event_type = _first_header_text(row, "event", "event_type", "description", "setting")
    date = _first_header_text(row, "date", "event_date", "filed", "scheduled")
    result = _first_header_text(row, "result", "status", "comment")
    return {"date": date, "event_type": event_type, "result": result}


def _document_from_row(row: Mapping[str, str]) -> dict[str, Any]:
    document_type = _first_header_text(row, "document_type", "document", "doc_type", "filing", "description")
    document_number = _first_header_text(row, "document_number", "doc_number", "instrument_number", "number", "source_ref")
    filed_at = _first_header_text(row, "filed", "filed_date", "date")
    return {"filed_at": filed_at, "document_type": document_type, "document_number": document_number}


def _normalize_parties(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    parties: list[dict[str, Any]] = []
    for value in values:
        role_text = _text_or_none(value.get("role") or value.get("party_type") or value.get("type"))
        party = {
            "role": _canonical_role(role_text),
            "raw_role": role_text,
            "name": _text_or_none(value.get("name") or value.get("party_name") or value.get("person_name")),
            "address": _text_or_none(value.get("address") or value.get("mailing_address")),
            "attorney_name": _text_or_none(value.get("attorney_name") or value.get("attorney")),
        }
        if any(party.values()):
            parties.append(party)
    return parties


def _normalize_events(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for value in values:
        event = {
            "date": _text_or_none(value.get("date") or value.get("event_date")),
            "event_type": _text_or_none(value.get("event_type") or value.get("event") or value.get("description")),
            "result": _text_or_none(value.get("result") or value.get("status")),
        }
        if any(event.values()):
            events.append(event)
    return events


def _normalize_documents(values: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for value in values:
        document = {
            "filed_at": _text_or_none(value.get("filed_at") or value.get("filed") or value.get("date")),
            "document_type": _text_or_none(value.get("document_type") or value.get("doc_type") or value.get("type")),
            "document_number": _text_or_none(
                value.get("document_number") or value.get("doc_number") or value.get("instrument_number") or value.get("source_ref")
            ),
        }
        if any(document.values()):
            documents.append(document)
    return documents


def _contact_candidates(parties: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[tuple[int, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for party in parties:
        name = _text_or_none(party.get("name"))
        if not name:
            continue
        raw_role = _text_or_none(party.get("raw_role") or party.get("role")) or "unknown"
        role = _canonical_role(raw_role)
        if role == "decedent":
            continue
        priority = _contact_priority(role, raw_role)
        if priority <= 0:
            continue
        key = (name.casefold(), role)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            (
                priority,
                {
                    "name": name,
                    "role": role,
                    "raw_role": raw_role,
                    "candidate_kind": _candidate_kind(role, raw_role),
                    "address": _text_or_none(party.get("address")),
                    "confidence": "medium" if priority >= 8 else "low",
                    "evidence_source": "probate_case_detail_party",
                    "is_confirmed_seller": False,
                    "seller_authority_verified": False,
                    "skiptrace_status": "not_requested",
                    "paid_skiptrace_allowed": False,
                    "outbound_allowed": False,
                },
            )
        )
    return [candidate for _priority, candidate in sorted(candidates, key=lambda item: (-item[0], item[1]["name"]))]


def _case_detail_pain_stack(detail: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "status": detail.get("status"),
        "party_count": detail.get("party_count"),
        "event_count": detail.get("event_count"),
        "document_reference_count": detail.get("document_reference_count"),
        "contact_candidate_count": detail.get("contact_candidate_count"),
        "primary_contact_candidate_count": detail.get("primary_contact_candidate_count"),
        "hearing_clue_count": detail.get("hearing_clue_count"),
        "publication_clue_count": detail.get("publication_clue_count"),
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
    }


def _incomplete_detail(
    *,
    source_row: Mapping[str, Any],
    business_id: str,
    environment: str,
    reason: str,
    live_case_detail_calls_attempted: bool,
) -> dict[str, Any]:
    return _empty_detail(
        source_row=source_row,
        business_id=business_id,
        environment=environment,
        status="incomplete",
        incomplete_reason=reason,
        warnings=[] if reason == "case_detail_not_available" else [reason],
        live_case_detail_calls_attempted=live_case_detail_calls_attempted,
    )


def _blocked_detail(
    *,
    source_row: Mapping[str, Any],
    payload: Mapping[str, Any],
    business_id: str,
    environment: str,
    live_case_detail_calls_attempted: bool,
) -> dict[str, Any]:
    return _empty_detail(
        source_row=source_row,
        business_id=business_id,
        environment=environment,
        status="blocked",
        incomplete_reason=_text_or_none(payload.get("incomplete_reason")) or "case_detail_blocked",
        warnings=_string_list(payload.get("warnings")),
        source_url=_source_url(payload, source_row),
        live_case_detail_calls_attempted=live_case_detail_calls_attempted,
    )


def _empty_detail(
    *,
    source_row: Mapping[str, Any],
    business_id: str,
    environment: str,
    status: str,
    incomplete_reason: str | None,
    warnings: list[str],
    live_case_detail_calls_attempted: bool,
    source_url: str | None = None,
) -> dict[str, Any]:
    return {
        "version": CASE_DETAIL_ENRICHMENT_VERSION,
        "business_id": business_id,
        "environment": environment,
        "case_number": _text_or_none(source_row.get("case_number")),
        "county": _normalize_county(source_row.get("county")),
        "status": status,
        "incomplete_reason": incomplete_reason,
        "source_url": source_url or _case_detail_url(source_row),
        "parties": [],
        "events": [],
        "document_references": [],
        "contact_candidates": [],
        "primary_contact_candidates": [],
        "extra_contact_candidate_count": 0,
        "party_count": 0,
        "event_count": 0,
        "document_reference_count": 0,
        "contact_candidate_count": 0,
        "primary_contact_candidate_count": 0,
        "attorney_count": 0,
        "hearing_clue_count": 0,
        "publication_clue_count": 0,
        "warnings": warnings,
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
        "live_case_detail_calls_attempted": live_case_detail_calls_attempted,
    }


def _lookup_detail(details_by_case: Mapping[str, Mapping[str, Any]], case_number: str) -> Mapping[str, Any] | None:
    if not case_number:
        return None
    return details_by_case.get(case_number) or details_by_case.get(case_number.strip().casefold())


def _structured_list(payload: Mapping[str, Any], *keys: str) -> list[Mapping[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    return []


def _source_url(payload: Mapping[str, Any], source_row: Mapping[str, Any]) -> str | None:
    return _text_or_none(payload.get("source_url") or payload.get("case_detail_url")) or _case_detail_url(source_row)


def _case_detail_url(source_row: Mapping[str, Any]) -> str | None:
    raw_value = source_row.get("raw")
    raw_export_value = source_row.get("raw_export_row")
    raw_live_value = source_row.get("raw_live_row")
    raw: Mapping[str, Any] = raw_value if isinstance(raw_value, Mapping) else {}
    raw_export: Mapping[str, Any] = raw_export_value if isinstance(raw_export_value, Mapping) else {}
    raw_live: Mapping[str, Any] = raw_live_value if isinstance(raw_live_value, Mapping) else {}
    for value in (
        source_row.get("case_detail_url"),
        source_row.get("detail_url"),
        source_row.get("case_url"),
        raw.get("case_detail_url"),
        raw_export.get("case_detail_url"),
        raw_live.get("case_detail_url"),
    ):
        text = _text_or_none(value)
        if text:
            return text
    return None


def _is_allowed_public_case_detail_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False
    if parsed.scheme != "https":
        return False
    host = (parsed.hostname or "").lower()
    allowed_paths = _ALLOWED_CASE_DETAIL_HOSTS.get(host)
    if not allowed_paths:
        return False
    path = parsed.path.lower()
    return any(path.endswith(allowed_path) for allowed_path in allowed_paths)


def _contact_priority(role: str, raw_role: str) -> int:
    haystack = f"{role} {raw_role}".upper()
    if any(token in haystack for token in ("APPLICANT", "EXECUTOR", "ADMINISTRATOR", "PERSONAL REPRESENTATIVE", "PETITIONER")):
        return 10
    if any(token in haystack for token in ("HEIR", "BENEFICIARY", "DEVISEE")):
        return 8
    if any(token in haystack for token in ("INTERESTED", "RESPONDENT")):
        return 5
    if "ATTORNEY" in haystack or "AD LITEM" in haystack:
        return 2
    return 0


def _candidate_kind(role: str, raw_role: str) -> str:
    haystack = f"{role} {raw_role}".upper()
    if "ATTORNEY" in haystack or "AD LITEM" in haystack:
        return "professional_contact"
    if "HEIR" in haystack or "BENEFICIARY" in haystack or "DEVISEE" in haystack:
        return "heir_or_beneficiary_candidate"
    if "INTERESTED" in haystack or "RESPONDENT" in haystack:
        return "interested_party_candidate"
    return "applicant_or_representative_candidate"


def _canonical_role(value: Any) -> str:
    text = _clean_text(str(value or ""))
    upper = text.upper()
    if "DECEDENT" in upper or "DECEASED" in upper:
        return "decedent"
    if "APPLICANT" in upper:
        return "applicant"
    if "EXECUTOR" in upper:
        return "executor"
    if "ADMIN" in upper:
        return "administrator"
    if "PERSONAL REPRESENTATIVE" in upper:
        return "personal_representative"
    if "HEIR" in upper:
        return "heir"
    if "BENEFICIARY" in upper:
        return "beneficiary"
    if "PETITIONER" in upper:
        return "petitioner"
    if "ATTORNEY" in upper:
        return "attorney"
    if "AD LITEM" in upper:
        return "ad_litem"
    if "INTERESTED" in upper:
        return "interested_party"
    if "RESPONDENT" in upper:
        return "respondent"
    return _safe_enum_text(text) or "unknown"


def _attorney_count(parties: Sequence[Mapping[str, Any]]) -> int:
    names = {
        _text_or_none(party.get("attorney_name"))
        for party in parties
        if _text_or_none(party.get("attorney_name"))
    }
    names.update(
        _text_or_none(party.get("name"))
        for party in parties
        if str(party.get("role") or "") in {"attorney", "ad_litem"} and _text_or_none(party.get("name"))
    )
    return len(names)


def _clue_count(events: Sequence[Mapping[str, Any]], documents: Sequence[Mapping[str, Any]], *, tokens: tuple[str, ...]) -> int:
    count = 0
    for item in [*events, *documents]:
        haystack = " ".join(str(value or "") for value in item.values()).upper()
        if any(token in haystack for token in tokens):
            count += 1
    return count


def _summary_status(*, received_count: int, completed: int, incomplete: int, blocked: int) -> str:
    if received_count == 0:
        return "not_run"
    if blocked:
        return "blocked" if completed == 0 else "partial"
    if incomplete:
        return "incomplete" if completed == 0 else "partial"
    return "completed"


def _first_header_text(row: Mapping[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value:
            return _text_or_none(value)
    return None


def _normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _normalize_county(value: Any) -> str | None:
    normalized = str(value or "").strip().lower().replace("_county", "").replace(" county", "")
    return normalized if normalized in {"harris", "montgomery"} else None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = _clean_text(str(value))
    return text or None


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value).strip())


def _safe_enum_text(value: str) -> str | None:
    text = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    return text or None
