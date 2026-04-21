from __future__ import annotations

from typing import Iterable, Literal
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.ares import AresCounty, AresExecutionRunSpec, AresLeadRecord, AresRunRequest, AresSourceLane
from app.db.client import get_control_plane_client, utc_now
from app.services.ares_copy_service import AresCopyService
from app.services.ares_execution_service import AresExecutionService
from app.services.ares_autonomous_operator_service import autonomous_operator_service
from app.services.ares_playbook_service import AresPlaybookRunRequest, AresPlaybookService
from app.services.ares_planner_service import AresPlannerService
from app.services.ares_policy_service import AresPolicyDecision, AresPolicyService, AresToolPolicySpec
from app.services.ares_service import AresMatchingService

router = APIRouter(prefix="/ares", tags=["ares"])

_matching_service = AresMatchingService()
_copy_service = AresCopyService()
_planner_service = AresPlannerService()
_control_plane_client = get_control_plane_client()


class AresRuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run: AresRunRequest = Field(default_factory=AresRunRequest)
    probate_records: list[AresLeadRecord] = Field(default_factory=list)
    tax_records: list[AresLeadRecord] = Field(default_factory=list)


class AresLeadBriefResponse(BaseModel):
    rank: int
    county: AresCounty
    source_lane: AresSourceLane
    rationale: str
    brief: str


class AresOutreachDraftResponse(BaseModel):
    rank: int
    county: AresCounty
    source_lane: AresSourceLane
    rationale: str
    approval_status: str
    auto_send: bool
    subject: str
    body: str


class AresRankedLeadResponse(BaseModel):
    rank: int
    tier: str
    tax_delinquent: bool
    lead: AresLeadRecord
    brief: AresLeadBriefResponse | None = None
    draft: AresOutreachDraftResponse | None = None


class AresRuntimeResponse(BaseModel):
    counties: list[AresCounty]
    include_briefs: bool
    include_drafts: bool
    lead_count: int
    ranked_leads: list[AresRankedLeadResponse]


class AresPlannerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=1)
    business_id: str = Field(default="limitless", min_length=1)
    environment: str = Field(default="dev", min_length=1)

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("String should have at least 1 character")
        return normalized


class AresPlannerResponse(BaseModel):
    business_id: str
    environment: str
    goal: str
    explanation: str
    plan: dict[str, object]
    generated_at: str


class AresExecutionCountyRecordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_address: str = Field(min_length=1)
    owner_name: str | None = None
    estate_of: bool = False


class AresExecutionCountyPayloadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    probate: list[AresExecutionCountyRecordRequest] = Field(default_factory=list)
    tax: list[AresExecutionCountyRecordRequest] = Field(default_factory=list)


class AresExecutionRuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(default="limitless", min_length=1)
    environment: str = Field(default="dev", min_length=1)
    market: str = Field(min_length=1)
    counties: list[AresCounty] = Field(min_length=1, max_length=2)
    action_budget: int = Field(ge=1, le=20)
    retry_limit: int = Field(ge=0, le=3)
    approved_tools: tuple[str, ...] = Field(min_length=1)
    county_payloads: dict[AresCounty, AresExecutionCountyPayloadRequest] = Field(default_factory=dict)


class AresExecutionFailureResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    county: AresCounty | None
    stage: str
    reason: str


class AresExecutionTaskSuggestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_type: str
    rank: int
    county: AresCounty
    title: str
    reason: str


class AresExecutionFollowUpWorkResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_type: str
    rank: int
    county: AresCounty
    payload: dict[str, object]


class AresExecutionRuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    business_id: str
    environment: str
    market: str
    counties: list[AresCounty]
    state: str
    interrupted: bool
    lead_count: int
    failures: list[AresExecutionFailureResponse] = Field(default_factory=list)
    ranked_leads: list[AresRankedLeadResponse] = Field(default_factory=list)
    task_suggestions: list[AresExecutionTaskSuggestionResponse] = Field(default_factory=list)
    follow_up_work_queue: list[AresExecutionFollowUpWorkResponse] = Field(default_factory=list)
    high_risk_policy_checks: list["AresExecutionHighRiskPolicyCheckResponse"] = Field(default_factory=list)
    workflow_eval: "AresExecutionWorkflowEvalResponse"
    drift_detection: "AresExecutionDriftDetectionResponse"
    major_decisions: list[str] = Field(default_factory=list)
    major_failures: list[str] = Field(default_factory=list)
    generated_at: str


class AresOperatorRuntimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_id: str = Field(min_length=1)
    objective_status: Literal["approved"]
    business_id: str = Field(default="limitless", min_length=1)
    environment: str = Field(default="dev", min_length=1)
    market: str = Field(min_length=1)
    counties: list[AresCounty] = Field(min_length=1, max_length=2)
    county_payloads: dict[AresCounty, AresExecutionCountyPayloadRequest] = Field(default_factory=dict)
    response_events: tuple[str, ...] = Field(default_factory=tuple)


class AresOperatorPolicyCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class AresOperatorRuntimeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    objective_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    market: str = Field(min_length=1)
    counties: list[AresCounty] = Field(default_factory=list)
    state: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    agent_revision: str = Field(min_length=1)
    playbook_workflow_id: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    adaptation_summary: str = Field(min_length=1)
    escalation_required: bool
    escalation_reason: str | None = None
    policy_checks: list[AresOperatorPolicyCheckResponse] = Field(default_factory=list)
    decision_log: list[str] = Field(default_factory=list)
    exception_log: list[str] = Field(default_factory=list)
    eval_metrics: dict[str, float] = Field(default_factory=dict)
    memory_counts: dict[str, int] = Field(default_factory=dict)
    audit_log: list[dict[str, object]] = Field(default_factory=list)
    generated_at: str


class AresExecutionHighRiskPolicyCheckResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    requires_human_approval: bool


class AresExecutionWorkflowEvalResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(min_length=1)
    exception_count: int = Field(ge=0)
    surfaced_exceptions: list[str] = Field(default_factory=list)
    suggested_next_action: str = Field(min_length=1)


class AresExecutionDriftDetectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected: bool
    reason: str = Field(min_length=1)


class _AresExecutionPolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str = Field(min_length=1)


class _AresExecutionPolicyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)


def _build_execution_policy_service() -> AresPolicyService:
    return AresPolicyService(
        policies=[
            AresToolPolicySpec(
                tool_name="county_fetch",
                input_model=_AresExecutionPolicyInput,
                output_model=_AresExecutionPolicyOutput,
                declared_effects=(),
                requires_hard_approval=False,
            ),
            AresToolPolicySpec(
                tool_name="send_outreach",
                input_model=_AresExecutionPolicyInput,
                output_model=_AresExecutionPolicyOutput,
                declared_effects=("outreach_send",),
                requires_hard_approval=True,
            ),
            AresToolPolicySpec(
                tool_name="create_contract",
                input_model=_AresExecutionPolicyInput,
                output_model=_AresExecutionPolicyOutput,
                declared_effects=("contract_generation",),
                requires_hard_approval=True,
            ),
            AresToolPolicySpec(
                tool_name="send_disposition_packet",
                input_model=_AresExecutionPolicyInput,
                output_model=_AresExecutionPolicyOutput,
                declared_effects=("disposition_send",),
                requires_hard_approval=True,
            ),
        ]
    )


def _detect_execution_drift(*, previous_snapshot: dict[str, object] | None, lead_count: int, failure_count: int) -> tuple[bool, str]:
    if previous_snapshot is None:
        return False, "No prior execution run in this scope."

    previous_lead_count = int(previous_snapshot.get("lead_count", 0))
    previous_failure_count = int(previous_snapshot.get("failure_count", 0))
    if lead_count != previous_lead_count:
        return True, f"Lead count changed from {previous_lead_count} to {lead_count}."
    if failure_count != previous_failure_count:
        return True, f"Failure count changed from {previous_failure_count} to {failure_count}."
    return False, "No drift from previous scoped execution run."


def _filter_by_counties(records: Iterable[AresLeadRecord], counties: list[AresCounty]) -> list[AresLeadRecord]:
    if not counties:
        return list(records)
    allowed = set(counties)
    return [record for record in records if record.county in allowed]


@router.post("/run", response_model=AresRuntimeResponse)
def run_ares_runtime(request: AresRuntimeRequest) -> AresRuntimeResponse:
    probate_records = _filter_by_counties(request.probate_records, request.run.counties)
    tax_records = _filter_by_counties(request.tax_records, request.run.counties)
    ranked = _matching_service.rank_leads(probate_records=probate_records, tax_records=tax_records)

    briefs_by_rank: dict[int, AresLeadBriefResponse] = {}
    drafts_by_rank: dict[int, AresOutreachDraftResponse] = {}

    if request.run.include_briefs:
        briefs_by_rank = {
            brief.rank: AresLeadBriefResponse(**brief.__dict__)
            for brief in _copy_service.generate_lead_briefs(ranked)
        }
    if request.run.include_drafts:
        drafts_by_rank = {
            draft.rank: AresOutreachDraftResponse(**draft.__dict__)
            for draft in _copy_service.generate_outreach_drafts(ranked)
        }

    ranked_response = [
        AresRankedLeadResponse(
            rank=item.rank,
            tier=item.tier.name,
            tax_delinquent=item.tax_delinquent,
            lead=item.lead,
            brief=briefs_by_rank.get(item.rank),
            draft=drafts_by_rank.get(item.rank),
        )
        for item in ranked
    ]

    return AresRuntimeResponse(
        counties=request.run.counties,
        include_briefs=request.run.include_briefs,
        include_drafts=request.run.include_drafts,
        lead_count=len(ranked_response),
        ranked_leads=ranked_response,
    )


