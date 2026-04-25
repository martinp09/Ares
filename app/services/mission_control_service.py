from __future__ import annotations

from copy import deepcopy
import json
from collections import Counter
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.suppression import SuppressionRepository
from app.db.tasks import TasksRepository
from app.db.title_packets import TitlePacketsRepository
from app.models.approvals import ApprovalStatus
from app.models.mission_control import (
    MissionControlAgentSummary,
    MissionControlAgentsResponse,
    MissionControlApprovalSummary,
    MissionControlApprovalsResponse,
    MissionControlAssetSummary,
    MissionControlAssetsResponse,
    MissionControlDashboardResponse,
    MissionControlEmailTestRequest,
    MissionControlInboxResponse,
    MissionControlInboxSummary,
    MissionControlLeadMachineLeadRecord,
    MissionControlLeadMachineResponse,
    MissionControlLeadMachineSummary,
    MissionControlLeadMachineTaskRecord,
    MissionControlLeadMachineTimelineRecord,
    MissionControlOutboundSendResponse,
    MissionControlProviderStatus,
    MissionControlProvidersStatusResponse,
    MissionControlRunSummary,
    MissionControlRunsResponse,
    MissionControlSmsTestRequest,
    MissionControlTaskSummary,
    MissionControlTasksResponse,
    MissionControlThreadDetail,
    MissionControlThreadRecord,
    MissionControlThreadSummary,
    MissionControlTurnSummary,
    MissionControlTurnsResponse,
)
from app.models.runs import RunStatus
from app.models.tasks import TaskStatus
from app.models.provider_extras import InstantlyProviderExtrasSnapshot
from app.services.providers.resend import get_resend_status, send_test_email
from app.services.providers.textgrid import get_textgrid_status, send_test_sms
from app.services.audit_service import audit_service
from app.services.provider_extras_service import provider_extras_service
from app.services.secrets_service import secret_service
from app.services.usage_service import usage_service
from app.models.audit import AuditListResponse
from app.models.secrets import SecretListResponse, SecretBindingListResponse
from app.models.usage import UsageEventKind, UsageResponse

ACTIVE_RUN_STATUSES = {RunStatus.QUEUED, RunStatus.IN_PROGRESS}


