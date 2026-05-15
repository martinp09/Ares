from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.db.source_runs import SourceRunsRepository, source_runs_repository
from app.models.source_runs import (
    MorningBrief,
    MorningBriefRequest,
    MorningBriefSummary,
    NightlySourcePullRequest,
    NightlySourcePullResponse,
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
    is_probate_autopilot_request,
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


class NightlyLeadMachineService:
    def __init__(self, repository: SourceRunsRepository | None = None, settings: Settings | None = None) -> None:
        self.repository = repository or source_runs_repository
        self.settings = settings or get_settings()

    def run_nightly_source_pull(self, request: NightlySourcePullRequest) -> NightlySourcePullResponse:
        if request.live_source_calls:
            raise RuntimeError("live source calls are disabled for probate autopilot Phase 1 no-send source pulls")

        if request.idempotency_key:
            existing = self.repository.get_nightly_response_by_idempotency_key(
                business_id=request.business_id,
                environment=request.environment,
                idempotency_key=request.idempotency_key,
            )
            if existing is not None:
                return existing.model_copy(update={"duplicate": True, "replayed": True})

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

        brief = self.build_morning_brief(
            business_id=request.business_id,
            environment=request.environment,
            source_runs=created_runs,
            metadata=request.metadata,
        )
        self.repository.save_brief(brief)
        response = NightlySourcePullResponse(source_runs=created_runs, morning_brief=brief, warnings=response_warnings + brief.warnings)
        if request.idempotency_key:
            self.repository.save_nightly_response_for_idempotency_key(
                idempotency_key=request.idempotency_key,
                response=response,
            )
        return response

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
        artifact_warning_count = 0

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
        )
        unique_warnings = list(dict.fromkeys(warnings))
        operator_next_actions = self._operator_next_actions(
            failed_lane_count=len(blocked_lanes),
            mismatch_count=len(source_count_mismatches),
            invalid_row_count=invalid_row_count,
            keep_now_count=keep_now_total,
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
            "enrichment_backlog": {
                "property_match_pending_count": keep_now_total,
                "tax_overlay_pending_count": keep_now_total,
                "hubspot_mirror_blocked_until_approval_count": keep_now_total,
                "outbound_blocked_until_explicit_approval_count": keep_now_total,
            },
            "operator_next_actions": operator_next_actions,
            "blocked_lanes": blocked_lanes,
            "source_count_mismatches": source_count_mismatches,
            "no_send_confirmation": {
                "no_send": True,
                "provider_sends_enabled": False,
                "instantly_enrollment_enabled": False,
                "message": "Probate autopilot source pulls do not enroll, activate, or send outreach.",
            },
            "metadata": metadata or {},
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
        keep_now_count: int,
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
        if keep_now_count:
            actions.append(
                {
                    "priority": "high",
                    "action": "run_property_tax_title_enrichment",
                    "reason": f"{keep_now_count} keep-now probate row(s) are ready for property match, tax overlay, and title-friction enrichment",
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
            return int(value)
        if isinstance(value, int) and value >= 0:
            return value
        return 0

    @staticmethod
    def _optional_int_from_metadata(metadata: dict[str, Any], key: str) -> int | None:
        value = metadata.get(key)
        if isinstance(value, int) and value >= 0 and not isinstance(value, bool):
            return value
        return None


nightly_lead_machine_service = NightlyLeadMachineService()
