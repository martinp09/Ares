from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Iterable, Mapping

from app.models.probate_leads import ProbateLeadRecord


KEEP_NOW_FILING_TYPES = frozenset(
    {
        "PROBATE OF WILL (INDEPENDENT ADMINISTRATION)",
        "INDEPENDENT ADMINISTRATION",
        "APP FOR INDEPENDENT ADMINISTRATION WITH WILL ANNEXED",
        "APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP",
        "APP TO DETERMINE HEIRSHIP",
    }
)


class HarrisProbateIntakeService:
    def is_keep_now_case(self, payload: Mapping[str, Any]) -> bool:
        filing_type = _normalize_filing_type(payload.get("filing_type") or payload.get("type"))
        return filing_type in KEEP_NOW_FILING_TYPES

    def normalize_case(self, payload: Mapping[str, Any]) -> ProbateLeadRecord:
        estate_name = _normalize_text(payload.get("estate_name") or payload.get("style_of_case") or payload.get("style"))
        decedent_name = _normalize_text(payload.get("decedent_name")) or _extract_decedent_name(estate_name)
        filing_type = _normalize_filing_type(payload.get("filing_type") or payload.get("type") or "")
        return ProbateLeadRecord(
            case_number=str(payload.get("case_number") or payload.get("cause_number") or "").strip(),
            file_date=_parse_date(payload.get("file_date") or payload.get("filed_date")),
            court_number=_normalize_text(payload.get("court_number") or payload.get("court")),
            status=_normalize_text(payload.get("status")),
            filing_type=filing_type,
            filing_subtype=_normalize_text(payload.get("filing_subtype") or payload.get("subtype")),
            estate_name=estate_name,
            decedent_name=decedent_name,
            keep_now=filing_type in KEEP_NOW_FILING_TYPES,
            mailing_address=_normalize_text(payload.get("mailing_address") or payload.get("mail_to")),
            property_address=_normalize_text(payload.get("property_address") or payload.get("site_address")),
            last_seen_at=_parse_datetime(payload.get("last_seen_at") or payload.get("scraped_at")),
            raw_payload=dict(payload),
        )

    def ingest_cases(self, payloads: Iterable[Mapping[str, Any]], *, keep_only: bool = True) -> list[ProbateLeadRecord]:
        records = [self.normalize_case(payload) for payload in payloads]
        if keep_only:
            return [record for record in records if record.keep_now]
        return records


_whitespace_pattern = re.compile(r"\s+")
_name_noise_pattern = re.compile(r"\b(ESTATE|DECEASED|OF|THE)\b")


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = _whitespace_pattern.sub(" ", str(value).strip())
    if not text:
        return None
    return text


def _normalize_filing_type(value: Any) -> str:
    normalized = _normalize_text(value) or ""
    return normalized.upper()


def _extract_decedent_name(estate_name: str | None) -> str | None:
    if not estate_name:
        return None
    normalized = _name_noise_pattern.sub(" ", estate_name.upper())
    normalized = re.sub(r"[^A-Z0-9 ]+", " ", normalized)
    normalized = _whitespace_pattern.sub(" ", normalized).strip()
    if not normalized:
        return None
    return normalized.title()


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        if "/" in text:
            month, day, year = text.split("/")
            return date(int(year), int(month), int(day))
        raise


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00"))
