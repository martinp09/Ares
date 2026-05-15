from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.db.source_runs import SourceRunsRepository, source_runs_repository
from app.models.source_runs import (
    MorningBrief,
    MorningBriefRequest,
    MorningBriefSummary,
    NightlySourcePullRequest,
    NightlySourcePullResponse,
    ProbateAutopilotHealthResponse,
    SourceLane,
    SourceRun,
    SourceRunArtifact,
    SourceRunArtifactSummary,
    SourceRunManifest,
    SourceRunStatus,
    SourceRunSummary,
)
from app.services.probate_autopilot_manifest_service import (
    build_probate_autopilot_manifests,
    collect_probate_autopilot_keep_now_rows,
    is_probate_autopilot_request,
)
from app.services.probate_property_tax_title_enrichment_service import ProbatePropertyTaxTitleEnrichmentService
from app.services.probate_source_provider_service import (
    ProbateSourceProviderBridgeService,
    probate_source_provider_bridge_service,
)


DEFAULT_SOURCE_DEFINITIONS: tuple[dict[str, str], ...] = (
    {
        "source_key": "harris_county_probate_fixture",
        "source_label": "Harris County Probate fixture manifest",
        "source_lane": "harris_county_probate",
    },
    {
        "source_key": "hcad_estate_of_fixture",
        "source_label": "HCAD estate-of fixture manifest",
        "source_lane": "hcad_estate_of",
    },
    {
        "source_key": "hctax_delinquency_overlay_fixture",
        "source_label": "HCTax delinquency overlay fixture manifest",
        "source_lane": "hctax_delinquency_overlay",
    },
    {
        "source_key": "harris_land_records_fixture",
        "source_label": "Harris land records fixture manifest",
        "source_lane": "harris_land_records",
    },
)

_PROBATE_SOURCE_LANES = {"harris_county_probate", "montgomery_county_probate"}
_PROPERTY_MATCH_LANES = {"harris": "harris_hcad_property_match", "montgomery": "montgomery_cad_property_match"}
_TAX_OVERLAY_LANES = {"harris": "harris_hctax_overlay", "montgomery": "montgomery_act_tax_overlay"}
_LAND_RECORD_LANES = {"harris": "harris_land_records", "montgomery": "montgomery_land_records"}
_ENRICHMENT_STAGE_LABELS = {
    "property_match": "Property/CAD match enrichment",
    "tax_overlay": "Tax delinquency overlay enrichment",
    "title_friction": "Land-record/title-friction enrichment",
}


