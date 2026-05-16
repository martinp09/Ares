from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from app.core.config import Settings, get_settings
from app.db.probate_source_identities import ProbateSourceIdentityRepository
from app.db.source_runs import SourceRunsPersistenceError, SourceRunsRepository, source_runs_repository
from app.models.slack_notifications import SlackNotificationAttempt, SlackNotificationRoute
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
    probate_source_identity_key,
)
from app.services.probate_case_detail_enrichment_service import ProbateCaseDetailEnrichmentService
from app.services.probate_property_tax_title_enrichment_service import ProbatePropertyTaxTitleEnrichmentService
from app.services.probate_source_provider_service import ProbateSourceProviderBridgeService
from app.services.slack_notification_service import slack_notification_service


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
_CASE_DETAIL_LANES = {"harris": "harris_probate_case_detail", "montgomery": "montgomery_probate_case_detail"}
_PROPERTY_MATCH_LANES = {"harris": "harris_hcad_property_match", "montgomery": "montgomery_cad_property_match"}
_TAX_OVERLAY_LANES = {"harris": "harris_hctax_overlay", "montgomery": "montgomery_act_tax_overlay"}
_LAND_RECORD_LANES = {"harris": "harris_land_records", "montgomery": "montgomery_land_records"}
_ENRICHMENT_STAGE_LABELS = {
    "case_detail": "Case-detail party/event/document enrichment",
    "property_match": "Property/CAD match enrichment",
    "tax_overlay": "Tax delinquency overlay enrichment",
    "title_friction": "Land-record/title-friction enrichment",
}
_HOT_LEAD_VISIBLE_LIMIT = 10
_PHONE_KEYS = ("phone", "phone_number", "primary_phone", "mobile", "mobile_phone", "contact_phone")
_EMAIL_KEYS = ("email", "email_address", "primary_email", "contact_email")


