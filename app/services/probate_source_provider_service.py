from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, cast

from app.core.config import Settings, get_settings
from app.models.source_runs import NightlySourcePullRequest, SourceCounty
from app.services.probate_autopilot_manifest_service import PROBATE_AUTOPILOT_KEY
from app.services.probate_source_adapter_service import ADAPTER_VERSION, probate_source_adapter_service
from app.services.probate_source_file_service import ProbateSourceFileService

PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION = "probate_source_provider_bridge_v1"
_SUPPORTED_MODE = "local_export_files"
_PROVIDER_LABELS: dict[SourceCounty, str] = {
    "harris": "harris_county_probate_export",
    "montgomery": "montgomery_county_probate_export",
}


class ProbateSourceProviderBridgeService:
    """Bridge source-provider intent into no-send source-row metadata.

    This is intentionally *not* a live county scraper. The bridge gives the
    scheduled source-pull path a stable provider contract while only accepting
    local export files. Live source calls remain behind a separate env gate and
    explicit operator approval before any network/browser adapter can be wired.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        file_service: ProbateSourceFileService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.file_service = file_service or ProbateSourceFileService()

    def reject_live_source_calls(self, request: NightlySourcePullRequest) -> None:
        approval = request.metadata.get("source_provider_approval") if isinstance(request.metadata, Mapping) else None
        approved = isinstance(approval, Mapping) and approval.get("approved") is True
        if not self.settings.lead_machine_live_source_calls_enabled:
            raise RuntimeError(
                "live source calls are disabled; probate source-provider bridge currently supports local_export_files only"
            )
        if not approved:
            raise RuntimeError("live source calls require explicit source_provider_approval.approved=true")
        raise RuntimeError("live source calls have no registered Harris/Montgomery county adapters yet")

    def hydrate_request(self, request: NightlySourcePullRequest) -> NightlySourcePullRequest:
        bridge_config = self._bridge_config(request.metadata)
        if bridge_config is None or request.source_runs:
            return request
        mode = str(bridge_config.get("mode") or "").strip().lower()
        if mode != _SUPPORTED_MODE:
            raise ValueError("probate source-provider bridge only supports mode=local_export_files")
        exports = bridge_config.get("exports") or request.metadata.get("source_provider_exports")
        export_items = self._export_items(exports)
        grouped_rows, summaries, source_uris, record_counts = self._load_exports(export_items)
        expected_counties = self._expected_counties(bridge_config, grouped_rows)
        merged_metadata = {
            **request.metadata,
            "autopilot": request.metadata.get("autopilot") or PROBATE_AUTOPILOT_KEY,
            "county_scope": list(grouped_rows),
            "expected_counties": expected_counties,
            "source_rows": grouped_rows,
            "source_uri": summaries[0]["path"] if len(summaries) == 1 else None,
            "source_uris": source_uris,
            "source_files": summaries,
            "record_counts": record_counts,
            "source_adapter_contract": ADAPTER_VERSION,
            "source_provider_bridge": {
                "version": PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION,
                "mode": _SUPPORTED_MODE,
                "export_count": len(summaries),
                "county_scope": list(grouped_rows),
                "expected_counties": expected_counties,
                "would_call_live_sources": False,
                "live_source_calls_requested": bool(request.live_source_calls),
                "provider_adapters": sorted({_PROVIDER_LABELS[county] for county in grouped_rows}),
                "no_send": True,
                "provider_sends_enabled": False,
            },
            "no_send": True,
            "provider_sends_enabled": False,
        }
        return request.model_copy(update={"metadata": merged_metadata, "live_source_calls": False})

    @staticmethod
    def _bridge_config(metadata: Mapping[str, Any]) -> Mapping[str, Any] | None:
        bridge_config = metadata.get("source_provider_bridge") or metadata.get("source_provider")
        if isinstance(bridge_config, Mapping):
            return bridge_config
        if metadata.get("source_provider_exports"):
            return {"mode": _SUPPORTED_MODE, "exports": metadata.get("source_provider_exports")}
        return None

    @staticmethod
    def _export_items(exports: Any) -> list[Mapping[str, Any]]:
        if not isinstance(exports, list) or not exports:
            raise ValueError("source_provider_bridge.exports must be a non-empty list")
        items: list[Mapping[str, Any]] = []
        for index, item in enumerate(exports, start=1):
            if isinstance(item, (str, Path)):
                items.append({"path": str(item)})
                continue
            if not isinstance(item, Mapping):
                raise ValueError(f"source_provider_bridge export {index} must be an object or path string")
            items.append(item)
        return items

    @staticmethod
    def _expected_counties(config: Mapping[str, Any], grouped_rows: Mapping[SourceCounty, list[dict[str, Any]]]) -> list[SourceCounty]:
        configured = config.get("expected_counties")
        if isinstance(configured, list) and configured:
            counties = [_normalize_county(item) for item in configured]
            if all(county is not None for county in counties):
                return cast(list[SourceCounty], counties)
        return ["harris", "montgomery"] if set(grouped_rows) <= {"harris", "montgomery"} else list(grouped_rows)

    def _load_exports(
        self,
        exports: Iterable[Mapping[str, Any]],
    ) -> tuple[dict[SourceCounty, list[dict[str, Any]]], list[dict[str, Any]], dict[SourceCounty, str], dict[str, dict[str, int]]]:
        grouped_rows: dict[SourceCounty, list[dict[str, Any]]] = {}
        summaries: list[dict[str, Any]] = []
        source_uris: dict[SourceCounty, str] = {}
        record_counts: dict[str, dict[str, int]] = {}
        for index, export in enumerate(exports, start=1):
            path_value = export.get("path") or export.get("source_file") or export.get("source_uri")
            if not path_value:
                raise ValueError(f"source_provider_bridge export {index} is missing path")
            source_path = Path(str(path_value))
            default_county = _normalize_county(export.get("county"))
            rows = self.file_service.load_rows(source_path)
            file_grouped = self._group_rows(rows, default_county=default_county, export_index=index)
            source_reported_count = _optional_int(export.get("source_reported_count")) or len(rows)
            for county, county_rows in file_grouped.items():
                normalized = probate_source_adapter_service.normalize_rows(
                    county_rows,
                    county=county,
                    source_uri=source_path,
                )
                grouped_rows.setdefault(county, []).extend(normalized)
                source_uris.setdefault(county, str(source_path))
                counts = record_counts.setdefault(county, {"source_reported_count": 0})
                counts["source_reported_count"] += source_reported_count if len(file_grouped) == 1 else len(county_rows)
            summaries.append(
                {
                    "path": str(source_path),
                    "row_count": len(rows),
                    "county_scope": list(file_grouped),
                    "source_reported_count": source_reported_count,
                    "provider": _PROVIDER_LABELS[list(file_grouped)[0]] if len(file_grouped) == 1 else "mixed_probate_export",
                    "bridge_version": PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION,
                }
            )
        if not grouped_rows:
            raise ValueError("source_provider_bridge did not load any Harris or Montgomery probate rows")
        return grouped_rows, summaries, source_uris, record_counts

    @staticmethod
    def _group_rows(
        rows: list[dict[str, Any]],
        *,
        default_county: SourceCounty | None,
        export_index: int,
    ) -> dict[SourceCounty, list[dict[str, Any]]]:
        grouped: dict[SourceCounty, list[dict[str, Any]]] = {}
        missing_rows: list[int] = []
        for row_index, row in enumerate(rows, start=1):
            county = _normalize_county(row.get("county") or default_county)
            if county is None:
                missing_rows.append(row_index)
                continue
            grouped.setdefault(county, []).append({**row, "county": county})
        if missing_rows:
            raise ValueError(
                f"source_provider_bridge export {export_index} has rows missing supported county: "
                + ", ".join(str(row) for row in missing_rows)
            )
        return grouped


probate_source_provider_bridge_service = ProbateSourceProviderBridgeService()


def _normalize_county(value: Any) -> SourceCounty | None:
    normalized = str(value or "").strip().lower().replace("_county", "").replace(" county", "")
    if normalized in {"harris", "montgomery"}:
        return cast(SourceCounty, normalized)
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return value
    return None
