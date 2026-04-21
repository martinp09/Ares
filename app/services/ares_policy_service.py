from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.db.client import ControlPlaneClient, get_control_plane_client
from app.models.approvals import ApprovalStatus


class AresPolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class AresPolicyAuditAction(StrEnum):
    EVALUATE = "evaluate"
    OUTPUT_VALIDATE = "output_validate"
    KILL_SWITCH_UPDATED = "kill_switch_updated"


class AresToolPolicySpec(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    tool_name: str = Field(min_length=1)
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    declared_effects: tuple[str, ...] = Field(default_factory=tuple)
    requires_hard_approval: bool = False


class AresPolicyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: AresPolicyDecision
    reason: str


class AresPolicyAuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sequence: int
    action: AresPolicyAuditAction
    tool_name: str | None = None
    decision: AresPolicyDecision | None = None
    reason: str | None = None
    requested_effects: tuple[str, ...] = Field(default_factory=tuple)
    hard_approval_id: str | None = None
    kill_switch_enabled: bool | None = None


class AresPolicyService:
    def __init__(
        self,
        *,
        policies: Iterable[AresToolPolicySpec] = (),
        control_plane_client: ControlPlaneClient | None = None,
    ) -> None:
        self._policies_by_tool: dict[str, AresToolPolicySpec] = {
            policy.tool_name: policy for policy in policies
        }
        self._control_plane_client = control_plane_client or get_control_plane_client()
        self._kill_switch_enabled = False
        self._kill_switch_reason = ""
        self._audit_entries: list[AresPolicyAuditEntry] = []

    def evaluate_call(
        self,
        *,
        tool_name: str,
        raw_input: Mapping[str, object],
        requested_effects: Sequence[str] | None = None,
        hard_approval_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> AresPolicyResult:
        effects = tuple(requested_effects or ())

        if self._kill_switch_enabled:
            return self._audit_evaluation(
                tool_name=tool_name,
                decision=AresPolicyDecision.DENY,
                reason=f"Denied by kill switch: {self._kill_switch_reason}",
                requested_effects=effects,
                hard_approval_id=hard_approval_id,
            )

        policy = self._policies_by_tool.get(tool_name)
        if policy is None:
            return self._audit_evaluation(
                tool_name=tool_name,
                decision=AresPolicyDecision.DENY,
                reason="Tool is not allowlisted",
                requested_effects=effects,
                hard_approval_id=hard_approval_id,
            )

        try:
            policy.input_model.model_validate(dict(raw_input))
        except ValidationError as exc:
            return self._audit_evaluation(
                tool_name=tool_name,
                decision=AresPolicyDecision.DENY,
                reason=f"Typed input validation failed: {exc.errors()[0]['msg']}",
                requested_effects=effects,
                hard_approval_id=hard_approval_id,
            )

        undeclared_effects = [effect for effect in effects if effect not in policy.declared_effects]
        if undeclared_effects:
            return self._audit_evaluation(
                tool_name=tool_name,
                decision=AresPolicyDecision.DENY,
                reason="Denied for magical side effects outside declared policy",
                requested_effects=effects,
                hard_approval_id=hard_approval_id,
            )

        if policy.requires_hard_approval and not self._has_valid_hard_approval(
            tool_name=tool_name,
            hard_approval_id=hard_approval_id,
            business_id=business_id,
            environment=environment,
        ):
            return self._audit_evaluation(
                tool_name=tool_name,
                decision=AresPolicyDecision.REQUIRE_APPROVAL,
                reason="Hard approval required for risky tool call",
                requested_effects=effects,
                hard_approval_id=hard_approval_id,
            )

        return self._audit_evaluation(
            tool_name=tool_name,
            decision=AresPolicyDecision.ALLOW,
            reason="Tool call is policy-compliant",
            requested_effects=effects,
            hard_approval_id=hard_approval_id,
        )

    def validate_output(self, *, tool_name: str, raw_output: Mapping[str, object]) -> BaseModel:
        policy = self._policies_by_tool.get(tool_name)
        if policy is None:
            raise ValueError("Tool is not allowlisted")
        try:
            output = policy.output_model.model_validate(dict(raw_output))
        except ValidationError as exc:
            self._append_audit_entry(
                action=AresPolicyAuditAction.OUTPUT_VALIDATE,
                tool_name=tool_name,
                decision=AresPolicyDecision.DENY,
                reason=f"Typed output validation failed: {exc.errors()[0]['msg']}",
            )
            raise
        self._append_audit_entry(
            action=AresPolicyAuditAction.OUTPUT_VALIDATE,
            tool_name=tool_name,
            decision=AresPolicyDecision.ALLOW,
            reason="Typed output validation passed",
        )
        return output

    def set_kill_switch(self, *, enabled: bool, reason: str) -> None:
        self._kill_switch_enabled = enabled
        self._kill_switch_reason = reason.strip()
        self._append_audit_entry(
            action=AresPolicyAuditAction.KILL_SWITCH_UPDATED,
            reason=self._kill_switch_reason,
            kill_switch_enabled=enabled,
        )

    def audit_trail(self) -> list[AresPolicyAuditEntry]:
        return [entry.model_copy(deep=True) for entry in self._audit_entries]

    def _has_valid_hard_approval(
        self,
        *,
        tool_name: str,
        hard_approval_id: str | None,
        business_id: str | None,
        environment: str | None,
    ) -> bool:
        if not isinstance(hard_approval_id, str):
            return False
        normalized_approval_id = hard_approval_id.strip()
        if not normalized_approval_id:
            return False
        with self._control_plane_client.transaction() as store:
            approval = store.approvals.get(normalized_approval_id)
        if approval is None:
            return False
        if approval.status is not ApprovalStatus.APPROVED:
            return False
        if approval.command_type != tool_name:
            return False
        if business_id is not None and approval.business_id != business_id:
            return False
        if environment is not None and approval.environment != environment:
            return False
        return True

    def _audit_evaluation(
        self,
        *,
        tool_name: str,
        decision: AresPolicyDecision,
        reason: str,
        requested_effects: tuple[str, ...],
        hard_approval_id: str | None,
    ) -> AresPolicyResult:
        self._append_audit_entry(
            action=AresPolicyAuditAction.EVALUATE,
            tool_name=tool_name,
            decision=decision,
            reason=reason,
            requested_effects=requested_effects,
            hard_approval_id=hard_approval_id,
        )
        return AresPolicyResult(decision=decision, reason=reason)

    def _append_audit_entry(
        self,
        *,
        action: AresPolicyAuditAction,
        tool_name: str | None = None,
        decision: AresPolicyDecision | None = None,
        reason: str | None = None,
        requested_effects: tuple[str, ...] = (),
        hard_approval_id: str | None = None,
        kill_switch_enabled: bool | None = None,
    ) -> None:
        entry = AresPolicyAuditEntry(
            sequence=len(self._audit_entries) + 1,
            action=action,
            tool_name=tool_name,
            decision=decision,
            reason=reason,
            requested_effects=requested_effects,
            hard_approval_id=hard_approval_id,
            kill_switch_enabled=kill_switch_enabled,
        )
        self._audit_entries.append(entry)
