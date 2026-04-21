from __future__ import annotations

from collections.abc import Callable, Mapping

from pydantic import BaseModel, ConfigDict

from app.db.client import STORE, reset_control_plane_store, utc_now
from app.models.approvals import ApprovalRecord, ApprovalStatus

from app.domains.ares import AresCounty
from app.services.ares_execution_service import (
    AresExecutionActionSpec,
    AresExecutionDecision,
    AresExecutionRunSpec,
    AresExecutionService,
)
from app.services.ares_policy_service import AresPolicyService, AresToolPolicySpec


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str


class StubCountyFetcher:
    def __init__(
        self,
        responses: Mapping[AresCounty, Mapping[str, list[Mapping[str, object]]]],
        failures: Mapping[AresCounty, str] | None = None,
    ) -> None:
        self._responses = dict(responses)
        self._failures = dict(failures or {})
        self.calls: list[AresCounty] = []

    def __call__(self, county: AresCounty) -> Mapping[str, list[Mapping[str, object]]]:
        self.calls.append(county)
        if county in self._failures:
            raise RuntimeError(self._failures[county])
        return self._responses[county]


def _service(fetcher: Callable[[AresCounty], Mapping[str, list[Mapping[str, object]]]]) -> AresExecutionService:
    policy = AresPolicyService(
        policies=[
            AresToolPolicySpec(
                tool_name="lookup_lead",
                input_model=ToolInput,
                output_model=ToolOutput,
                declared_effects=(),
                requires_hard_approval=False,
            ),
        ]
    )
    return AresExecutionService(policy_service=policy, county_fetcher=fetcher)


def _run_spec() -> AresExecutionRunSpec:
    return AresExecutionRunSpec(
        run_id="run-1",
        business_id="limitless",
        environment="dev",
        market="houston",
        counties=[AresCounty.HARRIS, AresCounty.DALLAS],
        action_budget=3,
        retry_limit=1,
        approved_tools=("lookup_lead",),
    )


def test_execution_service_fetches_normalizes_dedupes_and_enriches_records() -> None:
    fetcher = StubCountyFetcher(
        {
            AresCounty.HARRIS: {
                "probate": [
                    {"property_address": " 123 Main   St  ", "owner_name": ""},
                    {"property_address": "123 main st", "owner_name": "Estate Of Jane Doe"},
                    {"property_address": "789 Pine St", "owner_name": "Bob Ray"},
                ],
                "tax": [
                    {"property_address": "123 MAIN ST", "owner_name": "Estate of Jane Doe"},
                    {"property_address": "456 Oak Ave", "owner_name": "Alice Stone"},
                    {"property_address": " 456  Oak Ave ", "owner_name": "Alice Stone"},
                ],
            },
            AresCounty.DALLAS: {
                "probate": [],
                "tax": [],
            },
        }
    )
    service = _service(fetcher)
    service.register_run(_run_spec())

    result = service.execute_bounded_run(run_id="run-1")

    assert result.failures == []
    assert result.interrupted is False
    assert len(result.normalized_probate_records) == 2
    assert len(result.normalized_tax_records) == 2

    first_probate = result.normalized_probate_records[0]
    assert first_probate.property_address == "123 Main St"
    assert first_probate.owner_name == "Estate Of Jane Doe"
    assert first_probate.estate_of is True


def test_execution_service_runs_overlay_matching_and_returns_ranked_outputs() -> None:
    fetcher = StubCountyFetcher(
        {
            AresCounty.HARRIS: {
                "probate": [
                    {"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"},
                    {"property_address": "789 Pine St", "owner_name": "Bob Ray"},
                ],
                "tax": [
                    {"property_address": "123 Main St", "owner_name": "Estate of Jane Doe"},
                ],
            },
            AresCounty.DALLAS: {
                "probate": [],
                "tax": [],
            },
        }
    )
    service = _service(fetcher)
    service.register_run(_run_spec())

    result = service.execute_bounded_run(run_id="run-1")

    assert [item.rank for item in result.ranked_leads] == [1, 2]
    assert result.ranked_leads[0].tax_delinquent is True
    assert result.ranked_leads[1].tax_delinquent is False
    assert len(result.briefs) == 2
    assert len(result.drafts) == 2


def test_execution_service_generates_task_suggestions_and_follow_up_queue() -> None:
    fetcher = StubCountyFetcher(
        {
            AresCounty.HARRIS: {
                "probate": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
                "tax": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
            },
            AresCounty.DALLAS: {
                "probate": [],
                "tax": [],
            },
        }
    )
    service = _service(fetcher)
    service.register_run(_run_spec())

    result = service.execute_bounded_run(run_id="run-1")

    assert len(result.task_suggestions) == 2
    assert result.task_suggestions[0].task_type == "review_lead_brief"
    assert result.task_suggestions[1].task_type == "review_outreach_draft"
    assert len(result.follow_up_work_queue) == 2
    assert result.follow_up_work_queue[0].work_type == "operator_review"
    assert result.follow_up_work_queue[1].work_type == "draft_approval"


def test_execution_service_keeps_failures_visible_and_recoverable() -> None:
    first_fetcher = StubCountyFetcher(
        {
            AresCounty.HARRIS: {
                "probate": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
                "tax": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
            },
            AresCounty.DALLAS: {
                "probate": [{"property_address": "100 Elm St", "owner_name": "Estate Of Ann Example"}],
                "tax": [{"property_address": "100 Elm St", "owner_name": "Estate Of Ann Example"}],
            },
        },
        failures={AresCounty.DALLAS: "county datasource timeout"},
    )
    service = _service(first_fetcher)
    service.register_run(_run_spec())

    first_result = service.execute_bounded_run(run_id="run-1")

    assert len(first_result.failures) == 1
    assert first_result.failures[0].county == AresCounty.DALLAS
    assert "timeout" in first_result.failures[0].reason
    assert first_result.ranked_leads

    recovery_fetcher = StubCountyFetcher(
        {
            AresCounty.HARRIS: {
                "probate": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
                "tax": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
            },
            AresCounty.DALLAS: {
                "probate": [{"property_address": "100 Elm St", "owner_name": "Estate Of Ann Example"}],
                "tax": [{"property_address": "100 Elm St", "owner_name": "Estate Of Ann Example"}],
            },
        }
    )
    service.set_county_fetcher(recovery_fetcher)

    recovered = service.execute_bounded_run(run_id="run-1")

    assert recovered.failures == []
    assert len(recovered.ranked_leads) == 2