class NightlyLeadMachineService:
    def __init__(
        self,
        repository: SourceRunsRepository | None = None,
        settings: Settings | None = None,
        source_provider_bridge: ProbateSourceProviderBridgeService | None = None,
        enrichment_service: ProbatePropertyTaxTitleEnrichmentService | None = None,
    ) -> None:
        self.repository = repository or source_runs_repository
        self.settings = settings or get_settings()
        self.source_provider_bridge = source_provider_bridge or probate_source_provider_bridge_service
        self.enrichment_service = enrichment_service or ProbatePropertyTaxTitleEnrichmentService(settings=self.settings)

    def run_nightly_source_pull(self, request: NightlySourcePullRequest) -> NightlySourcePullResponse:
        if request.live_source_calls:
            self.source_provider_bridge.reject_live_source_calls(request)

        if request.idempotency_key:
            existing = self.repository.get_nightly_response_by_idempotency_key(
                business_id=request.business_id,
                environment=request.environment,
                idempotency_key=request.idempotency_key,
            )
            if existing is not None:
                return existing.model_copy(update={"duplicate": True, "replayed": True})

        if not request.source_runs:
            request = self.source_provider_bridge.hydrate_request(request)

        if request.source_runs:
            manifests = request.source_runs
        elif is_probate_autopilot_request(request.metadata):
            manifests = build_probate_autopilot_manifests(
                metadata=request.metadata,
                idempotency_key=request.idempotency_key,
                artifact_root=self.settings.lead_machine_artifact_root,
            )
        else:
            manifests = self._default_manifests()

        enrichment_result = self._run_probate_property_tax_title_enrichment(request)
        if enrichment_result is not None:
            manifests = [
                *manifests,
                *self._probate_enrichment_manifests(
                    request=request,
                    enrichment_result=enrichment_result,
                ),
            ]
        created_runs: list[SourceRun] = []
        response_warnings: list[str] = []
        if not request.source_runs and not is_probate_autopilot_request(request.metadata):
            response_warnings.append("no source artifacts supplied; fixture source definitions recorded with zero counts")

        for manifest in manifests:
            run = SourceRun(
                business_id=request.business_id,
                environment=request.environment,
                source_key=manifest.source_key,
                source_label=manifest.source_label,
                source_lane=manifest.source_lane,
                county=manifest.county,
                run_kind=manifest.run_kind,
                window_start=manifest.window_start,
                window_end=manifest.window_end,
                idempotency_key=manifest.idempotency_key or request.idempotency_key,
                source_reported_count=manifest.source_reported_count,
                raw_count=manifest.raw_count,
                parsed_count=manifest.parsed_count,
                keep_now_count=manifest.keep_now_count,
                metadata={
                    **manifest.metadata,
                    "would_call_external_sources": False,
                    "live_source_calls_enabled": False,
                },
            )
            stored = self.repository.start_run(run)
            for artifact in manifest.artifacts:
                stored = self.repository.attach_artifact(stored.id, artifact)
            if manifest.failed or manifest.error_message:
                stored = self.repository.fail_run(
                    stored.id,
                    error_message=manifest.error_message or "source manifest marked failed",
                    warnings=manifest.warnings,
                )
            else:
                record_count = manifest.record_count
                if record_count is None:
                    record_count = sum(artifact.record_count for artifact in manifest.artifacts)
                stored = self.repository.complete_run(stored.id, record_count=record_count, warnings=manifest.warnings)
            created_runs.append(stored)

        brief_metadata = request.metadata
        if enrichment_result is not None:
            brief_metadata = {
                **request.metadata,
                "probate_property_tax_title_enrichment": _safe_enrichment_summary(enrichment_result),
            }
        brief = self.build_morning_brief(
            business_id=request.business_id,
            environment=request.environment,
            source_runs=created_runs,
            metadata=brief_metadata,
        )
        self.repository.save_brief(brief)
        response = NightlySourcePullResponse(source_runs=created_runs, morning_brief=brief, warnings=response_warnings + brief.warnings)
        if request.idempotency_key:
            self.repository.save_nightly_response_for_idempotency_key(
                idempotency_key=request.idempotency_key,
                response=response,
            )
        return response

    def _run_probate_property_tax_title_enrichment(
        self,
        request: NightlySourcePullRequest,
    ) -> dict[str, Any] | None:
        keep_now_rows = collect_probate_autopilot_keep_now_rows(metadata=request.metadata)
        if not keep_now_rows:
            return None
        enrichment_config = _enrichment_config(request.metadata)
        return self.enrichment_service.run_enrichment(
            business_id=request.business_id,
            environment=request.environment,
            keep_now_rows=keep_now_rows,
            hcad_candidates_by_case=_mapping_from_enrichment_config(
                enrichment_config,
                request.metadata,
                "hcad_candidates_by_case",
            ),
            tax_overlays_by_case=_mapping_from_enrichment_config(
                enrichment_config,
                request.metadata,
                "tax_overlays_by_case",
            ),
            tax_overlays_by_account=_mapping_from_enrichment_config(
                enrichment_config,
                request.metadata,
                "tax_overlays_by_account",
            ),
            land_record_rows_by_case=_mapping_from_enrichment_config(
                enrichment_config,
                request.metadata,
                "land_record_rows_by_case",
            ),
            live_cad_calls=_bool_from_enrichment_config(enrichment_config, request.metadata, "live_cad_calls"),
            live_tax_calls=_bool_from_enrichment_config(enrichment_config, request.metadata, "live_tax_calls"),
            live_land_record_calls=_bool_from_enrichment_config(
                enrichment_config,
                request.metadata,
                "live_land_record_calls",
            ),
            enrichment_approval=_mapping_from_enrichment_config(
                enrichment_config,
                request.metadata,
                "enrichment_approval",
            ),
        )

    def _probate_enrichment_manifests(
        self,
        *,
        request: NightlySourcePullRequest,
        enrichment_result: Mapping[str, Any],
    ) -> list[SourceRunManifest]:
        records_by_county: dict[str, list[dict[str, Any]]] = {"harris": [], "montgomery": []}
        for record in enrichment_result.get("records", []):
            if not isinstance(record, dict):
                continue
            county = _record_county(record)
            if county in records_by_county:
                records_by_county[county].append(record)

        run_kind = _metadata_run_kind(request.metadata)
        window_key = _window_key_from_metadata(request.metadata)
        manifests: list[SourceRunManifest] = []
        for county, records in records_by_county.items():
            if not records:
                continue
            summary = _county_enrichment_summary(records, enrichment_result=enrichment_result)
            for stage, lane in (
                ("property_match", _PROPERTY_MATCH_LANES[county]),
                ("tax_overlay", _TAX_OVERLAY_LANES[county]),
                ("title_friction", _LAND_RECORD_LANES[county]),
            ):
                stage_summary = _stage_summary(summary, stage=stage)
                manifests.append(
                    SourceRunManifest(
                        source_key=":".join(
                            [
                                lane,
                                run_kind,
                                window_key,
                                request.idempotency_key or "no-idempotency-key",
                            ]
                        ),
                        source_label=f"{county.title()} {_ENRICHMENT_STAGE_LABELS[stage]}",
                        source_lane=lane,  # type: ignore[arg-type]
                        county=county,  # type: ignore[arg-type]
                        run_kind=run_kind,  # type: ignore[arg-type]
                        window_start=_parse_metadata_datetime(request.metadata.get("window_start")),
                        window_end=_parse_metadata_datetime(request.metadata.get("window_end")),
                        idempotency_key=(
                            f"{request.idempotency_key}:{county}:{stage}" if request.idempotency_key else None
                        ),
                        raw_count=0,
                        parsed_count=0,
                        keep_now_count=0,
                        record_count=0,
                        artifacts=[
                            self._enrichment_artifact(
                                county=county,
                                run_kind=run_kind,
                                window_key=window_key,
                                stage=stage,
                                summary=stage_summary,
                                records=records,
                            )
                        ],
                        metadata={
                            "autopilot": "harris_montgomery_probate",
                            "phase": "phase_3_property_tax_title_enrichment",
                            "county": county,
                            "run_kind": run_kind,
                            "enrichment_stage": stage,
                            **stage_summary,
                            "no_send": True,
                            "provider_sends_enabled": False,
                            "outbound_allowed": False,
                        },
                    )
                )
        return manifests

    def _enrichment_artifact(
        self,
        *,
        county: str,
        run_kind: str,
        window_key: str,
        stage: str,
        summary: Mapping[str, Any],
        records: list[dict[str, Any]],
    ) -> SourceRunArtifact:
        payload = {
            "county": county,
            "run_kind": run_kind,
            "stage": stage,
            "summary": dict(summary),
            "records": records,
            "no_send": True,
            "provider_sends_enabled": False,
            "outbound_allowed": False,
        }
        body = json.dumps(payload, sort_keys=True, default=str, indent=2) + "\n"
        checksum = hashlib.sha256(body.encode("utf-8")).hexdigest()
        logical_path = (
            f"/opt/ares/lead-data/probate_autopilot/{county}/{run_kind}/"
            f"{_safe_path_part(window_key)}/{stage}_enrichment.json"
        )
        path = logical_path
        if self.settings.lead_machine_artifact_root:
            root = Path(self.settings.lead_machine_artifact_root).expanduser()
            file_path = (
                root
                / "probate_autopilot"
                / county
                / run_kind
                / _safe_path_part(window_key)
                / f"{stage}_enrichment.json"
            )
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(body, encoding="utf-8")
            path = str(file_path)
        return SourceRunArtifact(
            path=path,
            artifact_type=f"{stage}_enrichment",
            record_count=0,
            checksum=checksum,
            metadata={"county": county, "run_kind": run_kind, "stage": stage, **dict(summary)},
        )

    def build_morning_brief(
        self,
        *,
        business_id: str,
        environment: str,
        source_runs: list[SourceRun] | None = None,
        source_run_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MorningBrief:
        if source_runs is None:
            source_runs = self.repository.list_runs(business_id=business_id, environment=environment)
            if source_run_ids:
                wanted = set(source_run_ids)
                source_runs = [run for run in source_runs if run.id in wanted]

        warnings: list[str] = []
        lane_summaries: dict[str, dict[str, Any]] = {}
        hot_lead_count = 0
        warm_lead_count = 0
        blocked_count = 0
        approval_required_count = 0
        county_summaries: dict[str, dict[str, Any]] = {}
        source_count_mismatches: list[dict[str, Any]] = []
        blocked_lanes: list[dict[str, Any]] = []
        invalid_row_count = 0
        duplicate_case_count = 0
        duplicate_case_count_by_county: dict[str, int] = {}
        artifact_warning_count = 0
        enrichment_summary = _safe_enrichment_summary(
            (metadata or {}).get("probate_property_tax_title_enrichment")
        )

        for run in source_runs:
            lane_summary = lane_summaries.setdefault(
                run.source_lane,
                {"source_lane": run.source_lane, "run_count": 0, "record_count": 0, "failed_count": 0, "warning_count": 0},
            )
            lane_summary["run_count"] += 1
            lane_summary["record_count"] += run.record_count
            lane_summary["warning_count"] += run.warning_count
            if run.county:
                raw_count = run.raw_count if run.raw_count is not None else self._int_from_metadata(run.metadata, "raw_count")
                parsed_count = run.parsed_count if run.parsed_count is not None else self._int_from_metadata(run.metadata, "parsed_count")
                keep_now_count = run.keep_now_count if run.keep_now_count is not None else self._int_from_metadata(run.metadata, "keep_now_count")
                county_summary = county_summaries.setdefault(
                    run.county,
                    {
                        "county": run.county,
                        "run_count": 0,
                        "record_count": 0,
                        "raw_count": 0,
                        "parsed_count": 0,
                        "keep_now_count": 0,
                        "failed_count": 0,
                    },
                )
                county_summary["run_count"] += 1
                county_summary["record_count"] += run.record_count
                county_summary["raw_count"] += raw_count
                county_summary["parsed_count"] += parsed_count
                county_summary["keep_now_count"] += keep_now_count
                if run.status == SourceRunStatus.FAILED:
                    county_summary["failed_count"] += 1
                source_reported_count = run.source_reported_count
                if source_reported_count is None:
                    source_reported_count = self._optional_int_from_metadata(run.metadata, "source_reported_count")
                if source_reported_count is not None and parsed_count != source_reported_count:
                    source_count_mismatches.append(
                        {
                            "source_key": run.source_key,
                            "source_lane": run.source_lane,
                            "county": run.county,
                            "source_reported_count": source_reported_count,
                            "parsed_count": parsed_count,
                        }
                    )
            if run.status == SourceRunStatus.FAILED:
                lane_summary["failed_count"] += 1
                blocked_lanes.append(
                    {
                        "source_key": run.source_key,
                        "source_lane": run.source_lane,
                        "county": run.county,
                        "error_message": run.error_message or "unknown error",
                    }
                )
                warnings.append(f"{run.source_key} failed: {run.error_message or 'unknown error'}")
            warnings.extend(str(item) for item in run.metadata.get("warnings", []) if item)
            invalid_row_count += self._int_from_metadata(run.metadata, "invalid_row_count")
            run_duplicate_case_count = self._int_from_metadata(run.metadata, "duplicate_case_count")
            duplicate_case_count += run_duplicate_case_count
            if run_duplicate_case_count:
                county_key = run.county or run.source_lane
                duplicate_case_count_by_county[county_key] = (
                    duplicate_case_count_by_county.get(county_key, 0) + run_duplicate_case_count
                )

            for artifact in run.artifacts:
                hot_lead_count += self._int_from_metadata(artifact.metadata, "hot_lead_count")
                warm_lead_count += self._int_from_metadata(artifact.metadata, "warm_lead_count")
                blocked_count += self._int_from_metadata(artifact.metadata, "blocked_count")
                approval_required_count += self._int_from_metadata(artifact.metadata, "approval_required_count")
                artifact_warning_count += len(artifact.warnings)
                warnings.extend(artifact.warnings)
            hot_lead_count += self._int_from_metadata(run.metadata, "hot_lead_count")
            warm_lead_count += self._int_from_metadata(run.metadata, "warm_lead_count")
            blocked_count += self._int_from_metadata(run.metadata, "blocked_count")
            approval_required_count += self._int_from_metadata(run.metadata, "approval_required_count")

        new_record_count = sum(run.record_count for run in source_runs if run.status == SourceRunStatus.COMPLETED)
        keep_now_total = sum(item["keep_now_count"] for item in county_summaries.values())
        expected_counties = self._expected_counties(metadata=metadata or {}, source_runs=source_runs)
        missing_counties = [county for county in expected_counties if county not in county_summaries]
        source_anomalies = self._source_anomalies(
            blocked_lanes=blocked_lanes,
            source_count_mismatches=source_count_mismatches,
            county_summaries=county_summaries,
            expected_counties=expected_counties,
            missing_counties=missing_counties,
            invalid_row_count=invalid_row_count,
            duplicate_case_count=duplicate_case_count,
            duplicate_case_count_by_county=duplicate_case_count_by_county,
        )
        unique_warnings = list(dict.fromkeys(warnings))
        operator_next_actions = self._operator_next_actions(
            failed_lane_count=len(blocked_lanes),
            mismatch_count=len(source_count_mismatches),
            invalid_row_count=invalid_row_count,
            duplicate_case_count=duplicate_case_count,
            keep_now_count=keep_now_total,
            enrichment_pending_count=_enrichment_pending_count(keep_now_total, enrichment_summary),
        )
        sections = {
            "source_health": {
                "would_call_external_sources": False,
                "live_source_calls_enabled": False,
                "total_runs": len(source_runs),
                "completed_runs": sum(1 for run in source_runs if run.status == SourceRunStatus.COMPLETED),
                "failed_runs": sum(1 for run in source_runs if run.status == SourceRunStatus.FAILED),
                "lanes": list(lane_summaries.values()),
            },
            "approvals": {
                "approval_required_count": approval_required_count,
                "blocked_count": blocked_count,
            },
            "lead_temperature": {
                "hot_lead_count": hot_lead_count,
                "warm_lead_count": warm_lead_count,
            },
            "county_counts": list(county_summaries.values()),
            "keep_now": {
                "keep_now_count": keep_now_total,
            },
            "source_quality": {
                "source_count_mismatch_count": len(source_count_mismatches),
                "invalid_row_count": invalid_row_count,
                "duplicate_case_count": duplicate_case_count,
                "duplicate_case_count_by_county": duplicate_case_count_by_county,
                "artifact_warning_count": artifact_warning_count,
            },
            "sla_health": self._sla_health(
                failed_lane_count=len(blocked_lanes),
                mismatch_count=len(source_count_mismatches),
                anomaly_count=len(source_anomalies),
                expected_counties=expected_counties,
                missing_counties=missing_counties,
                completed_county_count=len(
                    [
                        county
                        for county in expected_counties
                        if county in county_summaries and county_summaries[county]["failed_count"] == 0
                    ]
                ),
            ),
            "source_anomalies": source_anomalies,
            "enrichment_backlog": _enrichment_backlog(keep_now_total, enrichment_summary),
            "operator_next_actions": operator_next_actions,
            "blocked_lanes": blocked_lanes,
            "source_count_mismatches": source_count_mismatches,
            "no_send_confirmation": {
                "no_send": True,
                "provider_sends_enabled": False,
                "instantly_enrollment_enabled": False,
                "message": "Probate autopilot source pulls do not enroll, activate, or send outreach.",
            },
            "source_request": self._safe_request_metadata(metadata or {}),
        }
        return MorningBrief(
            business_id=business_id,
            environment=environment,
            source_runs=source_runs,
            new_record_count=new_record_count,
            hot_lead_count=hot_lead_count,
            warm_lead_count=warm_lead_count,
            blocked_count=blocked_count,
            approval_required_count=approval_required_count,
            sections=sections,
            warnings=unique_warnings,
        )

    def create_morning_brief(self, request: MorningBriefRequest) -> MorningBrief:
        if request.idempotency_key:
            existing = self.repository.get_brief_by_idempotency_key(
                business_id=request.business_id,
                environment=request.environment,
                idempotency_key=request.idempotency_key,
            )
            if existing is not None:
                return existing

        brief = self.build_morning_brief(
            business_id=request.business_id,
            environment=request.environment,
            source_run_ids=request.source_run_ids,
            metadata=request.metadata,
        )
        stored = self.repository.save_brief(brief)
        if request.idempotency_key:
            self.repository.save_brief_for_idempotency_key(idempotency_key=request.idempotency_key, brief=stored)
        return stored

    def get_latest_morning_brief(self, *, business_id: str, environment: str) -> MorningBrief | None:
        return self.repository.latest_brief(business_id=business_id, environment=environment)

    def get_probate_autopilot_health(
        self,
        *,
        business_id: str,
        environment: str,
        max_brief_age_hours: float | None = None,
        now: datetime | None = None,
    ) -> ProbateAutopilotHealthResponse:
        brief = self.get_latest_morning_brief(business_id=business_id, environment=environment)
        if brief is None:
            return ProbateAutopilotHealthResponse(
                business_id=business_id,
                environment=environment,
                status="no_data",
                freshness_ok=False,
                no_send_ok=False,
                outbound_allowed=False,
                operator_next_actions=[
                    {
                        "priority": "urgent",
                        "action": "run_probate_autopilot_source_pull",
                        "reason": "No probate autopilot morning brief is present for this scope",
                    }
                ],
            )

        sections = brief.sections
        sla_health = self._dict_from_section(sections, "sla_health")
        source_quality = self._dict_from_section(sections, "source_quality")
        enrichment_backlog = self._dict_from_section(sections, "enrichment_backlog")
        no_send = self._dict_from_section(sections, "no_send_confirmation")
        anomalies = self._list_from_section(sections, "source_anomalies")
        operator_next_actions = self._list_from_section(sections, "operator_next_actions")
        status = str(sla_health.get("status") or "unknown")
        generated_at = brief.generated_at if brief.generated_at.tzinfo else brief.generated_at.replace(tzinfo=timezone.utc)
        now_aware = now or datetime.now(timezone.utc)
        brief_age_hours = max(0.0, (now_aware - generated_at).total_seconds() / 3600)
        freshness_ok = max_brief_age_hours is None or brief_age_hours <= max_brief_age_hours
        stale_brief = not freshness_ok
        if stale_brief:
            status = "blocked"
            operator_next_actions = [
                {
                    "priority": "urgent",
                    "action": "run_or_repair_probate_autopilot_source_pull",
                    "reason": f"Latest probate autopilot brief is {brief_age_hours:.2f} hours old; SLA is {max_brief_age_hours:.2f} hours.",
                },
                *operator_next_actions,
            ]
        return ProbateAutopilotHealthResponse(
            business_id=brief.business_id,
            environment=brief.environment,
            status=status,
            latest_brief_id=brief.id,
            generated_at=brief.generated_at,
            brief_age_hours=round(brief_age_hours, 3),
            freshness_sla_hours=max_brief_age_hours,
            freshness_ok=freshness_ok,
            stale_brief=stale_brief,
            no_send_ok=no_send.get("no_send") is True and no_send.get("provider_sends_enabled") is False,
            outbound_allowed=bool(sla_health.get("outbound_allowed")) and bool(no_send.get("provider_sends_enabled")),
            source_run_count=len(brief.source_runs),
            warning_count=len(brief.warnings),
            new_record_count=brief.new_record_count,
            sla_health=sla_health,
            source_quality=source_quality,
            enrichment_backlog=enrichment_backlog,
            anomaly_count=len(anomalies),
            anomalies=anomalies[:10],
            operator_next_actions=operator_next_actions[:10],
        )

    def list_source_runs(
        self,
        *,
        business_id: str,
        environment: str,
        limit: int | None = None,
        source_lane: SourceLane | None = None,
    ) -> list[SourceRun]:
        return self.repository.list_runs(
            business_id=business_id,
            environment=environment,
            limit=limit,
            source_lane=source_lane,
        )

    def summarize_source_runs(self, runs: list[SourceRun]) -> list[SourceRunSummary]:
        return [self._summarize_source_run(run) for run in runs]

    def summarize_morning_brief(self, brief: MorningBrief | None) -> MorningBriefSummary | None:
        if brief is None:
            return None
        return MorningBriefSummary(
            id=brief.id,
            business_id=brief.business_id,
            environment=brief.environment,
            generated_at=brief.generated_at,
            source_runs=self.summarize_source_runs(brief.source_runs),
            new_record_count=brief.new_record_count,
            hot_lead_count=brief.hot_lead_count,
            warm_lead_count=brief.warm_lead_count,
            blocked_count=brief.blocked_count,
            approval_required_count=brief.approval_required_count,
            sections=self._sanitize_brief_sections(brief.sections),
            warnings=brief.warnings,
        )

    def _default_manifests(self) -> list[SourceRunManifest]:
        return [
            SourceRunManifest(
                source_key=item["source_key"],
                source_label=item["source_label"],
                source_lane=item["source_lane"],  # type: ignore[arg-type]
                record_count=0,
                warnings=["no source artifacts supplied"],
            )
            for item in DEFAULT_SOURCE_DEFINITIONS
        ]

    @staticmethod
    def _summarize_source_run(run: SourceRun) -> SourceRunSummary:
        return SourceRunSummary(
            id=run.id,
            business_id=run.business_id,
            environment=run.environment,
            source_key=run.source_key,
            source_label=run.source_label,
            source_lane=run.source_lane,
            county=run.county,
            run_kind=run.run_kind,
            window_start=run.window_start,
            window_end=run.window_end,
            idempotency_key=run.idempotency_key,
            source_reported_count=run.source_reported_count,
            raw_count=run.raw_count,
            parsed_count=run.parsed_count,
            keep_now_count=run.keep_now_count,
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            artifact_count=run.artifact_count,
            record_count=run.record_count,
            warning_count=run.warning_count,
            error_message=run.error_message,
            artifacts=[
                SourceRunArtifactSummary(
                    path=artifact.path,
                    artifact_type=artifact.artifact_type,
                    record_count=artifact.record_count,
                    checksum=artifact.checksum,
                    warning_count=len(artifact.warnings),
                )
                for artifact in run.artifacts
            ],
        )

    @staticmethod
    def _sanitize_brief_sections(sections: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in sections.items() if key != "metadata"}

    @staticmethod
    def _safe_request_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        safe_keys = {
            "autopilot",
            "probate_autopilot",
            "run_kind",
            "slot",
            "schedule_slot",
            "county_scope",
            "expected_counties",
            "counties",
            "window_start",
            "window_end",
            "no_send",
            "provider_sends_enabled",
            "source_adapter_contract",
        }
        return {key: value for key, value in metadata.items() if key in safe_keys}

    @staticmethod
    def _dict_from_section(sections: dict[str, Any], key: str) -> dict[str, Any]:
        value = sections.get(key)
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _list_from_section(sections: dict[str, Any], key: str) -> list[dict[str, Any]]:
        value = sections.get(key)
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    @staticmethod
    def _expected_counties(*, metadata: dict[str, Any], source_runs: list[SourceRun]) -> list[str]:
        for key in ("expected_counties", "county_scope", "counties"):
            value = metadata.get(key)
            counties = NightlyLeadMachineService._normalize_county_list(value)
            if counties:
                return counties
        if any(run.metadata.get("autopilot") == "harris_montgomery_probate" for run in source_runs):
            return ["harris", "montgomery"]
        return sorted({run.county for run in source_runs if run.county})

    @staticmethod
    def _normalize_county_list(value: Any) -> list[str]:
        if isinstance(value, str):
            raw_items = [value]
        elif isinstance(value, (list, tuple, set)):
            raw_items = list(value)
        else:
            return []
        counties: list[str] = []
        for item in raw_items:
            normalized = str(item or "").strip().lower().replace("_county", "").replace(" county", "")
            if normalized in {"harris", "montgomery"} and normalized not in counties:
                counties.append(normalized)
        return counties

    @staticmethod
    def _source_anomalies(
        *,
        blocked_lanes: list[dict[str, Any]],
        source_count_mismatches: list[dict[str, Any]],
        county_summaries: dict[str, dict[str, Any]],
        expected_counties: list[str],
        missing_counties: list[str],
        invalid_row_count: int,
        duplicate_case_count: int,
        duplicate_case_count_by_county: dict[str, int],
    ) -> list[dict[str, Any]]:
        anomalies: list[dict[str, Any]] = []
        for county in missing_counties:
            anomalies.append(
                {
                    "severity": "blocked",
                    "type": "missing_expected_county",
                    "county": county,
                    "message": f"Expected {county} probate source lane was not present in this run",
                }
            )
        for lane in blocked_lanes:
            anomalies.append(
                {
                    "severity": "blocked",
                    "type": "source_lane_failed",
                    "source_key": lane["source_key"],
                    "source_lane": lane["source_lane"],
                    "county": lane.get("county"),
                    "message": lane["error_message"],
                }
            )
        for mismatch in source_count_mismatches:
            anomalies.append(
                {
                    "severity": "warning",
                    "type": "source_count_mismatch",
                    **mismatch,
                }
            )
        raw_total = sum(summary["raw_count"] for summary in county_summaries.values())
        invalid_rate = invalid_row_count / raw_total if raw_total else 0
        if invalid_row_count and (invalid_rate >= 0.10 or invalid_row_count >= 5):
            anomalies.append(
                {
                    "severity": "warning",
                    "type": "invalid_row_rate_high",
                    "invalid_row_count": invalid_row_count,
                    "raw_count": raw_total,
                    "invalid_row_rate": round(invalid_rate, 4),
                }
            )
        if duplicate_case_count:
            anomalies.append(
                {
                    "severity": "warning",
                    "type": "duplicate_case_numbers",
                    "duplicate_case_count": duplicate_case_count,
                    "duplicate_case_count_by_county": duplicate_case_count_by_county,
                    "message": "One or more source files repeated the same probate case; dedupe before enrichment and CRM mirror.",
                }
            )
        for county in expected_counties:
            summary = county_summaries.get(county)
            if summary and summary["raw_count"] > 0 and summary["parsed_count"] == 0:
                anomalies.append(
                    {
                        "severity": "blocked",
                        "type": "zero_parse_yield",
                        "county": county,
                        "raw_count": summary["raw_count"],
                        "message": "A source lane returned raw rows but none could be parsed",
                    }
                )
        return anomalies

    @staticmethod
    def _sla_health(
        *,
        failed_lane_count: int,
        mismatch_count: int,
        anomaly_count: int,
        expected_counties: list[str],
        missing_counties: list[str],
        completed_county_count: int,
    ) -> dict[str, Any]:
        if failed_lane_count or missing_counties:
            status = "blocked"
        elif mismatch_count or anomaly_count:
            status = "warning"
        else:
            status = "healthy"
        return {
            "status": status,
            "expected_counties": expected_counties,
            "missing_counties": missing_counties,
            "completed_county_count": completed_county_count,
            "failed_lane_count": failed_lane_count,
            "source_count_mismatch_count": mismatch_count,
            "anomaly_count": anomaly_count,
            "outbound_allowed": False,
            "operator_message": "Autopilot source SLA is for scrape/enrich/brief readiness only; outbound remains separately approval-gated.",
        }

    @staticmethod
    def _operator_next_actions(
        *,
        failed_lane_count: int,
        mismatch_count: int,
        invalid_row_count: int,
        duplicate_case_count: int,
        keep_now_count: int,
        enrichment_pending_count: int,
    ) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if failed_lane_count:
            actions.append(
                {
                    "priority": "urgent",
                    "action": "review_failed_source_lanes",
                    "reason": f"{failed_lane_count} source lane(s) failed during this pull",
                }
            )
        if mismatch_count:
            actions.append(
                {
                    "priority": "high",
                    "action": "reconcile_source_count_mismatches",
                    "reason": f"{mismatch_count} source lane(s) reported a different count than Ares parsed",
                }
            )
        if invalid_row_count:
            actions.append(
                {
                    "priority": "normal",
                    "action": "inspect_invalid_source_rows",
                    "reason": f"{invalid_row_count} source row(s) could not be normalized",
                }
            )
        if duplicate_case_count:
            actions.append(
                {
                    "priority": "normal",
                    "action": "dedupe_duplicate_case_rows",
                    "reason": f"{duplicate_case_count} duplicate probate case row(s) were detected across the source packet",
                }
            )
        if keep_now_count:
            if enrichment_pending_count:
                actions.append(
                    {
                        "priority": "high",
                        "action": "complete_property_tax_title_enrichment",
                        "reason": (
                            f"{enrichment_pending_count} keep-now probate row(s) still need property match, "
                            "tax overlay, or title-friction evidence"
                        ),
                    }
                )
            else:
                actions.append(
                    {
                        "priority": "normal",
                        "action": "review_enriched_probate_queue",
                        "reason": (
                            f"{keep_now_count} keep-now probate row(s) completed the scheduled property, tax, "
                            "and title-friction enrichment pass"
                        ),
                    }
                )
            actions.append(
                {
                    "priority": "normal",
                    "action": "keep_outbound_blocked",
                    "reason": "No sends/enrollment are allowed until enrichment, suppression, and exact copy approval are complete",
                }
            )
        if not actions:
            actions.append(
                {
                    "priority": "normal",
                    "action": "monitor_next_scheduled_pull",
                    "reason": "No keep-now probate rows or source failures were detected in this brief",
                }
            )
        return actions

    @staticmethod
    def _int_from_metadata(metadata: dict[str, Any], key: str) -> int:
        value = metadata.get(key)
        if isinstance(value, bool):
            return 0
        if isinstance(value, int) and value >= 0:
            return value
        return 0

    @staticmethod
    def _optional_int_from_metadata(metadata: dict[str, Any], key: str) -> int | None:
        value = metadata.get(key)
        if isinstance(value, int) and value >= 0 and not isinstance(value, bool):
            return value
        return None


def _enrichment_config(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("property_tax_title_enrichment", "probate_property_tax_title_enrichment", "enrichment"):
        value = metadata.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _mapping_from_enrichment_config(
    enrichment_config: Mapping[str, Any],
    metadata: Mapping[str, Any],
    key: str,
) -> Mapping[str, Any]:
    value = enrichment_config.get(key)
    if isinstance(value, Mapping):
        return value
    value = metadata.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


def _bool_from_enrichment_config(enrichment_config: Mapping[str, Any], metadata: Mapping[str, Any], key: str) -> bool:
    if key in enrichment_config:
        return enrichment_config.get(key) is True
    return metadata.get(key) is True


def _safe_enrichment_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {
            "status": "not_run",
            "received_count": 0,
            "enriched_count": 0,
            "property_match_completed_count": 0,
            "property_match_unmatched_count": 0,
            "property_match_pending_count": 0,
            "tax_overlay_completed_count": 0,
            "tax_overlay_pending_count": 0,
            "tax_overlay_ambiguous_count": 0,
            "title_friction_completed_count": 0,
            "title_friction_pending_count": 0,
            "title_friction_review_count": 0,
            "hubspot_mirror_blocked_until_approval_count": 0,
            "outbound_blocked_until_explicit_approval_count": 0,
            "no_send": True,
            "provider_sends_enabled": False,
            "outbound_allowed": False,
            "live_cad_calls_attempted": False,
            "live_tax_calls_attempted": False,
            "live_land_record_calls_attempted": False,
        }
    enriched_count = _non_negative_int(value.get("enriched_count"))
    property_completed = _non_negative_int(value.get("property_match_completed_count"))
    tax_completed = _non_negative_int(value.get("tax_overlay_completed_count"))
    title_completed = _non_negative_int(value.get("title_friction_completed_count"))
    property_pending = max(0, enriched_count - property_completed)
    tax_pending = max(0, enriched_count - tax_completed)
    title_pending = max(0, enriched_count - title_completed)
    status = "not_run"
    if enriched_count and any((property_pending, tax_pending, title_pending)):
        status = "partial"
    elif enriched_count:
        status = "completed"
    return {
        "status": status,
        "received_count": _non_negative_int(value.get("received_count")),
        "enriched_count": enriched_count,
        "property_match_completed_count": property_completed,
        "property_match_unmatched_count": _non_negative_int(value.get("property_match_unmatched_count")),
        "property_match_pending_count": property_pending,
        "tax_overlay_completed_count": tax_completed,
        "tax_overlay_pending_count": tax_pending,
        "tax_overlay_ambiguous_count": _non_negative_int(value.get("tax_overlay_ambiguous_count")),
        "title_friction_completed_count": title_completed,
        "title_friction_pending_count": title_pending,
        "title_friction_review_count": _non_negative_int(value.get("title_friction_review_count")),
        "hubspot_mirror_blocked_until_approval_count": _non_negative_int(
            value.get("hubspot_mirror_blocked_until_approval_count")
        ),
        "outbound_blocked_until_explicit_approval_count": _non_negative_int(
            value.get("outbound_blocked_until_explicit_approval_count")
        ),
        "no_send": value.get("no_send") is not False,
        "provider_sends_enabled": value.get("provider_sends_enabled") is True,
        "outbound_allowed": value.get("outbound_allowed") is True,
        "live_cad_calls_attempted": value.get("live_cad_calls_attempted") is True,
        "live_tax_calls_attempted": value.get("live_tax_calls_attempted") is True,
        "live_land_record_calls_attempted": value.get("live_land_record_calls_attempted") is True,
    }


def _enrichment_backlog(keep_now_count: int, enrichment_summary: Mapping[str, Any]) -> dict[str, Any]:
    if enrichment_summary.get("status") == "not_run":
        return {
            "status": "pending",
            "property_match_pending_count": keep_now_count,
            "tax_overlay_pending_count": keep_now_count,
            "title_friction_pending_count": keep_now_count,
            "hubspot_mirror_blocked_until_approval_count": keep_now_count,
            "outbound_blocked_until_explicit_approval_count": keep_now_count,
        }
    return {
        "status": enrichment_summary.get("status"),
        "enriched_count": _non_negative_int(enrichment_summary.get("enriched_count")),
        "property_match_completed_count": _non_negative_int(
            enrichment_summary.get("property_match_completed_count")
        ),
        "property_match_pending_count": _non_negative_int(enrichment_summary.get("property_match_pending_count")),
        "property_match_unmatched_count": _non_negative_int(
            enrichment_summary.get("property_match_unmatched_count")
        ),
        "tax_overlay_completed_count": _non_negative_int(enrichment_summary.get("tax_overlay_completed_count")),
        "tax_overlay_pending_count": _non_negative_int(enrichment_summary.get("tax_overlay_pending_count")),
        "tax_overlay_ambiguous_count": _non_negative_int(enrichment_summary.get("tax_overlay_ambiguous_count")),
        "title_friction_completed_count": _non_negative_int(
            enrichment_summary.get("title_friction_completed_count")
        ),
        "title_friction_pending_count": _non_negative_int(enrichment_summary.get("title_friction_pending_count")),
        "title_friction_review_count": _non_negative_int(enrichment_summary.get("title_friction_review_count")),
        "hubspot_mirror_blocked_until_approval_count": _non_negative_int(
            enrichment_summary.get("hubspot_mirror_blocked_until_approval_count")
        ),
        "outbound_blocked_until_explicit_approval_count": _non_negative_int(
            enrichment_summary.get("outbound_blocked_until_explicit_approval_count")
        ),
        "no_send": enrichment_summary.get("no_send") is True,
        "provider_sends_enabled": enrichment_summary.get("provider_sends_enabled") is True,
        "outbound_allowed": enrichment_summary.get("outbound_allowed") is True,
        "live_cad_calls_attempted": enrichment_summary.get("live_cad_calls_attempted") is True,
        "live_tax_calls_attempted": enrichment_summary.get("live_tax_calls_attempted") is True,
        "live_land_record_calls_attempted": enrichment_summary.get("live_land_record_calls_attempted") is True,
    }


def _enrichment_pending_count(keep_now_count: int, enrichment_summary: Mapping[str, Any]) -> int:
    if enrichment_summary.get("status") == "not_run":
        return keep_now_count
    return max(
        _non_negative_int(enrichment_summary.get("property_match_pending_count")),
        _non_negative_int(enrichment_summary.get("tax_overlay_pending_count")),
        _non_negative_int(enrichment_summary.get("title_friction_pending_count")),
    )


def _county_enrichment_summary(
    records: list[dict[str, Any]],
    *,
    enrichment_result: Mapping[str, Any],
) -> dict[str, Any]:
    property_completed = sum(1 for record in records if record.get("hcad_acct"))
    tax_completed = 0
    tax_ambiguous = 0
    title_completed = 0
    title_review = 0
    for record in records:
        pain_stack = record.get("pain_stack") if isinstance(record.get("pain_stack"), Mapping) else {}
        tax_overlay = pain_stack.get("tax_overlay") if isinstance(pain_stack.get("tax_overlay"), Mapping) else {}
        title_friction = pain_stack.get("title_friction") if isinstance(pain_stack.get("title_friction"), Mapping) else {}
        tax_status = str(tax_overlay.get("status") or "")
        if tax_status and tax_status != "tax_overlay_not_checked":
            tax_completed += 1
        if tax_status == "tax_overlay_ambiguous":
            tax_ambiguous += 1
        title_status = str(title_friction.get("status") or "")
        if title_status and title_status != "not_checked":
            title_completed += 1
        if title_friction.get("next_action") in {"needs_document_image_review", "needs_land_record_review"}:
            title_review += 1
    enriched_count = len(records)
    return {
        "enriched_count": enriched_count,
        "property_match_completed_count": property_completed,
        "property_match_unmatched_count": max(0, enriched_count - property_completed),
        "property_match_pending_count": max(0, enriched_count - property_completed),
        "tax_overlay_completed_count": tax_completed,
        "tax_overlay_pending_count": max(0, enriched_count - tax_completed),
        "tax_overlay_ambiguous_count": tax_ambiguous,
        "title_friction_completed_count": title_completed,
        "title_friction_pending_count": max(0, enriched_count - title_completed),
        "title_friction_review_count": title_review,
        "hubspot_mirror_blocked_until_approval_count": enriched_count,
        "outbound_blocked_until_explicit_approval_count": enriched_count,
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
        "live_cad_calls_attempted": enrichment_result.get("live_cad_calls_attempted") is True,
        "live_tax_calls_attempted": enrichment_result.get("live_tax_calls_attempted") is True,
        "live_land_record_calls_attempted": enrichment_result.get("live_land_record_calls_attempted") is True,
    }


def _stage_summary(summary: Mapping[str, Any], *, stage: str) -> dict[str, Any]:
    base = {
        "enriched_count": _non_negative_int(summary.get("enriched_count")),
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
    }
    if stage == "property_match":
        return {
            **base,
            "property_match_completed_count": _non_negative_int(
                summary.get("property_match_completed_count")
            ),
            "property_match_pending_count": _non_negative_int(summary.get("property_match_pending_count")),
            "property_match_unmatched_count": _non_negative_int(
                summary.get("property_match_unmatched_count")
            ),
            "live_cad_calls_attempted": summary.get("live_cad_calls_attempted") is True,
        }
    if stage == "tax_overlay":
        return {
            **base,
            "tax_overlay_completed_count": _non_negative_int(summary.get("tax_overlay_completed_count")),
            "tax_overlay_pending_count": _non_negative_int(summary.get("tax_overlay_pending_count")),
            "tax_overlay_ambiguous_count": _non_negative_int(summary.get("tax_overlay_ambiguous_count")),
            "live_tax_calls_attempted": summary.get("live_tax_calls_attempted") is True,
        }
    return {
        **base,
        "title_friction_completed_count": _non_negative_int(summary.get("title_friction_completed_count")),
        "title_friction_pending_count": _non_negative_int(summary.get("title_friction_pending_count")),
        "title_friction_review_count": _non_negative_int(summary.get("title_friction_review_count")),
        "live_land_record_calls_attempted": summary.get("live_land_record_calls_attempted") is True,
    }


def _record_county(record: Mapping[str, Any]) -> str | None:
    raw_payload = record.get("raw_payload") if isinstance(record.get("raw_payload"), Mapping) else {}
    source_row = raw_payload.get("source_row") if isinstance(raw_payload.get("source_row"), Mapping) else {}
    raw = source_row.get("raw") if isinstance(source_row.get("raw"), Mapping) else {}
    for candidate in (record.get("county"), source_row.get("county"), raw.get("county")):
        normalized = str(candidate or "").strip().lower().replace(" county", "")
        if normalized in {"harris", "montgomery"}:
            return normalized
    return None


def _metadata_run_kind(metadata: Mapping[str, Any]) -> str:
    value = str(metadata.get("run_kind") or metadata.get("slot") or metadata.get("schedule_slot") or "manual")
    normalized = value.strip().lower()
    if normalized in {
        "morning_catchup",
        "midday",
        "end_of_day",
        "daily_reconciliation",
        "weekly_reconciliation",
        "manual",
    }:
        return normalized
    return "manual"


def _window_key_from_metadata(metadata: Mapping[str, Any]) -> str:
    start = metadata.get("window_start")
    end = metadata.get("window_end")
    if start or end:
        return f"{start or 'open'}__{end or 'open'}"
    return "unspecified-window"


def _parse_metadata_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _safe_path_part(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9_.=-]+", "-", str(value or "").strip())
    return text.strip("-") or "unspecified"


def _non_negative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int) and value >= 0:
        return value
    return 0


nightly_lead_machine_service = NightlyLeadMachineService()
