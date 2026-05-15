from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, cast

from app.core.config import Settings, get_settings
from app.models.source_runs import NightlySourcePullRequest, SourceCounty
from app.services.probate_autopilot_manifest_service import PROBATE_AUTOPILOT_KEY
from app.services.probate_live_source_adapter_service import (
    PROBATE_LIVE_SOURCE_ADAPTER_VERSION,
    ProbateLiveSourceAdapterService,
    probate_live_source_adapter_service,
)
from app.services.probate_source_adapter_service import ADAPTER_VERSION, probate_source_adapter_service
from app.services.probate_source_file_service import ProbateSourceFileService

PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION = "probate_source_provider_bridge_v1"
PROBATE_SOURCE_ADAPTER_PREVIEW_VERSION = "probate_source_adapter_preview_v1"
_LOCAL_EXPORT_MODE = "local_export_files"
_ADAPTER_PREVIEW_MODE = "adapter_preview"
_LIVE_SOURCE_MODE = "live_source_adapters"
_PROVIDER_LABELS: dict[SourceCounty, str] = {
    "harris": "harris_county_probate_export",
    "montgomery": "montgomery_county_probate_export",
}
_LIVE_PROVIDER_LABELS: dict[SourceCounty, str] = {
    "harris": "harris_county_probate_live_v1",
    "montgomery": "montgomery_county_probate_live_v1",
}
_ADAPTER_DISCOVERY_STATUS: dict[SourceCounty, str] = {
    "harris": "adapter_contract_ready_no_network_implementation",
    "montgomery": "adapter_contract_ready_no_network_implementation",
}