def test_execution_service_run_is_interruptible_via_kill_switch() -> None:
    fetcher = StubCountyFetcher(
        {
            AresCounty.HARRIS: {
                "probate": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
                "tax": [{"property_address": "123 Main St", "owner_name": "Estate Of Jane Doe"}],
            },
            AresCounty.DALLAS: {
                "probate": [{"property_address": "100 Elm St", "owner_name": "Estate Of Ann Example"}],
                "tax": [{"property_address": "100 Elm St", "owner_name": "Estate Of Ann Example"}],
            },
        }
    )
    service = _service(fetcher)
    service.register_run(_run_spec())

    service.set_kill_switch(enabled=True, reason="operator halt")
    blocked = service.execute_bounded_run(run_id="run-1")

    assert blocked.interrupted is True
    assert blocked.ranked_leads == []
    assert blocked.failures == []


def test_execution_guardrails_still_enforce_budget_retry_and_allowlist() -> None:
    fetcher = StubCountyFetcher({AresCounty.HARRIS: {"probate": [], "tax": []}, AresCounty.DALLAS: {"probate": [], "tax": []}})
    service = _service(fetcher)
    service.register_run(_run_spec())

    allowed = service.authorize_action(
        run_id="run-1",
        action=AresExecutionActionSpec(
            action_id="step-1",
            tool_name="lookup_lead",
            raw_input={"lead_id": "lead-1"},
            requested_effects=(),
            attempt=0,
        ),
    )
    assert allowed.decision is AresExecutionDecision.ALLOW

    denied_retry = service.authorize_action(
        run_id="run-1",
        action=AresExecutionActionSpec(
            action_id="step-1",
            tool_name="lookup_lead",
            raw_input={"lead_id": "lead-1"},
            requested_effects=(),
            attempt=2,
        ),
    )
    assert denied_retry.decision is AresExecutionDecision.DENY

    denied_tool = service.authorize_action(
        run_id="run-1",
        action=AresExecutionActionSpec(
            action_id="step-2",
            tool_name="send_outreach",
            raw_input={"lead_id": "lead-2"},
            requested_effects=(),
            attempt=0,
        ),
    )
    assert denied_tool.decision is AresExecutionDecision.DENY


def test_execution_guardrails_do_not_allow_reusing_same_action_id_to_bypass_budget() -> None:
    fetcher = StubCountyFetcher({AresCounty.HARRIS: {"probate": [], "tax": []}, AresCounty.DALLAS: {"probate": [], "tax": []}})
    service = _service(fetcher)
    run = _run_spec().model_copy(update={"action_budget": 1})
    service.register_run(run)

    first = service.authorize_action(
        run_id="run-1",
        action=AresExecutionActionSpec(
            action_id="same-action",
            tool_name="lookup_lead",
            raw_input={"lead_id": "lead-1"},
            requested_effects=(),
            attempt=0,
        ),
    )
    second = service.authorize_action(
        run_id="run-1",
        action=AresExecutionActionSpec(
            action_id="same-action",
            tool_name="lookup_lead",
            raw_input={"lead_id": "lead-1"},
            requested_effects=(),
            attempt=1,
        ),
    )

    assert first.decision is AresExecutionDecision.ALLOW
    assert second.decision is AresExecutionDecision.DENY


def test_execution_guardrails_reject_hard_approval_from_other_scope() -> None:
    reset_control_plane_store(STORE)
    fetcher = StubCountyFetcher({AresCounty.HARRIS: {"probate": [], "tax": []}, AresCounty.DALLAS: {"probate": [], "tax": []}})
    policy = AresPolicyService(
        policies=[
            AresToolPolicySpec(
                tool_name="lookup_lead",
                input_model=ToolInput,
                output_model=ToolOutput,
                declared_effects=(),
                requires_hard_approval=False,
            ),
            AresToolPolicySpec(
                tool_name="send_outreach",
                input_model=ToolInput,
                output_model=ToolOutput,
                declared_effects=("send_message",),
                requires_hard_approval=True,
            ),
        ]
    )
    service = AresExecutionService(policy_service=policy, county_fetcher=fetcher)
    run = _run_spec().model_copy(update={"approved_tools": ("lookup_lead", "send_outreach")})
    service.register_run(run)
    STORE.approvals["apr-other-scope"] = ApprovalRecord(
        id="apr-other-scope",
        command_id="cmd-9",
        business_id="other-biz",
        environment="prod",
        command_type="send_outreach",
        status=ApprovalStatus.APPROVED,
        payload_snapshot={},
        created_at=utc_now(),
        approved_at=utc_now(),
        actor_id="tester",
    )

    decision = service.authorize_action(
        run_id="run-1",
        action=AresExecutionActionSpec(
            action_id="send-1",
            tool_name="send_outreach",
            raw_input={"lead_id": "lead-1"},
            requested_effects=("send_message",),
            attempt=0,
            hard_approval_id=" apr-other-scope ",
        ),
    )

    assert decision.decision is AresExecutionDecision.DENY
    assert "Hard approval required" in decision.reason
