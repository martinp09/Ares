from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domains.ares import AresCounty
from app.services.ares_agent_registry_service import AresAgentRegistryService
from app.services.ares_eval_loop_service import AresEvalLoopService, AresEvalSample
from app.services.ares_memory_service import AresMemoryService
from app.services.ares_playbook_service import AresPlaybookRunRequest, AresPlaybookService
from app.services.ares_policy_service import AresPolicyDecision, AresPolicyService, AresToolPolicySpec


class _PolicyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_id: str = Field(min_length=1)


class _PolicyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)


class AresAutonomousOperatorPolicyCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class AresAutonomousOperatorRunSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    objective_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    market: str = Field(min_length=1)
    counties: list[str] = Field(default_factory=list)
    state: Literal["completed", "completed_with_escalation"]
    agent_name: str = Field(min_length=1)
    agent_revision: str = Field(min_length=1)
    playbook_workflow_id: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    adaptation_summary: str = Field(min_length=1)
    escalation_required: bool
    escalation_reason: str | None = None
    policy_checks: list[AresAutonomousOperatorPolicyCheck] = Field(default_factory=list)
    decision_log: list[str] = Field(default_factory=list)
    exception_log: list[str] = Field(default_factory=list)
    eval_metrics: dict[str, float] = Field(default_factory=dict)
    memory_counts: dict[str, int] = Field(default_factory=dict)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str


