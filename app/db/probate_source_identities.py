from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping

from app.core.config import Settings, get_settings
from app.db.lead_machine_supabase import (
    fetch_rows,
    insert_rows,
    lead_machine_backend_enabled,
    patch_rows,
    resolve_tenant,
)
from app.models.source_runs import SourceCounty, SourceRun, SourceRunStatus
from app.services.probate_autopilot_manifest_service import probate_source_identity_key

_PROBATE_SOURCE_LANES = {"harris_county_probate", "montgomery_county_probate"}
_REMOTE_TENANT_ENVIRONMENTS = {"dev", "staging", "prod"}
_SUPPORTED_COUNTIES: tuple[SourceCounty, ...] = ("harris", "montgomery")
_SOURCE_IDENTITY_VERSION = "county_case_sha256_v1"
_TABLE = "probate_source_identities"


class ProbateSourceIdentityRepository:
    """Supabase-backed identity ledger for probate source-run dedupe.

    The operational source-run ledger can stay file-backed while this repository
    supplies the durable identity set used for cross-run dedupe once
    LEAD_MACHINE_BACKEND=supabase. Manual Hermes environments such as
    ``prod-manual`` intentionally remain file/manual-only so they cannot poison
    the autonomous remote ledger.
    """

    def __init__(self, *, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def list_identity_keys(
        self,
        *,
        business_id: str,
        environment: str,
        run_scope: str,
        counties: Iterable[SourceCounty],
    ) -> dict[str, set[str]]:
        requested_counties = tuple(_supported_counties(counties))
        result: dict[str, set[str]] = {county: set() for county in requested_counties}
        if not self._remote_enabled(environment):
            return result

        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        params = {
            "select": "county,source_identity_key",
            "business_id": f"eq.{tenant.business_pk}",
            "environment": f"eq.{tenant.environment}",
            "source_run_scope": f"eq.{_source_run_scope_from_value(run_scope)}",
        }
        if requested_counties:
            params["county"] = f"in.({','.join(requested_counties)})"
        for row in fetch_rows(_TABLE, params=params, settings=self.settings):
            county = _county_from_value(row.get("county"))
            key = row.get("source_identity_key")
            if county in result and isinstance(key, str) and key.strip():
                result[county].add(key)
        return result

    def record_source_run(self, run: SourceRun) -> int:
        if not self._should_record_run(run):
            return 0
        assert run.county is not None
        tenant = resolve_tenant(run.business_id, run.environment, settings=self.settings)
        run_scope = _source_run_scope(run)
        rows = _identity_rows_from_run(run)
        recorded = 0
        for row in rows:
            source_identity_key = row["source_identity_key"]
            existing = fetch_rows(
                _TABLE,
                params={
                    "select": "id,seen_count",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "source_run_scope": f"eq.{run_scope}",
                    "county": f"eq.{run.county}",
                    "source_identity_key": f"eq.{source_identity_key}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            latest_metadata = _latest_metadata(run)
            if existing:
                existing_row = existing[0]
                patch_rows(
                    _TABLE,
                    params={"id": f"eq.{existing_row['id']}"},
                    row={
                        "last_source_run_id": run.id,
                        "last_source_key": run.source_key,
                        "last_idempotency_key": run.idempotency_key,
                        "seen_count": _seen_count(existing_row) + 1,
                        "latest_record_count": run.record_count,
                        "latest_keep_now": row["latest_keep_now"],
                        "latest_metadata": latest_metadata,
                    },
                    select="id",
                    settings=self.settings,
                )
            else:
                insert_rows(
                    _TABLE,
                    [
                        {
                            "business_id": tenant.business_pk,
                            "environment": tenant.environment,
                            "source_run_scope": run_scope,
                            "county": run.county,
                            "source_identity_key": source_identity_key,
                            "source_identity_version": _SOURCE_IDENTITY_VERSION,
                            "first_source_run_id": run.id,
                            "first_source_key": run.source_key,
                            "first_idempotency_key": run.idempotency_key,
                            "last_source_run_id": run.id,
                            "last_source_key": run.source_key,
                            "last_idempotency_key": run.idempotency_key,
                            "seen_count": 1,
                            "latest_record_count": run.record_count,
                            "latest_keep_now": row["latest_keep_now"],
                            "latest_metadata": latest_metadata,
                        }
                    ],
                    select="id",
                    settings=self.settings,
                )
            recorded += 1
        return recorded

    def _remote_enabled(self, environment: str) -> bool:
        return lead_machine_backend_enabled(self.settings) and environment in _REMOTE_TENANT_ENVIRONMENTS

    def _should_record_run(self, run: SourceRun) -> bool:
        return bool(
            self._remote_enabled(run.environment)
            and run.status == SourceRunStatus.COMPLETED
            and run.source_lane in _PROBATE_SOURCE_LANES
            and run.county in _SUPPORTED_COUNTIES
            and _source_run_scope(run) in {"autonomous", "manual"}
        )


def _identity_rows_from_run(run: SourceRun) -> list[dict[str, Any]]:
    assert run.county is not None
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in _identity_rows_from_metadata(run):
        key = row["source_identity_key"]
        if key not in seen:
            seen.add(key)
            rows.append(row)
    for artifact in run.artifacts:
        if artifact.artifact_type != "normalized_source_rows":
            continue
        path = Path(artifact.path)
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, Mapping):
                continue
            key = payload.get("source_identity_key")
            if not isinstance(key, str) or not key.strip():
                key = probate_source_identity_key(payload, county=run.county)
            if not isinstance(key, str) or not key.strip() or key in seen:
                continue
            seen.add(key)
            rows.append({"source_identity_key": key, "latest_keep_now": payload.get("keep_now") is True})
    return rows


def _identity_rows_from_metadata(run: SourceRun) -> list[dict[str, Any]]:
    records = run.metadata.get("source_identity_records")
    if not isinstance(records, list):
        return []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            continue
        key = record.get("source_identity_key")
        if not isinstance(key, str) or not key.strip() or key in seen:
            continue
        seen.add(key)
        rows.append({"source_identity_key": key, "latest_keep_now": record.get("keep_now") is True})
    return rows


def _latest_metadata(run: SourceRun) -> dict[str, Any]:
    return {
        "source_lane": run.source_lane,
        "run_kind": run.run_kind,
        "source_identity_version": run.metadata.get("source_identity_version") or _SOURCE_IDENTITY_VERSION,
        "source_run_scope": _source_run_scope(run),
    }


def _source_run_scope(run: SourceRun) -> Literal["autonomous", "manual"]:
    return _source_run_scope_from_value(run.metadata.get("source_run_scope"), run_kind=run.run_kind)


def _source_run_scope_from_value(value: object, *, run_kind: object | None = None) -> Literal["autonomous", "manual"]:
    candidate = str(value or "").strip().lower()
    if candidate in {"autonomous", "manual"}:
        return candidate  # type: ignore[return-value]
    return "manual" if str(run_kind or "").strip().lower() == "manual" else "autonomous"


def _supported_counties(counties: Iterable[SourceCounty]) -> list[SourceCounty]:
    result: list[SourceCounty] = []
    for county in counties:
        normalized = _county_from_value(county)
        if normalized and normalized not in result:
            result.append(normalized)
    return result


def _county_from_value(value: object) -> SourceCounty | None:
    normalized = str(value or "").strip().lower().replace(" county", "").replace("_county", "")
    if normalized in _SUPPORTED_COUNTIES:
        return normalized  # type: ignore[return-value]
    return None


def _seen_count(row: Mapping[str, Any]) -> int:
    value = row.get("seen_count")
    return value if isinstance(value, int) and value >= 0 else 0