@router.post("/plans", response_model=AresPlannerResponse)
def plan_ares_runtime(request: AresPlannerRequest) -> AresPlannerResponse:
    plan = _planner_service.build_plan(goal=request.goal)
    explanation = _planner_service.explain_plan(plan)
    generated_at = utc_now()
    snapshot = {
        "business_id": request.business_id,
        "environment": request.environment,
        "goal": request.goal,
        "explanation": explanation,
        "plan": plan.model_dump(mode="json"),
        "generated_at": generated_at.isoformat(),
    }
    with _control_plane_client.transaction() as store:
        store.ares_plans_by_scope[(request.business_id, request.environment)] = snapshot

    return AresPlannerResponse(
        business_id=request.business_id,
        environment=request.environment,
        goal=request.goal,
        explanation=explanation,
        plan=plan.model_dump(mode="json"),
        generated_at=generated_at.isoformat(),
    )


@router.post("/execution/run", response_model=AresExecutionRuntimeResponse)
def execute_ares_bounded_runtime(request: AresExecutionRuntimeRequest) -> AresExecutionRuntimeResponse:
    run_id = f"ares_exec_{uuid4().hex[:12]}"

    def county_fetcher(county: AresCounty) -> dict[str, list[dict[str, object]]]:
        payload = request.county_payloads.get(county, AresExecutionCountyPayloadRequest())
        return {
            "probate": [record.model_dump(mode="json") for record in payload.probate],
            "tax": [record.model_dump(mode="json") for record in payload.tax],
        }

    policy_service = _build_execution_policy_service()
    execution_service = AresExecutionService(policy_service=policy_service, county_fetcher=county_fetcher)
    execution_service.register_run(
        AresExecutionRunSpec(
            run_id=run_id,
            business_id=request.business_id,
            environment=request.environment,
            market=request.market,
            counties=request.counties,
            action_budget=request.action_budget,
            retry_limit=request.retry_limit,
            approved_tools=request.approved_tools,
        )
    )
    result = execution_service.execute_bounded_run(run_id=run_id)
    workflow_result = AresPlaybookService(county_fetcher=county_fetcher).run(
        AresPlaybookRunRequest(workflow_id=f"{run_id}_workflow", counties=tuple(request.counties))
    )

    briefs_by_rank = {brief.rank: brief for brief in result.briefs}
    drafts_by_rank = {draft.rank: draft for draft in result.drafts}
    ranked_response = [
        AresRankedLeadResponse(
            rank=item.rank,
            tier=item.tier.name,
            tax_delinquent=item.tax_delinquent,
            lead=item.lead,
            brief=(
                AresLeadBriefResponse(**briefs_by_rank[item.rank].__dict__)
                if item.rank in briefs_by_rank
                else None
            ),
            draft=(
                AresOutreachDraftResponse(**drafts_by_rank[item.rank].__dict__)
                if item.rank in drafts_by_rank
                else None
            ),
        )
        for item in result.ranked_leads
    ]
    generated_at = utc_now().isoformat()
    if result.interrupted:
        state = "interrupted"
    elif result.failures:
        state = "completed_with_failures"
    else:
        state = "completed"

    high_risk_policy_checks: list[AresExecutionHighRiskPolicyCheckResponse] = []
    for tool_name, effects in (
        ("send_outreach", ("outreach_send",)),
        ("create_contract", ("contract_generation",)),
        ("send_disposition_packet", ("disposition_send",)),
    ):
        decision = policy_service.evaluate_call(
            tool_name=tool_name,
            raw_input={"lead_id": run_id},
            requested_effects=effects,
            hard_approval_id=None,
        )
        high_risk_policy_checks.append(
            AresExecutionHighRiskPolicyCheckResponse(
                tool_name=tool_name,
                decision=decision.decision.value,
                reason=decision.reason,
                requires_human_approval=decision.decision is AresPolicyDecision.REQUIRE_APPROVAL,
            )
        )

    workflow_eval = AresExecutionWorkflowEvalResponse(
        workflow_id=workflow_result.eval_report.workflow_id,
        exception_count=workflow_result.eval_report.exception_count,
        surfaced_exceptions=list(workflow_result.eval_report.surfaced_exceptions),
        suggested_next_action=workflow_result.eval_report.suggested_next_action,
    )

    scope_key = (request.business_id, request.environment)
    with _control_plane_client.transaction() as store:
        previous_snapshot = store.ares_execution_runs_by_scope.get(scope_key)

    drift_detected, drift_reason = _detect_execution_drift(
        previous_snapshot=previous_snapshot,
        lead_count=len(ranked_response),
        failure_count=len(result.failures),
    )
    drift_detection = AresExecutionDriftDetectionResponse(detected=drift_detected, reason=drift_reason)
    major_decisions = [
        f"Execution scope ran for counties: {','.join(county.value for county in request.counties)}.",
        f"Workflow next action: {workflow_result.next_best_action}",
        "High-risk steps (send, contract, disposition) require hard approval before execution.",
    ]
    major_failures = [f"{failure.stage}:{failure.reason}" for failure in result.failures]
    major_failures.extend(workflow_eval.surfaced_exceptions)

    snapshot = {
        "run_id": run_id,
        "business_id": request.business_id,
        "environment": request.environment,
        "market": request.market,
        "counties": [county.value for county in request.counties],
        "state": state,
        "interrupted": result.interrupted,
        "lead_count": len(ranked_response),
        "failure_count": len(result.failures),
        "high_risk_policy_checks": [item.model_dump(mode="json") for item in high_risk_policy_checks],
        "workflow_eval": workflow_eval.model_dump(mode="json"),
        "drift_detection": drift_detection.model_dump(mode="json"),
        "major_decisions": major_decisions,
        "major_failures": major_failures,
        "ranked_leads": [
            {
                "rank": item.rank,
                "tier": item.tier.name,
                "tax_delinquent": item.tax_delinquent,
                "county": item.lead.county.value,
                "source_lane": item.lead.source_lane.value,
            }
            for item in result.ranked_leads
        ],
        "generated_at": generated_at,
    }
    with _control_plane_client.transaction() as store:
        store.ares_execution_runs_by_scope[scope_key] = snapshot

    return AresExecutionRuntimeResponse(
        run_id=run_id,
        business_id=request.business_id,
        environment=request.environment,
        market=request.market,
        counties=request.counties,
        state=state,
        interrupted=result.interrupted,
        lead_count=len(ranked_response),
        failures=[AresExecutionFailureResponse(**failure.model_dump(mode="json")) for failure in result.failures],
        ranked_leads=ranked_response,
        task_suggestions=[
            AresExecutionTaskSuggestionResponse(
                task_type=item.task_type,
                rank=item.rank,
                county=item.county,
                title=item.title,
                reason=item.reason,
            )
            for item in result.task_suggestions
        ],
        follow_up_work_queue=[
            AresExecutionFollowUpWorkResponse(
                work_type=item.work_type,
                rank=item.rank,
                county=item.county,
                payload=item.payload,
            )
            for item in result.follow_up_work_queue
        ],
        high_risk_policy_checks=high_risk_policy_checks,
        workflow_eval=workflow_eval,
        drift_detection=drift_detection,
        major_decisions=major_decisions,
        major_failures=major_failures,
        generated_at=generated_at,
    )