class MissionControlService:
    def __init__(self, client: ControlPlaneClient | None = None) -> None:
        self.client = client or get_control_plane_client()
        self.leads_repository = LeadsRepository(self.client)
        self.lead_events_repository = LeadEventsRepository(self.client)
        self.suppression_repository = SuppressionRepository(self.client)
        self.tasks_repository = TasksRepository(self.client)
        self.title_packets_repository = TitlePacketsRepository(self.client)

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
            threads = [
                thread
                for thread in store.mission_control_threads.values()
                if self._matches_scope(thread.business_id, thread.environment, business_id, environment)
            ]
            agents = [
                agent
                for agent in store.agents.values()
                if self._matches_scope(agent.business_id, agent.environment, business_id, environment)
            ]

        distinct_channels = {thread.channel for thread in threads}
        pending_leads = [thread for thread in threads if thread.status in {"open", "waiting"} and thread.unread_count > 0]
        booked_leads = [thread for thread in threads if self._thread_booking_status(thread) == "booked"]
        active_enrollments = [
            thread
            for thread in threads
            if self._thread_sequence_status(thread) not in {None, "complete", "completed"}
            and self._thread_booking_status(thread) != "booked"
        ]
        manual_calls_due = [thread for thread in threads if self._thread_manual_call_due_at(thread)]
        replies_needing_review = [thread for thread in threads if self._thread_reply_needs_review(thread)]
        failed_runs = [run for run in runs if run.status == RunStatus.FAILED]
        recent_completed_runs = [run for run in runs if run.status == RunStatus.COMPLETED]
        system_status = "healthy"
        if failed_runs:
            system_status = "watch" if len(failed_runs) < max(len(runs), 1) else "degraded"

        return MissionControlDashboardResponse(
            approval_count=len(approvals),
            active_run_count=sum(1 for run in runs if run.status in ACTIVE_RUN_STATUSES),
            failed_run_count=len(failed_runs),
            active_agent_count=sum(1 for agent in agents if agent.active_revision_id is not None),
            unread_conversation_count=sum(thread.unread_count for thread in threads),
            busy_channel_count=len(distinct_channels),
            recent_completed_count=len(recent_completed_runs),
            pending_lead_count=len(pending_leads),
            booked_lead_count=len(booked_leads),
            active_non_booker_enrollment_count=len(active_enrollments),
            due_manual_call_count=len(manual_calls_due),
            replies_needing_review_count=len(replies_needing_review),
            system_status=system_status,
            updated_at=datetime.now(UTC),
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
        with self.client.transaction() as store:
            approvals = [
                approval
                for approval in store.approvals.values()
                if approval.status == ApprovalStatus.PENDING
                and self._matches_scope(approval.business_id, approval.environment, business_id, environment)
            ]
            commands_by_id = dict(store.commands)

        ordered_approvals = sorted(approvals, key=lambda approval: approval.created_at, reverse=True)
        summary_rows = []
        for approval in ordered_approvals:
            command = commands_by_id.get(approval.command_id)
            command_type = command.command_type if command is not None else approval.command_type
            payload_preview = json.dumps(approval.payload_snapshot, sort_keys=True)
            if len(payload_preview) > 120:
                payload_preview = f"{payload_preview[:117]}..."
            summary_rows.append(
                MissionControlApprovalSummary(
                    id=approval.id,
                    title=f"Approve {command_type.replace('_', ' ')}",
                    reason=self._approval_reason(command_type),
                    risk_level=self._approval_risk_level(command_type),
                    status=approval.status.value,
                    command_type=command_type,
                    requested_at=approval.created_at,
                    payload_preview=payload_preview,
                )
            )
        return MissionControlApprovalsResponse(approvals=summary_rows)

    def get_tasks(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlTasksResponse:
        with self.client.transaction() as store:
            threads = [
                thread
                for thread in store.mission_control_threads.values()
                if self._matches_scope(thread.business_id, thread.environment, business_id, environment)
            ]

        ordered_threads = sorted(
            [thread for thread in threads if self._thread_manual_call_due_at(thread) or self._thread_reply_needs_review(thread)],
            key=lambda thread: self._thread_manual_call_due_at(thread) or thread.updated_at.isoformat(),
        )
        tasks = [
            MissionControlTaskSummary(
                thread_id=thread.id,
                lead_name=thread.contact.display_name,
                channel=thread.channel,
                booking_status=self._thread_booking_status(thread) or ("booked" if thread.status == "closed" else "pending"),
                sequence_status=self._thread_sequence_status(thread) or thread.context.get("sequence_status", "idle"),
                next_sequence_step=self._thread_next_sequence_step(thread)
                or thread.context.get("next_sequence_step")
                or thread.context.get("next_best_action", "Inspect thread"),
                manual_call_due_at=self._thread_manual_call_due_at(thread) or "not scheduled",
                recent_reply_preview=self._thread_recent_reply_preview(thread),
                reply_needs_review=self._thread_reply_needs_review(thread),
            )
            for thread in ordered_threads
        ]
        return MissionControlTasksResponse(due_count=len(tasks), tasks=tasks)

    def get_lead_machine(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        lead_id: str | None = None,
        campaign_id: str | None = None,
        limit: int | None = None,
    ) -> MissionControlLeadMachineResponse:
        with self.client.transaction() as store:
            campaigns = [
                campaign
                for campaign in store.campaigns.values()
                if self._matches_scope(campaign.business_id, campaign.environment, business_id, environment)
            ]
        campaign_scope_ids = self._resolve_campaign_filter_ids(campaigns, campaign_id)
        leads = self.leads_repository.list(business_id=business_id, environment=environment)
        title_packets = self.title_packets_repository.list(business_id=business_id, environment=environment)
        events = self.lead_events_repository.list(business_id=business_id, environment=environment)
        tasks = self.tasks_repository.list(business_id=business_id, environment=environment, lead_id=lead_id)
        suppressions = self.suppression_repository.list_active(business_id=business_id, environment=environment)

        lead_by_id = {lead.id: lead for lead in leads if lead.id is not None}
        packet_by_lead_id = {packet.lead_id: packet for packet in title_packets if packet.lead_id is not None}
        event_by_id = {event.id: event for event in events if event.id is not None}

        scoped_leads = [
            lead
            for lead in leads
            if self._matches_lead_machine_filters(
                resolved_lead_id=lead.id,
                resolved_campaign_id=lead.campaign_id,
                requested_lead_id=lead_id,
                requested_campaign_ids=campaign_scope_ids,
            )
        ]
        scoped_events = [
            event
            for event in events
            if self._matches_lead_machine_filters(
                resolved_lead_id=event.lead_id,
                resolved_campaign_id=event.campaign_id,
                requested_lead_id=lead_id,
                requested_campaign_ids=campaign_scope_ids,
            )
        ]
        scoped_tasks = [
            task
            for task in tasks
            if self._task_matches_lead_machine_filters(
                task,
                lead_by_id=lead_by_id,
                event_by_id=event_by_id,
                requested_campaign_ids=campaign_scope_ids,
            )
        ]
        scoped_suppressions = [
            record
            for record in suppressions
            if self._suppression_matches_lead_machine_filters(
                record,
                lead_by_id=lead_by_id,
                requested_lead_id=lead_id,
                requested_campaign_ids=campaign_scope_ids,
            )
        ]
        scoped_lead_ids = {lead.id for lead in scoped_leads if lead.id is not None}
        scoped_title_packets = [packet for packet in title_packets if packet.lead_id in scoped_lead_ids]

        ordered_leads = sorted(
            scoped_leads,
            key=lambda lead: (-(lead.score or 0), lead.updated_at, lead.id or ""),
        )
        ordered_tasks = sorted(
            scoped_tasks,
            key=lambda task: (task.due_at or task.created_at, task.created_at, task.id or ""),
        )
        ordered_events = sorted(
            scoped_events,
            key=lambda event: (event.event_timestamp, event.received_at, event.id or ""),
            reverse=True,
        )
        if limit is not None:
            ordered_leads = ordered_leads[:limit]
            ordered_tasks = ordered_tasks[:limit]
            ordered_events = ordered_events[:limit]

        lead_rows = []
        for lead in ordered_leads:
            packet = packet_by_lead_id.get(lead.id or "")
            custom_variables = lead.custom_variables
            personalization = lead.personalization
            lead_rows.append(
                MissionControlLeadMachineLeadRecord(
                    id=lead.id or "",
                    business_id=lead.business_id,
                    environment=lead.environment,
                    external_key=lead.external_key,
                    lead_name=self._lead_display_name(lead),
                    email=lead.email,
                    phone=lead.phone,
                    company_name=lead.company_name,
                    property_address=lead.property_address,
                    mailing_address=lead.mailing_address,
                    probate_case_number=lead.probate_case_number,
                    score=lead.score,
                    lifecycle_status=lead.lifecycle_status,
                    verification_status=lead.verification_status,
                    enrichment_status=lead.enrichment_status,
                    upload_method=lead.upload_method,
                    assigned_to=lead.assigned_to,
                    operator_lane=personalization.get("operator_lane"),
                    why_now=personalization.get("why_now"),
                    tax_due=custom_variables.get("tax_due"),
                    delinquent_years=custom_variables.get("delinquent_years"),
                    manual_pull_queue=custom_variables.get("manual_pull_queue"),
                    title_packet_id=(packet.id if packet is not None else None),
                    title_packet_status=(packet.status if packet is not None else None),
                    hctax_account=custom_variables.get("hctax_account") or (packet.hctax_account if packet is not None else None),
                    created_at=lead.created_at,
                    updated_at=lead.updated_at,
                )
            )

        task_rows = []
        for task in ordered_tasks:
            lead = lead_by_id.get(task.lead_id or "") if task.lead_id is not None else None
            source_event = event_by_id.get(task.source_event_id or "") if task.source_event_id is not None else None
            task_rows.append(
                MissionControlLeadMachineTaskRecord(
                    id=task.id or "",
                    business_id=task.business_id,
                    environment=task.environment,
                    lead_id=task.lead_id,
                    campaign_id=(source_event.campaign_id if source_event is not None else (lead.campaign_id if lead is not None else None)),
                    lead_name=self._lead_display_name(lead),
                    lead_email=(lead.email if lead is not None else None),
                    title=task.title,
                    status=task.status,
                    task_type=task.task_type,
                    priority=task.priority,
                    due_at=task.due_at,
                    assigned_to=task.assigned_to,
                    source_event_id=task.source_event_id,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    details=self._scrub_sensitive_data(deepcopy(task.details)),
                )
            )

        timeline_rows = []
        for event in ordered_events:
            lead = lead_by_id.get(event.lead_id)
            timeline_rows.append(
                MissionControlLeadMachineTimelineRecord(
                    id=event.id or "",
                    business_id=event.business_id,
                    environment=event.environment,
                    lead_id=event.lead_id,
                    campaign_id=event.campaign_id,
                    lead_name=self._lead_display_name(lead),
                    lead_email=(lead.email if lead is not None else None),
                    event_type=event.event_type,
                    provider_name=event.provider_name,
                    provider_event_id=event.provider_event_id,
                    provider_receipt_id=event.provider_receipt_id,
                    event_timestamp=event.event_timestamp,
                    received_at=event.received_at,
                    metadata=self._scrub_lead_event_metadata(event.metadata),
                )
            )

        return MissionControlLeadMachineResponse(
            summary=MissionControlLeadMachineSummary(
                lead_count=len(scoped_leads),
                title_packet_count=len(scoped_title_packets),
                task_count=len(scoped_tasks),
                open_task_count=sum(1 for task in scoped_tasks if task.status == TaskStatus.OPEN),
                event_count=len(scoped_events),
                suppression_count=len(scoped_suppressions),
            ),
            leads=lead_rows,
            tasks=task_rows,
            timeline=timeline_rows,
        )

    def get_agents(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAgentsResponse:
        with self.client.transaction() as store:
            agents = [
                agent
                for agent in store.agents.values()
                if self._matches_scope(agent.business_id, agent.environment, business_id, environment)
            ]
            revisions = dict(store.agent_revisions)
            sessions = list(store.sessions.values())
            permissions = list(store.permissions.values())

        agent_summaries: list[MissionControlAgentSummary] = []
        for agent in sorted(agents, key=lambda item: item.updated_at, reverse=True):
            active_revision_id = agent.active_revision_id
            active_revision = revisions.get(active_revision_id) if active_revision_id is not None else None
            agent_sessions = [session for session in sessions if session.agent_id == agent.id]
            if business_id is not None:
                agent_sessions = [session for session in agent_sessions if session.business_id == business_id]
            if environment is not None:
                agent_sessions = [session for session in agent_sessions if session.environment == environment]
            latest_session_environment = (
                sorted(agent_sessions, key=lambda session: (session.updated_at, session.created_at), reverse=True)[0].environment
                if agent_sessions
                else "unassigned"
            )
            active_revision_state = active_revision.state.value if active_revision is not None else "draft"
            delegated_work_count = sum(
                1
                for permission in permissions
                if permission.agent_revision_id == active_revision_id and permission.mode != "always_allow"
            )
            agent_summaries.append(
                MissionControlAgentSummary(
                    id=agent.id,
                    name=agent.name,
                    active_revision_id=active_revision_id,
                    active_revision_state=active_revision_state,
                    environment=latest_session_environment,
                    live_session_count=len(agent_sessions),
                    delegated_work_count=delegated_work_count,
                )
            )
        return MissionControlAgentsResponse(agents=agent_summaries)

    def get_assets(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MissionControlAssetsResponse:
        with self.client.transaction() as store:
            assets = list(store.agent_assets.values())
            agents = dict(store.agents)

        asset_rows = []
        for asset in sorted(assets, key=lambda item: item.updated_at, reverse=True):
            if business_id is not None and asset.metadata.get("business_id") not in {None, business_id}:
                continue
            if environment is not None and asset.metadata.get("environment") not in {None, environment}:
                continue
            agent = agents.get(asset.agent_id)
            asset_rows.append(
                MissionControlAssetSummary(
                    id=asset.id,
                    name=asset.label,
                    category=asset.asset_type.value,
                    status=("connected" if asset.status.value == "bound" else ("attention" if asset.connect_later else "unbound")),
                    binding_target=asset.binding_reference or (agent.name if agent is not None else "not set"),
                    updated_at=asset.updated_at,
                )
            )
        return MissionControlAssetsResponse(assets=asset_rows)

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
            contact=thread.contact,
            booking_status=self._thread_booking_status(thread),
            sequence_status=self._thread_sequence_status(thread),
            next_sequence_step=self._thread_next_sequence_step(thread),
            manual_call_due_at=self._thread_manual_call_due_at(thread),
            recent_reply_preview=self._thread_recent_reply_preview(thread),
            reply_needs_review=self._thread_reply_needs_review(thread),
        )

    def _build_thread_detail(
        self,
        thread: MissionControlThreadRecord,
        *,
        runs_by_id: dict[str, object],
        approvals_by_id: dict[str, object],
    ) -> MissionControlThreadDetail:
        context = self._scrub_sensitive_data(deepcopy(thread.context))
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
            contact=thread.contact,
            booking_status=thread.booking_status or self._thread_booking_status(thread),
            sequence_status=thread.sequence_status or self._thread_sequence_status(thread),
            next_sequence_step=thread.next_sequence_step or self._thread_next_sequence_step(thread),
            manual_call_due_at=thread.manual_call_due_at or self._thread_manual_call_due_at(thread),
            recent_reply_preview=thread.recent_reply_preview or self._thread_recent_reply_preview(thread),
            reply_needs_review=thread.reply_needs_review or self._thread_reply_needs_review(thread),
            messages=thread.messages,
            context=context,
        )

    @staticmethod
    def _matches_lead_machine_filters(
        *,
        resolved_lead_id: str | None,
        resolved_campaign_id: str | None,
        requested_lead_id: str | None,
        requested_campaign_ids: set[str] | None,
    ) -> bool:
        if requested_lead_id is not None and resolved_lead_id != requested_lead_id:
            return False
        if requested_campaign_ids is not None and resolved_campaign_id not in requested_campaign_ids:
            return False
        return True

    @staticmethod
    def _resolve_campaign_filter_ids(campaigns: list[object], requested_campaign_id: str | None) -> set[str] | None:
        if requested_campaign_id is None:
            return None
        resolved = {requested_campaign_id}
        for campaign in campaigns:
            if requested_campaign_id not in {campaign.id, campaign.provider_campaign_id}:
                continue
            if campaign.id is not None:
                resolved.add(campaign.id)
            if campaign.provider_campaign_id is not None:
                resolved.add(campaign.provider_campaign_id)
        return resolved

    @staticmethod
    def _lead_display_name(lead) -> str | None:
        if lead is None:
            return None
        full_name = " ".join(part.strip() for part in (lead.first_name or "", lead.last_name or "") if part and part.strip())
        if full_name:
            return full_name
        if lead.company_name:
            return str(lead.company_name)
        if lead.email:
            return str(lead.email)
        return lead.id

    @classmethod
    def _task_matches_lead_machine_filters(
        cls,
        task,
        *,
        lead_by_id: dict[str, object],
        event_by_id: dict[str, object],
        requested_campaign_ids: set[str] | None,
    ) -> bool:
        if requested_campaign_ids is None:
            return True
        source_event = event_by_id.get(task.source_event_id or "") if task.source_event_id is not None else None
        if source_event is not None and source_event.campaign_id in requested_campaign_ids:
            return True
        if task.lead_id is None:
            return False
        lead = lead_by_id.get(task.lead_id)
        return lead is not None and lead.campaign_id in requested_campaign_ids

    @classmethod
    def _suppression_matches_lead_machine_filters(
        cls,
        record,
        *,
        lead_by_id: dict[str, object],
        requested_lead_id: str | None,
        requested_campaign_ids: set[str] | None,
    ) -> bool:
        if requested_lead_id is not None and record.lead_id != requested_lead_id:
            return False
        if requested_campaign_ids is None:
            return True
        if record.campaign_id in requested_campaign_ids:
            return True
        if record.lead_id is None:
            return False
        lead = lead_by_id.get(record.lead_id)
        return lead is not None and lead.campaign_id in requested_campaign_ids

    @classmethod
    def _scrub_lead_event_metadata(cls, metadata: dict[str, object]) -> dict[str, object]:
        redacted_keys = {"provider_payload", "payload", "email_html", "reply_html"}
        scrubbed = {
            key: cls._scrub_sensitive_data(value)
            for key, value in metadata.items()
            if key not in redacted_keys and value is not None
        }
        for text_key in ("email_text", "reply_text"):
            value = metadata.get(text_key)
            if value is None:
                continue
            preview = str(value).strip()
            scrubbed[text_key] = preview[:160] if len(preview) <= 160 else f"{preview[:157]}..."
        return scrubbed

    @staticmethod
    def _scrub_sensitive_data(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: "[redacted]" if isinstance(key, str) and MissionControlService._looks_sensitive(key) else MissionControlService._scrub_sensitive_data(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [MissionControlService._scrub_sensitive_data(item) for item in value]
        if isinstance(value, tuple):
            return tuple(MissionControlService._scrub_sensitive_data(item) for item in value)
        return value

    @staticmethod
    def _looks_sensitive(key: str) -> bool:
        normalized = key.lower()
        markers = (
            "secret",
            "secretvalue",
            "token",
            "password",
            "passphrase",
            "apikey",
            "api_key",
            "clientsecret",
            "client_secret",
            "webhooksecret",
            "webhook_secret",
            "privatekey",
            "private_key",
            "authorization",
            "credential",
            "passwd",
            "authtoken",
            "access_token",
            "refresh_token",
        )
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _thread_booking_status(thread: MissionControlThreadRecord) -> str | None:
        value = thread.booking_status or thread.context.get("booking_status")
        return str(value) if value is not None else None

    @staticmethod
    def _thread_sequence_status(thread: MissionControlThreadRecord) -> str | None:
        value = thread.sequence_status or thread.context.get("sequence_status")
        return str(value) if value is not None else None

    @staticmethod
    def _thread_next_sequence_step(thread: MissionControlThreadRecord) -> str | None:
        value = thread.next_sequence_step or thread.context.get("next_sequence_step")
        return str(value) if value is not None else None

    @staticmethod
    def _thread_manual_call_due_at(thread: MissionControlThreadRecord) -> str | None:
        value = thread.manual_call_due_at or thread.context.get("manual_call_due_at")
        return str(value) if value is not None else None

    @staticmethod
    def _thread_recent_reply_preview(thread: MissionControlThreadRecord) -> str | None:
        value = thread.recent_reply_preview or thread.context.get("recent_reply_preview")
        if value is not None:
            return str(value)
        if thread.messages:
            return thread.messages[-1].body
        return None

    @staticmethod
    def _thread_reply_needs_review(thread: MissionControlThreadRecord) -> bool:
        return bool(thread.reply_needs_review or thread.context.get("reply_needs_review"))

    @staticmethod
    def _turn_retry_count(turn, turns_by_id: dict[str, object]) -> int:
        history_retry_count = 0
        cursor = turn.resumed_from_turn_id
        visited: set[str] = set()
        while cursor is not None and cursor not in visited:
            visited.add(cursor)
            history_retry_count += 1
            previous_turn = turns_by_id.get(cursor)
            if previous_turn is None:
                break
            cursor = previous_turn.resumed_from_turn_id
        metadata_retry_count = MissionControlService._metadata_retry_count(turn.metadata)
        return max(history_retry_count, metadata_retry_count)

    @staticmethod
    def _metadata_retry_count(metadata: dict[str, object]) -> int:
        candidates: list[int] = []
        retry_count = metadata.get("retry_count")
        if isinstance(retry_count, int):
            candidates.append(retry_count)
        retries = metadata.get("retries")
        if isinstance(retries, int):
            candidates.append(retries)
        attempt_count = metadata.get("attempt_count")
        if isinstance(attempt_count, int):
            candidates.append(attempt_count - 1)
        for nested_key in ("retry", "retry_state", "provider_retry"):
            nested = metadata.get(nested_key)
            if isinstance(nested, dict):
                candidates.append(MissionControlService._metadata_retry_count(nested))
        return max([0, *candidates])

    @staticmethod
    def _approval_reason(command_type: str) -> str:
        if "call" in command_type or "voice" in command_type:
            return "Voice actions stay operator-reviewed until live policy tuning is complete."
        if "publish" in command_type or "send" in command_type:
            return "Customer-facing actions stay operator-reviewed before release."
        return "The command requires an approval gate before execution."

    @staticmethod
    def _approval_risk_level(command_type: str) -> str:
        if "call" in command_type or "voice" in command_type:
            return "high"
        if "publish" in command_type or "send" in command_type:
            return "medium"
        return "low"

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
