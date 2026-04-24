from __future__ import annotations

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.db.agents import AgentsRepository
from app.db.commands import CommandsRepository
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.models.actors import ActorContext
from app.models.approvals import ApprovalRecord
from app.models.commands import CommandRecord
from app.models.runs import RunRecord
from app.models.usage import UsageCreateRequest, UsageEventKind
from app.services.audit_service import AuditService, audit_service as default_audit_service
from app.services.usage_service import UsageService, usage_service as default_usage_service


class RuntimeObservabilityService:
    def __init__(
        self,
        *,
        audit: AuditService | None = None,
        usage: UsageService | None = None,
        agents_repository: AgentsRepository | None = None,
        commands_repository: CommandsRepository | None = None,
        dispatches_repository: HostAdapterDispatchesRepository | None = None,
    ) -> None:
        self.audit = audit or default_audit_service
        self.usage = usage or default_usage_service
        self.agents_repository = agents_repository or AgentsRepository()
        self.commands_repository = commands_repository or CommandsRepository()
        self.dispatches_repository = dispatches_repository or HostAdapterDispatchesRepository()

    def nonfatal(self, recorder, *args, **kwargs) -> None:
        try:
            recorder(*args, **kwargs)
        except Exception:
            return

    def record_command_invoked(
        self,
        command: CommandRecord,
        *,
        deduped: bool = False,
        agent_revision_id: str | None = None,
    ) -> None:
        agent_context = self._agent_context(agent_revision_id)
        self.audit.append_event(
            event_type="hermes_command_invoked",
            summary=f"Hermes command invoked: {command.command_type}",
            org_id=agent_context["org_id"],
            resource_type="command",
            resource_id=command.id,
            agent_id=agent_context["agent_id"],
            agent_revision_id=agent_revision_id,
            run_id=command.run_id,
            metadata={
                "business_id": command.business_id,
                "environment": command.environment,
                "command_type": command.command_type,
                "policy": command.policy.value,
                "status": command.status.value,
                "deduped": deduped,
            },
        )
        self.usage.record_usage(
            UsageCreateRequest(
                kind=UsageEventKind.TOOL_CALL,
                org_id=agent_context["org_id"],
                agent_id=agent_context["agent_id"],
                agent_revision_id=agent_revision_id,
                source_kind="hermes",
                metadata={
                    "command_id": command.id,
                    "command_type": command.command_type,
                    "business_id": command.business_id,
                    "environment": command.environment,
                    "deduped": deduped,
                },
            )
        )

    def record_approval_created(self, approval: ApprovalRecord, *, agent_revision_id: str | None = None) -> None:
        agent_context = self._agent_context(agent_revision_id)
        self.audit.append_event(
            event_type="approval_created",
            summary=f"Approval created: {approval.command_type}",
            org_id=agent_context["org_id"],
            resource_type="approval",
            resource_id=approval.id,
            agent_id=agent_context["agent_id"],
            agent_revision_id=agent_revision_id,
            metadata={
                "command_id": approval.command_id,
                "business_id": approval.business_id,
                "environment": approval.environment,
                "command_type": approval.command_type,
                "status": approval.status.value,
            },
        )

    def record_approval_approved(self, approval: ApprovalRecord, *, agent_revision_id: str | None = None) -> None:
        agent_context = self._agent_context(agent_revision_id)
        self.audit.append_event(
            event_type="approval_approved",
            summary=f"Approval approved: {approval.command_type}",
            org_id=agent_context["org_id"],
            resource_type="approval",
            resource_id=approval.id,
            agent_id=agent_context["agent_id"],
            agent_revision_id=agent_revision_id,
            actor_id=approval.actor_id,
            actor_type="user" if approval.actor_id is not None else None,
            metadata={
                "command_id": approval.command_id,
                "business_id": approval.business_id,
                "environment": approval.environment,
                "command_type": approval.command_type,
                "status": approval.status.value,
            },
        )

    def record_run_created(self, run: RunRecord, *, agent_revision_id: str | None = None) -> None:
        agent_context = self._agent_context(agent_revision_id)
        self.audit.append_event(
            event_type="run_created",
            summary=f"Run created: {run.command_type}",
            org_id=agent_context["org_id"],
            resource_type="run",
            resource_id=run.id,
            agent_id=agent_context["agent_id"],
            agent_revision_id=agent_revision_id,
            run_id=run.id,
            metadata={
                "command_id": run.command_id,
                "business_id": run.business_id,
                "environment": run.environment,
                "command_type": run.command_type,
                "command_policy": run.command_policy.value,
                "parent_run_id": run.parent_run_id,
                "replay_reason": run.replay_reason,
            },
        )
        self.usage.record_usage(
            UsageCreateRequest(
                kind=UsageEventKind.RUN,
                org_id=agent_context["org_id"],
                agent_id=agent_context["agent_id"],
                agent_revision_id=agent_revision_id,
                run_id=run.id,
                source_kind="ares_runtime",
                metadata={
                    "command_id": run.command_id,
                    "command_type": run.command_type,
                    "parent_run_id": run.parent_run_id,
                },
            )
        )

    def record_host_dispatch_attempt(self, run: RunRecord, *, source_kind: str, trigger_run_id: str | None = None) -> None:
        agent_context = self._run_agent_context(run)
        self.usage.record_usage(
            UsageCreateRequest(
                kind=UsageEventKind.HOST_DISPATCH,
                org_id=agent_context["org_id"],
                agent_id=agent_context["agent_id"],
                agent_revision_id=agent_context["agent_revision_id"],
                run_id=run.id,
                source_kind=source_kind,
                metadata={
                    "command_id": run.command_id,
                    "command_type": run.command_type,
                    "trigger_run_id": trigger_run_id,
                },
            )
        )

    def record_trigger_lifecycle(self, run: RunRecord, *, event_type: str, trigger_run_id: str | None = None) -> None:
        agent_context = self._run_agent_context(run)
        self.audit.append_event(
            event_type=f"trigger_{event_type}",
            summary=f"Trigger {event_type.replace('_', ' ')}: {run.command_type}",
            org_id=agent_context["org_id"],
            resource_type="run",
            resource_id=run.id,
            agent_id=agent_context["agent_id"],
            agent_revision_id=agent_context["agent_revision_id"],
            run_id=run.id,
            metadata={
                "command_id": run.command_id,
                "business_id": run.business_id,
                "environment": run.environment,
                "command_type": run.command_type,
                "trigger_run_id": trigger_run_id,
            },
        )
        if event_type == "run_started":
            self.record_host_dispatch_attempt(run, source_kind="trigger_dev", trigger_run_id=trigger_run_id)

    def record_replay_requested(
        self,
        parent_run: RunRecord,
        *,
        actor_context: ActorContext,
        child_run_id: str | None,
        approval_id: str | None,
        replay_reason: str | None,
    ) -> None:
        self.audit.append_event(
            event_type="replay_requested",
            summary=f"Replay requested: {parent_run.command_type}",
            resource_type="run",
            resource_id=parent_run.id,
            run_id=parent_run.id,
            actor_context=actor_context,
            metadata={
                "command_id": parent_run.command_id,
                "business_id": parent_run.business_id,
                "environment": parent_run.environment,
                "command_type": parent_run.command_type,
                "child_run_id": child_run_id,
                "approval_id": approval_id,
                "requires_approval": approval_id is not None,
                "replay_reason": replay_reason,
            },
        )

    def _agent_context(self, agent_revision_id: str | None) -> dict[str, str | None]:
        if agent_revision_id is None:
            return {"org_id": DEFAULT_INTERNAL_ORG_ID, "agent_id": None}
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            return {"org_id": DEFAULT_INTERNAL_ORG_ID, "agent_id": None}
        agent = self.agents_repository.get_agent(revision.agent_id)
        if agent is None:
            return {"org_id": DEFAULT_INTERNAL_ORG_ID, "agent_id": revision.agent_id}
        return {"org_id": agent.org_id, "agent_id": agent.id}

    def _run_agent_context(self, run: RunRecord) -> dict[str, str | None]:
        dispatch = self.dispatches_repository.get_by_run_id(run.id)
        if dispatch is None:
            command = self.commands_repository.get(run.command_id)
            agent_revision_id = command.agent_revision_id if command is not None else None
            agent_context = self._agent_context(agent_revision_id)
            return {
                "org_id": agent_context["org_id"],
                "agent_id": agent_context["agent_id"],
                "agent_revision_id": agent_revision_id,
            }
        agent_context = self._agent_context(dispatch.agent_revision_id)
        return {
            "org_id": agent_context["org_id"],
            "agent_id": agent_context["agent_id"],
            "agent_revision_id": dispatch.agent_revision_id,
        }


runtime_observability_service = RuntimeObservabilityService()
