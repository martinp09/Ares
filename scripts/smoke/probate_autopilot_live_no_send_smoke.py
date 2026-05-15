#!/usr/bin/env python3
"""Live public-source no-send smoke for the Harris + Montgomery probate autopilot.

This smoke uses the same Ares nightly source-pull service path as the Trigger.dev
schedule, but stores state in memory and writes artifacts to a temp/local folder.
It proves public county source/CAD/tax/land-record calls are wired while keeping
all outbound/provider sends disabled.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime, time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import Settings
from app.db.source_runs import SourceRunsRepository
from app.models.source_runs import NightlySourcePullRequest
from app.services.nightly_lead_machine_service import NightlyLeadMachineService
from app.services.probate_source_provider_service import ProbateSourceProviderBridgeService


def _utc_day_window(day: str | None) -> tuple[str, str]:
    if day:
        date_value = datetime.fromisoformat(day).date()
    else:
        date_value = datetime.now(tz=UTC).date()
    start = datetime.combine(date_value, time.min, tzinfo=UTC)
    end = datetime.combine(date_value, time.max, tzinfo=UTC)
    return start.isoformat(), end.isoformat()


def _build_request(args: argparse.Namespace) -> NightlySourcePullRequest:
    window_start, window_end = args.window_start, args.window_end
    if not window_start or not window_end:
        window_start, window_end = _utc_day_window(args.day)
    idempotency_key = args.idempotency_key or f"probate-autopilot-live-no-send-smoke:{window_start}:{window_end}"
    return NightlySourcePullRequest(
        business_id=args.business_id,
        environment=args.environment,
        live_source_calls=True,
        idempotency_key=idempotency_key,
        metadata={
            "autopilot": "harris_montgomery_probate",
            "county_scope": ["harris", "montgomery"],
            "expected_counties": ["harris", "montgomery"],
            "window_start": window_start,
            "window_end": window_end,
            "run_kind": "manual_live_no_send_smoke",
            "no_send": True,
            "provider_sends_enabled": False,
            "source_provider_approval": {
                "approved": True,
                "approved_by": "probate_autopilot_live_no_send_smoke",
                "scope": "harris_montgomery_public_probate_sources",
                "no_send": True,
                "provider_sends_enabled": False,
            },
            "source_provider_bridge": {
                "mode": "live_source_adapters",
                "expected_counties": ["harris", "montgomery"],
            },
            "property_tax_title_enrichment": {
                "live_cad_calls": True,
                "live_tax_calls": True,
                "live_land_record_calls": True,
                "enrichment_approval": {
                    "approved": True,
                    "approved_by": "probate_autopilot_live_no_send_smoke",
                    "scope": "harris_montgomery_public_cad_tax_land_records",
                    "no_send": True,
                    "provider_sends_enabled": False,
                },
            },
        },
    )


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    artifact_root = args.artifact_root
    if artifact_root is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="ares-probate-autopilot-live-smoke-")
        artifact_root = temp_dir.name
    try:
        settings = Settings(
            _env_file=None,
            lead_machine_artifact_root=str(Path(artifact_root).resolve()),
            lead_machine_live_source_calls_enabled=True,
            lead_machine_live_cad_calls_enabled=True,
            lead_machine_live_tax_calls_enabled=True,
            lead_machine_live_land_record_calls_enabled=True,
            instantly_provider_live_enrollment_enabled=False,
            provider_live_sends_enabled=False,
        )
        service = NightlyLeadMachineService(
            repository=SourceRunsRepository(),
            settings=settings,
            source_provider_bridge=ProbateSourceProviderBridgeService(settings=settings),
        )
        response = service.run_nightly_source_pull(_build_request(args))
        brief = response.morning_brief.sections
        enrichment = brief.get("enrichment_backlog", {}) if isinstance(brief.get("enrichment_backlog"), dict) else {}
        no_send = brief.get("no_send_confirmation", {}) if isinstance(brief.get("no_send_confirmation"), dict) else {}
        source_health = brief.get("source_health", {}) if isinstance(brief.get("source_health"), dict) else {}
        keep_now = brief.get("keep_now", {}) if isinstance(brief.get("keep_now"), dict) else {}
        sla_health = brief.get("sla_health", {}) if isinstance(brief.get("sla_health"), dict) else {}
        operator_actions = brief.get("operator_next_actions", []) if isinstance(brief.get("operator_next_actions"), list) else []
        result = {
            "status": response.status,
            "business_id": args.business_id,
            "environment": args.environment,
            "idempotency_key": args.idempotency_key or (response.source_runs[0].idempotency_key if response.source_runs else None),
            "would_call_external_sources": response.would_call_external_sources,
            "live_source_calls_enabled": response.live_source_calls_enabled,
            "source_run_count": len(response.source_runs),
            "counties": sorted({run.county for run in response.source_runs if run.county}),
            "source_health_completed_runs": source_health.get("completed_runs"),
            "source_health_failed_runs": source_health.get("failed_runs"),
            "sla_status": sla_health.get("status"),
            "source_record_count": sum(
                run.record_count
                for run in response.source_runs
                if run.source_lane in {"harris_county_probate", "montgomery_county_probate"}
            ),
            "keep_now_count": keep_now.get("keep_now_count"),
            "enrichment_status": enrichment.get("status"),
            "live_cad_calls_attempted": enrichment.get("live_cad_calls_attempted"),
            "live_tax_calls_attempted": enrichment.get("live_tax_calls_attempted"),
            "live_land_record_calls_attempted": enrichment.get("live_land_record_calls_attempted"),
            "enriched_count": enrichment.get("enriched_count"),
            "property_match_unmatched_count": enrichment.get("property_match_unmatched_count"),
            "tax_overlay_ambiguous_count": enrichment.get("tax_overlay_ambiguous_count"),
            "title_friction_review_count": enrichment.get("title_friction_review_count"),
            "no_send": no_send.get("no_send"),
            "provider_sends_enabled": no_send.get("provider_sends_enabled"),
            "operator_actions": [item.get("action") for item in operator_actions if isinstance(item, dict)],
            "warnings_count": len(response.warnings),
            "artifact_root": str(Path(artifact_root).resolve()),
        }
        required_true = [
            result["would_call_external_sources"],
            result["live_source_calls_enabled"],
            result["live_cad_calls_attempted"],
            result["live_tax_calls_attempted"],
            result["live_land_record_calls_attempted"],
            result["no_send"],
        ]
        if not all(value is True for value in required_true):
            raise RuntimeError(f"live no-send smoke failed required true checks: {result}")
        if result["provider_sends_enabled"] is not False:
            raise RuntimeError(f"provider sends were not blocked: {result}")
        if result["source_record_count"] <= 0:
            raise RuntimeError(f"live source adapters returned no probate source records: {result}")
        return result
    finally:
        if temp_dir is not None and not args.keep_temp_artifacts:
            temp_dir.cleanup()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--business-id", default="limitless")
    parser.add_argument("--environment", default="live-smoke")
    parser.add_argument("--day", help="UTC date to smoke, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--window-start", help="Explicit ISO window start.")
    parser.add_argument("--window-end", help="Explicit ISO window end.")
    parser.add_argument("--artifact-root", help="Optional artifact directory. Defaults to a temp dir.")
    parser.add_argument("--idempotency-key")
    parser.add_argument("--keep-temp-artifacts", action="store_true")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run_smoke(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
