from __future__ import annotations

from copy import deepcopy
from datetime import UTC
from datetime import datetime
from typing import Any

from app.core.config import get_settings
from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.opportunities import OpportunitiesRepository
from app.db.suppression import SuppressionRepository
from app.db.tasks import TasksRepository
from app.models.approvals import ApprovalStatus
from app.models.campaigns import CampaignMembershipStatus, CampaignStatus
from app.models.leads import LeadInterestStatus, LeadLifecycleStatus, LeadRecord, LeadSource
from app.models.tasks import TaskStatus, TaskType
from app.models.suppression import SuppressionRecord, SuppressionScope, SuppressionSource
from app.models.mission_control import (
    MissionControlAgentsResponse,
    MissionControlAgentSummary,
    MissionControlApprovalsResponse,
    MissionControlApprovalSummary,
    MissionControlAssetsResponse,
    MissionControlAssetSummary,
    MissionControlDashboardResponse,
    MissionControlEmailTestRequest,
    MissionControlInboxResponse,
    MissionControlInboxSummary,
    MissionControlLeadMachineCampaignSummary,
    MissionControlLeadMachineCampaignsSummary,
    MissionControlLeadMachineQueueSummary,
    MissionControlLeadMachineResponse,
    MissionControlLeadMachineSummary,
    MissionControlOutboundSendResponse,
    MissionControlProviderStatus,
    MissionControlProvidersStatusResponse,
    MissionControlSmsTestRequest,
    MissionControlLeadMachineTaskSummary,
    MissionControlLeadMachineTasksSummary,
    MissionControlLeadMachineTimelineItem,
    MissionControlLeadMachineTimelineSummary,
    MissionControlOpportunityStageSummary,
    MissionControlRunSummary,
    MissionControlRunsResponse,
    MissionControlTaskActionResponse,
    MissionControlTaskSummary,
    MissionControlTasksResponse,
    MissionControlThreadDetail,
    MissionControlThreadRecord,
    MissionControlThreadSummary,
    MissionControlTurnSummary,
    MissionControlTurnsResponse,
    MissionControlLeadActionResponse,
)
from app.models.runs import RunStatus
from app.models.provider_extras import InstantlyProviderExtrasSnapshot
from app.models.audit import AuditListResponse
from app.models.secrets import SecretBindingListResponse, SecretListResponse
from app.models.usage import UsageEventKind, UsageResponse
from app.services.agent_asset_service import AgentAssetService, agent_asset_service
from app.services.agent_registry_service import AgentRegistryService, agent_registry_service
from app.services.approval_service import ApprovalService, approval_service
from app.services.audit_service import audit_service
from app.services.provider_extras_service import provider_extras_service
from app.services.providers.resend import get_resend_status, send_test_email
from app.services.providers.textgrid import get_textgrid_status, send_test_sms
from app.services.secrets_service import secret_service
from app.services.usage_service import usage_service

ACTIVE_RUN_STATUSES = {RunStatus.QUEUED, RunStatus.IN_PROGRESS}


