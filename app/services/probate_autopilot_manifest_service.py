from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.models.source_runs import SourceCounty, SourceRunArtifact, SourceRunKind, SourceRunManifest
from app.services.harris_probate_intake_service import HarrisProbateIntakeService

PROBATE_AUTOPILOT_KEY = "harris_montgomery_probate"
DEFAULT_PROBATE_AUTOPILOT_COUNTIES: tuple[SourceCounty, ...] = ("harris", "montgomery")

_COUNTY_PROBATE_LANES: dict[SourceCounty, str] = {
    "harris": "harris_county_probate",
    "montgomery": "montgomery_county_probate",
}

_COUNTY_LABELS: dict[SourceCounty, str] = {
    "harris": "Harris County Probate autopilot source window",
    "montgomery": "Montgomery County Probate autopilot source window",
}

_RUN_KIND_LABELS: dict[SourceRunKind, str] = {
    "morning_catchup": "morning catchup",
    "midday": "midday pull",
    "end_of_day": "end-of-day pull",
    "daily_reconciliation": "daily reconciliation",
    "weekly_reconciliation": "weekly reconciliation",
    "manual": "manual run",
}

_NO_LIVE_SOURCE_WARNING = "probate autopilot Phase 1 records source-run placeholders only; live county scraping is deferred"
_NO_SEND_METADATA = {"no_send": True, "provider_sends_enabled": False}


def is_probate_autopilot_request(metadata: dict[str, Any]) -> bool:
    return bool(
        metadata.get("probate_autopilot") is True
        or metadata.get("autopilot") == PROBATE_AUTOPILOT_KEY
        or metadata.get("autopilot") == "probate_autopilot"
    )


def build_probate_autopilot_manifests(
    *,
    metadata: dict[str, Any],
    idempotency_key: str | None = None,
    artifact_root: str | Path | None = None,
) -> list[SourceRunManifest]:
    run_kind = _run_kind(metadata.get("run_kind") or metadata.get("slot") or metadata.get("schedule_slot"))
    window_start = _parse_datetime(metadata.get("window_start"))
    window_end = _parse_datetime(metadata.get("window_end"))
    counties = _counties(metadata.get("county_scope") or metadata.get("counties"))
    rows_by_county = _rows_by_county(metadata.get("source_rows"), counties=counties)

    manifests: list[SourceRunManifest] = []
    for county in counties:
        if rows_by_county.get(county):
            manifests.append(
                _build_row_manifest(
                    county=county,
                    rows=rows_by_county[county],
                    metadata=metadata,
                    run_kind=run_kind,
                    window_start=window_start,
                    window_end=window_end,
                    idempotency_key=idempotency_key,
                    artifact_root=artifact_root,
                )
            )
        else:
            manifests.append(
                _build_placeholder_manifest(
                    county=county,
                    metadata=metadata,
                    run_kind=run_kind,
                    window_start=window_start,
                    window_end=window_end,
                    idempotency_key=idempotency_key,
                )
            )
    return manifests


