from __future__ import annotations

from copy import deepcopy
from datetime import datetime

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.approvals import ApprovalStatus
from app.models.mission_control import (
    MissionControlAgentsResponse,
    MissionControlAgentSummary,
    MissionControlApprovalsResponse,
    MissionControlApprovalSummary,
    MissionControlAssetsResponse,
    MissionControlAssetSummary,
    MissionControlDashboardResponse,
    MissionControlInboxResponse,
    MissionControlInboxSummary,
    MissionControlRunSummary,
    MissionControlRunsResponse,
    MissionControlThreadDetail,
    MissionControlThreadRecord,
    MissionControlThreadSummary,
)
from app.models.runs import RunStatus
from app.services.agent_asset_service import AgentAssetService, agent_asset_service
from app.services.agent_registry_service import AgentRegistryService, agent_registry_service
from app.services.approval_service import ApprovalService, approval_service

ACTIVE_RUN_STATUSES = {RunStatus.QUEUED, RunStatus.IN_PROGRESS}


class MissionControlService:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        approval_service_dependency: ApprovalService | None = None,
        agent_registry_service_dependency: AgentRegistryService | None = None,
        agent_asset_service_dependency: AgentAssetService | None = None,
    ) -> None:
        self.client = client or get_control_plane_client()
        self.approval_service = approval_service_dependency or approval_service
        self.agent_registry_service = agent_registry_service_dependency or agent_registry_service
        self.agent_asset_service = agent_asset_service_dependency or agent_asset_service

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

        latest_timestamps: list[datetime] = [approval.created_at for approval in approvals]
        latest_timestamps.extend(run.updated_at for run in runs)
        latest_timestamps.extend(thread.updated_at for thread in threads)
        latest_updated_at = max(latest_timestamps, default=utc_now())

        unread_conversation_count = sum(1 for thread in threads if thread.unread_count > 0)
        busy_channel_count = len({thread.channel for thread in threads if thread.unread_count > 0})
        recent_completed_count = sum(1 for run in runs if run.status == RunStatus.COMPLETED)
        failed_run_count = sum(1 for run in runs if run.status == RunStatus.FAILED)
        active_run_count = sum(1 for run in runs if run.status in ACTIVE_RUN_STATUSES)
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
            messages=sorted(thread.messages, key=lambda message: message.created_at),
            context=context,
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
