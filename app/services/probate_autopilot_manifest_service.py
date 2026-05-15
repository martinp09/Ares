from __future__ import annotations

from datetime import datetime
from typing import Any

from app.models.source_runs import SourceCounty, SourceRunArtifact, SourceRunKind, SourceRunManifest

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
) -> list[SourceRunManifest]:
    run_kind = _run_kind(metadata.get("run_kind") or metadata.get("slot") or metadata.get("schedule_slot"))
    window_start = _parse_datetime(metadata.get("window_start"))
    window_end = _parse_datetime(metadata.get("window_end"))
    counties = _counties(metadata.get("county_scope") or metadata.get("counties"))

    manifests: list[SourceRunManifest] = []
    for county in counties:
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
                "no_send": True,
                "provider_sends_enabled": False,
            },
        )
        manifests.append(
            SourceRunManifest(
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
                    "no_send": True,
                    "provider_sends_enabled": False,
                    "live_source_adapter_status": "deferred",
                    "window_start": window_start.isoformat() if window_start else None,
                    "window_end": window_end.isoformat() if window_end else None,
                },
            )
        )
    return manifests


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
        normalized = str(item).strip().lower().replace("_county", "")
        if normalized in {"harris", "montgomery"} and normalized not in counties:
            counties.append(normalized)  # type: ignore[arg-type]
    return tuple(counties) or DEFAULT_PROBATE_AUTOPILOT_COUNTIES


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