def _build_placeholder_manifest(
    *,
    county: SourceCounty,
    metadata: dict[str, Any],
    run_kind: SourceRunKind,
    window_start: datetime | None,
    window_end: datetime | None,
    idempotency_key: str | None,
) -> SourceRunManifest:
    lane = _COUNTY_PROBATE_LANES[county]
    county_record_counts = _county_counts(metadata.get("record_counts"), county)
    record_count = county_record_counts.get("record_count", 0)
    raw_count = county_record_counts.get("raw_count", record_count)
    parsed_count = county_record_counts.get("parsed_count", record_count)
    keep_now_count = county_record_counts.get("keep_now_count", 0)
    source_reported_count = county_record_counts.get("source_reported_count")
    artifact = SourceRunArtifact(
        path=f"/opt/ares/lead-data/probate_autopilot/pending/{county}/{run_kind}/raw-placeholder.json",
        artifact_type="probate_autopilot_phase1_placeholder",
        record_count=record_count,
        warnings=[_NO_LIVE_SOURCE_WARNING],
        metadata={
            "county": county,
            "run_kind": run_kind,
            "raw_count": raw_count,
            "parsed_count": parsed_count,
            "keep_now_count": keep_now_count,
            "source_reported_count": source_reported_count,
            **_NO_SEND_METADATA,
        },
    )
    return SourceRunManifest(
        source_key=f"{lane}:{run_kind}:{_window_key(window_start, window_end)}",
        source_label=f"{_COUNTY_LABELS[county]} ({_RUN_KIND_LABELS[run_kind]})",
        source_lane=lane,  # type: ignore[arg-type]
        county=county,
        run_kind=run_kind,
        window_start=window_start,
        window_end=window_end,
        idempotency_key=f"{idempotency_key}:{county}" if idempotency_key else None,
        source_reported_count=source_reported_count,
        raw_count=raw_count,
        parsed_count=parsed_count,
        keep_now_count=keep_now_count,
        record_count=record_count,
        warnings=[_NO_LIVE_SOURCE_WARNING],
        artifacts=[artifact],
        metadata={
            "autopilot": PROBATE_AUTOPILOT_KEY,
            "phase": "phase_1_source_run_foundation",
            "county": county,
            "run_kind": run_kind,
            **_NO_SEND_METADATA,
            "live_source_adapter_status": "deferred",
            "window_start": window_start.isoformat() if window_start else None,
            "window_end": window_end.isoformat() if window_end else None,
        },
    )


def _build_row_manifest(
    *,
    county: SourceCounty,
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
    run_kind: SourceRunKind,
    window_start: datetime | None,
    window_end: datetime | None,
    idempotency_key: str | None,
    artifact_root: str | Path | None,
) -> SourceRunManifest:
    lane = _COUNTY_PROBATE_LANES[county]
    normalized_rows, invalid_rows = _normalize_source_rows(rows, county=county)
    keep_now_rows = [row for row in normalized_rows if row["keep_now"]]
    duplicate_case_numbers = _duplicate_case_numbers(normalized_rows)
    duplicate_case_count = sum(count - 1 for count in duplicate_case_numbers.values())
    county_record_counts = _county_counts(metadata.get("record_counts"), county)
    raw_count = len(rows)
    parsed_count = len(normalized_rows)
    keep_now_count = len(keep_now_rows)
    source_reported_count = county_record_counts.get("source_reported_count", raw_count)
    warnings = []
    if invalid_rows:
        warnings.append(f"{len(invalid_rows)} {county} probate source rows skipped because case number or filing type was missing")
    if source_reported_count != parsed_count:
        warnings.append(
            f"{county} probate source reported {source_reported_count} rows but Ares parsed {parsed_count}; review source_count_mismatches"
        )
    if duplicate_case_count:
        warnings.append(
            f"{county} probate source packet contains {duplicate_case_count} duplicate case row(s); review duplicate_case_numbers before enrichment"
        )

    window_key = _window_key(window_start, window_end)
    artifacts = [
        _artifact_for_records(
            county=county,
            run_kind=run_kind,
            window_key=window_key,
            artifact_type="raw_source_rows",
            records=rows,
            artifact_root=artifact_root,
        ),
        _artifact_for_records(
            county=county,
            run_kind=run_kind,
            window_key=window_key,
            artifact_type="normalized_source_rows",
            records=normalized_rows,
            artifact_root=artifact_root,
        ),
        _artifact_for_records(
            county=county,
            run_kind=run_kind,
            window_key=window_key,
            artifact_type="keep_now_rows",
            records=keep_now_rows,
            artifact_root=artifact_root,
        ),
    ]

    if invalid_rows:
        artifacts.append(
            _artifact_for_records(
                county=county,
                run_kind=run_kind,
                window_key=window_key,
                artifact_type="invalid_source_rows",
                records=invalid_rows,
                artifact_root=artifact_root,
            )
        )
    if duplicate_case_numbers:
        artifacts.append(
            _artifact_for_records(
                county=county,
                run_kind=run_kind,
                window_key=window_key,
                artifact_type="duplicate_case_numbers",
                records=[
                    {"case_number": case_number, "duplicate_row_count": count}
                    for case_number, count in sorted(duplicate_case_numbers.items())
                ],
                artifact_root=artifact_root,
            )
        )

    return SourceRunManifest(
        source_key=f"{lane}:{run_kind}:{window_key}",
        source_label=f"{_COUNTY_LABELS[county]} ({_RUN_KIND_LABELS[run_kind]})",
        source_lane=lane,  # type: ignore[arg-type]
        county=county,
        run_kind=run_kind,
        window_start=window_start,
        window_end=window_end,
        idempotency_key=f"{idempotency_key}:{county}" if idempotency_key else None,
        source_reported_count=source_reported_count,
        raw_count=raw_count,
        parsed_count=parsed_count,
        keep_now_count=keep_now_count,
        record_count=parsed_count,
        warnings=warnings,
        artifacts=artifacts,
        metadata={
            "autopilot": PROBATE_AUTOPILOT_KEY,
            "phase": "phase_2_file_drop_source_rows",
            "county": county,
            "run_kind": run_kind,
            **_NO_SEND_METADATA,
            "live_source_adapter_status": "file_drop_or_external_adapter",
            "source_uri": _source_uri(metadata, county),
            "invalid_row_count": len(invalid_rows),
            "duplicate_case_count": duplicate_case_count,
            "duplicate_case_numbers": duplicate_case_numbers,
            "window_start": window_start.isoformat() if window_start else None,
            "window_end": window_end.isoformat() if window_end else None,
        },
    )