class AresAutonomousOperatorService:
    def __init__(
        self,
        *,
        agent_registry_service: AresAgentRegistryService | None = None,
        memory_service_factory: Callable[[str, str], AresMemoryService] | None = None,
        eval_loop_service_factory: Callable[[str, str], AresEvalLoopService] | None = None,
        runtime_root: Path | None = None,
    ) -> None:
        self._agent_registry = agent_registry_service or AresAgentRegistryService()
        self._runtime_root = runtime_root or Path("/tmp/ares-runtime")
        self._memory_service_factory = memory_service_factory or self._default_memory_service_factory
        self._eval_loop_service_factory = eval_loop_service_factory or self._default_eval_loop_service_factory

    def initialize_surface(self) -> None:
        self._agent_registry.register_revision(
            name="ares_guarded_operator",
            purpose="Run approved objectives with deterministic policy and escalation boundaries.",
            revision="v1",
            allowed_tools=(
                "county_fetch",
                "route_to_human_approval_queue",
                "record_metrics",
            ),
            risk_policy="hard_approval_required_for_send_contract_spend_and_market_expansion",
            output_contract="mission_control.autonomous_operator_snapshot.v1",
            set_active=True,
        )

    def run_approved_objective(
        self,
        *,
        objective_id: str,
        business_id: str,
        environment: str,
        market: str,
        counties: Iterable[AresCounty],
        county_payloads: Mapping[AresCounty, Mapping[str, list[dict[str, object]]]],
        response_events: tuple[str, ...],
    ) -> AresAutonomousOperatorRunSnapshot:
        self.initialize_surface()
        run_id = f"ares_op_{uuid4().hex[:12]}"
        selected_counties = tuple(counties)

        def county_fetcher(county: AresCounty) -> dict[str, list[dict[str, object]]]:
            payload = county_payloads.get(county, {"probate": [], "tax": []})
            return {
                "probate": [dict(record) for record in payload.get("probate", [])],
                "tax": [dict(record) for record in payload.get("tax", [])],
            }

        playbook = AresPlaybookService(county_fetcher=county_fetcher)
        playbook_result = playbook.run(
            AresPlaybookRunRequest(
                workflow_id=f"{run_id}_workflow",
                counties=selected_counties,
                market=market,
                response_events=response_events,
            )
        )

        policy_service = self._build_policy_service()
        policy_checks: list[AresAutonomousOperatorPolicyCheck] = []
        for tool_name, effects in (
            ("send_outreach", ("outreach_send",)),
            ("sign_contract", ("contract_sign",)),
            ("spend_funds", ("funds_spend",)),
            ("expand_market_scope", ("market_expansion",)),
        ):
            result = policy_service.evaluate_call(
                tool_name=tool_name,
                raw_input={"objective_id": objective_id},
                requested_effects=effects,
                hard_approval_id=None,
            )
            policy_checks.append(
                AresAutonomousOperatorPolicyCheck(
                    tool_name=tool_name,
                    decision=result.decision.value,
                    reason=result.reason,
                )
            )

        requires_approval_gate = any(check.decision == AresPolicyDecision.REQUIRE_APPROVAL.value for check in policy_checks)
        has_exceptions = playbook_result.eval_report.exception_count > 0
        escalation_required = has_exceptions or requires_approval_gate
        escalation_reason = (
            "Workflow exceptions surfaced during playbook execution"
            if has_exceptions
            else "High-risk actions remain behind hard approval gates"
        ) if escalation_required else None

        adaptation_summary = (
            "Paused and escalated for operator review after surfaced exceptions."
            if has_exceptions
            else "Adapted next action within bounded counties and routed risky actions to approval gates."
        )

        memory_service = self._memory_service_factory(business_id, environment)
        memory_service.load()
        for ranked in playbook_result.ranked_leads:
            memory_service.record_lead_history(
                {
                    "run_id": run_id,
                    "rank": ranked.rank,
                    "tier": ranked.tier.name,
                    "county": ranked.lead.county.value,
                    "source_lane": ranked.lead.source_lane.value,
                }
            )
        for draft in playbook_result.drafts:
            memory_service.record_outreach_history(
                {
                    "run_id": run_id,
                    "rank": draft.rank,
                    "county": draft.county.value,
                    "approval_status": draft.approval_status,
                }
            )
        memory_service.record_operator_decision(
            {
                "run_id": run_id,
                "objective_id": objective_id,
                "decision": "escalate" if escalation_required else "continue",
                "reason": escalation_reason or "No escalation required",
                "next_action": playbook_result.next_best_action,
            }
        )
        memory_service.record_outcome(
            {
                "run_id": run_id,
                "objective_id": objective_id,
                "state": "completed_with_escalation" if escalation_required else "completed",
                "lead_count": len(playbook_result.ranked_leads),
                "workflow_id": playbook_result.workflow_id,
            }
        )
        for exception_message in playbook_result.eval_report.surfaced_exceptions:
            memory_service.record_exception(
                {
                    "run_id": run_id,
                    "workflow_id": playbook_result.workflow_id,
                    "message": exception_message,
                }
            )
        memory_service.save()
        memory_snapshot = memory_service.snapshot()

        eval_loop_service = self._eval_loop_service_factory(business_id, environment)
        eval_loop_service.load()
        eval_result = eval_loop_service.evaluate_and_record(
            run_id=run_id,
            sample=AresEvalSample(
                leads_reviewed=len(playbook_result.ranked_leads),
                qualified_leads=len(playbook_result.ranked_leads),
                responses_sent=len(playbook_result.drafts),
                quality_responses=max(0, len(response_events) - playbook_result.eval_report.exception_count),
                conversion_opportunities=len(playbook_result.follow_up_tasks),
                successful_conversions=min(1, len(response_events)),
                false_positives=playbook_result.eval_report.exception_count,
                duplicate_work_items=0,
                operator_corrections=(1 if escalation_required else 0),
            ),
        )
        eval_loop_service.save()

        decision_log = [
            f"Objective {objective_id} executed in market {market} for counties: {', '.join(county.value for county in selected_counties)}",
            f"Playbook next action: {playbook_result.next_best_action}",
            "Risky actions remain policy-gated and require hard approval.",
        ]
        exception_log = list(playbook_result.eval_report.surfaced_exceptions)

        snapshot = AresAutonomousOperatorRunSnapshot(
            run_id=run_id,
            objective_id=objective_id,
            business_id=business_id,
            environment=environment,
            market=market,
            counties=[county.value for county in selected_counties],
            state=("completed_with_escalation" if escalation_required else "completed"),
            agent_name="ares_guarded_operator",
            agent_revision="v1",
            playbook_workflow_id=playbook_result.workflow_id,
            next_action=playbook_result.next_best_action,
            adaptation_summary=adaptation_summary,
            escalation_required=escalation_required,
            escalation_reason=escalation_reason,
            policy_checks=policy_checks,
            decision_log=decision_log,
            exception_log=exception_log,
            eval_metrics=eval_result.metrics.model_dump(mode="json"),
            memory_counts={
                "lead_history": len(memory_snapshot.lead_history),
                "outreach_history": len(memory_snapshot.outreach_history),
                "operator_decisions": len(memory_snapshot.operator_decisions),
                "outcomes": len(memory_snapshot.outcomes),
                "exceptions": len(memory_snapshot.exceptions),
            },
            audit_log=[entry.model_dump(mode="json") for entry in policy_service.audit_trail()],
            generated_at=eval_result.recorded_at.isoformat(),
        )
        return snapshot

    def _build_policy_service(self) -> AresPolicyService:
        return AresPolicyService(
            policies=[
                AresToolPolicySpec(
                    tool_name="county_fetch",
                    input_model=_PolicyInput,
                    output_model=_PolicyOutput,
                    declared_effects=(),
                    requires_hard_approval=False,
                ),
                AresToolPolicySpec(
                    tool_name="send_outreach",
                    input_model=_PolicyInput,
                    output_model=_PolicyOutput,
                    declared_effects=("outreach_send",),
                    requires_hard_approval=True,
                ),
                AresToolPolicySpec(
                    tool_name="sign_contract",
                    input_model=_PolicyInput,
                    output_model=_PolicyOutput,
                    declared_effects=("contract_sign",),
                    requires_hard_approval=True,
                ),
                AresToolPolicySpec(
                    tool_name="spend_funds",
                    input_model=_PolicyInput,
                    output_model=_PolicyOutput,
                    declared_effects=("funds_spend",),
                    requires_hard_approval=True,
                ),
                AresToolPolicySpec(
                    tool_name="expand_market_scope",
                    input_model=_PolicyInput,
                    output_model=_PolicyOutput,
                    declared_effects=("market_expansion",),
                    requires_hard_approval=True,
                ),
            ]
        )

    def _default_memory_service_factory(self, business_id: str, environment: str) -> AresMemoryService:
        scope = f"{business_id}-{environment}".replace("/", "-")
        return AresMemoryService(self._runtime_root / f"{scope}-memory.json")

    def _default_eval_loop_service_factory(self, business_id: str, environment: str) -> AresEvalLoopService:
        scope = f"{business_id}-{environment}".replace("/", "-")
        return AresEvalLoopService(self._runtime_root / f"{scope}-eval-loop.json")


autonomous_operator_service = AresAutonomousOperatorService()