class ProbateSourceProviderBridgeService:
    """Bridge source-provider intent into no-send source-row metadata.

    This is intentionally *not* a live county scraper. The bridge gives the
    scheduled source-pull path a stable provider contract while accepting local
    export files and a dry-run adapter-preview mode. Live source calls remain
    behind a separate env gate and explicit operator approval before any
    network/browser adapter can be wired.
    """

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        file_service: ProbateSourceFileService | None = None,
        live_source_adapter: ProbateLiveSourceAdapterService | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.file_service = file_service or ProbateSourceFileService()
        self.live_source_adapter = live_source_adapter or probate_live_source_adapter_service

    def reject_live_source_calls(self, request: NightlySourcePullRequest) -> None:
        self._validate_live_source_gate(request, self._bridge_config(request.metadata))

    def _validate_live_source_gate(
        self,
        request: NightlySourcePullRequest,
        bridge_config: Mapping[str, Any] | None,
    ) -> Mapping[str, Any]:
        approval = request.metadata.get("source_provider_approval") if isinstance(request.metadata, Mapping) else None
        if approval is None and isinstance(bridge_config, Mapping):
            approval = bridge_config.get("source_provider_approval") or bridge_config.get("approval")
        approved = isinstance(approval, Mapping) and approval.get("approved") is True
        if not self.settings.lead_machine_live_source_calls_enabled:
            raise RuntimeError(
                "live source calls are disabled; probate source-provider bridge currently supports local_export_files and dry-run adapter_preview only"
            )
        if not approved:
            raise RuntimeError("live source calls require explicit source_provider_approval.approved=true")
        if bridge_config is None or str(bridge_config.get("mode") or "").strip().lower() != _LIVE_SOURCE_MODE:
            raise RuntimeError("live source calls require source_provider_bridge.mode=live_source_adapters")
        if approval.get("no_send") is not True or approval.get("provider_sends_enabled") is not False:
            raise RuntimeError("live source calls require source_provider_approval.no_send=true and provider_sends_enabled=false")
        if request.metadata.get("no_send") is False or request.metadata.get("provider_sends_enabled") is True:
            raise RuntimeError("live source calls are no-send only; provider_sends_enabled must remain false")
        return cast(Mapping[str, Any], approval)

    def hydrate_request(self, request: NightlySourcePullRequest) -> NightlySourcePullRequest:
        bridge_config = self._bridge_config(request.metadata)
        if bridge_config is None or request.source_runs:
            return request
        mode = str(bridge_config.get("mode") or "").strip().lower()
        if mode == _LIVE_SOURCE_MODE:
            return self._hydrate_live_source_adapters(request, bridge_config)
        if mode == _ADAPTER_PREVIEW_MODE:
            return self._hydrate_adapter_preview(request, bridge_config)
        if mode != _LOCAL_EXPORT_MODE:
            raise ValueError(
                "probate source-provider bridge only supports mode=local_export_files, mode=adapter_preview, or mode=live_source_adapters"
            )
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
                "mode": _LOCAL_EXPORT_MODE,
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

    def _hydrate_live_source_adapters(
        self,
        request: NightlySourcePullRequest,
        bridge_config: Mapping[str, Any],
    ) -> NightlySourcePullRequest:
        if not request.live_source_calls:
            raise RuntimeError("live_source_adapters mode requires live_source_calls=true")
        approval = self._validate_live_source_gate(request, bridge_config)
        expected_counties = self._expected_counties(bridge_config, {})
        window_start = request.metadata.get("window_start") or bridge_config.get("window_start")
        window_end = request.metadata.get("window_end") or bridge_config.get("window_end")
        fetched = self.live_source_adapter.fetch_window(
            counties=expected_counties,
            window_start=window_start,
            window_end=window_end,
            live_source_calls_enabled=self.settings.lead_machine_live_source_calls_enabled,
            source_provider_approval=approval,
        )
        grouped_rows = {county: fetched[county].rows for county in expected_counties if county in fetched}
        source_uris = {county: fetched[county].source_url for county in grouped_rows}
        record_counts = {
            county: {
                "source_reported_count": fetched[county].source_reported_count,
                "raw_count": fetched[county].raw_count,
                "parsed_count": len(fetched[county].rows),
                "record_count": len(fetched[county].rows),
            }
            for county in grouped_rows
        }
        summaries = [
            {
                "source_url": fetched[county].source_url,
                "row_count": len(fetched[county].rows),
                "county": county,
                "source_reported_count": fetched[county].source_reported_count,
                "provider": _LIVE_PROVIDER_LABELS[county],
                "bridge_version": PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION,
                "live_source_adapter_version": PROBATE_LIVE_SOURCE_ADAPTER_VERSION,
                "metadata": fetched[county].metadata,
                "warnings": fetched[county].parser_warnings,
            }
            for county in grouped_rows
        ]
        missing_counties = [county for county in expected_counties if county not in grouped_rows]
        if missing_counties:
            raise RuntimeError("live source adapters returned no result for: " + ", ".join(missing_counties))
        merged_metadata = {
            **request.metadata,
            "autopilot": request.metadata.get("autopilot") or PROBATE_AUTOPILOT_KEY,
            "county_scope": expected_counties,
            "expected_counties": expected_counties,
            "source_rows": grouped_rows,
            "source_uri": summaries[0]["source_url"] if len(summaries) == 1 else None,
            "source_uris": source_uris,
            "source_files": summaries,
            "record_counts": record_counts,
            "source_adapter_contract": PROBATE_LIVE_SOURCE_ADAPTER_VERSION,
            "source_provider_bridge": {
                "version": PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION,
                "mode": _LIVE_SOURCE_MODE,
                "county_scope": expected_counties,
                "expected_counties": expected_counties,
                "would_call_live_sources": True,
                "live_source_calls_requested": True,
                "provider_adapters": sorted(_LIVE_PROVIDER_LABELS[county] for county in expected_counties),
                "live_source_adapter_version": PROBATE_LIVE_SOURCE_ADAPTER_VERSION,
                "network_calls_attempted": True,
                "browser_calls_attempted": False,
                "dry_run": False,
                "no_send": True,
                "provider_sends_enabled": False,
            },
            "no_send": True,
            "provider_sends_enabled": False,
        }
        return request.model_copy(update={"metadata": merged_metadata, "live_source_calls": False})

    def _hydrate_adapter_preview(
        self,
        request: NightlySourcePullRequest,
        bridge_config: Mapping[str, Any],
    ) -> NightlySourcePullRequest:
        if request.live_source_calls:
            raise RuntimeError("adapter_preview is dry-run only; live_source_calls must be false")
        if not self.settings.lead_machine_source_adapter_preview_enabled:
            raise RuntimeError(
                "probate source adapter preview is disabled; set LEAD_MACHINE_SOURCE_ADAPTER_PREVIEW_ENABLED=true for dry-run adapter preview"
            )
        approval = request.metadata.get("source_provider_approval") if isinstance(request.metadata, Mapping) else None
        if approval is None:
            approval = bridge_config.get("source_provider_approval") or bridge_config.get("approval")
        approved = isinstance(approval, Mapping) and approval.get("approved") is True
        if not approved:
            raise RuntimeError("adapter_preview requires explicit source_provider_approval.approved=true")

        expected_counties = self._expected_counties(bridge_config, {})
        adapter_labels = sorted(_LIVE_PROVIDER_LABELS[county] for county in expected_counties)
        merged_metadata = {
            **request.metadata,
            "autopilot": request.metadata.get("autopilot") or PROBATE_AUTOPILOT_KEY,
            "county_scope": expected_counties,
            "expected_counties": expected_counties,
            "source_rows": {county: [] for county in expected_counties},
            "record_counts": {county: {"source_reported_count": 0} for county in expected_counties},
            "source_adapter_contract": PROBATE_SOURCE_ADAPTER_PREVIEW_VERSION,
            "source_provider_bridge": {
                "version": PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION,
                "adapter_preview_version": PROBATE_SOURCE_ADAPTER_PREVIEW_VERSION,
                "mode": _ADAPTER_PREVIEW_MODE,
                "adapter_status": "dry_run_preview_only_no_network_calls",
                "dry_run": True,
                "county_scope": expected_counties,
                "expected_counties": expected_counties,
                "would_call_live_sources": False,
                "live_source_calls_requested": bool(request.live_source_calls),
                "network_calls_attempted": False,
                "browser_calls_attempted": False,
                "provider_adapters": adapter_labels,
                "adapter_discovery_status": {county: _ADAPTER_DISCOVERY_STATUS[county] for county in expected_counties},
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
            return {"mode": _LOCAL_EXPORT_MODE, "exports": metadata.get("source_provider_exports")}
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