@router.post("/operator/run", response_model=AresOperatorRuntimeResponse)
def run_ares_guarded_operator(request: AresOperatorRuntimeRequest) -> AresOperatorRuntimeResponse:
    snapshot = autonomous_operator_service.run_approved_objective(
        objective_id=request.objective_id,
        business_id=request.business_id,
        environment=request.environment,
        market=request.market,
        counties=request.counties,
        county_payloads={
            county: {
                "probate": [record.model_dump(mode="json") for record in payload.probate],
                "tax": [record.model_dump(mode="json") for record in payload.tax],
            }
            for county, payload in request.county_payloads.items()
        },
        response_events=request.response_events,
    )

    with _control_plane_client.transaction() as store:
        store.ares_operator_runs_by_scope[(request.business_id, request.environment)] = snapshot.model_dump(mode="json")

    return AresOperatorRuntimeResponse(
        run_id=snapshot.run_id,
        objective_id=snapshot.objective_id,
        business_id=snapshot.business_id,
        environment=snapshot.environment,
        market=snapshot.market,
        counties=[AresCounty(county) for county in snapshot.counties],
        state=snapshot.state,
        agent_name=snapshot.agent_name,
        agent_revision=snapshot.agent_revision,
        playbook_workflow_id=snapshot.playbook_workflow_id,
        next_action=snapshot.next_action,
        adaptation_summary=snapshot.adaptation_summary,
        escalation_required=snapshot.escalation_required,
        escalation_reason=snapshot.escalation_reason,
        policy_checks=[AresOperatorPolicyCheckResponse(**check.model_dump(mode="json")) for check in snapshot.policy_checks],
        decision_log=list(snapshot.decision_log),
        exception_log=list(snapshot.exception_log),
        eval_metrics=dict(snapshot.eval_metrics),
        memory_counts=dict(snapshot.memory_counts),
        audit_log=list(snapshot.audit_log),
        generated_at=snapshot.generated_at,
    )
