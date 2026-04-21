from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from app.db.client import STORE, reset_control_plane_store, utc_now
from app.models.approvals import ApprovalRecord, ApprovalStatus
from app.services.ares_policy_service import (
    AresPolicyAuditAction,
    AresPolicyDecision,
    AresPolicyService,
    AresToolPolicySpec,
)


class LookupInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_id: str


class LookupOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str


def _policy_service() -> AresPolicyService:
    service = AresPolicyService(
        policies=[
            AresToolPolicySpec(
                tool_name="lookup_lead",
                input_model=LookupInput,
                output_model=LookupOutput,
                declared_effects=(),
                requires_hard_approval=False,
            ),
            AresToolPolicySpec(
                tool_name="send_outreach",
                input_model=LookupInput,
                output_model=LookupOutput,
                declared_effects=("send_message",),
                requires_hard_approval=True,
            ),
        ]
    )
    return service


def test_policy_enforces_explicit_tool_allowlist() -> None:
    service = _policy_service()

    decision = service.evaluate_call(
        tool_name="unknown_tool",
        raw_input={"lead_id": "lead-1"},
    )

    assert decision.decision is AresPolicyDecision.DENY
    assert "not allowlisted" in decision.reason


def test_policy_enforces_typed_input_output_contracts() -> None:
    service = _policy_service()

    allowed = service.evaluate_call(
        tool_name="lookup_lead",
        raw_input={"lead_id": "lead-1"},
    )
    assert allowed.decision is AresPolicyDecision.ALLOW

    typed_output = service.validate_output(
        tool_name="lookup_lead",
        raw_output={"summary": "Lead is probate verified"},
    )
    assert typed_output.summary == "Lead is probate verified"


def test_policy_blocks_magical_side_effects() -> None:
    service = _policy_service()

    decision = service.evaluate_call(
        tool_name="lookup_lead",
        raw_input={"lead_id": "lead-1"},
        requested_effects=["write_db"],
    )

    assert decision.decision is AresPolicyDecision.DENY
    assert "magical side effects" in decision.reason


def test_risky_tool_call_requires_hard_approval() -> None:
    reset_control_plane_store(STORE)
    service = _policy_service()

    missing_approval = service.evaluate_call(
        tool_name="send_outreach",
        raw_input={"lead_id": "lead-1"},
        requested_effects=["send_message"],
    )
    assert missing_approval.decision is AresPolicyDecision.REQUIRE_APPROVAL

    approved = service.evaluate_call(
        tool_name="send_outreach",
        raw_input={"lead_id": "lead-1"},
        requested_effects=["send_message"],
        hard_approval_id="appr-1",
    )
    assert approved.decision is AresPolicyDecision.REQUIRE_APPROVAL


def test_risky_tool_call_requires_registered_approved_hard_approval() -> None:
    reset_control_plane_store(STORE)
    service = _policy_service()

    STORE.approvals["apr-pending"] = ApprovalRecord(
        id="apr-pending",
        command_id="cmd-1",
        business_id="limitless",
        environment="dev",
        command_type="send_outreach",
        status=ApprovalStatus.PENDING,
        payload_snapshot={},
        created_at=utc_now(),
    )
    STORE.approvals["apr-approved"] = ApprovalRecord(
        id="apr-approved",
        command_id="cmd-2",
        business_id="limitless",
        environment="dev",
        command_type="send_outreach",
        status=ApprovalStatus.APPROVED,
        payload_snapshot={},
        created_at=utc_now(),
        approved_at=utc_now(),
        actor_id="tester",
    )

    fake = service.evaluate_call(
        tool_name="send_outreach",
        raw_input={"lead_id": "lead-1"},
        requested_effects=["send_message"],
        hard_approval_id="fake-approval-id",
    )
    pending = service.evaluate_call(
        tool_name="send_outreach",
        raw_input={"lead_id": "lead-1"},
        requested_effects=["send_message"],
        hard_approval_id="apr-pending",
    )
    approved = service.evaluate_call(
        tool_name="send_outreach",
        raw_input={"lead_id": "lead-1"},
        requested_effects=["send_message"],
        hard_approval_id="apr-approved",
    )

    assert fake.decision is AresPolicyDecision.REQUIRE_APPROVAL
    assert pending.decision is AresPolicyDecision.REQUIRE_APPROVAL
    assert approved.decision is AresPolicyDecision.ALLOW


def test_risky_tool_call_rejects_approved_hard_approval_from_other_scope() -> None:
    reset_control_plane_store(STORE)
    service = _policy_service()

    STORE.approvals["apr-other-scope"] = ApprovalRecord(
        id="apr-other-scope",
        command_id="cmd-3",
        business_id="other-biz",
        environment="prod",
        command_type="send_outreach",
        status=ApprovalStatus.APPROVED,
        payload_snapshot={},
        created_at=utc_now(),
        approved_at=utc_now(),
        actor_id="tester",
    )

    decision = service.evaluate_call(
        tool_name="send_outreach",
        raw_input={"lead_id": "lead-1"},
        requested_effects=["send_message"],
        hard_approval_id=" apr-other-scope ",
        business_id="limitless",
        environment="dev",
    )

    assert decision.decision is AresPolicyDecision.REQUIRE_APPROVAL


def test_policy_exposes_audit_trail_and_kill_switch() -> None:
    service = _policy_service()
    service.evaluate_call(tool_name="lookup_lead", raw_input={"lead_id": "lead-1"})

    service.set_kill_switch(enabled=True, reason="incident lock")
    blocked = service.evaluate_call(
        tool_name="lookup_lead",
        raw_input={"lead_id": "lead-2"},
    )

    audit_log = service.audit_trail()

    assert blocked.decision is AresPolicyDecision.DENY
    assert "kill switch" in blocked.reason
    assert [entry.action for entry in audit_log] == [
        AresPolicyAuditAction.EVALUATE,
        AresPolicyAuditAction.KILL_SWITCH_UPDATED,
        AresPolicyAuditAction.EVALUATE,
    ]


def test_output_validation_failure_is_still_audited() -> None:
    service = _policy_service()

    with pytest.raises(Exception):
        service.validate_output(
            tool_name="lookup_lead",
            raw_output={},
        )

    audit_log = service.audit_trail()

    assert audit_log[-1].action is AresPolicyAuditAction.OUTPUT_VALIDATE
    assert audit_log[-1].decision is AresPolicyDecision.DENY
    assert "validation failed" in (audit_log[-1].reason or "")