class MissionControlService:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        approval_service_dependency: ApprovalService | None = None,
        agent_registry_service_dependency: AgentRegistryService | None = None,
        agent_asset_service_dependency: AgentAssetService | None = None,
        opportunities_repository: OpportunitiesRepository | None = None,
        campaigns_repository: CampaignsRepository | None = None,
        leads_repository: LeadsRepository | None = None,
        suppression_repository: SuppressionRepository | None = None,
        campaign_memberships_repository: CampaignMembershipsRepository | None = None,
        lead_events_repository: LeadEventsRepository | None = None,
        automation_runs_repository: AutomationRunsRepository | None = None,
        tasks_repository: TasksRepository | None = None,
    ) -> None:
        self.client = client or get_control_plane_client()
        self.approval_service = approval_service_dependency or approval_service
        self.agent_registry_service = agent_registry_service_dependency or agent_registry_service
        self.agent_asset_service = agent_asset_service_dependency or agent_asset_service
        self.opportunities_repository = opportunities_repository or OpportunitiesRepository(client=self.client)
        self.campaigns_repository = campaigns_repository or CampaignsRepository(client=self.client)
        self.leads_repository = leads_repository or LeadsRepository(client=self.client)
        self.suppression_repository = suppression_repository or SuppressionRepository(client=self.client)
        self.campaign_memberships_repository = campaign_memberships_repository or CampaignMembershipsRepository(client=self.client)
        self.lead_events_repository = lead_events_repository or LeadEventsRepository(client=self.client)
        self.automation_runs_repository = automation_runs_repository or AutomationRunsRepository(client=self.client)
        self.tasks_repository = tasks_repository or TasksRepository(client=self.client)

    def upsert_thread_projection(self, thread: MissionControlThreadRecord) -> MissionControlThreadRecord:
        with self.client.transaction() as store:
            store.mission_control_threads[thread.id] = thread.model_copy(deep=True)
            return store.mission_control_threads[thread.id]

    def get_dashboard(self, *, business_id: str | None = None, environment: str | None = None) -> MissionControlDashboardResponse:
        with self.client.transaction() as store:
            approvals = [
                approval
                for approval in store.approvals.values()
                if approval.status == ApprovalStatus.PENDING
                and self._matches_scope(approval.business_id, approval.environment, business_id, environment)
            ]
            runs = [
                run
                for run in store.runs.values()
                if self._matches_scope(run.business_id, run.environment, business_id, environment)
            ]
            agents = [
                agent
                for agent in store.agents.values()
                if self._matches_scope(agent.business_id, agent.environment, business_id, environment)
            ]
            threads = [
                thread if isinstance(thread, MissionControlThreadRecord) else MissionControlThreadRecord.model_validate(thread)
                for thread in store.mission_control_threads.values()
                if self._matches_scope(thread.business_id, thread.environment, business_id, environment)
            ]
        opportunities = self.opportunities_repository.list(business_id=business_id, environment=environment)
        lead_machine_summary = self._build_lead_machine_summary(business_id=business_id, environment=environment)

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
        opportunity_stage_counts: dict[tuple[str, str], int] = {}
        for opportunity in opportunities:
            lane = str(opportunity.source_lane)
            stage = str(opportunity.stage)
            key = (lane, stage)
            opportunity_stage_counts[key] = opportunity_stage_counts.get(key, 0) + 1
        opportunity_stage_summaries = [
            MissionControlOpportunityStageSummary(source_lane=lane, stage=stage, count=count)
            for (lane, stage), count in sorted(opportunity_stage_counts.items())
        ]
        has_marketing_context = any(self._has_marketing_context(thread.context) for thread in threads)
        has_lead_machine_context = lead_machine_summary is not None
        has_opportunity_context = bool(opportunity_stage_summaries)
        if failed_run_count > 0:
            system_status = "degraded"
        elif approvals or unread_conversation_count or active_run_count:
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
            lead_machine_summary=(lead_machine_summary if has_lead_machine_context else None),
            opportunity_count=(sum(opportunity_stage_counts.values()) if has_opportunity_context else None),
            opportunity_stage_summaries=(opportunity_stage_summaries if has_opportunity_context else None),
            system_status=system_status,
            updated_at=latest_updated_at.isoformat(),
        )

    def get_inbox(
        self,
        *,
        selected_thread_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlInboxResponse:
        with self.client.transaction() as store:
            threads = [
                thread if isinstance(thread, MissionControlThreadRecord) else MissionControlThreadRecord.model_validate(thread)
                for thread in store.mission_control_threads.values()
                if self._matches_scope(thread.business_id, thread.environment, business_id, environment)
            ]
            runs_by_id = dict(store.runs)
            approvals_by_id = dict(store.approvals)

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
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlTasksResponse:
        with self.client.transaction() as store:
            threads = [
                thread if isinstance(thread, MissionControlThreadRecord) else MissionControlThreadRecord.model_validate(thread)
                for thread in store.mission_control_threads.values()
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

        ordered_tasks = sorted(tasks, key=lambda task: task.manual_call_due_at)
        return MissionControlTasksResponse(due_count=len(ordered_tasks), tasks=ordered_tasks)

    def complete_task_for_thread(
        self,
        *,
        thread_id: str,
        notes: str | None = None,
        follow_up_outcome: str | None = None,
    ) -> MissionControlTaskActionResponse:
        thread = self._require_thread_projection(thread_id)
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
        reason: str,
        note: str | None = None,
    ) -> MissionControlLeadActionResponse:
        thread = self._require_thread_projection(thread_id)
        lead = self._resolve_lead_for_thread(thread)
        if lead is None or lead.id is None:
            raise KeyError(thread_id)

        now = utc_now()
        suppression = self.suppression_repository.upsert(
            SuppressionRecord(
                business_id=lead.business_id,
                environment=lead.environment,
                lead_id=lead.id,
                email=lead.email,
                phone=lead.phone,
                scope=SuppressionScope.GLOBAL,
                reason=reason,
                source=SuppressionSource.MANUAL,
                idempotency_key=f"mission-control:suppress:{thread.id}",
                metadata={"thread_id": thread.id, "note": note, "operator_action": "suppress"},
            )
        )

        self.leads_repository.upsert(
            lead.model_copy(
                update={
                    "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                    "updated_at": now,
                    "last_touched_at": now,
                }
            )
        )
        self._set_campaign_memberships_status(lead_id=lead.id, status=CampaignMembershipStatus.SUPPRESSED)
        self._cancel_open_tasks_for_lead(lead_id=lead.id, suppression_reason=reason, note=note)
        self.upsert_thread_projection(
            thread.model_copy(
                update={
                    "context": self._merge_thread_context(
                        thread.context,
                        {
                            "sequence_status": "suppressed",
                            "reply_needs_review": False,
                            "manual_call_due_at": None,
                            "suppression_reason": reason,
                            "suppressed_at": now.isoformat(),
                            "last_operator_note": note,
                        },
                    ),
                    "updated_at": now,
                }
            )
        )

        return MissionControlLeadActionResponse(
            thread_id=thread.id,
            lead_name=thread.contact.display_name,
            action="suppressed",
            suppression_count=len(
                self.suppression_repository.list_active(business_id=lead.business_id, environment=lead.environment)
            ),
            lead_status=str(LeadLifecycleStatus.SUPPRESSED),
            note=note,
            reason=reason,
            updated_at=now,
        )

    def unsuppress_thread(
        self,
        *,
        thread_id: str,
        note: str | None = None,
    ) -> MissionControlLeadActionResponse:
        thread = self._require_thread_projection(thread_id)
        lead = self._resolve_lead_for_thread(thread)
        if lead is None or lead.id is None:
            raise KeyError(thread_id)

        now = utc_now()
        archived_count = self._archive_lead_suppressions(lead_id=lead.id, note=note)
        restored_membership_count = self._set_campaign_memberships_status(lead_id=lead.id, status=CampaignMembershipStatus.ACTIVE)
        lead_after_restore = self.leads_repository.upsert(
            lead.model_copy(
                update={
                    "lifecycle_status": LeadLifecycleStatus.ACTIVE if restored_membership_count > 0 else LeadLifecycleStatus.READY,
                    "updated_at": now,
                    "last_touched_at": now,
                }
            )
        )
        self.upsert_thread_projection(
            thread.model_copy(
                update={
                    "context": self._merge_thread_context(
                        thread.context,
                        {
                            "sequence_status": "active",
                            "suppression_reason": None,
                            "suppressed_at": None,
                            "last_operator_note": note,
                        },
                    ),
                    "updated_at": now,
                }
            )
        )

        return MissionControlLeadActionResponse(
            thread_id=thread.id,
            lead_name=thread.contact.display_name,
            action="unsuppressed",
            suppression_count=archived_count,
            lead_status=str(lead_after_restore.lifecycle_status),
            note=note,
            reason=None,
            updated_at=now,
        )

    def _require_thread_projection(self, thread_id: str) -> MissionControlThreadRecord:
        with self.client.transaction() as store:
            thread = store.mission_control_threads.get(thread_id)
            if thread is None:
                raise KeyError(thread_id)
            if isinstance(thread, MissionControlThreadRecord):
                return thread
            return MissionControlThreadRecord.model_validate(thread)

    def _resolve_lead_for_thread(self, thread: MissionControlThreadRecord) -> LeadRecord | None:
        lead_id = self._context_value(thread.context, "lead_id")
        if lead_id is not None:
            lead = self.leads_repository.get(lead_id)
            if lead is not None:
                return lead
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
        now = utc_now()
        archived_count = 0
        lead = self.leads_repository.get(lead_id)
        if lead is None:
            return 0
        for suppression in self.suppression_repository.list_active(business_id=lead.business_id, environment=lead.environment):
            if suppression.lead_id != lead_id and suppression.email != lead.email and suppression.phone != lead.phone:
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

    def get_lead_machine(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        lead_id: str | None = None,
        campaign_id: str | None = None,
        limit: int | None = None,
    ) -> MissionControlLeadMachineResponse:
        leads = self._lead_machine_leads(business_id=business_id, environment=environment)
        campaigns = self.campaigns_repository.list(business_id=business_id, environment=environment)
        memberships = self._safe_repo_call(
            lambda: [
                membership
                for campaign in campaigns
                if campaign.id is not None
                for membership in self.campaign_memberships_repository.list_for_campaign(campaign.id)
            ]
        )
        lead_events = self.lead_events_repository.list(business_id=business_id, environment=environment)
        automation_runs = self.automation_runs_repository.list(business_id=business_id, environment=environment)
        tasks = self.tasks_repository.list(business_id=business_id, environment=environment)

        lead_ids = {lead.id for lead in leads if lead.id is not None}
        campaign_ids = {campaign.id for campaign in campaigns if campaign.id is not None}
        filtered_memberships = [
            membership
            for membership in memberships
            if membership.lead_id in lead_ids or membership.campaign_id in campaign_ids
        ]
        filtered_events = [
            event
            for event in lead_events
            if event.lead_id in lead_ids or (event.campaign_id is not None and event.campaign_id in campaign_ids)
        ]
        filtered_runs = [
            run
            for run in automation_runs
            if run.lead_id in lead_ids or (run.campaign_id is not None and run.campaign_id in campaign_ids)
        ]
        filtered_tasks = [task for task in tasks if task.lead_id in lead_ids]

        memberships_by_campaign: dict[str, list[Any]] = {}
        for membership in filtered_memberships:
            memberships_by_campaign.setdefault(membership.campaign_id, []).append(membership)

        updated_at_candidates: list[datetime] = []
        updated_at_candidates.extend(lead.updated_at for lead in leads)
        updated_at_candidates.extend(campaign.updated_at for campaign in campaigns)
        updated_at_candidates.extend(task.updated_at for task in filtered_tasks)
        updated_at_candidates.extend(run.updated_at for run in filtered_runs)
        updated_at_candidates.extend(event.received_at for event in filtered_events)

        return MissionControlLeadMachineResponse(
            queue=MissionControlLeadMachineQueueSummary(
                total_lead_count=len(leads),
                ready_count=sum(1 for lead in leads if lead.lifecycle_status == LeadLifecycleStatus.READY),
                active_count=sum(1 for lead in leads if lead.lifecycle_status == LeadLifecycleStatus.ACTIVE),
                suppressed_count=self._lead_machine_suppressed_count(
                    leads=leads,
                    business_id=business_id,
                    environment=environment,
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
                    for task in sorted(
                        filtered_tasks,
                        key=lambda record: (record.due_at or record.updated_at, record.created_at),
                        reverse=True,
                    )[:10]
                    if task.id is not None
                ],
            ),
            timeline=MissionControlLeadMachineTimelineSummary(
                items=self._build_lead_machine_timeline(
                    lead_events=filtered_events,
                    automation_runs=filtered_runs,
                    tasks=filtered_tasks,
                )
            ),
            updated_at=max(updated_at_candidates, default=utc_now()).isoformat(),
        )

    def get_runs(self, *, business_id: str | None = None, environment: str | None = None) -> MissionControlRunsResponse:
        with self.client.transaction() as store:
            runs = [
                run
                for run in store.runs.values()
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
                )
                for run in ordered_runs
            ]
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
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlApprovalsResponse:
        approvals = self.approval_service.list_approvals(
            business_id=business_id,
            environment=environment,
            status=ApprovalStatus.PENDING,
        )
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
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAgentsResponse:
        agents = self.agent_registry_service.list_agents(business_id=business_id, environment=environment)
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
                    created_at=agent.created_at,
                    updated_at=agent.updated_at,
                )
                for agent in ordered_agents
            ]
        )

    def get_settings_assets(
        self,
        *,
        agent_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAssetsResponse:
        assets = self.agent_asset_service.list_assets(
            agent_id=agent_id,
            business_id=business_id,
            environment=environment,
        )
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
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAssetsResponse:
        return self.get_settings_assets(business_id=business_id, environment=environment)

    def get_provider_status(self) -> MissionControlProvidersStatusResponse:
        settings = get_settings()
        return MissionControlProvidersStatusResponse(
            sms=MissionControlProviderStatus(**get_textgrid_status(settings)),
            email=MissionControlProviderStatus(**get_resend_status(settings)),
        )

    def get_instantly_provider_extras(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> InstantlyProviderExtrasSnapshot:
        return provider_extras_service.get_instantly_snapshot(
            business_id=business_id,
            environment=environment,
        )

    def get_secrets(self, *, org_id: str | None = None) -> SecretListResponse:
        return SecretListResponse(secrets=secret_service.list_secrets(org_id=org_id))

    def get_secret_bindings(self, *, revision_id: str) -> SecretBindingListResponse:
        return SecretBindingListResponse(bindings=secret_service.list_bindings_for_revision(revision_id))

    def get_audit(
        self,
        *,
        org_id: str | None = None,
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        session_id: str | None = None,
        run_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        event_type: str | None = None,
        limit: int | None = None,
    ) -> AuditListResponse:
        return AuditListResponse(
            events=audit_service.list_events(
                org_id=org_id,
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
        agent_id: str | None = None,
        agent_revision_id: str | None = None,
        kind: UsageEventKind | None = None,
        source_kind: str | None = None,
        limit: int | None = None,
    ) -> UsageResponse:
        return usage_service.list_usage(
            org_id=org_id,
            agent_id=agent_id,
            agent_revision_id=agent_revision_id,
            kind=kind,
            source_kind=source_kind,
            limit=limit,
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
        business_id: str | None,
        environment: str | None,
    ) -> int:
        suppressions = self._safe_repo_call(
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
