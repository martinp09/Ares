from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from datetime import UTC
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.contacts import ContactsRepository
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.opportunities import OpportunitiesRepository
from app.db.suppression import SuppressionRepository
from app.db.tasks import TasksRepository
from app.host_adapters.registry import HostAdapterRegistry, host_adapter_registry
from app.models.approvals import ApprovalStatus
from app.models.campaigns import CampaignMembershipStatus, CampaignStatus
from app.models.leads import LeadInterestStatus, LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.marketing_leads import MarketingLeadRecord
from app.models.tasks import TaskStatus, TaskType
from app.models.agents import AgentRevisionState
from app.models.release_management import ReleaseEventType
from app.models.suppression import SuppressionRecord, SuppressionScope, SuppressionSource
from app.models.mission_control import (
    MissionControlAutonomyVisibilityResponse,
    MissionControlAgentsResponse,
    MissionControlAgentSummary,
    MissionControlAutonomousOperatorSummary,
    MissionControlApprovalsResponse,
    MissionControlApprovalSummary,
    MissionControlAssetsResponse,
    MissionControlAssetSummary,
    MissionControlDashboardResponse,
    MissionControlEmailTestRequest,
    MissionControlExecutionReviewSummary,
    MissionControlFailedStepSummary,
    MissionControlGovernanceResponse,
    MissionControlHostAdapterSummary,
    MissionControlInboxResponse,
    MissionControlInboxSummary,
    MissionControlInboundLeaseOptionSummary,
    MissionControlLeadMachineCampaignSummary,
    MissionControlLeadMachineCampaignsSummary,
    MissionControlLeadMachineQueueSummary,
    MissionControlLeadMachineResponse,
    MissionControlLeadMachineSummary,
    MissionControlOutboundSendResponse,
    MissionControlProviderStatus,
    MissionControlProvidersStatusResponse,
    MissionControlReleaseEvaluationSummary,
    MissionControlRevisionSecretsHealthSummary,
    MissionControlRunReplaySummary,
    MissionControlRunSummary,
    MissionControlRunsResponse,
    MissionControlSmsTestRequest,
    MissionControlSecretsHealthSnapshot,
    MissionControlLeadMachineTaskSummary,
    MissionControlLeadMachineTasksSummary,
    MissionControlLeadMachineTimelineItem,
    MissionControlLeadMachineTimelineSummary,
    MissionControlOpportunityPipelineSummary,
    MissionControlOpportunityStageSummary,
    MissionControlOutboundProbateSummary,
    MissionControlPlannerReviewSummary,
    MissionControlReplayActorSummary,
    MissionControlReplayRevisionSummary,
    MissionControlTaskActionResponse,
    MissionControlTaskSummary,
    MissionControlTasksResponse,
    MissionControlThreadDetail,
    MissionControlThreadRecord,
    MissionControlThreadSummary,
    MissionControlTurnSummary,
    MissionControlTurnsResponse,
    MissionControlLeadActionResponse,
    MissionControlAgentReleaseSummary,
)
from app.models.runs import RunStatus
from app.models.provider_extras import InstantlyProviderExtrasSnapshot, ProviderExtraFamilyStatus, ProviderExtrasSummary
from app.models.audit import AuditListResponse
from app.models.secrets import SecretBindingListResponse, SecretListResponse
from app.models.opportunities import OpportunitySourceLane, OpportunityStage
from app.models.usage import UsageEventKind, UsageResponse
from app.services.agent_asset_service import AgentAssetService, agent_asset_service
from app.services.agent_registry_service import AgentRegistryService, agent_registry_service
from app.services.approval_service import ApprovalService, approval_service
from app.services.audit_service import audit_service
from app.services.opportunity_service import OpportunityService
from app.services.provider_extras_service import provider_extras_service
from app.services.providers.resend import get_resend_status, send_test_email
from app.services.providers.textgrid import get_textgrid_status, send_test_sms
from app.services.secrets_service import secret_service
from app.services.usage_service import usage_service

ACTIVE_RUN_STATUSES = {RunStatus.QUEUED, RunStatus.IN_PROGRESS}
_OPPORTUNITY_QUALIFIED_OUTCOMES = {"qualified", "ready", "ready_for_offer", "offer_path_selected"}
_OPPORTUNITY_READY_OUTCOMES = {"ready", "ready_for_offer", "offer_path_selected"}