class NightlyLeadMachineService:
    def __init__(
        self,
        repository: SourceRunsRepository | None = None,
        settings: Settings | None = None,
        source_provider_bridge: ProbateSourceProviderBridgeService | None = None,
        case_detail_service: ProbateCaseDetailEnrichmentService | None = None,
        enrichment_service: ProbatePropertyTaxTitleEnrichmentService | None = None,
        source_identity_repository: ProbateSourceIdentityRepository | None = None,
        slack_notifier: Any | None = None,
    ) -> None:
        self.repository = repository or source_runs_repository
        self.settings = settings or get_settings()
        self.source_provider_bridge = source_provider_bridge or ProbateSourceProviderBridgeService(settings=self.settings)
        self.case_detail_service = case_detail_service or ProbateCaseDetailEnrichmentService(settings=self.settings)
        self.enrichment_service = enrichment_service or ProbatePropertyTaxTitleEnrichmentService(settings=self.settings)
        self.source_identity_repository = source_identity_repository or ProbateSourceIdentityRepository(settings=self.settings)
        self.slack_notifier = slack_notifier or slack_notification_service

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

        if is_probate_autopilot_request(request.metadata):
            request = self._with_source_dedupe_context(request)

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

        case_detail_result = self._run_probate_case_detail_enrichment(request)
        if case_detail_result is not None:
            manifests = [
                *manifests,
                *self._probate_case_detail_manifests(
                    request=request,
                    case_detail_result=case_detail_result,
                ),
            ]
        enrichment_result = self._run_probate_property_tax_title_enrichment(
            request,
            keep_now_rows=(case_detail_result or {}).get("records") if case_detail_result is not None else None,
        )
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
        would_call_external_sources = _metadata_would_call_live_sources(request.metadata)
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
                    "would_call_external_sources": would_call_external_sources
                    or _metadata_would_call_live_sources(manifest.metadata),
                    "live_source_calls_enabled": would_call_external_sources
                    or _metadata_would_call_live_sources(manifest.metadata),
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
                stored = self._record_source_identities_without_blocking(stored)
            created_runs.append(stored)

        brief_metadata = request.metadata
        if case_detail_result is not None:
            brief_metadata = {
                **brief_metadata,
                "probate_case_detail_enrichment": _safe_case_detail_summary(case_detail_result),
            }
        if enrichment_result is not None:
            brief_metadata = {
                **brief_metadata,
                "probate_property_tax_title_enrichment": _safe_enrichment_summary(enrichment_result),
            }
        brief = self.build_morning_brief(
            business_id=request.business_id,
            environment=request.environment,
            source_runs=created_runs,
            metadata=brief_metadata,
        )
        self.repository.save_brief(brief)
        notifications = self._send_source_pull_notifications(
            request=request,
            source_runs=created_runs,
            brief=brief,
            response_warnings=response_warnings,
            enrichment_result=enrichment_result,
        )
        response = NightlySourcePullResponse(
            would_call_external_sources=would_call_external_sources,
            live_source_calls_enabled=would_call_external_sources,
            source_runs=created_runs,
            morning_brief=brief,
            warnings=response_warnings + brief.warnings,
            notifications=notifications,
        )
        if request.idempotency_key:
            return self.repository.save_nightly_response_for_idempotency_key(
                idempotency_key=request.idempotency_key,
                response=response,
            )
        return response

    def _record_source_identities_without_blocking(self, run: SourceRun) -> SourceRun:
        try:
            recorded_count = self.source_identity_repository.record_source_run(run)
        except Exception as exc:  # pragma: no cover - exact provider exceptions vary by runtime/client
            warning = (
                f"probate source identity ledger write failed with {exc.__class__.__name__}; "
                "nightly source pull continued without provider/outbound side effects"
            )
            return self.repository.complete_run(
                run.id,
                record_count=run.record_count,
                warnings=[*run.metadata.get("warnings", []), warning],
            )
        if recorded_count:
            return run.model_copy(
                update={
                    "metadata": {
                        **run.metadata,
                        "source_identity_remote_record_status": "recorded",
                        "source_identity_remote_recorded_count": recorded_count,
                    }
                }
            )
        return run

    def _with_source_dedupe_context(self, request: NightlySourcePullRequest) -> NightlySourcePullRequest:
        rows = request.metadata.get("source_rows")
        if not rows:
            return request
        run_scope = _source_run_scope(request.metadata)
        existing, remote_identity_warning = self._existing_probate_source_identity_keys_by_county(
            business_id=request.business_id,
            environment=request.environment,
            run_scope=run_scope,
        )
        metadata_warnings = [str(item) for item in request.metadata.get("warnings", []) if item]
        if remote_identity_warning:
            metadata_warnings.append(remote_identity_warning)
        metadata = {
            **request.metadata,
            "warnings": list(dict.fromkeys(metadata_warnings)),
            "source_run_scope": run_scope,
            "source_identity_version": "county_case_sha256_v1",
            "existing_source_identity_keys_by_county": {
                county: sorted(keys) for county, keys in existing.items() if keys
            },
            "source_dedupe": {
                "strategy": "county_case_sha256_v1",
                "scope": run_scope,
                "existing_identity_count_by_county": {county: len(keys) for county, keys in existing.items()},
                "remote_identity_ledger_status": "warning" if remote_identity_warning else "loaded",
                "manual_runs_isolated": run_scope != "manual",
            },
        }
        return request.model_copy(update={"metadata": metadata})

    def _existing_probate_source_identity_keys_by_county(
        self,
        *,
        business_id: str,
        environment: str,
        run_scope: str,
    ) -> tuple[dict[str, set[str]], str | None]:
        keys_by_county: dict[str, set[str]] = {"harris": set(), "montgomery": set()}
        remote_identity_warning: str | None = None
        try:
            remote_keys = self.source_identity_repository.list_identity_keys(
                business_id=business_id,
                environment=environment,
                run_scope=run_scope,
                counties=("harris", "montgomery"),
            )
        except Exception as exc:  # pragma: no cover - exact provider exceptions vary by runtime/client
            remote_keys = {}
            remote_identity_warning = (
                f"probate source identity ledger read failed with {exc.__class__.__name__}; "
                "continuing with file-backed completed-run dedupe"
            )
        for county, keys in remote_keys.items():
            keys_by_county.setdefault(county, set()).update(keys)
        for run in self.repository.list_runs(business_id=business_id, environment=environment):
            if run.source_lane not in _PROBATE_SOURCE_LANES or run.status != SourceRunStatus.COMPLETED or not run.county:
                continue
            if _source_run_scope(run.metadata, run_kind=run.run_kind) != run_scope:
                continue
            county = run.county
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
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    identity_key = row.get("source_identity_key")
                    if not isinstance(identity_key, str) or not identity_key:
                        identity_key = probate_source_identity_key(row, county=county)  # type: ignore[arg-type]
                    if identity_key:
                        keys_by_county.setdefault(county, set()).add(identity_key)
        return keys_by_county, remote_identity_warning

    def _send_source_pull_notifications(
        self,
        *,
        request: NightlySourcePullRequest,
        source_runs: list[SourceRun],
        brief: MorningBrief,
        response_warnings: list[str],
        enrichment_result: Mapping[str, Any] | None,
    ) -> list[dict[str, Any]]:
        hot_records = _hot_records_from_enrichment(enrichment_result)
        notifications = [
            self._notify_lead_run_digest(
                request=request,
                source_runs=source_runs,
                brief=brief,
                response_warnings=response_warnings,
                hot_records=hot_records,
            )
        ]
        if hot_records:
            notifications.append(
                self._notify_hot_leads_digest(
                    request=request,
                    source_runs=source_runs,
                    hot_records=hot_records,
                )
            )
        return notifications

    def _notify_lead_run_digest(
        self,
        *,
        request: NightlySourcePullRequest,
        source_runs: list[SourceRun],
        brief: MorningBrief,
        response_warnings: list[str],
        hot_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        dedupe_key = _source_pull_dedupe_key(request=request, source_runs=source_runs)
        source_summary = _source_summary_from_brief(brief)
        run_counts = {
            "total": len(source_runs),
            "completed": sum(1 for run in source_runs if run.status == SourceRunStatus.COMPLETED),
            "failed": sum(1 for run in source_runs if run.status == SourceRunStatus.FAILED),
        }
        payload = {
            "kind": "nightly_lead_machine_source_run_digest",
            "business_id": request.business_id,
            "environment": request.environment,
            "run_id": request.run_id,
            "command_id": request.command_id,
            "trigger_run_id": request.trigger_run_id,
            "idempotency_key": request.idempotency_key,
            "run_counts": run_counts,
            "new_record_count": brief.new_record_count,
            "hot_lead_count": max(brief.hot_lead_count, len(hot_records)),
            "warm_lead_count": brief.warm_lead_count,
            "warnings": list(dict.fromkeys([*response_warnings, *brief.warnings]))[:10],
            "source_summary": source_summary,
            "no_send": True,
            "provider_sends_enabled": False,
        }
        text = (
            f"Lead-machine source run digest: {run_counts['completed']}/{run_counts['total']} completed, "
            f"{brief.new_record_count} new records, {payload['hot_lead_count']} hot leads."
        )
        blocks = _lead_run_digest_blocks(text=text, payload=payload)
        return self._notify_and_summarize(
            route=SlackNotificationRoute.LEAD_RUNS,
            business_id=request.business_id,
            environment=request.environment,
            dedupe_key=dedupe_key,
            text=text,
            blocks=blocks,
            payload=payload,
        )

    def _notify_hot_leads_digest(
        self,
        *,
        request: NightlySourcePullRequest,
        source_runs: list[SourceRun],
        hot_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        hot_leads = [_hot_lead_payload(record) for record in hot_records]
        visible_hot_leads = hot_leads[:_HOT_LEAD_VISIBLE_LIMIT]
        remaining_count = max(0, len(hot_leads) - len(visible_hot_leads))
        base_key = _source_pull_dedupe_key(request=request, source_runs=source_runs)
        dedupe_key = f"{base_key}:hot-leads"
        payload = {
            "kind": "nightly_lead_machine_hot_leads",
            "business_id": request.business_id,
            "environment": request.environment,
            "run_id": request.run_id,
            "command_id": request.command_id,
            "trigger_run_id": request.trigger_run_id,
            "idempotency_key": request.idempotency_key,
            "hot_leads": visible_hot_leads,
            "total_hot_lead_count": len(hot_leads),
            "visible_hot_lead_count": len(visible_hot_leads),
            "remaining_count": remaining_count,
            "next_action": "Review enriched probate lead before any outreach approval.",
            "no_send": True,
            "provider_sends_enabled": False,
        }
        text = (
            f"Hot probate lead digest: {len(hot_leads)} hot lead(s), showing {len(visible_hot_leads)}"
            + (f"; {remaining_count} additional hidden by cap." if remaining_count else ".")
        )
        blocks = _hot_leads_digest_blocks(
            text=text,
            hot_leads=visible_hot_leads,
            remaining_count=remaining_count,
            next_action=str(payload["next_action"]),
        )
        return self._notify_and_summarize(
            route=SlackNotificationRoute.HOT_LEADS,
            business_id=request.business_id,
            environment=request.environment,
            dedupe_key=dedupe_key,
            text=text,
            blocks=blocks,
            payload=payload,
        )

    def _notify_and_summarize(
        self,
        *,
        route: SlackNotificationRoute,
        business_id: str,
        environment: str,
        dedupe_key: str,
        text: str,
        blocks: list[dict[str, Any]],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            attempt = self.slack_notifier.notify(
                route=route,
                business_id=business_id,
                environment=environment,
                dedupe_key=dedupe_key,
                text=text,
                blocks=blocks,
                payload=payload,
            )
        except Exception as exc:
            return {
                "route": route.value,
                "status": "failed",
                "deduped": False,
                "channel_id": None,
                "dedupe_key": dedupe_key,
                "slack_message_ts": None,
                "error_message": str(exc),
            }
        return _notification_summary(attempt, route=route, dedupe_key=dedupe_key)

    def _run_probate_case_detail_enrichment(
        self,
        request: NightlySourcePullRequest,
    ) -> dict[str, Any] | None:
        keep_now_rows = collect_probate_autopilot_keep_now_rows(metadata=request.metadata)
        if not keep_now_rows:
            return None
        case_detail_config = _case_detail_config(request.metadata)
        return self.case_detail_service.run_enrichment(
            business_id=request.business_id,
            environment=request.environment,
            keep_now_rows=keep_now_rows,
            case_details_by_case=_mapping_from_enrichment_config(
                case_detail_config,
                request.metadata,
                "case_details_by_case",
            ),
            live_case_detail_calls=_bool_from_enrichment_config(
                case_detail_config,
                request.metadata,
                "live_case_detail_calls",
            ),
            case_detail_approval=_mapping_from_enrichment_config(
                case_detail_config,
                request.metadata,
                "case_detail_approval",
            ),
        )

    def _run_probate_property_tax_title_enrichment(
        self,
        request: NightlySourcePullRequest,
        *,
        keep_now_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        if keep_now_rows is None:
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

    def _probate_case_detail_manifests(
        self,
        *,
        request: NightlySourcePullRequest,
        case_detail_result: Mapping[str, Any],
    ) -> list[SourceRunManifest]:
        records_by_county: dict[str, list[dict[str, Any]]] = {"harris": [], "montgomery": []}
        for record in case_detail_result.get("records", []):
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
            summary = _county_case_detail_summary(records, case_detail_result=case_detail_result)
            lane = _CASE_DETAIL_LANES[county]
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
                    source_label=f"{county.title()} {_ENRICHMENT_STAGE_LABELS['case_detail']}",
                    source_lane=lane,  # type: ignore[arg-type]
                    county=county,  # type: ignore[arg-type]
                    run_kind=run_kind,  # type: ignore[arg-type]
                    window_start=_parse_metadata_datetime(request.metadata.get("window_start")),
                    window_end=_parse_metadata_datetime(request.metadata.get("window_end")),
                    idempotency_key=(f"{request.idempotency_key}:{county}:case_detail" if request.idempotency_key else None),
                    raw_count=0,
                    parsed_count=0,
                    keep_now_count=0,
                    record_count=0,
                    artifacts=[
                        self._case_detail_artifact(
                            county=county,
                            run_kind=run_kind,
                            window_key=window_key,
                            summary=summary,
                            records=records,
                        )
                    ],
                    metadata={
                        "autopilot": "harris_montgomery_probate",
                        "phase": "phase_3_case_detail_enrichment",
                        "county": county,
                        "run_kind": run_kind,
                        "enrichment_stage": "case_detail",
                        **summary,
                        "no_send": True,
                        "provider_sends_enabled": False,
                        "outbound_allowed": False,
                    },
                )
            )
        return manifests

    def _case_detail_artifact(
        self,
        *,
        county: str,
        run_kind: str,
        window_key: str,
        summary: Mapping[str, Any],
        records: list[dict[str, Any]],
    ) -> SourceRunArtifact:
        payload = {
            "county": county,
            "run_kind": run_kind,
            "stage": "case_detail",
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
            f"{_safe_path_part(window_key)}/case_detail_enrichment.json"
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
                / "case_detail_enrichment.json"
            )
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(body, encoding="utf-8")
            path = str(file_path)
        return SourceRunArtifact(
            path=path,
            artifact_type="case_detail_enrichment",
            record_count=len(records),
            checksum=checksum,
            metadata={"county": county, "run_kind": run_kind, "stage": "case_detail", **dict(summary)},
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
        duplicate_prior_run_count = 0
        duplicate_current_run_count = 0
        duplicate_case_count_by_county: dict[str, int] = {}
        artifact_warning_count = 0
        enrichment_summary = _safe_enrichment_summary(
            (metadata or {}).get("probate_property_tax_title_enrichment")
        )
        case_detail_summary = _safe_case_detail_summary((metadata or {}).get("probate_case_detail_enrichment"))

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
            run_duplicate_prior_count = self._int_from_metadata(run.metadata, "duplicate_prior_run_count")
            run_duplicate_current_count = self._int_from_metadata(run.metadata, "duplicate_current_run_count")
            duplicate_case_count += run_duplicate_case_count
            duplicate_prior_run_count += run_duplicate_prior_count
            duplicate_current_run_count += run_duplicate_current_count
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
        live_source_calls_attempted = _brief_would_call_live_sources(metadata or {}, source_runs)
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
            case_detail_pending_count=_case_detail_pending_count(keep_now_total, case_detail_summary),
            enrichment_pending_count=_enrichment_pending_count(keep_now_total, enrichment_summary),
        )
        sections = {
            "source_health": {
                "would_call_external_sources": live_source_calls_attempted,
                "live_source_calls_enabled": live_source_calls_attempted,
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
                "duplicate_prior_run_count": duplicate_prior_run_count,
                "duplicate_current_run_count": duplicate_current_run_count,
                "deduped_existing_record_count": duplicate_prior_run_count,
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
            "case_detail": case_detail_summary,
            "enrichment_backlog": _enrichment_backlog(keep_now_total, enrichment_summary, case_detail_summary),
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
        try:
            brief = self.get_latest_morning_brief(business_id=business_id, environment=environment)
        except SourceRunsPersistenceError:
            return ProbateAutopilotHealthResponse(
                business_id=business_id,
                environment=environment,
                status="blocked",
                freshness_ok=False,
                no_send_ok=False,
                outbound_allowed=False,
                operator_next_actions=[
                    {
                        "priority": "urgent",
                        "action": "repair_probate_autopilot_state",
                        "reason": "The source-runs repository state is unreadable; repair or restore the durable state file before trusting scheduler health.",
                    }
                ],
            )
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
            "source_run_scope",
            "source_identity_version",
            "source_dedupe",
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
        case_detail_pending_count: int,
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
            if case_detail_pending_count:
                actions.append(
                    {
                        "priority": "high",
                        "action": "complete_case_detail_enrichment",
                        "reason": (
                            f"{case_detail_pending_count} keep-now probate row(s) still need party, event, "
                            "document, or contact-candidate evidence"
                        ),
                    }
                )
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
            elif not case_detail_pending_count:
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


def _case_detail_config(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("case_detail_enrichment", "probate_case_detail_enrichment", "case_detail"):
        value = metadata.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


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


def _safe_case_detail_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {
            "status": "not_run",
            "received_count": 0,
            "detail_completed_count": 0,
            "detail_incomplete_count": 0,
            "detail_blocked_count": 0,
            "party_count": 0,
            "event_count": 0,
            "document_reference_count": 0,
            "contact_candidate_count": 0,
            "primary_contact_candidate_count": 0,
            "attorney_count": 0,
            "hearing_clue_count": 0,
            "publication_clue_count": 0,
            "no_send": True,
            "provider_sends_enabled": False,
            "outbound_allowed": False,
            "live_case_detail_calls_attempted": False,
        }
    received_count = _non_negative_int(value.get("received_count"))
    completed = _non_negative_int(value.get("detail_completed_count"))
    incomplete = _non_negative_int(value.get("detail_incomplete_count"))
    blocked = _non_negative_int(value.get("detail_blocked_count"))
    status = str(value.get("status") or "")
    if status not in {"not_run", "completed", "partial", "incomplete", "blocked"}:
        status = _case_detail_status(received_count=received_count, completed=completed, incomplete=incomplete, blocked=blocked)
    return {
        "status": status,
        "received_count": received_count,
        "detail_completed_count": completed,
        "detail_incomplete_count": incomplete,
        "detail_blocked_count": blocked,
        "party_count": _non_negative_int(value.get("party_count")),
        "event_count": _non_negative_int(value.get("event_count")),
        "document_reference_count": _non_negative_int(value.get("document_reference_count")),
        "contact_candidate_count": _non_negative_int(value.get("contact_candidate_count")),
        "primary_contact_candidate_count": _non_negative_int(value.get("primary_contact_candidate_count")),
        "attorney_count": _non_negative_int(value.get("attorney_count")),
        "hearing_clue_count": _non_negative_int(value.get("hearing_clue_count")),
        "publication_clue_count": _non_negative_int(value.get("publication_clue_count")),
        "no_send": value.get("no_send") is not False,
        "provider_sends_enabled": value.get("provider_sends_enabled") is True,
        "outbound_allowed": value.get("outbound_allowed") is True,
        "live_case_detail_calls_attempted": value.get("live_case_detail_calls_attempted") is True,
    }


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


def _enrichment_backlog(
    keep_now_count: int,
    enrichment_summary: Mapping[str, Any],
    case_detail_summary: Mapping[str, Any],
) -> dict[str, Any]:
    case_detail_pending = _case_detail_pending_count(keep_now_count, case_detail_summary)
    case_detail_fields = {
        "case_detail_status": case_detail_summary.get("status"),
        "case_detail_completed_count": _non_negative_int(case_detail_summary.get("detail_completed_count")),
        "case_detail_pending_count": case_detail_pending,
        "case_detail_blocked_count": _non_negative_int(case_detail_summary.get("detail_blocked_count")),
        "case_detail_incomplete_count": _non_negative_int(case_detail_summary.get("detail_incomplete_count")),
        "contact_candidate_count": _non_negative_int(case_detail_summary.get("contact_candidate_count")),
        "primary_contact_candidate_count": _non_negative_int(case_detail_summary.get("primary_contact_candidate_count")),
        "live_case_detail_calls_attempted": case_detail_summary.get("live_case_detail_calls_attempted") is True,
    }
    if enrichment_summary.get("status") == "not_run":
        return {
            "status": "pending",
            **case_detail_fields,
            "property_match_pending_count": keep_now_count,
            "tax_overlay_pending_count": keep_now_count,
            "title_friction_pending_count": keep_now_count,
            "hubspot_mirror_blocked_until_approval_count": keep_now_count,
            "outbound_blocked_until_explicit_approval_count": keep_now_count,
        }
    return {
        "status": _combined_enrichment_status(enrichment_summary.get("status"), case_detail_pending),
        **case_detail_fields,
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


def _combined_enrichment_status(property_tax_title_status: Any, case_detail_pending: int) -> str:
    status = str(property_tax_title_status or "not_run")
    if case_detail_pending and status == "completed":
        return "partial"
    return status


def _case_detail_pending_count(keep_now_count: int, case_detail_summary: Mapping[str, Any]) -> int:
    status = case_detail_summary.get("status")
    if status == "not_run":
        return keep_now_count
    completed = _non_negative_int(case_detail_summary.get("detail_completed_count"))
    return max(0, keep_now_count - completed)


def _enrichment_pending_count(keep_now_count: int, enrichment_summary: Mapping[str, Any]) -> int:
    if enrichment_summary.get("status") == "not_run":
        return keep_now_count
    return max(
        _non_negative_int(enrichment_summary.get("property_match_pending_count")),
        _non_negative_int(enrichment_summary.get("tax_overlay_pending_count")),
        _non_negative_int(enrichment_summary.get("title_friction_pending_count")),
    )


def _county_case_detail_summary(
    records: list[dict[str, Any]],
    *,
    case_detail_result: Mapping[str, Any],
) -> dict[str, Any]:
    detail_completed = 0
    detail_incomplete = 0
    detail_blocked = 0
    party_count = 0
    event_count = 0
    document_reference_count = 0
    contact_candidate_count = 0
    primary_contact_candidate_count = 0
    attorney_count = 0
    hearing_clue_count = 0
    publication_clue_count = 0
    for record in records:
        detail = record.get("case_detail") if isinstance(record.get("case_detail"), Mapping) else {}
        status = detail.get("status")
        if status == "completed":
            detail_completed += 1
        elif status == "blocked":
            detail_blocked += 1
        else:
            detail_incomplete += 1
        party_count += _non_negative_int(detail.get("party_count"))
        event_count += _non_negative_int(detail.get("event_count"))
        document_reference_count += _non_negative_int(detail.get("document_reference_count"))
        contact_candidate_count += _non_negative_int(detail.get("contact_candidate_count"))
        primary_contact_candidate_count += _non_negative_int(detail.get("primary_contact_candidate_count"))
        attorney_count += _non_negative_int(detail.get("attorney_count"))
        hearing_clue_count += _non_negative_int(detail.get("hearing_clue_count"))
        publication_clue_count += _non_negative_int(detail.get("publication_clue_count"))
    return {
        "status": _case_detail_status(
            received_count=len(records),
            completed=detail_completed,
            incomplete=detail_incomplete,
            blocked=detail_blocked,
        ),
        "received_count": len(records),
        "detail_completed_count": detail_completed,
        "detail_incomplete_count": detail_incomplete,
        "detail_blocked_count": detail_blocked,
        "party_count": party_count,
        "event_count": event_count,
        "document_reference_count": document_reference_count,
        "contact_candidate_count": contact_candidate_count,
        "primary_contact_candidate_count": primary_contact_candidate_count,
        "attorney_count": attorney_count,
        "hearing_clue_count": hearing_clue_count,
        "publication_clue_count": publication_clue_count,
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
        "live_case_detail_calls_attempted": case_detail_result.get("live_case_detail_calls_attempted") is True,
    }


def _case_detail_status(*, received_count: int, completed: int, incomplete: int, blocked: int) -> str:
    if received_count == 0:
        return "not_run"
    if blocked:
        return "blocked" if completed == 0 else "partial"
    if incomplete:
        return "incomplete" if completed == 0 else "partial"
    return "completed"


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


def _source_run_scope(metadata: Mapping[str, Any], *, run_kind: str | None = None) -> str:
    explicit = str(metadata.get("source_run_scope") or metadata.get("run_scope") or "").strip().lower()
    if explicit in {"autonomous", "manual"}:
        return explicit
    kind = str(run_kind or metadata.get("run_kind") or metadata.get("slot") or "").strip().lower()
    return "manual" if kind == "manual" or kind.startswith("manual") else "autonomous"


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


def _metadata_would_call_live_sources(metadata: Mapping[str, Any]) -> bool:
    bridge = metadata.get("source_provider_bridge")
    return isinstance(bridge, Mapping) and bridge.get("would_call_live_sources") is True


def _brief_would_call_live_sources(metadata: Mapping[str, Any], source_runs: list[SourceRun]) -> bool:
    if _metadata_would_call_live_sources(metadata):
        return True
    return any(run.metadata.get("would_call_external_sources") is True for run in source_runs)


def _source_pull_dedupe_key(*, request: NightlySourcePullRequest, source_runs: list[SourceRun]) -> str:
    if request.idempotency_key:
        return f"nightly-source-pull:{request.idempotency_key}"
    run_ids = sorted(run.id for run in source_runs)
    digest = hashlib.sha256("|".join(run_ids).encode("utf-8")).hexdigest()[:24]
    return f"nightly-source-pull:runs:{digest}"


def _source_summary_from_brief(brief: MorningBrief) -> dict[str, Any]:
    source_health = brief.sections.get("source_health") if isinstance(brief.sections.get("source_health"), Mapping) else {}
    lanes = source_health.get("lanes") if isinstance(source_health.get("lanes"), list) else []
    county_counts = brief.sections.get("county_counts") if isinstance(brief.sections.get("county_counts"), list) else []
    return {
        "lanes": [
            {
                "source_lane": item.get("source_lane"),
                "run_count": _non_negative_int(item.get("run_count")),
                "record_count": _non_negative_int(item.get("record_count")),
                "failed_count": _non_negative_int(item.get("failed_count")),
            }
            for item in lanes
            if isinstance(item, Mapping)
        ],
        "counties": [
            {
                "county": item.get("county"),
                "run_count": _non_negative_int(item.get("run_count")),
                "record_count": _non_negative_int(item.get("record_count")),
            }
            for item in county_counts
            if isinstance(item, Mapping)
        ],
    }


def _hot_records_from_enrichment(enrichment_result: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(enrichment_result, Mapping):
        return []
    records = enrichment_result.get("records")
    if not isinstance(records, list):
        return []
    hot_records = [
        dict(record)
        for record in records
        if isinstance(record, Mapping) and _is_hot_record(record)
    ]
    return sorted(hot_records, key=lambda record: _lead_score(record.get("lead_score")), reverse=True)


def _hot_lead_payload(record: Mapping[str, Any]) -> dict[str, Any]:
    source_row = _mapping_path(record, "raw_payload", "source_row")
    contact_candidates = _contact_candidates(record, source_row)
    return {
        "score": _lead_score(record.get("lead_score")),
        "case_number": _text_or_none(record.get("case_number")),
        "property_address": _text_or_none(record.get("property_address")),
        "owner_name": _text_or_none(record.get("owner_name")),
        "decedent_name": _text_or_none(record.get("decedent_name")),
        "contact_hint": _contact_hint(contact_candidates),
        "phone": _contact_value(record, source_row, contact_candidates, keys=_PHONE_KEYS),
        "email": _contact_value(record, source_row, contact_candidates, keys=_EMAIL_KEYS),
    }


def _notification_summary(
    attempt: SlackNotificationAttempt | Mapping[str, Any],
    *,
    route: SlackNotificationRoute,
    dedupe_key: str,
) -> dict[str, Any]:
    payload = attempt.model_dump(mode="json") if isinstance(attempt, SlackNotificationAttempt) else dict(attempt)
    raw_route = payload.get("route")
    return {
        "route": raw_route.value if isinstance(raw_route, SlackNotificationRoute) else str(raw_route or route.value),
        "status": str(payload.get("status") or "failed"),
        "deduped": payload.get("deduped") is True,
        "channel_id": payload.get("channel_id"),
        "dedupe_key": str(payload.get("dedupe_key") or dedupe_key),
        "slack_message_ts": payload.get("slack_message_ts"),
        "error_message": payload.get("error_message"),
    }


def _lead_run_digest_blocks(*, text: str, payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_summary = payload.get("source_summary") if isinstance(payload.get("source_summary"), Mapping) else {}
    warnings = payload.get("warnings") if isinstance(payload.get("warnings"), list) else []
    blocks = [
        _section_block(text),
        _section_block(
            " | ".join(
                [
                    f"Failed: {_mapping_path(payload, 'run_counts').get('failed', 0)}",
                    f"Warm: {payload.get('warm_lead_count', 0)}",
                    f"Warnings: {len(warnings)}",
                ]
            )
        ),
        _section_block(f"*Lane summary*\n{_format_source_summary_items(source_summary.get('lanes'), key='source_lane')}"),
        _section_block(f"*County summary*\n{_format_source_summary_items(source_summary.get('counties'), key='county')}"),
    ]
    if warnings:
        blocks.append(_section_block("*Warnings*\n" + "\n".join(f"- {warning}" for warning in warnings[:10])))
    return blocks


def _hot_leads_digest_blocks(
    *,
    text: str,
    hot_leads: list[dict[str, Any]],
    remaining_count: int,
    next_action: str,
) -> list[dict[str, Any]]:
    lead_lines = [_hot_lead_line(lead) for lead in hot_leads]
    if remaining_count:
        lead_lines.append(f"{remaining_count} additional hot lead(s) hidden by Slack digest cap.")
    return [
        _section_block(text),
        _section_block("*Hot leads*\n" + "\n".join(lead_lines)),
        _section_block(f"Next action: {next_action}"),
    ]


def _hot_lead_line(lead: Mapping[str, Any]) -> str:
    parts = [
        f"Case {lead.get('case_number') or 'unknown'}: score {lead.get('score')}",
        f"Property: {lead.get('property_address') or 'unknown'}",
        f"Owner: {lead.get('owner_name') or 'unknown'}",
        f"Decedent: {lead.get('decedent_name') or 'unknown'}",
        f"Contact: {lead.get('contact_hint') or 'unknown'}",
    ]
    if lead.get("phone"):
        parts.append(f"Phone: {lead['phone']}")
    if lead.get("email"):
        parts.append(f"Email: {lead['email']}")
    return " | ".join(parts)


def _format_source_summary_items(items: Any, *, key: str) -> str:
    if not isinstance(items, list):
        return "none"
    lines = []
    for item in items[:10]:
        if not isinstance(item, Mapping):
            continue
        label = item.get(key) or "unknown"
        lines.append(
            f"{label}: {_non_negative_int(item.get('record_count'))} records, "
            f"{_non_negative_int(item.get('run_count'))} runs"
        )
    return "\n".join(lines) if lines else "none"


def _section_block(text: str) -> dict[str, Any]:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text[:3000]}}


def _mapping_path(value: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping):
            return {}
        current = current.get(key)
    return dict(current) if isinstance(current, Mapping) else {}


def _lead_score(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _is_hot_record(record: Mapping[str, Any]) -> bool:
    if _lead_score(record.get("lead_score")) >= 70:
        return True
    return str(record.get("temperature") or record.get("lead_temperature") or "").strip().lower() == "hot"


def _text_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _contact_candidates(record: Mapping[str, Any], source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    for container in (record, source_row):
        for key in ("contact_candidates", "all_contact_candidate_evidence", "contacts"):
            value = container.get(key)
            if isinstance(value, list):
                candidates.extend(item for item in value if isinstance(item, Mapping))
    return candidates


def _contact_value(
    record: Mapping[str, Any],
    source_row: Mapping[str, Any],
    contact_candidates: list[Mapping[str, Any]],
    *,
    keys: tuple[str, ...],
) -> str | None:
    for container in (record, source_row, *contact_candidates):
        for key in keys:
            text = _text_or_none(container.get(key))
            if text:
                return text
    return None


def _contact_hint(contact_candidates: Any) -> str | None:
    if not isinstance(contact_candidates, list):
        return None
    for candidate in contact_candidates:
        if not isinstance(candidate, Mapping):
            continue
        for key in ("name", "full_name", "contact_name"):
            text = _text_or_none(candidate.get(key))
            if text:
                return text
    return None


def _safe_dedupe_part(value: Any) -> str:
    return _safe_path_part(value).lower()


nightly_lead_machine_service = NightlyLeadMachineService()
