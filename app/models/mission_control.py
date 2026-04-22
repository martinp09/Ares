from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domains.ares import AresPlannerPlan
from app.models.agent_assets import AgentAssetStatus, AgentAssetType
from app.models.agents import AgentRevisionState
from app.models.approvals import ApprovalStatus
from app.models.audit import AuditRecord
from app.models.commands import generate_id
from app.models.outcomes import OutcomeStatus
from app.models.release_management import ReleaseEventType
from app.models.runs import RunStatus
from app.models.tasks import TaskPriority, TaskStatus, TaskType
from app.models.turns import TurnStatus
from app.models.usage import UsageRecord, UsageSummaryRecord

MissionControlThreadStatus = Literal["open", "waiting", "closed"]
MissionControlMessageDirection = Literal["inbound", "outbound", "internal"]
MissionControlApprovalRisk = Literal["low", "medium", "high"]
MissionControlProviderName = Literal["textgrid", "resend"]
MissionControlProviderChannel = Literal["sms", "email"]
MissionControlOutboundSendStatus = Literal["queued", "sent", "failed"]


class MissionControlContactRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("mc_contact"))
    display_name: str = Field(min_length=1)
    phone: str | None = None
    email: str | None = None


class MissionControlMessageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("mc_msg"))
    direction: MissionControlMessageDirection
    channel: str = Field(min_length=1)
    body: str = Field(min_length=1)
    created_at: datetime
    message_type: str = Field(default="message", min_length=1)
    approval_id: str | None = None
    run_id: str | None = None


class MissionControlThreadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: generate_id("mc_thread"))
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    status: MissionControlThreadStatus = "open"
    unread_count: int = Field(default=0, ge=0)
    contact: MissionControlContactRecord
    messages: list[MissionControlMessageRecord] = Field(default_factory=list)
    requires_approval: bool = False
    related_run_id: str | None = None
    related_approval_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MissionControlDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_count: int = Field(ge=0)
    active_run_count: int = Field(ge=0)
    failed_run_count: int = Field(ge=0)
    active_agent_count: int = Field(ge=0)
    unread_conversation_count: int = Field(default=0, ge=0)
    busy_channel_count: int = Field(default=0, ge=0)
    recent_completed_count: int = Field(default=0, ge=0)
    pending_lead_count: int | None = Field(default=None, ge=0)
    booked_lead_count: int | None = Field(default=None, ge=0)
    active_non_booker_enrollment_count: int | None = Field(default=None, ge=0)
    due_manual_call_count: int | None = Field(default=None, ge=0)
    replies_needing_review_count: int | None = Field(default=None, ge=0)
    outbound_probate_summary: MissionControlOutboundProbateSummary | None = None
    inbound_lease_option_summary: MissionControlInboundLeaseOptionSummary | None = None
    lead_machine_summary: MissionControlLeadMachineSummary | None = None
    opportunity_count: int | None = Field(default=None, ge=0)
    opportunity_stage_summaries: list[MissionControlOpportunityStageSummary] | None = None
    opportunity_pipeline_summary: MissionControlOpportunityPipelineSummary | None = None
    system_status: Literal["healthy", "watch", "degraded"] = "healthy"
    updated_at: str


class MissionControlProviderStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: MissionControlProviderName
    configured: bool
    can_send: bool
    sender_identity: str | None = None
    endpoint: str | None = None
    details: str | None = None
    checked_at: datetime


class MissionControlProvidersStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sms: MissionControlProviderStatus
    email: MissionControlProviderStatus


class MissionControlSmsTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str = Field(min_length=1)
    body: str = Field(min_length=1)


class MissionControlEmailTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    to: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    text: str = Field(min_length=1)
    html: str | None = None


class MissionControlTaskCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None
    follow_up_outcome: str | None = None


class MissionControlLeadSuppressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)
    note: str | None = None


class MissionControlLeadUnsuppressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note: str | None = None


class MissionControlOutboundSendResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: MissionControlProviderChannel
    provider: MissionControlProviderName
    status: MissionControlOutboundSendStatus
    provider_message_id: str | None = None
    to: str
    from_identity: str | None = None
    attempted_at: datetime
    error_message: str | None = None


class MissionControlLeadMachineSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_campaign_count: int = Field(ge=0)
    ready_lead_count: int = Field(ge=0)
    active_lead_count: int = Field(ge=0)
    interested_lead_count: int = Field(ge=0)
    suppressed_lead_count: int = Field(ge=0)


class MissionControlLeadMachineQueueSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_lead_count: int = Field(ge=0)
    ready_count: int = Field(ge=0)
    active_count: int = Field(ge=0)
    suppressed_count: int = Field(ge=0)
    interested_count: int = Field(ge=0)


class MissionControlLeadMachineCampaignSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    name: str
    status: str
    member_count: int = Field(ge=0)
    active_member_count: int = Field(ge=0)
    suppressed_member_count: int = Field(ge=0)


class MissionControlLeadMachineCampaignsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_campaign_count: int = Field(ge=0)
    active_campaign_count: int = Field(ge=0)
    items: list[MissionControlLeadMachineCampaignSummary] = Field(default_factory=list)


class MissionControlLeadMachineTaskSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    status: str
    priority: str
    lead_id: str | None = None
    due_at: datetime | None = None


class MissionControlLeadMachineTasksSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    open_count: int = Field(ge=0)
    items: list[MissionControlLeadMachineTaskSummary] = Field(default_factory=list)


class MissionControlLeadMachineTimelineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["event", "run", "task"]
    occurred_at: datetime
    summary: str = Field(min_length=1)
    lead_id: str | None = None
    campaign_id: str | None = None
    task_id: str | None = None
    automation_run_id: str | None = None


class MissionControlLeadMachineTimelineSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[MissionControlLeadMachineTimelineItem] = Field(default_factory=list)


class MissionControlOpportunityStageSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_lane: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    count: int = Field(ge=0)


class MissionControlOpportunityPipelineSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_opportunity_count: int = Field(ge=0)
    lane_stage_summaries: list[MissionControlOpportunityStageSummary] = Field(default_factory=list)


class MissionControlOutboundProbateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_campaign_count: int = Field(ge=0)
    ready_lead_count: int = Field(ge=0)
    active_lead_count: int = Field(ge=0)
    interested_lead_count: int = Field(ge=0)
    suppressed_lead_count: int = Field(ge=0)
    open_task_count: int = Field(ge=0)


class MissionControlInboundLeaseOptionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pending_lead_count: int = Field(ge=0)
    booked_lead_count: int = Field(ge=0)
    active_non_booker_enrollment_count: int = Field(ge=0)
    due_manual_call_count: int = Field(ge=0)
    replies_needing_review_count: int = Field(ge=0)


class MissionControlLeadMachineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queue: MissionControlLeadMachineQueueSummary
    campaigns: MissionControlLeadMachineCampaignsSummary
    tasks: MissionControlLeadMachineTasksSummary
    timeline: MissionControlLeadMachineTimelineSummary
    updated_at: str


class MissionControlInboxSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_count: int = Field(ge=0)
    unread_count: int = Field(ge=0)
    approval_required_count: int = Field(ge=0)


class MissionControlThreadSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    channel: str
    status: MissionControlThreadStatus
    unread_count: int = Field(ge=0)
    last_message_preview: str | None = None
    last_message_at: datetime | None = None
    requires_approval: bool = False
    related_run_id: str | None = None
    related_approval_id: str | None = None
    booking_status: str | None = None
    sequence_status: str | None = None
    next_sequence_step: str | None = None
    manual_call_due_at: str | None = None
    recent_reply_preview: str | None = None
    reply_needs_review: bool = False
    contact: MissionControlContactRecord


class MissionControlThreadDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    channel: str
    status: MissionControlThreadStatus
    unread_count: int = Field(ge=0)
    requires_approval: bool = False
    related_run_id: str | None = None
    related_approval_id: str | None = None
    booking_status: str | None = None
    sequence_status: str | None = None
    next_sequence_step: str | None = None
    manual_call_due_at: str | None = None
    recent_reply_preview: str | None = None
    reply_needs_review: bool = False
    contact: MissionControlContactRecord
    messages: list[MissionControlMessageRecord] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class MissionControlInboxResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: MissionControlInboxSummary
    threads: list[MissionControlThreadSummary] = Field(default_factory=list)
    selected_thread_id: str | None = None
    selected_thread: MissionControlThreadDetail | None = None


class MissionControlTaskSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    lead_name: str
    channel: str
    booking_status: str | None = None
    sequence_status: str | None = None
    next_sequence_step: str | None = None
    manual_call_due_at: str
    recent_reply_preview: str | None = None
    reply_needs_review: bool = False


class MissionControlTaskActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    lead_name: str
    completed_task_count: int = Field(default=0, ge=0)
    status: Literal["completed"] = "completed"
    notes: str | None = None
    follow_up_outcome: str | None = None
    updated_at: datetime


class MissionControlLeadActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    lead_name: str
    action: Literal["suppressed", "unsuppressed"]
    suppression_count: int = Field(default=0, ge=0)
    lead_status: str
    note: str | None = None
    reason: str | None = None
    updated_at: datetime


class MissionControlTasksResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    due_count: int = Field(default=0, ge=0)
    tasks: list[MissionControlTaskSummary] = Field(default_factory=list)


class MissionControlReleaseEvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome_id: str
    outcome_name: str
    status: OutcomeStatus
    satisfied: bool
    evaluator_result: str
    failure_details: list[str] = Field(default_factory=list)
    rubric_criteria: list[str] = Field(default_factory=list)
    require_passing_evaluation: bool = False
    blocked_promotion: bool = False
    rollback_reason: str | None = None


class MissionControlAgentReleaseSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: ReleaseEventType
    release_channel: str | None = None
    created_at: datetime
    previous_active_revision_id: str | None = None
    target_revision_id: str
    resulting_active_revision_id: str
    rollback_source_revision_id: str | None = None
    evaluation: MissionControlReleaseEvaluationSummary | None = None


class MissionControlReplayActorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str
    actor_id: str
    actor_type: str


class MissionControlReplayRevisionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str | None = None
    agent_revision_id: str | None = None
    active_revision_id: str | None = None
    revision_state: AgentRevisionState | None = None
    release_channel: str | None = None
    release_event_id: str | None = None
    release_event_type: ReleaseEventType | None = None


class MissionControlRunReplaySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["parent", "child"]
    requested_at: datetime
    resolved_at: datetime | None = None
    replay_reason: str | None = None
    requires_approval: bool | None = None
    approval_id: str | None = None
    child_run_id: str | None = None
    parent_run_id: str | None = None
    triggering_actor: MissionControlReplayActorSummary | None = None
    source: MissionControlReplayRevisionSummary | None = None
    replay: MissionControlReplayRevisionSummary | None = None


class MissionControlRunSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    command_id: str
    business_id: str
    environment: str
    command_type: str
    status: RunStatus
    parent_run_id: str | None = None
    child_run_ids: list[str] = Field(default_factory=list)
    trigger_run_id: str | None = None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_classification: str | None = None
    error_message: str | None = None
    replay: MissionControlRunReplaySummary | None = None


class MissionControlRunsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    runs: list[MissionControlRunSummary] = Field(default_factory=list)


class MissionControlFailedStepSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    step: str = Field(min_length=1)
    error_classification: str | None = None
    error_message: str | None = None
    failed_at: datetime


class MissionControlPlannerReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    goal: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    plan: AresPlannerPlan
    generated_at: str


class MissionControlExecutionRankedLeadSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    tier: str = Field(min_length=1)
    tax_delinquent: bool
    county: str = Field(min_length=1)
    source_lane: str = Field(min_length=1)


class MissionControlExecutionHighRiskPolicyCheckSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    requires_human_approval: bool


class MissionControlExecutionWorkflowEvalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str = Field(min_length=1)
    exception_count: int = Field(ge=0)
    surfaced_exceptions: list[str] = Field(default_factory=list)
    suggested_next_action: str = Field(min_length=1)


class MissionControlExecutionDriftDetectionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detected: bool
    reason: str = Field(min_length=1)


class MissionControlExecutionReviewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    market: str = Field(min_length=1)
    counties: list[str] = Field(default_factory=list)
    state: str = Field(min_length=1)
    interrupted: bool
    lead_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    high_risk_policy_checks: list[MissionControlExecutionHighRiskPolicyCheckSummary] = Field(default_factory=list)
    workflow_eval: MissionControlExecutionWorkflowEvalSummary
    drift_detection: MissionControlExecutionDriftDetectionSummary
    major_decisions: list[str] = Field(default_factory=list)
    major_failures: list[str] = Field(default_factory=list)
    ranked_leads: list[MissionControlExecutionRankedLeadSummary] = Field(default_factory=list)
    generated_at: str


