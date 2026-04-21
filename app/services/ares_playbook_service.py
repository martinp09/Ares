from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import re

from app.domains.ares import AresCounty, AresLeadRecord, AresSourceLane
from app.domains.ares_workflows import AresWorkflowScope, AresWorkflowStepStatus
from app.services.ares_copy_service import AresCopyService, AresLeadBrief, AresOutreachDraft
from app.services.ares_eval_service import AresEvalService, AresWorkflowEvalReport, AresWorkflowException
from app.services.ares_service import AresMatchingService, RankedAresLead
from app.services.ares_state_service import AresStateService


CountyFetchPayload = Mapping[str, Sequence[Mapping[str, object]]]
CountyFetcher = Callable[[AresCounty], CountyFetchPayload]
_ADDRESS_WHITESPACE_PATTERN = re.compile(r"\s+")
_DEFAULT_MARKET_COUNTIES: tuple[AresCounty, ...] = (AresCounty.HARRIS, AresCounty.DALLAS)


@dataclass(frozen=True)
class AresFollowUpTask:
    task_type: str
    rank: int
    county: AresCounty
    title: str


@dataclass(frozen=True)
class AresPlaybookRunRequest:
    workflow_id: str
    counties: tuple[AresCounty, ...] = ()
    market: str | None = None
    response_events: tuple[str, ...] = ()


@dataclass(frozen=True)
class AresPlaybookRunResult:
    workflow_id: str
    ranked_leads: tuple[RankedAresLead, ...]
    briefs: tuple[AresLeadBrief, ...]
    drafts: tuple[AresOutreachDraft, ...]
    follow_up_tasks: tuple[AresFollowUpTask, ...]
    next_best_action: str
    eval_report: AresWorkflowEvalReport


