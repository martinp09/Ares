from __future__ import annotations

from typing import Any

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
    def __init__(self, repository: SourceRunsRepository | None = None) -> None:
        self.repository = repository or source_runs_repository

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

            for artifact in run.artifacts:
                hot_lead_count += self._int_from_metadata(artifact.metadata, "hot_lead_count")
                warm_lead_count += self._int_from_metadata(artifact.metadata, "warm_lead_count")
                blocked_count += self._int_from_metadata(artifact.metadata, "blocked_count")
                approval_required_count += self._int_from_metadata(artifact.metadata, "approval_required_count")
                warnings.extend(artifact.warnings)
            hot_lead_count += self._int_from_metadata(run.metadata, "hot_lead_count")
            warm_lead_count += self._int_from_metadata(run.metadata, "warm_lead_count")
            blocked_count += self._int_from_metadata(run.metadata, "blocked_count")
            approval_required_count += self._int_from_metadata(run.metadata, "approval_required_count")

        new_record_count = sum(run.record_count for run in source_runs if run.status == SourceRunStatus.COMPLETED)
        unique_warnings = list(dict.fromkeys(warnings))
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
                "keep_now_count": sum(item["keep_now_count"] for item in county_summaries.values()),
            },
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
