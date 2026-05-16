from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.models.source_runs import SourceCounty

ADAPTER_VERSION = "probate_export_adapter_v1"

_COUNTY_ADAPTER_NAMES: dict[SourceCounty, str] = {
    "harris": "harris_probate_export_v1",
    "montgomery": "montgomery_probate_export_v1",
}

_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "case_number": (
        "case_number",
        "case number",
        "case no",
        "case no.",
        "case #",
        "case#",
        "case",
        "cause_number",
        "cause number",
        "cause no",
        "cause no.",
        "cause #",
    ),
    "filing_type": (
        "filing_type",
        "filing type",
        "case type",
        "type",
        "type desc",
        "type description",
        "case_type",
        "filingtype",
        "filing description",
        "description",
    ),
    "filing_subtype": (
        "filing_subtype",
        "filing subtype",
        "subtype",
        "sub type",
        "case subtype",
    ),
    "style": (
        "style",
        "style of case",
        "case style",
        "case name",
        "estate_name",
        "estate name",
        "party name",
        "decedent",
        "decedent name",
        "caption",
    ),
    "file_date": (
        "file_date",
        "file date",
        "filed_date",
        "filed date",
        "date filed",
        "filing date",
        "date",
    ),
    "court_number": (
        "court_number",
        "court number",
        "court no",
        "court no.",
        "court",
        "court name",
    ),
    "status": (
        "status",
        "case status",
        "disposition",
    ),
    "attorney_name": (
        "attorney",
        "attorney name",
        "attorney_of_record",
        "attorney of record",
    ),
    "applicant_name": (
        "applicant",
        "applicant name",
        "executor",
        "executor name",
        "administrator",
        "administrator name",
        "petitioner",
        "petitioner name",
    ),
    "mailing_address": (
        "mailing_address",
        "mailing address",
        "mail to",
        "mail_to",
        "applicant address",
        "executor address",
    ),
    "property_address": (
        "property_address",
        "property address",
        "site address",
        "situs address",
        "address",
    ),
    "case_detail_url": (
        "case_detail_url",
        "case detail url",
        "detail_url",
        "detail url",
        "case_url",
        "case url",
    ),
    "case_detail_postback_target": (
        "case_detail_postback_target",
        "case detail postback target",
        "postback_target",
        "postback target",
    ),
    "case_detail_source_url": (
        "case_detail_source_url",
        "case detail source url",
        "detail_source_url",
        "detail source url",
    ),
}


class ProbateSourceAdapterService:
    """Normalize Harris/Montgomery probate exports into the Ares source-row contract.

    This service is deliberately read-only and file/export-backed. It does not scrape
    county sites, call browsers, write CRM records, enroll leads, or trigger sends.
    """

    def normalize_rows(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        county: SourceCounty,
        source_uri: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        return [
            self.normalize_row(row, county=county, source_uri=source_uri, row_index=index)
            for index, row in enumerate(rows, start=1)
        ]

    def normalize_row(
        self,
        row: Mapping[str, Any],
        *,
        county: SourceCounty,
        source_uri: str | Path | None = None,
        row_index: int | None = None,
    ) -> dict[str, Any]:
        raw = dict(row)
        indexed = {_normalize_key(key): value for key, value in raw.items()}
        canonical: dict[str, Any] = {}
        for target, aliases in _FIELD_ALIASES.items():
            value = _first_text(indexed, aliases)
            if value is not None:
                canonical[target] = value

        source_uri_text = str(source_uri) if source_uri is not None else None
        case_number = str(canonical.get("case_number") or "").strip()
        file_date = str(canonical.get("file_date") or "").strip()
        style = str(canonical.get("style") or "").strip()
        canonical.update(
            {
                "county": county,
                "source_adapter": _COUNTY_ADAPTER_NAMES[county],
                "source_adapter_version": ADAPTER_VERSION,
                "source_row_index": row_index,
                "source_row_id": _source_row_id(
                    county=county,
                    case_number=case_number,
                    file_date=file_date,
                    style=style,
                    row_index=row_index,
                    source_uri=source_uri_text,
                ),
                "source_uri": source_uri_text,
                "raw_export_row": raw,
            }
        )
        return canonical


probate_source_adapter_service = ProbateSourceAdapterService()


def _first_text(indexed: Mapping[str, Any], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        value = indexed.get(_normalize_key(alias))
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def _source_row_id(
    *,
    county: SourceCounty,
    case_number: str,
    file_date: str,
    style: str,
    row_index: int | None,
    source_uri: str | None,
) -> str:
    basis = "|".join(
        [
            county,
            case_number or "missing-case",
            file_date or "missing-date",
            style or "missing-style",
            source_uri or "missing-source-uri",
            str(row_index or "missing-row-index"),
        ]
    )
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    case_part = re.sub(r"[^A-Za-z0-9]+", "-", case_number).strip("-").lower() or f"row-{row_index or 'unknown'}"
    return f"{county}:{case_part}:{digest}"