def _normalize_source_rows(rows: Iterable[Mapping[str, Any]], *, county: SourceCounty) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    intake = HarrisProbateIntakeService()
    normalized_rows: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        payload = dict(row)
        case_number = _first_text(payload, "case_number", "cause_number", "case_no", "case", "caseNumber")
        filing_type = _first_text(payload, "filing_type", "type", "type_desc", "case_type", "subtype", "filingType")
        if not case_number or not filing_type:
            invalid_rows.append({"row_index": index, "reason": "missing_case_number_or_filing_type", "raw": payload})
            continue
        normalized_payload = {
            **payload,
            "case_number": case_number,
            "filing_type": filing_type,
            "county": county,
        }
        record = intake.normalize_case(normalized_payload)
        normalized_rows.append(
            {
                "case_number": record.case_number,
                "file_date": record.file_date.isoformat() if record.file_date else None,
                "court_number": record.court_number,
                "status": record.status,
                "filing_type": record.filing_type,
                "filing_subtype": record.filing_subtype,
                "estate_name": record.estate_name,
                "decedent_name": record.decedent_name,
                "keep_now": record.keep_now,
                "county": county,
                "raw": payload,
            }
        )
    return normalized_rows, invalid_rows


def _artifact_for_records(
    *,
    county: SourceCounty,
    run_kind: SourceRunKind,
    window_key: str,
    artifact_type: str,
    records: list[Mapping[str, Any]],
    artifact_root: str | Path | None,
) -> SourceRunArtifact:
    body = _jsonl(records)
    checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
    logical_path = f"/opt/ares/lead-data/probate_autopilot/{county}/{run_kind}/{_safe_path_part(window_key)}/{artifact_type}.jsonl"
    path = logical_path
    if artifact_root:
        root = Path(artifact_root).expanduser()
        file_path = root / "probate_autopilot" / county / run_kind / _safe_path_part(window_key) / f"{artifact_type}.jsonl"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(body, encoding="utf-8")
        path = str(file_path)
    return SourceRunArtifact(
        path=path,
        artifact_type=artifact_type,
        record_count=len(records),
        checksum=checksum,
        metadata={"county": county, "run_kind": run_kind, **_NO_SEND_METADATA},
    )


def _jsonl(records: list[Mapping[str, Any]]) -> str:
    return "".join(json.dumps(record, sort_keys=True, default=str) + "\n" for record in records)