class MissionControlAutonomousOperatorPolicyCheckSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class MissionControlAutonomousOperatorSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    objective_id: str = Field(min_length=1)
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    market: str = Field(min_length=1)
    counties: list[str] = Field(default_factory=list)
    state: str = Field(min_length=1)
    agent_name: str = Field(min_length=1)
    agent_revision: str = Field(min_length=1)
    playbook_workflow_id: str = Field(min_length=1)
    next_action: str = Field(min_length=1)
    adaptation_summary: str = Field(min_length=1)
    escalation_required: bool
    escalation_reason: str | None = None
    policy_checks: list[MissionControlAutonomousOperatorPolicyCheckSummary] = Field(default_factory=list)
    decision_log: list[str] = Field(default_factory=list)
    exception_log: list[str] = Field(default_factory=list)
    eval_metrics: dict[str, float] = Field(default_factory=dict)
    memory_counts: dict[str, int] = Field(default_factory=dict)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    generated_at: str


class MissionControlAutonomyVisibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_phase: str = Field(min_length=1)
    active_run: MissionControlRunSummary | None = None
    pending_approval_count: int = Field(ge=0)
    pending_approvals: list[MissionControlApprovalSummary] = Field(default_factory=list)
    failed_steps: list[MissionControlFailedStepSummary] = Field(default_factory=list)
    planner_review: MissionControlPlannerReviewSummary | None = None
    execution_review: MissionControlExecutionReviewSummary | None = None
    autonomous_operator: MissionControlAutonomousOperatorSummary | None = None
    lead_quality: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    next_action: str = Field(min_length=1)
    updated_at: str


class MissionControlTurnSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    session_id: str
    org_id: str
    business_id: str
    environment: str
    agent_id: str
    agent_revision_id: str
    turn_number: int = Field(ge=1)
    state: TurnStatus
    retry_count: int = Field(default=0, ge=0)
    resumed_from_turn_id: str | None = None
    updated_at: datetime


class MissionControlTurnsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turns: list[MissionControlTurnSummary] = Field(default_factory=list)


class MissionControlApprovalSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    command_id: str
    business_id: str
    environment: str
    command_type: str
    status: ApprovalStatus
    payload_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    approved_at: datetime | None = None
    actor_id: str | None = None


class MissionControlApprovalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approvals: list[MissionControlApprovalSummary] = Field(default_factory=list)


class MissionControlAgentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    business_id: str
    environment: str
    name: str
    description: str | None = None
    active_revision_id: str | None = None
    active_revision_state: str | None = None
    release: MissionControlAgentReleaseSummary | None = None
    created_at: datetime
    updated_at: datetime


class MissionControlAgentsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agents: list[MissionControlAgentSummary] = Field(default_factory=list)


class MissionControlAssetSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    agent_id: str
    business_id: str
    environment: str
    asset_type: AgentAssetType
    label: str
    connect_later: bool
    status: AgentAssetStatus
    binding_reference: str | None = None
    updated_at: datetime


class MissionControlAssetsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assets: list[MissionControlAssetSummary] = Field(default_factory=list)


class MissionControlRevisionSecretsHealthSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    agent_name: str = Field(min_length=1)
    agent_revision_id: str
    business_id: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    status: Literal["healthy", "attention"]
    required_secret_count: int = Field(default=0, ge=0)
    configured_secret_count: int = Field(default=0, ge=0)
    missing_secret_count: int = Field(default=0, ge=0)
    required_secrets: list[str] = Field(default_factory=list)
    configured_secrets: list[str] = Field(default_factory=list)
    missing_secrets: list[str] = Field(default_factory=list)


class MissionControlSecretsHealthSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_revision_count: int = Field(default=0, ge=0)
    healthy_revision_count: int = Field(default=0, ge=0)
    attention_revision_count: int = Field(default=0, ge=0)
    required_secret_count: int = Field(default=0, ge=0)
    configured_secret_count: int = Field(default=0, ge=0)
    missing_secret_count: int = Field(default=0, ge=0)
    revisions: list[MissionControlRevisionSecretsHealthSummary] = Field(default_factory=list)


class MissionControlGovernanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    org_id: str = Field(min_length=1)
    pending_approvals: list[MissionControlApprovalSummary] = Field(default_factory=list)
    secrets_health: MissionControlSecretsHealthSnapshot
    recent_audit: list[AuditRecord] = Field(default_factory=list)
    usage_summary: UsageSummaryRecord
    recent_usage: list[UsageRecord] = Field(default_factory=list)
