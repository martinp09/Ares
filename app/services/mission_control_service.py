from __future__ import annotations

from copy import deepcopy
import json
from collections import Counter
from datetime import UTC, datetime

from app.core.config import get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
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
from app.services.providers.resend import get_resend_status, send_test_email
from app.services.providers.textgrid import get_textgrid_status, send_test_sms

ACTIVE_RUN_STATUSES = {RunStatus.QUEUED, RunStatus.IN_PROGRESS}


class MissionControlService:
    def __init__(self, client: ControlPlaneClient | None = None) -> None:
        self.client = client or get_control_plane_client()

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
            contact=thread.contact,
            booking_status=self._thread_booking_status(thread),
            sequence_status=self._thread_sequence_status(thread),
            next_sequence_step=self._thread_next_sequence_step(thread),
            manual_call_due_at=self._thread_manual_call_due_at(thread),
            recent_reply_preview=self._thread_recent_reply_preview(thread),
            reply_needs_review=self._thread_reply_needs_review(thread),
            messages=sorted(thread.messages, key=lambda message: message.created_at),
            context=context,
        )

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