def _duplicate_case_numbers(records: list[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        case_number = _first_text(record, "case_number")
        if not case_number:
            continue
        normalized = case_number.strip().upper()
        counts[normalized] = counts.get(normalized, 0) + 1
    return {case_number: count for case_number, count in counts.items() if count > 1}


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _source_uri(metadata: Mapping[str, Any], county: SourceCounty) -> str | None:
    value = metadata.get("source_uri")
    if isinstance(value, str) and value.strip():
        return value.strip()
    source_uris = metadata.get("source_uris")
    if isinstance(source_uris, Mapping):
        county_value = source_uris.get(county)
        if isinstance(county_value, str) and county_value.strip():
            return county_value.strip()
    return None


def _rows_by_county(value: Any, *, counties: tuple[SourceCounty, ...]) -> dict[SourceCounty, list[dict[str, Any]]]:
    rows: dict[SourceCounty, list[dict[str, Any]]] = {county: [] for county in counties}
    if isinstance(value, Mapping):
        for county in counties:
            county_rows = value.get(county)
            if isinstance(county_rows, list):
                rows[county] = [dict(item) for item in county_rows if isinstance(item, Mapping)]
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            county = _county_from_any(item.get("county"))
            if county in rows:
                rows[county].append(dict(item))
    return rows


def _counties(value: Any) -> tuple[SourceCounty, ...]:
    if value is None:
        return DEFAULT_PROBATE_AUTOPILOT_COUNTIES
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        return DEFAULT_PROBATE_AUTOPILOT_COUNTIES

    counties: list[SourceCounty] = []
    for item in raw_items:
        normalized = _county_from_any(item)
        if normalized and normalized not in counties:
            counties.append(normalized)
    return tuple(counties) or DEFAULT_PROBATE_AUTOPILOT_COUNTIES


def _county_from_any(value: Any) -> SourceCounty | None:
    normalized = str(value or "").strip().lower().replace("_county", "").replace(" county", "")
    if normalized in {"harris", "montgomery"}:
        return normalized  # type: ignore[return-value]
    return None


def _run_kind(value: Any) -> SourceRunKind:
    normalized = str(value or "manual").strip().lower().replace("-", "_")
    aliases = {
        "0710_ct": "morning_catchup",
        "0710": "morning_catchup",
        "morning": "morning_catchup",
        "1240_ct": "midday",
        "1240": "midday",
        "1740_ct": "end_of_day",
        "1740": "end_of_day",
        "0220_ct": "daily_reconciliation",
        "0220": "daily_reconciliation",
        "sunday_0315_ct": "weekly_reconciliation",
        "weekly": "weekly_reconciliation",
    }
    candidate = aliases.get(normalized, normalized)
    allowed: set[SourceRunKind] = {
        "morning_catchup",
        "midday",
        "end_of_day",
        "daily_reconciliation",
        "weekly_reconciliation",
        "manual",
    }
    if candidate in allowed:
        return candidate  # type: ignore[return-value]
    return "manual"


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _county_counts(value: Any, county: SourceCounty) -> dict[str, int | None]:
    if not isinstance(value, dict):
        return {}
    candidate = value.get(county)
    if not isinstance(candidate, dict):
        return {}
    allowed = {"record_count", "raw_count", "parsed_count", "keep_now_count", "source_reported_count"}
    counts: dict[str, int | None] = {}
    for key in allowed:
        item = candidate.get(key)
        counts[key] = item if isinstance(item, int) and not isinstance(item, bool) and item >= 0 else None
    return {key: item for key, item in counts.items() if item is not None}


def _window_key(window_start: datetime | None, window_end: datetime | None) -> str:
    if window_start and window_end:
        return f"{window_start.isoformat()}_{window_end.isoformat()}"
    if window_start:
        return window_start.isoformat()
    if window_end:
        return window_end.isoformat()
    return "unspecified-window"


def _safe_path_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.=-]+", "_", value).strip("_") or "unspecified-window"