class MissionControlService:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        approval_service_dependency: ApprovalService | None = None,
        agent_registry_service_dependency: AgentRegistryService | None = None,
        agent_asset_service_dependency: AgentAssetService | None = None,
        opportunities_repository: OpportunitiesRepository | None = None,
        opportunity_service_dependency: OpportunityService | None = None,
        campaigns_repository: CampaignsRepository | None = None,
        leads_repository: LeadsRepository | None = None,
        suppression_repository: SuppressionRepository | None = None,
        campaign_memberships_repository: CampaignMembershipsRepository | None = None,
        lead_events_repository: LeadEventsRepository | None = None,
        automation_runs_repository: AutomationRunsRepository | None = None,
        tasks_repository: TasksRepository | None = None,
        host_adapter_registry_dependency: HostAdapterRegistry | None = None,
    ) -> None:
        self.client = client or get_control_plane_client()
        self.approval_service = approval_service_dependency or approval_service
        self.agent_registry_service = agent_registry_service_dependency or agent_registry_service
        self.agent_asset_service = agent_asset_service_dependency or agent_asset_service
        self.opportunities_repository = opportunities_repository or OpportunitiesRepository(client=self.client)
        self.opportunity_service = opportunity_service_dependency or OpportunityService(self.opportunities_repository)
        self.contacts_repository = ContactsRepository(client=self.client)
        self.campaigns_repository = campaigns_repository or CampaignsRepository(client=self.client)
        self.leads_repository = leads_repository or LeadsRepository(client=self.client)
        self.suppression_repository = suppression_repository or SuppressionRepository(client=self.client)
        self.campaign_memberships_repository = campaign_memberships_repository or CampaignMembershipsRepository(client=self.client)
        self.lead_events_repository = lead_events_repository or LeadEventsRepository(client=self.client)
        self.automation_runs_repository = automation_runs_repository or AutomationRunsRepository(client=self.client)
        self.tasks_repository = tasks_repository or TasksRepository(client=self.client)
        self.host_adapter_registry = host_adapter_registry_dependency or host_adapter_registry

    def upsert_thread_projection(self, thread: MissionControlThreadRecord) -> MissionControlThreadRecord:
        with self.client.transaction() as store:
            store.mission_control_threads[thread.id] = thread.model_copy(deep=True)
            return store.mission_control_threads[thread.id]

    def get_dashboard(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlDashboardResponse:
        with self.client.transaction() as store:
            commands_by_id = dict(store.commands)
            approvals_by_id = dict(store.approvals)
            runs_by_id = dict(store.runs)
            approvals = [
                approval
                for approval in store.approvals.values()
                if approval.status == ApprovalStatus.PENDING
                and self._matches_actor_org(self._approval_org_id(approval, commands_by_id=commands_by_id), org_id)
                and self._matches_scope(approval.business_id, approval.environment, business_id, environment)
            ]
            planner_snapshots = [
                snapshot
                for (scope_business_id, scope_environment), snapshot in store.ares_plans_by_scope.items()
                if self._matches_scope(scope_business_id, scope_environment, business_id, environment)
            ]
            runs = [
                run
                for run in store.runs.values()
                if self._matches_actor_org(self._run_org_id(run, commands_by_id=commands_by_id), org_id)
                if self._matches_scope(run.business_id, run.environment, business_id, environment)
            ]
            agents = [
                agent
                for agent in store.agents.values()
                if self._matches_actor_org(self._record_org_id(agent), org_id)
                if self._matches_scope(agent.business_id, agent.environment, business_id, environment)
            ]
            threads = [
                thread if isinstance(thread, MissionControlThreadRecord) else MissionControlThreadRecord.model_validate(thread)
                for thread in store.mission_control_threads.values()
                if self._matches_actor_org(
                    self._thread_org_id(
                        thread,
                        approvals_by_id=approvals_by_id,
                        runs_by_id=runs_by_id,
                        commands_by_id=commands_by_id,
                    ),
                    org_id,
                )
                if self._matches_scope(thread.business_id, thread.environment, business_id, environment)
            ]
        can_expose_unscoped_context = self._can_expose_unscoped_context(org_id)
        lead_machine_summary = (
            self._build_lead_machine_summary(business_id=business_id, environment=environment)
            if can_expose_unscoped_context
            else None
        )

        latest_timestamps: list[datetime] = [approval.created_at for approval in approvals]
        latest_timestamps.extend(run.updated_at for run in runs)
        latest_timestamps.extend(thread.updated_at for thread in threads)
        latest_updated_at = max(latest_timestamps, default=utc_now())

        unread_conversation_count = sum(1 for thread in threads if thread.unread_count > 0)
        busy_channel_count = len({thread.channel for thread in threads if thread.unread_count > 0})
        recent_completed_count = sum(1 for run in runs if run.status == RunStatus.COMPLETED)
        failed_run_count = sum(1 for run in runs if run.status == RunStatus.FAILED)
        active_run_count = sum(1 for run in runs if run.status in ACTIVE_RUN_STATUSES)
        pending_lead_count = sum(1 for thread in threads if self._context_value(thread.context, "booking_status") == "pending")
        booked_lead_count = sum(1 for thread in threads if self._context_value(thread.context, "booking_status") == "booked")
        active_non_booker_enrollment_count = sum(
            1
            for thread in threads
            if self._context_value(thread.context, "sequence_status") == "active"
            and self._context_value(thread.context, "booking_status") != "booked"
        )
        due_manual_call_count = sum(
            1
            for thread in threads
            if self._is_due_manual_call(
                thread.context,
                now=utc_now(),
            )
        )
        replies_needing_review_count = sum(
            1 for thread in threads if bool(thread.context.get("reply_needs_review"))
        )
        opportunity_stage_summaries = (
            [
                MissionControlOpportunityStageSummary(
                    source_lane=str(summary.source_lane),
                    stage=str(summary.stage),
                    count=summary.count,
                )
                for summary in self.opportunity_service.summarize_by_lane_and_stage(
                    business_id=business_id,
                    environment=environment,
                )
            ]
            if can_expose_unscoped_context
            else []
        )
        lead_machine_leads = (
            self._lead_machine_leads(business_id=business_id, environment=environment)
            if can_expose_unscoped_context
            else []
        )
        lead_machine_lead_ids = {lead.id for lead in lead_machine_leads if lead.id is not None}
        open_probate_task_count = sum(
            1
            for task in self.tasks_repository.list(business_id=business_id, environment=environment)
            if task.lead_id in lead_machine_lead_ids and task.status == TaskStatus.OPEN
        )
        provider_failure_task_count = len(
            self.get_visible_provider_failure_tasks(
                org_id=org_id,
                business_id=business_id,
                environment=environment,
            )
        )
        has_marketing_context = any(self._has_marketing_context(thread.context) for thread in threads)
        has_lead_machine_context = lead_machine_summary is not None
        has_opportunity_context = bool(opportunity_stage_summaries)
        outbound_probate_summary = (
            MissionControlOutboundProbateSummary(
                active_campaign_count=lead_machine_summary.active_campaign_count,
                ready_lead_count=lead_machine_summary.ready_lead_count,
                active_lead_count=lead_machine_summary.active_lead_count,
                interested_lead_count=lead_machine_summary.interested_lead_count,
                suppressed_lead_count=lead_machine_summary.suppressed_lead_count,
                open_task_count=open_probate_task_count,
            )
            if lead_machine_summary is not None
            else None
        )
        inbound_lease_option_summary = (
            MissionControlInboundLeaseOptionSummary(
                pending_lead_count=pending_lead_count,
                booked_lead_count=booked_lead_count,
                active_non_booker_enrollment_count=active_non_booker_enrollment_count,
                due_manual_call_count=due_manual_call_count,
                replies_needing_review_count=replies_needing_review_count,
            )
            if has_marketing_context
            else None
        )
        opportunity_pipeline_summary = (
            MissionControlOpportunityPipelineSummary(
                total_opportunity_count=sum(summary.count for summary in opportunity_stage_summaries),
                lane_stage_summaries=opportunity_stage_summaries,
            )
            if has_opportunity_context
            else None
        )
        if failed_run_count > 0:
            system_status = "degraded"
        elif approvals or unread_conversation_count or active_run_count or provider_failure_task_count:
            system_status = "watch"
        else:
            system_status = "healthy"

        return MissionControlDashboardResponse(
            approval_count=len(approvals),
            active_run_count=active_run_count,
            failed_run_count=failed_run_count,
            active_agent_count=sum(1 for agent in agents if agent.active_revision_id is not None),
            unread_conversation_count=unread_conversation_count,
            busy_channel_count=busy_channel_count,
            recent_completed_count=recent_completed_count,
            pending_lead_count=(pending_lead_count if has_marketing_context else None),
            booked_lead_count=(booked_lead_count if has_marketing_context else None),
            active_non_booker_enrollment_count=(active_non_booker_enrollment_count if has_marketing_context else None),
            due_manual_call_count=(due_manual_call_count if has_marketing_context else None),
            replies_needing_review_count=(replies_needing_review_count if has_marketing_context else None),
            outbound_probate_summary=outbound_probate_summary,
            inbound_lease_option_summary=inbound_lease_option_summary,
            lead_machine_summary=(lead_machine_summary if has_lead_machine_context else None),
            opportunity_count=(sum(summary.count for summary in opportunity_stage_summaries) if has_opportunity_context else None),
            opportunity_stage_summaries=(opportunity_stage_summaries if has_opportunity_context else None),
            opportunity_pipeline_summary=opportunity_pipeline_summary,
            provider_failure_task_count=provider_failure_task_count,
            system_status=system_status,
            updated_at=latest_updated_at.isoformat(),
        )

    def get_inbox(
        self,
        *,
        selected_thread_id: str | None = None,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlInboxResponse:
        with self.client.transaction() as store:
            commands_by_id = dict(store.commands)
            approvals_by_id = dict(store.approvals)
            runs_by_id = dict(store.runs)
            threads = [
                thread if isinstance(thread, MissionControlThreadRecord) else MissionControlThreadRecord.model_validate(thread)
                for thread in store.mission_control_threads.values()
                if self._matches_actor_org(
                    self._thread_org_id(
                        thread,
                        approvals_by_id=approvals_by_id,
                        runs_by_id=runs_by_id,
                        commands_by_id=commands_by_id,
                    ),
                    org_id,
                )
                if self._matches_scope(thread.business_id, thread.environment, business_id, environment)
            ]

        ordered_threads = sorted(threads, key=lambda thread: (thread.updated_at, thread.created_at), reverse=True)
        thread_summaries = [
            self._build_thread_summary(thread, runs_by_id=runs_by_id) for thread in ordered_threads
        ]

        selected_record: MissionControlThreadRecord | None = None
        if selected_thread_id is not None:
            selected_record = next((thread for thread in ordered_threads if thread.id == selected_thread_id), None)
            if selected_record is None:
                raise KeyError(selected_thread_id)
        elif ordered_threads:
            selected_record = ordered_threads[0]

        return MissionControlInboxResponse(
            summary=MissionControlInboxSummary(
                thread_count=len(ordered_threads),
                unread_count=sum(thread.unread_count for thread in ordered_threads),
                approval_required_count=sum(1 for thread in ordered_threads if thread.requires_approval),
            ),
            threads=thread_summaries,
            selected_thread_id=selected_record.id if selected_record is not None else None,
            selected_thread=self._build_thread_detail(
                selected_record,
                runs_by_id=runs_by_id,
                approvals_by_id=approvals_by_id,
            )
            if selected_record is not None
            else None,
        )

    def get_tasks(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlTasksResponse:
        with self.client.transaction() as store:
            commands_by_id = dict(store.commands)
            approvals_by_id = dict(store.approvals)
            runs_by_id = dict(store.runs)
            threads = [
                thread if isinstance(thread, MissionControlThreadRecord) else MissionControlThreadRecord.model_validate(thread)
                for thread in store.mission_control_threads.values()
                if self._matches_actor_org(
                    self._thread_org_id(
                        thread,
                        approvals_by_id=approvals_by_id,
                        runs_by_id=runs_by_id,
                        commands_by_id=commands_by_id,
                    ),
                    org_id,
                )
                if self._matches_scope(thread.business_id, thread.environment, business_id, environment)
            ]

        tasks: list[MissionControlTaskSummary] = []
        for thread in threads:
            due_at = self._context_value(thread.context, "manual_call_due_at")
            if due_at is None:
                continue

            tasks.append(
                MissionControlTaskSummary(
                    thread_id=thread.id,
                    lead_name=thread.contact.display_name,
                    channel=thread.channel,
                    booking_status=self._context_value(thread.context, "booking_status"),
                    sequence_status=self._context_value(thread.context, "sequence_status"),
                    next_sequence_step=self._context_value(thread.context, "next_sequence_step"),
                    manual_call_due_at=due_at,
                    recent_reply_preview=self._recent_reply_preview(thread),
                    reply_needs_review=bool(thread.context.get("reply_needs_review")),
                )
            )

        for task in self.get_visible_provider_failure_tasks(
            org_id=org_id,
            business_id=business_id,
            environment=environment,
        ):
            tasks.append(
                MissionControlTaskSummary(
                    thread_id=task.lead_id or task.id or "provider_failure",
                    lead_name=str(task.details.get("phone") or task.lead_id or "Unknown lead"),
                    channel=str(task.details.get("side_effect") or "provider"),
                    booking_status=None,
                    sequence_status=None,
                    next_sequence_step=None,
                    manual_call_due_at=task.created_at.isoformat(),
                    recent_reply_preview=str(task.details.get("error_message") or ""),
                    reply_needs_review=True,
                    task_id=task.id,
                    task_type=str(task.task_type.value),
                    priority=str(task.priority.value),
                    provider_failure=True,
                    error_message=str(task.details.get("error_message") or ""),
                )
            )

        ordered_tasks = sorted(tasks, key=lambda task: task.manual_call_due_at)
        return MissionControlTasksResponse(due_count=len(ordered_tasks), tasks=ordered_tasks)

    def get_visible_provider_failure_tasks(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ):
        return [
            task
            for task in self.tasks_repository.list(business_id=business_id, environment=environment)
            if task.status == TaskStatus.OPEN
            and task.task_type == TaskType.MANUAL_REVIEW
            and bool(task.details.get("visible_in_mission_control"))
            and self._matches_actor_org(self._payload_org_id(task.details), org_id)
        ]

    def complete_task_for_thread(
        self,
        *,
        thread_id: str,
        org_id: str | None = None,
        notes: str | None = None,
        follow_up_outcome: str | None = None,
    ) -> MissionControlTaskActionResponse:
        thread = self._require_thread_projection(thread_id, org_id=org_id)
        self._require_safe_thread_mutation_access(thread, actor_org_id=org_id)
        lead = self._resolve_lead_for_thread(thread)
        now = utc_now()
        completed_task_count = 0

        if lead is not None and lead.id is not None:
            completed_task_count = self._complete_open_tasks_for_lead(
                lead_id=lead.id,
                notes=notes,
                follow_up_outcome=follow_up_outcome,
                completed_at=now,
            )

        thread_context = deepcopy(thread.context)
        thread_context.pop("manual_call_due_at", None)
        thread_context["reply_needs_review"] = False
        thread_context["task_completed_at"] = now.isoformat()
        if notes is not None:
            thread_context["task_completion_note"] = notes
        if follow_up_outcome is not None:
            thread_context["follow_up_outcome"] = follow_up_outcome
        if lead is not None and lead.id is not None:
            thread_context.setdefault("lead_id", lead.id)

        self.upsert_thread_projection(
            thread.model_copy(update={"context": thread_context, "updated_at": now})
        )
        self._sync_lease_option_opportunity_from_thread(
            thread=thread,
            thread_context=thread_context,
            follow_up_outcome=follow_up_outcome,
        )

        return MissionControlTaskActionResponse(
            thread_id=thread.id,
            lead_name=thread.contact.display_name,
            completed_task_count=completed_task_count,
            notes=notes,
            follow_up_outcome=follow_up_outcome,
            updated_at=now,
        )

    def suppress_thread(
        self,
        *,
        thread_id: str,
        org_id: str | None = None,
        reason: str,
        note: str | None = None,
    ) -> MissionControlLeadActionResponse:
        thread = self._require_thread_projection(thread_id, org_id=org_id)
        self._require_safe_thread_mutation_access(thread, actor_org_id=org_id)
        target = self._resolve_lead_for_thread(thread)
        if target is None or target.id is None:
            raise KeyError(thread_id)

        now = utc_now()
        thread_context = deepcopy(thread.context)
        thread_context["sequence_status"] = "suppressed"
        thread_context["reply_needs_review"] = False
        thread_context["manual_call_due_at"] = None
        thread_context["suppression_reason"] = reason
        thread_context["suppressed_at"] = now.isoformat()
        thread_context["last_operator_note"] = note
        thread_context["lead_id"] = target.id

        if isinstance(target, LeadRecord):
            self.suppression_repository.upsert(
                SuppressionRecord(
                    business_id=target.business_id,
                    environment=target.environment,
                    lead_id=target.id,
                    email=target.email,
                    phone=target.phone,
                    scope=SuppressionScope.GLOBAL,
                    reason=reason,
                    source=SuppressionSource.MANUAL,
                    idempotency_key=f"mission-control:suppress:{thread.id}",
                    metadata={"thread_id": thread.id, "note": note, "operator_action": "suppress"},
                )
            )
            self.leads_repository.upsert(
                target.model_copy(
                    update={
                        "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                        "updated_at": now,
                        "last_touched_at": now,
                    }
                )
            )
            self._set_campaign_memberships_status(lead_id=target.id, status=CampaignMembershipStatus.SUPPRESSED)
            self._cancel_open_tasks_for_lead(lead_id=target.id, suppression_reason=reason, note=note)
            lead_status = str(LeadLifecycleStatus.SUPPRESSED)
        else:
            previous_booking_status = str(target.booking_status)
            self.suppression_repository.upsert(
                SuppressionRecord(
                    business_id=target.business_id,
                    environment=target.environment,
                    lead_id=target.id,
                    email=target.email,
                    phone=target.phone,
                    scope=SuppressionScope.GLOBAL,
                    reason=reason,
                    source=SuppressionSource.MANUAL,
                    idempotency_key=f"mission-control:suppress:{thread.id}",
                    metadata={"thread_id": thread.id, "note": note, "operator_action": "suppress"},
                )
            )
            updated_contact = self.contacts_repository.update_booking_status(target.id, "cancelled")
            self._cancel_open_tasks_for_lead(lead_id=target.id, suppression_reason=reason, note=note)
            thread_context["booking_status_before_suppression"] = previous_booking_status
            thread_context["booking_status"] = "cancelled"
            lead_status = str(updated_contact.booking_status if updated_contact is not None else "cancelled")

        self.upsert_thread_projection(thread.model_copy(update={"context": thread_context, "updated_at": now}))

        return MissionControlLeadActionResponse(
            thread_id=thread.id,
            lead_name=thread.contact.display_name,
            action="suppressed",
            suppression_count=len(
                self.suppression_repository.list_active(business_id=target.business_id, environment=target.environment)
            ),
            lead_status=lead_status,
            note=note,
            reason=reason,
            updated_at=now,
        )

    def unsuppress_thread(
        self,
        *,
        thread_id: str,
        org_id: str | None = None,
        note: str | None = None,
    ) -> MissionControlLeadActionResponse:
        thread = self._require_thread_projection(thread_id, org_id=org_id)
        self._require_safe_thread_mutation_access(thread, actor_org_id=org_id)
        target = self._resolve_lead_for_thread(thread)
        if target is None or target.id is None:
            raise KeyError(thread_id)

        now = utc_now()
        thread_context = deepcopy(thread.context)
        thread_context["sequence_status"] = "active"
        thread_context["suppression_reason"] = None
        thread_context["suppressed_at"] = None
        thread_context["last_operator_note"] = note
        thread_context["lead_id"] = target.id

        if isinstance(target, LeadRecord):
            archived_count = self._archive_lead_suppressions(lead_id=target.id, note=note)
            restored_membership_count = self._set_campaign_memberships_status(lead_id=target.id, status=CampaignMembershipStatus.ACTIVE)
            lead_after_restore = self.leads_repository.upsert(
                target.model_copy(
                    update={
                        "lifecycle_status": LeadLifecycleStatus.ACTIVE if restored_membership_count > 0 else LeadLifecycleStatus.READY,
                        "updated_at": now,
                        "last_touched_at": now,
                    }
                )
            )
            lead_status = str(lead_after_restore.lifecycle_status)
        else:
            archived_count = self._archive_matching_suppressions(
                business_id=target.business_id,
                environment=target.environment,
                target_id=target.id,
                email=target.email,
                phone=target.phone,
                note=note,
            )
            restored_booking_status = str(
                thread_context.get("booking_status_before_suppression") or target.booking_status or "pending"
            )
            lead_after_restore = self.contacts_repository.update_booking_status(target.id, restored_booking_status)
            thread_context["booking_status"] = restored_booking_status
            thread_context["booking_status_before_suppression"] = None
            lead_status = str(lead_after_restore.booking_status if lead_after_restore is not None else restored_booking_status)

        self.upsert_thread_projection(thread.model_copy(update={"context": thread_context, "updated_at": now}))

        return MissionControlLeadActionResponse(
            thread_id=thread.id,
            lead_name=thread.contact.display_name,
            action="unsuppressed",
            suppression_count=archived_count,
            lead_status=lead_status,
            note=note,
            reason=None,
            updated_at=now,
        )

    def _require_thread_projection(
        self,
        thread_id: str,
        *,
        org_id: str | None = None,
    ) -> MissionControlThreadRecord:
        with self.client.transaction() as store:
            commands_by_id = dict(store.commands)
            approvals_by_id = dict(store.approvals)
            runs_by_id = dict(store.runs)
            for raw_thread in store.mission_control_threads.values():
                thread = (
                    raw_thread
                    if isinstance(raw_thread, MissionControlThreadRecord)
                    else MissionControlThreadRecord.model_validate(raw_thread)
                )
                if thread.id != thread_id:
                    continue
                if not self._matches_actor_org(
                    self._thread_org_id(
                        thread,
                        approvals_by_id=approvals_by_id,
                        runs_by_id=runs_by_id,
                        commands_by_id=commands_by_id,
                    ),
                    org_id,
                ):
                    break
                return thread
        raise KeyError(thread_id)

    def _require_safe_thread_mutation_access(
        self,
        thread: MissionControlThreadRecord,
        *,
        actor_org_id: str | None = None,
    ) -> None:
        if self._can_expose_unscoped_context(actor_org_id):
            return
        # Lead/contact/task/suppression records mutated by these endpoints are not org-scoped yet.
        # Fail closed for tenant actors until the underlying projection carries safe org metadata.
        raise KeyError(thread.id)

    def _load_lead_machine_projection(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> dict[str, list[Any]]:
        if not self._can_expose_unscoped_context(org_id):
            return {
                "leads": [],
                "campaigns": [],
                "memberships": [],
                "events": [],
                "runs": [],
                "tasks": [],
                "suppressions": [],
            }
        with self.client.transaction() as store:
            return {
                "leads": [
                    lead
                    for lead in store.leads.values()
                    if lead.source in {LeadSource.PROBATE_INTAKE, LeadSource.INSTANTLY_IMPORT, LeadSource.INSTANTLY_SYNC}
                    and self._matches_scope(lead.business_id, lead.environment, business_id, environment)
                ],
                "campaigns": [
                    campaign
                    for campaign in store.campaigns.values()
                    if self._matches_scope(campaign.business_id, campaign.environment, business_id, environment)
                ],
                "memberships": [
                    membership
                    for membership in store.campaign_memberships.values()
                    if self._matches_scope(membership.business_id, membership.environment, business_id, environment)
                ],
                "events": [
                    event
                    for event in store.lead_events.values()
                    if self._matches_scope(event.business_id, event.environment, business_id, environment)
                ],
                "runs": [
                    run
                    for run in store.automation_runs.values()
                    if self._matches_scope(run.business_id, run.environment, business_id, environment)
                ],
                "tasks": [
                    task
                    for task in store.tasks.values()
                    if self._matches_scope(task.business_id, task.environment, business_id, environment)
                ],
                "suppressions": [
                    record
                    for record in store.suppressions.values()
                    if record.active and self._matches_scope(record.business_id, record.environment, business_id, environment)
                ],
            }

    def _resolve_lead_for_thread(self, thread: MissionControlThreadRecord) -> LeadRecord | MarketingLeadRecord | None:
        lead_id = self._context_value(thread.context, "lead_id")
        if lead_id is not None:
            lead = self.leads_repository.get(lead_id)
            if lead is not None:
                return lead
            contact = self.contacts_repository.get_lead(lead_id)
            if contact is not None:
                return contact
        if thread.contact.email:
            lead = self.leads_repository.find_by_email(
                business_id=thread.business_id,
                environment=thread.environment,
                email=thread.contact.email,
            )
            if lead is not None:
                return lead
        if thread.contact.phone:
            normalized_phone = "".join(thread.contact.phone.split())
            for lead in self.leads_repository.list(business_id=thread.business_id, environment=thread.environment):
                if lead.phone is not None and "".join(lead.phone.split()) == normalized_phone:
                    return lead
            contact = self.contacts_repository.find_by_phone(
                phone=thread.contact.phone,
                business_id=thread.business_id,
                environment=thread.environment,
            )
            if contact is not None:
                return contact
        return None

    def _complete_open_tasks_for_lead(
        self,
        *,
        lead_id: str,
        notes: str | None,
        follow_up_outcome: str | None,
        completed_at: datetime,
    ) -> int:
        completed_count = 0
        for task in self.tasks_repository.list_for_lead(lead_id):
            if task.status not in {TaskStatus.OPEN, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED}:
                continue
            if task.task_type not in {TaskType.MANUAL_CALL, TaskType.MANUAL_REVIEW, TaskType.FOLLOW_UP}:
                continue
            details = deepcopy(task.details)
            details["completed_at"] = completed_at.isoformat()
            if notes is not None:
                details["operator_notes"] = notes
            if follow_up_outcome is not None:
                details["follow_up_outcome"] = follow_up_outcome
            updated = self.tasks_repository.update(
                task.id or "",
                {
                    "status": TaskStatus.COMPLETED,
                    "details": details,
                },
            )
            if updated is not None:
                completed_count += 1
        return completed_count

    def _cancel_open_tasks_for_lead(
        self,
        *,
        lead_id: str,
        suppression_reason: str,
        note: str | None,
    ) -> int:
        cancelled_count = 0
        for task in self.tasks_repository.list_for_lead(lead_id):
            if task.status not in {TaskStatus.OPEN, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED}:
                continue
            details = deepcopy(task.details)
            details["suppression_reason"] = suppression_reason
            if note is not None:
                details["operator_note"] = note
            updated = self.tasks_repository.update(
                task.id or "",
                {
                    "status": TaskStatus.CANCELLED,
                    "details": details,
                },
            )
            if updated is not None:
                cancelled_count += 1
        return cancelled_count

    def _set_campaign_memberships_status(
        self,
        *,
        lead_id: str,
        status: CampaignMembershipStatus,
    ) -> int:
        now = utc_now()
        updated_count = 0
        for membership in self.campaign_memberships_repository.list_for_lead(lead_id):
            if membership.status == status:
                continue
            updates: dict[str, Any] = {
                "status": status,
                "last_synced_at": now,
            }
            if status == CampaignMembershipStatus.SUPPRESSED:
                updates["unsubscribed_at"] = now
            elif status == CampaignMembershipStatus.ACTIVE:
                updates["unsubscribed_at"] = None
            self.campaign_memberships_repository.upsert(membership.model_copy(update=updates))
            updated_count += 1
        return updated_count

    def _archive_lead_suppressions(self, *, lead_id: str, note: str | None) -> int:
        lead = self.leads_repository.get(lead_id)
        if lead is None:
            return 0
        return self._archive_matching_suppressions(
            business_id=lead.business_id,
            environment=lead.environment,
            target_id=lead.id,
            email=lead.email,
            phone=lead.phone,
            note=note,
        )

    def _archive_matching_suppressions(
        self,
        *,
        business_id: str,
        environment: str,
        target_id: str,
        email: str | None,
        phone: str | None,
        note: str | None,
    ) -> int:
        now = utc_now()
        archived_count = 0
        for suppression in self.suppression_repository.list_active(business_id=business_id, environment=environment):
            if suppression.lead_id != target_id and suppression.email != email and suppression.phone != phone:
                continue
            metadata = deepcopy(suppression.metadata)
            metadata["archived_by"] = "mission_control"
            if note is not None:
                metadata["note"] = note
            self.suppression_repository.upsert(
                suppression.model_copy(
                    update={
                        "active": False,
                        "archived_at": now,
                        "metadata": metadata,
                    }
                )
            )
            archived_count += 1
        return archived_count

    @staticmethod
    def _merge_thread_context(context: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(context)
        for key, value in updates.items():
            if value is None:
                merged.pop(key, None)
            else:
                merged[key] = value
        return merged

    def _sync_lease_option_opportunity_from_thread(
        self,
        *,
        thread: MissionControlThreadRecord,
        thread_context: dict[str, Any],
        follow_up_outcome: str | None,
    ) -> None:
        normalized_outcome = (follow_up_outcome or "").strip().lower()
        booking_status = str(thread_context.get("booking_status") or "").strip().lower()
        should_open_opportunity = booking_status in {"booked", "rescheduled"} or normalized_outcome in _OPPORTUNITY_QUALIFIED_OUTCOMES
        if not should_open_opportunity:
            return

        contact = None
        contact_id = self._context_value(thread_context, "lead_id")
        if contact_id is not None:
            contact = self.contacts_repository.get_lead(contact_id)
        if contact is None and thread.contact.phone:
            contact = self.contacts_repository.find_by_phone(
                phone=thread.contact.phone,
                business_id=thread.business_id,
                environment=thread.environment,
            )
        if contact is None:
            return

        opportunity = self.opportunity_service.create_for_contact(
            business_id=contact.business_id,
            environment=contact.environment,
            contact_id=contact.id,
            source_lane=OpportunitySourceLane.LEASE_OPTION_INBOUND,
            metadata={
                "booking_status": booking_status or None,
                "follow_up_outcome": normalized_outcome or None,
            },
        )
        target_stage = (
            OpportunityStage.OFFER_PATH_SELECTED
            if normalized_outcome in _OPPORTUNITY_READY_OUTCOMES
            else OpportunityStage.QUALIFIED_OPPORTUNITY
        )
        if opportunity.id is not None and opportunity.stage != target_stage:
            try:
                self.opportunity_service.advance_stage(opportunity.id, target_stage)
            except ValueError:
                return

    def get_lead_machine(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
        lead_id: str | None = None,
        campaign_id: str | None = None,
        limit: int | None = None,
    ) -> MissionControlLeadMachineResponse:
        projection = self._load_lead_machine_projection(
            org_id=org_id,
            business_id=business_id,
            environment=environment,
        )
        leads = list(projection["leads"])
        campaigns = list(projection["campaigns"])
        filtered_memberships = list(projection["memberships"])
        filtered_events = list(projection["events"])
        filtered_runs = list(projection["runs"])
        filtered_tasks = list(projection["tasks"])
        filtered_suppressions = list(projection["suppressions"])

        if lead_id is not None:
            leads = [lead for lead in leads if lead.id == lead_id]
            filtered_memberships = [membership for membership in filtered_memberships if membership.lead_id == lead_id]
            filtered_events = [event for event in filtered_events if event.lead_id == lead_id]
            filtered_runs = [run for run in filtered_runs if run.lead_id == lead_id]
            filtered_tasks = [task for task in filtered_tasks if task.lead_id == lead_id]
            filtered_suppressions = [record for record in filtered_suppressions if record.lead_id == lead_id]
        scoped_lead_ids = {lead.id for lead in leads if lead.id is not None}

        if campaign_id is not None:
            campaigns = [campaign for campaign in campaigns if campaign.id == campaign_id]
            filtered_memberships = [membership for membership in filtered_memberships if membership.campaign_id == campaign_id]
            filtered_events = [event for event in filtered_events if event.campaign_id == campaign_id]
            filtered_runs = [run for run in filtered_runs if run.campaign_id == campaign_id]
            filtered_suppressions = [record for record in filtered_suppressions if record.campaign_id == campaign_id]
            if lead_id is None:
                scoped_lead_ids = {
                    membership.lead_id
                    for membership in filtered_memberships
                    if membership.lead_id is not None
                }
                leads = [lead for lead in leads if lead.id in scoped_lead_ids]
                filtered_tasks = [task for task in filtered_tasks if task.lead_id in scoped_lead_ids]
        if lead_id is None and campaign_id is None:
            scoped_lead_ids = {lead.id for lead in leads if lead.id is not None}

        campaign_ids = {campaign.id for campaign in campaigns if campaign.id is not None}
        filtered_memberships = [
            membership
            for membership in filtered_memberships
            if membership.lead_id in scoped_lead_ids or membership.campaign_id in campaign_ids
        ]
        filtered_events = [
            event
            for event in filtered_events
            if event.lead_id in scoped_lead_ids or (event.campaign_id is not None and event.campaign_id in campaign_ids)
        ]
        filtered_runs = [
            run
            for run in filtered_runs
            if run.lead_id in scoped_lead_ids or (run.campaign_id is not None and run.campaign_id in campaign_ids)
        ]
        filtered_tasks = [task for task in filtered_tasks if task.lead_id in scoped_lead_ids]
        filtered_suppressions = [
            record
            for record in filtered_suppressions
            if record.lead_id in scoped_lead_ids or (record.campaign_id is not None and record.campaign_id in campaign_ids)
        ]

        memberships_by_campaign: dict[str, list[Any]] = {}
        for membership in filtered_memberships:
            memberships_by_campaign.setdefault(membership.campaign_id, []).append(membership)

        updated_at_candidates: list[datetime] = []
        updated_at_candidates.extend(lead.updated_at for lead in leads)
        updated_at_candidates.extend(campaign.updated_at for campaign in campaigns)
        updated_at_candidates.extend(task.updated_at for task in filtered_tasks)
        updated_at_candidates.extend(run.updated_at for run in filtered_runs)
        updated_at_candidates.extend(event.received_at for event in filtered_events)

        recent_tasks = sorted(
            filtered_tasks,
            key=lambda record: (record.due_at or record.updated_at, record.created_at),
            reverse=True,
        )[: limit or 10]
        timeline_items = self._build_lead_machine_timeline(
            lead_events=filtered_events,
            automation_runs=filtered_runs,
            tasks=filtered_tasks,
        )[: limit or 10]

        return MissionControlLeadMachineResponse(
            queue=MissionControlLeadMachineQueueSummary(
                total_lead_count=len(leads),
                ready_count=sum(1 for lead in leads if lead.lifecycle_status == LeadLifecycleStatus.READY),
                active_count=sum(1 for lead in leads if lead.lifecycle_status == LeadLifecycleStatus.ACTIVE),
                suppressed_count=self._lead_machine_suppressed_count(
                    leads=leads,
                    suppressions=filtered_suppressions,
                ),
                interested_count=sum(1 for lead in leads if lead.lt_interest_status == LeadInterestStatus.INTERESTED),
            ),
            campaigns=MissionControlLeadMachineCampaignsSummary(
                total_campaign_count=len(campaigns),
                active_campaign_count=sum(1 for campaign in campaigns if campaign.status == CampaignStatus.ACTIVE),
                items=[
                    MissionControlLeadMachineCampaignSummary(
                        campaign_id=campaign.id,
                        name=campaign.name,
                        status=str(campaign.status),
                        member_count=len(memberships_by_campaign.get(campaign.id, [])),
                        active_member_count=sum(
                            1
                            for membership in memberships_by_campaign.get(campaign.id, [])
                            if membership.status == CampaignMembershipStatus.ACTIVE
                        ),
                        suppressed_member_count=sum(
                            1
                            for membership in memberships_by_campaign.get(campaign.id, [])
                            if membership.status == CampaignMembershipStatus.SUPPRESSED
                        ),
                    )
                    for campaign in sorted(campaigns, key=lambda record: (record.updated_at, record.created_at), reverse=True)
                    if campaign.id is not None
                ],
            ),
            tasks=MissionControlLeadMachineTasksSummary(
                open_count=sum(1 for task in filtered_tasks if str(task.status) == "open"),
                items=[
                    MissionControlLeadMachineTaskSummary(
                        task_id=task.id,
                        title=task.title,
                        status=str(task.status),
                        priority=str(task.priority),
                        lead_id=task.lead_id,
                        due_at=task.due_at,
                    )
                    for task in recent_tasks
                    if task.id is not None
                ],
            ),
            timeline=MissionControlLeadMachineTimelineSummary(items=timeline_items),
            updated_at=max(updated_at_candidates, default=utc_now()).isoformat(),
        )

    def get_runs(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlRunsResponse:
        with self.client.transaction() as store:
            commands_by_id = dict(store.commands)
            runs = [
                run
                for run in store.runs.values()
                if self._matches_actor_org(self._run_org_id(run, commands_by_id=commands_by_id), org_id)
                if self._matches_scope(run.business_id, run.environment, business_id, environment)
            ]

        child_run_ids_by_parent: dict[str, list[str]] = {}
        for run in runs:
            if run.parent_run_id is None:
                continue
            child_run_ids_by_parent.setdefault(run.parent_run_id, []).append(run.id)

        ordered_runs = sorted(runs, key=lambda run: (run.created_at, run.updated_at), reverse=True)
        return MissionControlRunsResponse(
            runs=[
                MissionControlRunSummary(
                    id=run.id,
                    command_id=run.command_id,
                    business_id=run.business_id,
                    environment=run.environment,
                    command_type=run.command_type,
                    status=run.status,
                    parent_run_id=run.parent_run_id,
                    child_run_ids=sorted(child_run_ids_by_parent.get(run.id, [])),
                    trigger_run_id=run.trigger_run_id,
                    created_at=run.created_at,
                    updated_at=run.updated_at,
                    started_at=run.started_at,
                    completed_at=run.completed_at,
                    error_classification=run.error_classification,
                    error_message=run.error_message,
                    replay=self._build_run_replay_summary(run),
                )
                for run in ordered_runs
            ]
        )

    def get_autonomy_visibility(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAutonomyVisibilityResponse:
        with self.client.transaction() as store:
            commands_by_id = dict(store.commands)
            runs = [
                run
                for run in store.runs.values()
                if self._matches_actor_org(self._run_org_id(run, commands_by_id=commands_by_id), org_id)
                and self._matches_scope(run.business_id, run.environment, business_id, environment)
            ]
            approvals = [
                approval
                for approval in store.approvals.values()
                if approval.status == ApprovalStatus.PENDING
                and self._matches_actor_org(self._approval_org_id(approval, commands_by_id=commands_by_id), org_id)
                and self._matches_scope(approval.business_id, approval.environment, business_id, environment)
            ]
            planner_snapshots = [
                snapshot
                for (scope_business_id, scope_environment), snapshot in store.ares_plans_by_scope.items()
                if self._matches_actor_org(self._payload_org_id(snapshot), org_id)
                and self._matches_scope(scope_business_id, scope_environment, business_id, environment)
            ]
            execution_snapshots = [
                snapshot
                for (scope_business_id, scope_environment), snapshot in store.ares_execution_runs_by_scope.items()
                if self._matches_actor_org(self._payload_org_id(snapshot), org_id)
                and self._matches_scope(scope_business_id, scope_environment, business_id, environment)
            ]
            operator_snapshots = [
                snapshot
                for (scope_business_id, scope_environment), snapshot in store.ares_operator_runs_by_scope.items()
                if self._matches_actor_org(self._payload_org_id(snapshot), org_id)
                and self._matches_scope(scope_business_id, scope_environment, business_id, environment)
            ]

        child_run_ids_by_parent: dict[str, list[str]] = {}
        for run in runs:
            if run.parent_run_id is None:
                continue
            child_run_ids_by_parent.setdefault(run.parent_run_id, []).append(run.id)

        ordered_runs = sorted(runs, key=lambda run: (run.updated_at, run.created_at), reverse=True)
        ordered_pending_approvals = sorted(approvals, key=lambda approval: approval.created_at, reverse=True)
        planner_snapshot = max(
            planner_snapshots,
            key=lambda snapshot: snapshot.get("generated_at", ""),
            default=None,
        )
        execution_snapshot = max(
            execution_snapshots,
            key=lambda snapshot: snapshot.get("generated_at", ""),
            default=None,
        )
        operator_snapshot = max(
            operator_snapshots,
            key=lambda snapshot: snapshot.get("generated_at", ""),
            default=None,
        )
        active_run = next((run for run in ordered_runs if run.status in ACTIVE_RUN_STATUSES), None)
        failed_steps = [
            MissionControlFailedStepSummary(
                run_id=run.id,
                step=run.command_type,
                error_classification=run.error_classification,
                error_message=run.error_message,
                failed_at=run.updated_at,
            )
            for run in ordered_runs
            if run.status == RunStatus.FAILED
        ]

        lead_quality = self._lead_quality_score(org_id=org_id, business_id=business_id, environment=environment)
        confidence = max(0.0, min(1.0, lead_quality - (0.15 if failed_steps else 0.0)))

        latest_snapshot_kind, _latest_snapshot = self._latest_autonomy_snapshot(
            planner_snapshot=planner_snapshot,
            execution_snapshot=execution_snapshot,
            operator_snapshot=operator_snapshot,
        )
        if latest_snapshot_kind == "operator":
            current_phase = "phase5_guarded_operator"
            if bool(operator_snapshot.get("escalation_required")):
                snapshot_next_action = "review_operator_escalation"
            else:
                snapshot_next_action = str(operator_snapshot.get("next_action", "continue_guarded_operator"))
        elif latest_snapshot_kind == "execution":
            current_phase = "phase3_bounded_executor"
            snapshot_next_action = str(
                execution_snapshot.get("workflow_eval", {}).get("suggested_next_action", "review_execution_summary")
            )
        elif latest_snapshot_kind == "planner":
            current_phase = "phase2_planner"
            snapshot_next_action = "review_planner_output"
        else:
            current_phase = self._current_phase_from_runs(ordered_runs)
            snapshot_next_action = None

        if ordered_pending_approvals:
            next_action = "await_human_approval"
        elif active_run is not None:
            next_action = f"continue_run:{active_run.command_type}"
        elif failed_steps:
            next_action = "triage_failed_step"
        elif snapshot_next_action is not None:
            next_action = snapshot_next_action
        else:
            next_action = "scan_next_lead_batch"

        if latest_snapshot_kind == "operator":
            updated_at = str(operator_snapshot.get("generated_at"))
        elif latest_snapshot_kind == "execution":
            updated_at = str(execution_snapshot.get("generated_at"))
        elif latest_snapshot_kind == "planner":
            updated_at = str(planner_snapshot.get("generated_at"))
        elif active_run is not None:
            updated_at = active_run.updated_at.isoformat()
        elif ordered_pending_approvals:
            updated_at = ordered_pending_approvals[0].created_at.isoformat()
        elif failed_steps:
            updated_at = failed_steps[0].failed_at.isoformat()
        else:
            updated_at = utc_now().isoformat()

        return MissionControlAutonomyVisibilityResponse(
            current_phase=current_phase,
            active_run=(
                MissionControlRunSummary(
                    id=active_run.id,
                    command_id=active_run.command_id,
                    business_id=active_run.business_id,
                    environment=active_run.environment,
                    command_type=active_run.command_type,
                    status=active_run.status,
                    parent_run_id=active_run.parent_run_id,
                    child_run_ids=sorted(child_run_ids_by_parent.get(active_run.id, [])),
                    trigger_run_id=active_run.trigger_run_id,
                    created_at=active_run.created_at,
                    updated_at=active_run.updated_at,
                    started_at=active_run.started_at,
                    completed_at=active_run.completed_at,
                    error_classification=active_run.error_classification,
                    error_message=active_run.error_message,
                )
                if active_run is not None
                else None
            ),
            pending_approval_count=len(ordered_pending_approvals),
            pending_approvals=[
                MissionControlApprovalSummary(
                    id=approval.id,
                    command_id=approval.command_id,
                    business_id=approval.business_id,
                    environment=approval.environment,
                    command_type=approval.command_type,
                    status=approval.status,
                    payload_snapshot=approval.payload_snapshot,
                    created_at=approval.created_at,
                    approved_at=approval.approved_at,
                    actor_id=approval.actor_id,
                )
                for approval in ordered_pending_approvals
            ],
            failed_steps=failed_steps,
            planner_review=(
                MissionControlPlannerReviewSummary.model_validate(planner_snapshot)
                if planner_snapshot is not None
                else None
            ),
            execution_review=(
                MissionControlExecutionReviewSummary.model_validate(execution_snapshot)
                if execution_snapshot is not None
                else None
            ),
            autonomous_operator=(
                MissionControlAutonomousOperatorSummary.model_validate(operator_snapshot)
                if operator_snapshot is not None
                else None
            ),
            lead_quality=lead_quality,
            confidence=confidence,
            next_action=next_action,
            updated_at=updated_at,
        )

    def get_turns(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlTurnsResponse:
        with self.client.transaction() as store:
            scoped_sessions_by_id = {
                session.id: session
                for session in store.sessions.values()
                if (org_id is None or session.org_id == org_id)
                and self._matches_scope(session.business_id, session.environment, business_id, environment)
            }
            turns = [turn for turn in store.turns.values() if turn.session_id in scoped_sessions_by_id]

        turns_by_id = {turn.id: turn for turn in turns}
        ordered_turns = sorted(turns, key=lambda turn: (turn.updated_at, turn.created_at), reverse=True)
        return MissionControlTurnsResponse(
            turns=[
                MissionControlTurnSummary(
                    id=turn.id,
                    session_id=turn.session_id,
                    org_id=getattr(turn, "org_id", scoped_sessions_by_id[turn.session_id].org_id),
                    business_id=scoped_sessions_by_id[turn.session_id].business_id,
                    environment=scoped_sessions_by_id[turn.session_id].environment,
                    agent_id=turn.agent_id,
                    agent_revision_id=turn.agent_revision_id,
                    turn_number=turn.turn_number,
                    state=turn.status,
                    retry_count=self._turn_retry_count(turn, turns_by_id),
                    resumed_from_turn_id=turn.resumed_from_turn_id,
                    updated_at=turn.updated_at,
                )
                for turn in ordered_turns
            ]
        )

    def get_approvals(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlApprovalsResponse:
        with self.client.transaction() as store:
            commands_by_id = dict(store.commands)
            approvals = [
                approval
                for approval in store.approvals.values()
                if approval.status == ApprovalStatus.PENDING
                and self._matches_actor_org(self._approval_org_id(approval, commands_by_id=commands_by_id), org_id)
                and self._matches_scope(approval.business_id, approval.environment, business_id, environment)
            ]
        ordered_approvals = sorted(approvals, key=lambda approval: approval.created_at, reverse=True)
        return MissionControlApprovalsResponse(
            approvals=[
                MissionControlApprovalSummary(
                    id=approval.id,
                    command_id=approval.command_id,
                    business_id=approval.business_id,
                    environment=approval.environment,
                    command_type=approval.command_type,
                    status=approval.status,
                    payload_snapshot=approval.payload_snapshot,
                    created_at=approval.created_at,
                    approved_at=approval.approved_at,
                    actor_id=approval.actor_id,
                )
                for approval in ordered_approvals
            ]
        )

    def get_agents(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAgentsResponse:
        agents = self.agent_registry_service.list_agents(
            org_id=org_id,
            business_id=business_id,
            environment=environment,
        )
        with self.client.transaction() as store:
            revisions_by_id = dict(store.agent_revisions)
            release_events_by_id = dict(store.release_events)
            release_event_ids_by_agent = {
                agent_id: list(event_ids)
                for agent_id, event_ids in store.release_event_ids_by_agent.items()
            }
        ordered_agents = sorted(agents, key=lambda agent: (agent.updated_at, agent.created_at), reverse=True)
        return MissionControlAgentsResponse(
            agents=[
                MissionControlAgentSummary(
                    id=agent.id,
                    business_id=agent.business_id,
                    environment=agent.environment,
                    name=agent.name,
                    description=agent.description,
                    active_revision_id=agent.active_revision_id,
                    active_revision_state=(
                        state.value if (state := self.agent_registry_service.get_agent_revision_state(agent)) is not None else None
                    ),
                    host_adapter=self._build_agent_host_adapter_summary(
                        agent,
                        revisions_by_id=revisions_by_id,
                    ),
                    release=self._build_agent_release_summary(
                        agent,
                        revisions_by_id=revisions_by_id,
                        release_events_by_id=release_events_by_id,
                        release_event_ids_by_agent=release_event_ids_by_agent,
                    ),
                    created_at=agent.created_at,
                    updated_at=agent.updated_at,
                )
                for agent in ordered_agents
            ]
        )

    def _build_agent_host_adapter_summary(
        self,
        agent,
        *,
        revisions_by_id: dict[str, Any],
    ) -> MissionControlHostAdapterSummary | None:
        if agent.active_revision_id is None:
            return None
        revision = revisions_by_id.get(agent.active_revision_id)
        if revision is None or getattr(revision, "host_adapter_kind", None) is None:
            return None
        try:
            adapter = self.host_adapter_registry.describe_adapter(revision.host_adapter_kind)
        except ValueError:
            return None
        return MissionControlHostAdapterSummary(
            kind=adapter.kind,
            enabled=adapter.enabled,
            display_name=adapter.display_name,
            adapter_details_label=adapter.adapter_details_label,
            capabilities=adapter.capabilities.model_copy(deep=True),
            disabled_reason=adapter.disabled_reason,
        )

    def get_settings_assets(
        self,
        *,
        org_id: str | None = None,
        agent_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAssetsResponse:
        assets = self.agent_asset_service.list_assets(
            agent_id=agent_id,
            business_id=business_id,
            environment=environment,
        )
        with self.client.transaction() as store:
            agents_by_id = dict(store.agents)
        if org_id is not None:
            assets = [
                asset
                for asset in assets
                if self._matches_actor_org(self._asset_org_id(asset, agents_by_id=agents_by_id), org_id)
            ]
        ordered_assets = sorted(assets, key=lambda asset: (asset.updated_at, asset.created_at), reverse=True)
        return MissionControlAssetsResponse(
            assets=[
                MissionControlAssetSummary(
                    id=asset.id,
                    agent_id=asset.agent_id,
                    business_id=asset.business_id,
                    environment=asset.environment,
                    asset_type=asset.asset_type,
                    label=asset.label,
                    connect_later=asset.connect_later,
                    status=asset.status,
                    binding_reference=asset.binding_reference,
                    updated_at=asset.updated_at,
                )
                for asset in ordered_assets
            ]
        )

    def get_assets(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAssetsResponse:
        return self.get_settings_assets(org_id=org_id, business_id=business_id, environment=environment)

    def get_provider_status(self) -> MissionControlProvidersStatusResponse:
        settings = get_settings()
        return MissionControlProvidersStatusResponse(
            sms=MissionControlProviderStatus(**get_textgrid_status(settings)),
            email=MissionControlProviderStatus(**get_resend_status(settings)),
        )

    def get_instantly_provider_extras(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> InstantlyProviderExtrasSnapshot:
        if not self._can_expose_unscoped_context(org_id):
            return self._empty_instantly_provider_extras_snapshot()
        return provider_extras_service.get_instantly_snapshot(
            business_id=business_id,
            environment=environment,
        )

    def get_secrets(
        self,
        *,
        org_id: str | None = None,
        actor_org_id: str | None = None,
    ) -> SecretListResponse:
        effective_org_id = self._resolve_actor_scoped_org_id(org_id, actor_org_id=actor_org_id)
        return SecretListResponse(secrets=secret_service.list_secrets(org_id=effective_org_id))

    def get_secret_bindings(self, *, revision_id: str, org_id: str | None = None) -> SecretBindingListResponse:
        self._require_revision_in_org(revision_id, org_id=org_id)
        return SecretBindingListResponse(bindings=secret_service.list_bindings_for_revision(revision_id))

    def get_audit(
        self,
        *,
        org_id: str | None = None,
        actor_org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> AuditListResponse:
        effective_org_id = self._resolve_actor_scoped_org_id(org_id, actor_org_id=actor_org_id)
        return AuditListResponse(
            events=audit_service.list_events(
                org_id=effective_org_id,
                agent_id=agent_id,
                agent_revision_id=agent_revision_id,
                session_id=session_id,
                run_id=run_id,
                resource_type=resource_type,
                resource_id=resource_id,
                event_type=event_type,
                limit=limit,
            )
        )

    def get_usage(
        self,
        *,
        org_id: str | None = None,
        actor_org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        kind: UsageEventKind | None = None,
        source_kind: str | None = None,
        limit: int | None = None,
    ) -> UsageResponse:
        effective_org_id = self._resolve_actor_scoped_org_id(org_id, actor_org_id=actor_org_id)
        return usage_service.list_usage(
            org_id=effective_org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            kind=kind,
            source_kind=source_kind,
            limit=limit,
        )

    def get_governance(self, *, org_id: str | None = None) -> MissionControlGovernanceResponse:
        effective_org_id = org_id or self._default_org_id()
        usage = self.get_usage(actor_org_id=effective_org_id, limit=10)
        return MissionControlGovernanceResponse(
            org_id=effective_org_id,
            pending_approvals=self.get_approvals(org_id=effective_org_id).approvals,
            secrets_health=self._build_secrets_health_snapshot(org_id=effective_org_id),
            recent_audit=self.get_audit(actor_org_id=effective_org_id, limit=10).events,
            usage_summary=usage.summary,
            recent_usage=usage.events,
        )

    def send_test_sms(self, request: MissionControlSmsTestRequest) -> MissionControlOutboundSendResponse:
        settings = get_settings()
        result = send_test_sms(settings, to=request.to, body=request.body)
        return MissionControlOutboundSendResponse(**result)

    def send_test_email(self, request: MissionControlEmailTestRequest) -> MissionControlOutboundSendResponse:
        settings = get_settings()
        result = send_test_email(
            settings,
            to=request.to,
            subject=request.subject,
            text=request.text,
            html=request.html,
        )
        return MissionControlOutboundSendResponse(**result)

    @staticmethod
    def _turn_retry_count(turn: Any, turns_by_id: dict[str, Any]) -> int:
        metadata = getattr(turn, "metadata", None)
        if isinstance(metadata, dict):
            retry_count = metadata.get("retry_count")
            if isinstance(retry_count, int) and retry_count >= 0:
                return retry_count
        retry_count = 0
        resumed_from_turn_id = getattr(turn, "resumed_from_turn_id", None)
        while resumed_from_turn_id:
            retry_count += 1
            resumed_turn = turns_by_id.get(resumed_from_turn_id)
            if resumed_turn is None:
                break
            resumed_from_turn_id = getattr(resumed_turn, "resumed_from_turn_id", None)
        return retry_count

    def _build_secrets_health_snapshot(self, *, org_id: str | None = None) -> MissionControlSecretsHealthSnapshot:
        with self.client.transaction() as store:
            agents = [
                agent
                for agent in store.agents.values()
                if self._matches_actor_org(self._record_org_id(agent), org_id)
                and getattr(agent, "active_revision_id", None) is not None
            ]
            revisions_by_id = dict(store.agent_revisions)
            secrets_by_id = dict(store.secrets)
            bindings_by_key = {
                (binding.agent_revision_id, binding.binding_name): binding for binding in store.secret_bindings.values()
            }

        revision_summaries: list[MissionControlRevisionSecretsHealthSummary] = []
        for agent in agents:
            revision_id = getattr(agent, "active_revision_id", None)
            if not isinstance(revision_id, str) or not revision_id:
                continue
            revision = revisions_by_id.get(revision_id)
            if revision is None:
                continue

            required_secrets = sorted(self._declared_secret_names(getattr(revision, "compatibility_metadata", {})))
            configured_secrets: list[str] = []
            missing_secrets: list[str] = []
            for binding_name in required_secrets:
                binding = bindings_by_key.get((revision.id, binding_name))
                secret = secrets_by_id.get(binding.secret_id) if binding is not None else None
                if binding is not None and secret is not None and getattr(secret, "org_id", None) == getattr(agent, "org_id", None):
                    configured_secrets.append(binding_name)
                else:
                    missing_secrets.append(binding_name)

            revision_summaries.append(
                MissionControlRevisionSecretsHealthSummary(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    agent_revision_id=revision.id,
                    business_id=agent.business_id,
                    environment=agent.environment,
                    status=("healthy" if not missing_secrets else "attention"),
                    required_secret_count=len(required_secrets),
                    configured_secret_count=len(configured_secrets),
                    missing_secret_count=len(missing_secrets),
                    required_secrets=required_secrets,
                    configured_secrets=configured_secrets,
                    missing_secrets=missing_secrets,
                )
            )

        ordered_revisions = sorted(revision_summaries, key=lambda revision: (revision.agent_name, revision.agent_revision_id))
        return MissionControlSecretsHealthSnapshot(
            active_revision_count=len(ordered_revisions),
            healthy_revision_count=sum(1 for revision in ordered_revisions if revision.status == "healthy"),
            attention_revision_count=sum(1 for revision in ordered_revisions if revision.status == "attention"),
            required_secret_count=sum(revision.required_secret_count for revision in ordered_revisions),
            configured_secret_count=sum(revision.configured_secret_count for revision in ordered_revisions),
            missing_secret_count=sum(revision.missing_secret_count for revision in ordered_revisions),
            revisions=ordered_revisions,
        )

    def _build_thread_summary(
        self,
        thread: MissionControlThreadRecord,
        *,
        runs_by_id: dict[str, object],
    ) -> MissionControlThreadSummary:
        last_message = thread.messages[-1] if thread.messages else None
        related_run_id = thread.related_run_id
        if related_run_id is not None:
            run = runs_by_id.get(related_run_id)
            if run is None:
                related_run_id = None

        return MissionControlThreadSummary(
            thread_id=thread.id,
            channel=thread.channel,
            status=thread.status,
            unread_count=thread.unread_count,
            last_message_preview=(last_message.body[:120] if last_message is not None else None),
            last_message_at=(last_message.created_at if last_message is not None else None),
            requires_approval=thread.requires_approval,
            related_run_id=related_run_id,
            related_approval_id=thread.related_approval_id,
            booking_status=self._context_value(thread.context, "booking_status"),
            sequence_status=self._context_value(thread.context, "sequence_status"),
            next_sequence_step=self._context_value(thread.context, "next_sequence_step"),
            manual_call_due_at=self._context_value(thread.context, "manual_call_due_at"),
            recent_reply_preview=self._recent_reply_preview(thread),
            reply_needs_review=bool(thread.context.get("reply_needs_review")),
            contact=thread.contact,
        )

    def _build_thread_detail(
        self,
        thread: MissionControlThreadRecord,
        *,
        runs_by_id: dict[str, object],
        approvals_by_id: dict[str, object],
    ) -> MissionControlThreadDetail:
        context = deepcopy(thread.context)
        if thread.related_run_id is not None:
            run = runs_by_id.get(thread.related_run_id)
            if run is not None:
                context.setdefault("related_run_id", run.id)
                context.setdefault("run_status", run.status.value)
        if thread.related_approval_id is not None:
            approval = approvals_by_id.get(thread.related_approval_id)
            if approval is not None:
                context.setdefault("related_approval_id", approval.id)
                context.setdefault("approval_status", approval.status.value)

        return MissionControlThreadDetail(
            thread_id=thread.id,
            channel=thread.channel,
            status=thread.status,
            unread_count=thread.unread_count,
            requires_approval=thread.requires_approval,
            related_run_id=thread.related_run_id,
            related_approval_id=thread.related_approval_id,
            booking_status=self._context_value(thread.context, "booking_status"),
            sequence_status=self._context_value(thread.context, "sequence_status"),
            next_sequence_step=self._context_value(thread.context, "next_sequence_step"),
            manual_call_due_at=self._context_value(thread.context, "manual_call_due_at"),
            recent_reply_preview=self._recent_reply_preview(thread),
            reply_needs_review=bool(thread.context.get("reply_needs_review")),
            contact=thread.contact,
            messages=sorted(thread.messages, key=lambda message: message.created_at),
            context=context,
        )

    def _build_lead_machine_summary(
        self,
        *,
        business_id: str | None,
        environment: str | None,
    ) -> MissionControlLeadMachineSummary | None:
        leads = self._lead_machine_leads(business_id=business_id, environment=environment)
        campaigns = self.campaigns_repository.list(business_id=business_id, environment=environment)
        suppressed_count = self._lead_machine_suppressed_count(
            leads=leads,
            business_id=business_id,
            environment=environment,
        )
        if not leads and not campaigns and suppressed_count == 0:
            return None
        return MissionControlLeadMachineSummary(
            active_campaign_count=sum(1 for campaign in campaigns if campaign.status == CampaignStatus.ACTIVE),
            ready_lead_count=sum(1 for lead in leads if lead.lifecycle_status == LeadLifecycleStatus.READY),
            active_lead_count=sum(1 for lead in leads if lead.lifecycle_status == LeadLifecycleStatus.ACTIVE),
            interested_lead_count=sum(1 for lead in leads if lead.lt_interest_status == LeadInterestStatus.INTERESTED),
            suppressed_lead_count=suppressed_count,
        )

    def _lead_quality_score(self, *, org_id: str | None = None, business_id: str | None, environment: str | None) -> float:
        if not self._can_expose_unscoped_context(org_id):
            return 0.0
        leads = self._lead_machine_leads(business_id=business_id, environment=environment)
        total = len(leads)
        if total == 0:
            return 0.0
        qualified = sum(
            1
            for lead in leads
            if lead.lifecycle_status in {LeadLifecycleStatus.READY, LeadLifecycleStatus.ACTIVE}
            or lead.lt_interest_status == LeadInterestStatus.INTERESTED
        )
        return round(qualified / total, 4)

    @classmethod
    def _snapshot_generated_at(cls, snapshot: dict[str, Any] | None) -> datetime | None:
        if snapshot is None:
            return None
        generated_at = snapshot.get("generated_at")
        if not isinstance(generated_at, str) or not generated_at:
            return None
        return cls._parse_datetime(generated_at)

    @classmethod
    def _latest_autonomy_snapshot(
        cls,
        *,
        planner_snapshot: dict[str, Any] | None,
        execution_snapshot: dict[str, Any] | None,
        operator_snapshot: dict[str, Any] | None,
    ) -> tuple[str | None, dict[str, Any] | None]:
        candidates: list[tuple[str, datetime, dict[str, Any]]] = []
        for kind, snapshot in (
            ("planner", planner_snapshot),
            ("execution", execution_snapshot),
            ("operator", operator_snapshot),
        ):
            generated_at = cls._snapshot_generated_at(snapshot)
            if generated_at is None or snapshot is None:
                continue
            candidates.append((kind, generated_at, snapshot))
        if not candidates:
            return None, None
        kind, _, snapshot = max(candidates, key=lambda item: item[1])
        return kind, snapshot

    @staticmethod
    def _current_phase_from_runs(
        runs: list[Any],
    ) -> str:
        command_types = {run.command_type for run in runs}
        if any(command_type.startswith("execute_") for command_type in command_types):
            return "phase3_bounded_executor"
        if any(command_type.startswith("plan_") for command_type in command_types):
            return "phase2_planner"
        return "phase1_lead_wedge"

    def _build_agent_release_summary(
        self,
        agent: Any,
        *,
        revisions_by_id: dict[str, Any],
        release_events_by_id: dict[str, Any],
        release_event_ids_by_agent: dict[str, list[str]],
    ) -> MissionControlAgentReleaseSummary | None:
        event_ids = release_event_ids_by_agent.get(agent.id, [])
        release_events = [release_events_by_id[event_id] for event_id in event_ids if event_id in release_events_by_id]
        if not release_events:
            return None
        release_events.sort(key=lambda event: (event.created_at, event.updated_at, event.id))
        latest_event = release_events[-1]
        if latest_event.resulting_active_revision_id != getattr(agent, "active_revision_id", None):
            return None
        resulting_revision = revisions_by_id.get(latest_event.resulting_active_revision_id)
        rollback_source_revision_id = None
        if latest_event.event_type == ReleaseEventType.ROLLBACK and resulting_revision is not None:
            rollback_source_revision_id = getattr(resulting_revision, "cloned_from_revision_id", None)
        return MissionControlAgentReleaseSummary(
            event_id=latest_event.id,
            event_type=latest_event.event_type,
            release_channel=latest_event.release_channel,
            created_at=latest_event.created_at,
            previous_active_revision_id=latest_event.previous_active_revision_id,
            target_revision_id=latest_event.target_revision_id,
            resulting_active_revision_id=latest_event.resulting_active_revision_id,
            rollback_source_revision_id=rollback_source_revision_id,
            evaluation=self._build_release_evaluation_summary(latest_event.evaluation_summary),
        )

    def _build_release_evaluation_summary(self, evaluation: Any | None) -> MissionControlReleaseEvaluationSummary | None:
        if evaluation is None:
            return None
        payload = evaluation.model_dump(mode="json") if hasattr(evaluation, "model_dump") else evaluation
        if not isinstance(payload, dict):
            return None
        try:
            return MissionControlReleaseEvaluationSummary.model_validate(payload)
        except Exception:
            return None

    def _build_run_replay_summary(self, run: Any) -> MissionControlRunReplaySummary | None:
        events = [event for event in getattr(run, "events", []) if isinstance(event, dict)]
        latest_requested = self._latest_run_event(events, event_type="replay_requested")
        latest_parent_resolution = self._latest_run_event(events, event_type="replay_child_bound")
        latest_child_lineage = self._latest_run_event(events, event_type="replay_lineage_bound")

        if latest_requested is not None:
            payload = self._event_payload(latest_requested)
            resolution_payload = self._event_payload(latest_parent_resolution)
            requested_at = self._event_created_at(latest_requested) or run.created_at
            resolved_at = self._event_created_at(latest_parent_resolution)
            child_run_id = self._payload_string(resolution_payload, "child_run_id") or self._payload_string(payload, "child_run_id")
            if resolved_at is None and child_run_id is not None:
                resolved_at = requested_at
            requires_approval = (
                bool(payload.get("requires_approval")) if "requires_approval" in payload else None
            )
            if child_run_id is not None:
                requires_approval = False
            approval_id = self._payload_string(resolution_payload, "approval_id") or self._payload_string(payload, "approval_id")
            return MissionControlRunReplaySummary(
                role="parent",
                requested_at=requested_at,
                resolved_at=resolved_at,
                replay_reason=self._payload_string(payload, "replay_reason") or getattr(run, "replay_reason", None),
                requires_approval=requires_approval,
                approval_id=approval_id,
                child_run_id=child_run_id,
                parent_run_id=getattr(run, "parent_run_id", None),
                triggering_actor=self._build_replay_actor_summary(payload.get("triggering_actor")),
                source=self._build_replay_revision_summary(payload.get("source")),
                replay=self._build_replay_revision_summary(payload.get("replay")),
            )

        if latest_child_lineage is not None or getattr(run, "parent_run_id", None) is not None or getattr(run, "replay_reason", None):
            payload = self._event_payload(latest_child_lineage)
            requested_at = self._event_created_at(latest_child_lineage) or run.created_at
            return MissionControlRunReplaySummary(
                role="child",
                requested_at=requested_at,
                resolved_at=requested_at,
                replay_reason=self._payload_string(payload, "replay_reason") or getattr(run, "replay_reason", None),
                child_run_id=getattr(run, "id", None),
                parent_run_id=self._payload_string(payload, "parent_run_id") or getattr(run, "parent_run_id", None),
                triggering_actor=self._build_replay_actor_summary(payload.get("triggering_actor")),
                source=self._build_replay_revision_summary(payload.get("source")),
                replay=self._build_replay_revision_summary(payload.get("replay")),
            )
        return None

    @staticmethod
    def _latest_run_event(events: list[dict[str, Any]], *, event_type: str) -> dict[str, Any] | None:
        matching = [event for event in events if event.get("event_type") == event_type]
        if not matching:
            return None
        matching.sort(key=lambda event: str(event.get("created_at", "")))
        return matching[-1]

    @classmethod
    def _event_created_at(cls, event: dict[str, Any] | None) -> datetime | None:
        if not isinstance(event, dict):
            return None
        raw = event.get("created_at")
        return cls._parse_datetime(raw) if isinstance(raw, str) else None

    @staticmethod
    def _event_payload(event: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(event, dict):
            return {}
        payload = event.get("payload")
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _payload_string(payload: dict[str, Any], key: str) -> str | None:
        raw = payload.get(key)
        return raw if isinstance(raw, str) and raw else None

    def _build_replay_actor_summary(self, payload: Any) -> MissionControlReplayActorSummary | None:
        if not isinstance(payload, dict):
            return None
        org_id = self._payload_string(payload, "org_id")
        actor_id = self._payload_string(payload, "actor_id")
        actor_type = self._payload_string(payload, "actor_type")
        if org_id is None or actor_id is None or actor_type is None:
            return None
        return MissionControlReplayActorSummary(org_id=org_id, actor_id=actor_id, actor_type=actor_type)

    def _build_replay_revision_summary(self, payload: Any) -> MissionControlReplayRevisionSummary | None:
        if not isinstance(payload, dict):
            return None
        try:
            return MissionControlReplayRevisionSummary.model_validate(payload)
        except Exception:
            return None

    def _lead_machine_leads(
        self,
        *,
        business_id: str | None,
        environment: str | None,
    ) -> list[LeadRecord]:
        return [
            lead
            for lead in self.leads_repository.list(business_id=business_id, environment=environment)
            if lead.source in {LeadSource.PROBATE_INTAKE, LeadSource.INSTANTLY_IMPORT, LeadSource.INSTANTLY_SYNC}
        ]

    def _lead_machine_suppressed_count(
        self,
        *,
        leads: list[LeadRecord],
        suppressions: list[Any] | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> int:
        suppressions = suppressions if suppressions is not None else self._safe_repo_call(
            lambda: self.suppression_repository.list_active(business_id=business_id, environment=environment)
        )
        targets = {
            record.lead_id or record.email or record.phone
            for record in suppressions
            if record.lead_id or record.email or record.phone
        }
        targets.update(lead.id for lead in leads if lead.id and lead.lifecycle_status == LeadLifecycleStatus.SUPPRESSED)
        return len(targets)

    def _build_lead_machine_timeline(
        self,
        *,
        lead_events: list[Any],
        automation_runs: list[Any],
        tasks: list[Any],
    ) -> list[MissionControlLeadMachineTimelineItem]:
        timeline: list[MissionControlLeadMachineTimelineItem] = []
        timeline.extend(
            MissionControlLeadMachineTimelineItem(
                kind="event",
                occurred_at=event.event_timestamp,
                summary=event.event_type,
                lead_id=event.lead_id,
                campaign_id=event.campaign_id,
            )
            for event in lead_events
        )
        timeline.extend(
            MissionControlLeadMachineTimelineItem(
                kind="run",
                occurred_at=run.completed_at or run.updated_at,
                summary=run.workflow_name,
                lead_id=run.lead_id,
                campaign_id=run.campaign_id,
                automation_run_id=run.id,
            )
            for run in automation_runs
        )
        timeline.extend(
            MissionControlLeadMachineTimelineItem(
                kind="task",
                occurred_at=task.due_at or task.updated_at,
                summary=task.title,
                lead_id=task.lead_id,
                task_id=task.id,
            )
            for task in tasks
            if task.id is not None
        )
        timeline.sort(key=lambda item: item.occurred_at, reverse=True)
        return timeline[:10]

    @staticmethod
    def _safe_repo_call(loader: Any) -> Any:
        try:
            return loader()
        except NotImplementedError:
            return []

    @staticmethod
    def _context_value(context: dict[str, Any], key: str) -> str | None:
        value = context.get(key)
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @classmethod
    def _is_due_manual_call(cls, context: dict[str, Any], *, now: datetime) -> bool:
        if cls._context_value(context, "booking_status") == "booked":
            return False
        due_at = cls._parse_datetime(cls._context_value(context, "manual_call_due_at"))
        if due_at is None:
            return False
        return due_at <= now

    @staticmethod
    def _recent_reply_preview(thread: MissionControlThreadRecord) -> str | None:
        inbound_messages = [message for message in thread.messages if message.direction == "inbound"]
        if not inbound_messages:
            return None
        return inbound_messages[-1].body

    @classmethod
    def _has_marketing_context(cls, context: dict[str, Any]) -> bool:
        return any(
            [
                cls._context_value(context, "booking_status") is not None,
                cls._context_value(context, "sequence_status") is not None,
                cls._context_value(context, "manual_call_due_at") is not None,
                bool(context.get("reply_needs_review")),
            ]
        )

    def _empty_instantly_provider_extras_snapshot(self) -> InstantlyProviderExtrasSnapshot:
        settings = get_settings()
        denied_note = "Tenant-scoped provider extras projection is not available yet for non-internal orgs."

        def family() -> ProviderExtraFamilyStatus:
            return ProviderExtraFamilyStatus(
                configured=False,
                status="configuration_missing",
                projection_mode="scaffold",
                projected_record_count=0,
                counts={},
                notes=[denied_note],
            )

        return InstantlyProviderExtrasSnapshot(
            configured=False,
            transport_ready=False,
            webhook_signing_configured=False,
            base_url=settings.instantly_base_url,
            batch_size=settings.instantly_batch_size,
            batch_wait_seconds=settings.instantly_batch_wait_seconds,
            summary=ProviderExtrasSummary(
                configured_family_count=0,
                projected_family_count=0,
                campaign_count=0,
                lead_count=0,
                workspace_count=0,
                webhook_receipt_count=0,
                blocklist_count=0,
            ),
            labels=family(),
            tags=family(),
            verification=family(),
            deliverability=family(),
            blocklists=family(),
            inbox_placement=family(),
            crm_actions=family(),
            workspace_resources=family(),
            checked_at=utc_now(),
        )

    def _require_revision_in_org(self, revision_id: str, *, org_id: str | None = None) -> tuple[Any, Any]:
        revision = self.agent_registry_service.agents_repository.get_revision(revision_id)
        if revision is None:
            raise ValueError("Agent revision not found")
        agent = self.agent_registry_service.agents_repository.get_agent(revision.agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            raise ValueError("Agent revision not found")
        return revision, agent

    @classmethod
    def _resolve_actor_scoped_org_id(cls, request_org_id: str | None, *, actor_org_id: str | None = None) -> str | None:
        if actor_org_id is None:
            return request_org_id
        if request_org_id in (None, cls._default_org_id()):
            return actor_org_id
        if request_org_id != actor_org_id:
            raise ValueError("Org id must match actor context")
        return actor_org_id

    @staticmethod
    def _record_org_id(record: Any) -> str | None:
        if isinstance(record, dict):
            raw = record.get("org_id")
        else:
            raw = getattr(record, "org_id", None)
        return raw if isinstance(raw, str) and raw else None

    @classmethod
    def _payload_org_id(cls, payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        raw = payload.get("org_id")
        if isinstance(raw, str) and raw:
            return raw
        actor_context = payload.get("actor_context")
        if isinstance(actor_context, dict):
            actor_org_id = actor_context.get("org_id")
            if isinstance(actor_org_id, str) and actor_org_id:
                return actor_org_id
        return None

    @staticmethod
    def _default_org_id() -> str:
        return get_settings().default_org_id

    @staticmethod
    def _declared_secret_names(compatibility_metadata: object) -> set[str]:
        if not isinstance(compatibility_metadata, dict):
            return set()
        raw_declared = compatibility_metadata.get("requires_secrets")
        if not isinstance(raw_declared, Iterable) or isinstance(raw_declared, str | bytes):
            return set()
        return {value for value in raw_declared if isinstance(value, str) and value}

    @classmethod
    def _command_org_id(cls, command: Any | None) -> str:
        return cls._payload_org_id(getattr(command, "payload", None)) or cls._default_org_id()

    @classmethod
    def _approval_org_id(cls, approval: Any, *, commands_by_id: dict[str, Any]) -> str:
        return (
            cls._payload_org_id(getattr(approval, "payload_snapshot", None))
            or cls._command_org_id(commands_by_id.get(getattr(approval, "command_id", "")))
        )

    @classmethod
    def _run_org_id(cls, run: Any, *, commands_by_id: dict[str, Any]) -> str:
        return cls._command_org_id(commands_by_id.get(getattr(run, "command_id", "")))

    @classmethod
    def _thread_org_id(
        cls,
        thread: MissionControlThreadRecord,
        *,
        approvals_by_id: dict[str, Any],
        runs_by_id: dict[str, Any],
        commands_by_id: dict[str, Any],
    ) -> str:
        return (
            cls._payload_org_id(thread.context)
            or (
                cls._approval_org_id(approvals_by_id[thread.related_approval_id], commands_by_id=commands_by_id)
                if thread.related_approval_id is not None and thread.related_approval_id in approvals_by_id
                else None
            )
            or (
                cls._run_org_id(runs_by_id[thread.related_run_id], commands_by_id=commands_by_id)
                if thread.related_run_id is not None and thread.related_run_id in runs_by_id
                else None
            )
            or cls._default_org_id()
        )

    @classmethod
    def _asset_org_id(cls, asset: Any, *, agents_by_id: dict[str, Any]) -> str:
        return cls._record_org_id(agents_by_id.get(getattr(asset, "agent_id", ""))) or cls._default_org_id()

    @classmethod
    def _matches_actor_org(cls, record_org_id: str | None, actor_org_id: str | None) -> bool:
        if actor_org_id is None:
            return True
        return (record_org_id or cls._default_org_id()) == actor_org_id

    @classmethod
    def _can_expose_unscoped_context(cls, org_id: str | None) -> bool:
        return org_id is None or org_id == cls._default_org_id()

    @staticmethod
    def _matches_scope(
        record_business_id: str,
        record_environment: str,
        business_id: str | None,
        environment: str | None,
    ) -> bool:
        if business_id is not None and record_business_id != business_id:
            return False
        if environment is not None and record_environment != environment:
            return False
        return True


mission_control_service = MissionControlService()