class AresPlaybookService:
    _STEP_IDS = [
        "choose_scope",
        "pull_signals",
        "enrich_and_score",
        "generate_outreach",
        "create_follow_up_tasks",
        "monitor_responses",
        "suggest_next_action",
    ]

    def __init__(
        self,
        *,
        state_service: AresStateService | None = None,
        eval_service: AresEvalService | None = None,
        county_fetcher: CountyFetcher | None = None,
        matching_service: AresMatchingService | None = None,
        copy_service: AresCopyService | None = None,
    ) -> None:
        self._state_service = state_service or AresStateService()
        self._eval_service = eval_service or AresEvalService()
        self._county_fetcher: CountyFetcher = county_fetcher or self._default_county_fetcher
        self._matching_service = matching_service or AresMatchingService()
        self._copy_service = copy_service or AresCopyService()

    def run(self, request: AresPlaybookRunRequest) -> AresPlaybookRunResult:
        exceptions: list[AresWorkflowException] = []
        scope = self._choose_scope(request)
        self._state_service.start_workflow(
            workflow_id=request.workflow_id,
            scope=scope,
            step_ids=self._STEP_IDS,
            initial_next_best_action="Pull probate and tax signals for selected scope",
        )
        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="choose_scope",
            status=AresWorkflowStepStatus.COMPLETED,
            detail=self._scope_detail(scope),
        )

        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="pull_signals",
            status=AresWorkflowStepStatus.IN_PROGRESS,
        )
        exception_count_before_pull = len(exceptions)
        probate_records, tax_records = self._pull_signals(request=request, scope=scope, exceptions=exceptions)
        if len(exceptions) == exception_count_before_pull:
            self._state_service.set_step_status(
                workflow_id=request.workflow_id,
                step_id="pull_signals",
                status=AresWorkflowStepStatus.COMPLETED,
                detail=f"Pulled {len(probate_records)} probate and {len(tax_records)} tax records",
            )

        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="enrich_and_score",
            status=AresWorkflowStepStatus.IN_PROGRESS,
        )
        ranked = self._matching_service.rank_leads(probate_records=probate_records, tax_records=tax_records)
        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="enrich_and_score",
            status=AresWorkflowStepStatus.COMPLETED,
            detail=f"Ranked {len(ranked)} leads",
        )

        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="generate_outreach",
            status=AresWorkflowStepStatus.IN_PROGRESS,
        )
        briefs = self._copy_service.generate_lead_briefs(ranked)
        drafts = self._copy_service.generate_outreach_drafts(ranked)
        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="generate_outreach",
            status=AresWorkflowStepStatus.COMPLETED,
            detail=f"Generated {len(drafts)} drafts",
        )

        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="create_follow_up_tasks",
            status=AresWorkflowStepStatus.IN_PROGRESS,
        )
        tasks = self._build_tasks(briefs=briefs, drafts=drafts)
        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="create_follow_up_tasks",
            status=AresWorkflowStepStatus.COMPLETED,
            detail=f"Created {len(tasks)} tasks",
        )

        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="monitor_responses",
            status=AresWorkflowStepStatus.IN_PROGRESS,
        )
        positive_responses = self._count_positive_responses(request.response_events)
        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="monitor_responses",
            status=AresWorkflowStepStatus.COMPLETED,
            detail=f"Positive responses: {positive_responses}",
        )

        next_action = self._suggest_next_action(
            positive_responses=positive_responses,
            draft_count=len(drafts),
            exception_count=len(exceptions),
        )
        self._state_service.set_step_status(
            workflow_id=request.workflow_id,
            step_id="suggest_next_action",
            status=AresWorkflowStepStatus.COMPLETED,
            detail=next_action,
        )
        self._state_service.update_next_best_action(
            workflow_id=request.workflow_id,
            next_best_action=next_action,
        )

        state = self._state_service.get_state(request.workflow_id)
        eval_report = self._eval_service.evaluate(state=state, exceptions=exceptions)

        return AresPlaybookRunResult(
            workflow_id=request.workflow_id,
            ranked_leads=tuple(ranked),
            briefs=tuple(briefs),
            drafts=tuple(drafts),
            follow_up_tasks=tuple(tasks),
            next_best_action=state.next_best_action,
            eval_report=eval_report,
        )

    def _choose_scope(self, request: AresPlaybookRunRequest) -> AresWorkflowScope:
        if request.counties:
            return AresWorkflowScope(counties=list(request.counties), market=request.market)
        if request.market:
            return AresWorkflowScope(counties=list(_DEFAULT_MARKET_COUNTIES), market=request.market)
        return AresWorkflowScope(counties=[AresCounty.HARRIS], market=None)

    def _pull_signals(
        self,
        *,
        request: AresPlaybookRunRequest,
        scope: AresWorkflowScope,
        exceptions: list[AresWorkflowException],
    ) -> tuple[list[AresLeadRecord], list[AresLeadRecord]]:
        probate_records: list[AresLeadRecord] = []
        tax_records: list[AresLeadRecord] = []
        for county in scope.counties:
            try:
                payload = self._county_fetcher(county)
            except Exception as exc:
                failure = self._state_service.record_retry_or_fallback(
                    workflow_id=request.workflow_id,
                    step_id="pull_signals",
                    reason=str(exc),
                    fallback_action="Escalate county fetch failure to operator",
                )
                exceptions.append(
                    self._eval_service.capture_exception(
                        workflow_id=request.workflow_id,
                        step_id="pull_signals",
                        message=f"{county.value}:{failure.reason}",
                    )
                )
                continue

            probate_records.extend(
                self._normalize_records(county=county, lane=AresSourceLane.PROBATE, records=payload.get("probate", ()))
            )
            tax_records.extend(
                self._normalize_records(
                    county=county,
                    lane=AresSourceLane.TAX_DELINQUENT,
                    records=payload.get("tax", ()),
                )
            )
        return probate_records, tax_records

    def _normalize_records(
        self,
        *,
        county: AresCounty,
        lane: AresSourceLane,
        records: Sequence[Mapping[str, object]],
    ) -> list[AresLeadRecord]:
        normalized: list[AresLeadRecord] = []
        for item in records:
            address = str(item.get("property_address", "")).strip()
            if not address:
                continue
            owner_name = item.get("owner_name")
            normalized.append(
                AresLeadRecord(
                    county=county,
                    source_lane=lane,
                    property_address=self._normalize_address(address),
                    owner_name=str(owner_name) if owner_name else None,
                )
            )
        return normalized

    def _build_tasks(
        self,
        *,
        briefs: Sequence[AresLeadBrief],
        drafts: Sequence[AresOutreachDraft],
    ) -> list[AresFollowUpTask]:
        tasks: list[AresFollowUpTask] = []
        for brief, draft in zip(briefs, drafts, strict=False):
            tasks.append(
                AresFollowUpTask(
                    task_type="human_approval",
                    rank=draft.rank,
                    county=draft.county,
                    title=f"Approve outreach draft for rank {draft.rank}: {brief.rationale}",
                )
            )
        return tasks

    @staticmethod
    def _count_positive_responses(response_events: tuple[str, ...]) -> int:
        positives = {"interested", "positive_reply", "call_booked"}
        return sum(1 for event in response_events if event in positives)

    @staticmethod
    def _suggest_next_action(*, positive_responses: int, draft_count: int, exception_count: int) -> str:
        if exception_count > 0:
            return "Escalate surfaced exceptions to operator review"
        if positive_responses > 0:
            return "Prioritize live follow-up for positive responders"
        if draft_count > 0:
            return "Route drafts to human approval queue"
        return "Refresh county slice and retry intake"

    @staticmethod
    def _normalize_address(address: str) -> str:
        return _ADDRESS_WHITESPACE_PATTERN.sub(" ", address).strip()

    @staticmethod
    def _scope_detail(scope: AresWorkflowScope) -> str:
        counties = ",".join(county.value for county in scope.counties) if scope.counties else "none"
        market = scope.market or "none"
        return f"Scope counties={counties} market={market}"

    @staticmethod
    def _default_county_fetcher(_county: AresCounty) -> CountyFetchPayload:
        return {"probate": (), "tax": ()}
