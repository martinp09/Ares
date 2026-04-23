from __future__ import annotations

from app.db.agents import AgentsRepository
from app.db.release_management import ReleaseManagementRepository
from app.models.actors import ActorContext
from app.models.agents import AgentRevisionState
from app.models.outcomes import OutcomeEvaluationPayload, ReleaseDecisionAction
from app.models.release_management import ReleaseEventListResponse, ReleaseTransitionResponse
from app.services.audit_service import audit_service
from app.services.outcome_service import OutcomeService, outcome_service


class ReleaseManagementService:
    def __init__(
        self,
        release_management_repository: ReleaseManagementRepository | None = None,
        agents_repository: AgentsRepository | None = None,
        outcomes: OutcomeService | None = None,
    ) -> None:
        self.release_management_repository = release_management_repository or ReleaseManagementRepository()
        self.agents_repository = agents_repository or AgentsRepository()
        self.outcomes = outcomes or outcome_service

    def list_events(self, agent_id: str, *, org_id: str | None = None) -> ReleaseEventListResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or (org_id is not None and agent.org_id != org_id):
            return None
        return ReleaseEventListResponse(
            events=self.release_management_repository.list_events(agent_id, org_id=agent.org_id)
        )

    def publish_revision(
        self,
        agent_id: str,
        revision_id: str,
        *,
        actor_context: ActorContext,
        notes: str | None = None,
        evaluation_summary: OutcomeEvaluationPayload | None = None,
        require_passing_evaluation: bool = False,
    ) -> ReleaseTransitionResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or agent.org_id != actor_context.org_id:
            return None
        revision = self.agents_repository.get_revision(revision_id)
        if revision is None or revision.agent_id != agent_id:
            return None
        self._assert_can_publish(agent, revision)

        release_evaluation = None
        if evaluation_summary is not None:
            evaluation_outcome = self.outcomes.record_release_decision_evaluation(
                agent_id=agent_id,
                revision_id=revision_id,
                action=ReleaseDecisionAction.PROMOTION,
                evaluation=evaluation_summary,
                notes=notes,
                require_passing_evaluation=require_passing_evaluation,
            )
            blocked_promotion = require_passing_evaluation and not evaluation_outcome.satisfied
            release_evaluation = self.outcomes.summarize_release_evaluation(
                evaluation_outcome,
                require_passing_evaluation=require_passing_evaluation,
                blocked_promotion=blocked_promotion,
            )
            if blocked_promotion:
                raise ValueError("Promotion blocked by failed evaluation summary")

        result = self.release_management_repository.publish_revision(
            agent_id,
            revision_id,
            actor_id=actor_context.actor_id,
            actor_type=actor_context.actor_type,
            notes=notes,
            evaluation_summary=release_evaluation,
        )
        if result is None:
            return None
        updated_agent, _, event = result
        audit_service.append_event(
            event_type="agent_release_published",
            summary=f"Published release event {event.id}",
            resource_type="agent_release_event",
            resource_id=event.id,
            agent_id=updated_agent.id,
            agent_revision_id=event.target_revision_id,
            actor_context=actor_context,
            metadata={
                "previous_active_revision_id": event.previous_active_revision_id,
                "resulting_active_revision_id": event.resulting_active_revision_id,
                "evaluation_outcome_id": event.evaluation_summary.outcome_id if event.evaluation_summary else None,
            },
        )
        return ReleaseTransitionResponse(
            agent=updated_agent,
            revisions=self.agents_repository.list_revisions(agent_id),
            event=event,
        )

    def rollback_revision(
        self,
        agent_id: str,
        revision_id: str,
        *,
        actor_context: ActorContext,
        notes: str | None = None,
        evaluation_summary: OutcomeEvaluationPayload | None = None,
        rollback_reason: str | None = None,
    ) -> ReleaseTransitionResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or agent.org_id != actor_context.org_id:
            return None
        revision = self.agents_repository.get_revision(revision_id)
        if revision is None or revision.agent_id != agent_id:
            return None
        self._assert_can_rollback(agent, revision)

        effective_rollback_reason = rollback_reason or notes
        release_evaluation = None
        if evaluation_summary is not None:
            evaluation_outcome = self.outcomes.record_release_decision_evaluation(
                agent_id=agent_id,
                revision_id=revision_id,
                action=ReleaseDecisionAction.ROLLBACK,
                evaluation=evaluation_summary,
                notes=notes,
                rollback_reason=effective_rollback_reason,
            )
            release_evaluation = self.outcomes.summarize_release_evaluation(
                evaluation_outcome,
                require_passing_evaluation=False,
                rollback_reason=effective_rollback_reason,
            )

        result = self.release_management_repository.rollback_revision(
            agent_id,
            revision_id,
            actor_id=actor_context.actor_id,
            actor_type=actor_context.actor_type,
            notes=notes,
            evaluation_summary=release_evaluation,
        )
        if result is None:
            return None
        updated_agent, _, event = result
        audit_service.append_event(
            event_type="agent_release_rolled_back",
            summary=f"Rolled back release event {event.id}",
            resource_type="agent_release_event",
            resource_id=event.id,
            agent_id=updated_agent.id,
            agent_revision_id=event.target_revision_id,
            actor_context=actor_context,
            metadata={
                "previous_active_revision_id": event.previous_active_revision_id,
                "resulting_active_revision_id": event.resulting_active_revision_id,
                "evaluation_outcome_id": event.evaluation_summary.outcome_id if event.evaluation_summary else None,
                "rollback_reason": effective_rollback_reason,
            },
        )
        return ReleaseTransitionResponse(
            agent=updated_agent,
            revisions=self.agents_repository.list_revisions(agent_id),
            event=event,
        )

    def _assert_can_publish(self, agent, revision) -> None:
        if revision.state == AgentRevisionState.ARCHIVED:
            raise ValueError("Archived revisions cannot be published")
        if revision.state == AgentRevisionState.DEPRECATED:
            raise ValueError("Deprecated revisions cannot be republished; create a new candidate instead")
        if agent.active_revision_id == revision.id and revision.state == AgentRevisionState.PUBLISHED:
            raise ValueError("Revision is already the active published revision")

    def _assert_can_rollback(self, agent, revision) -> None:
        if agent.active_revision_id is None:
            raise ValueError("No active revision to roll back")
        if agent.active_revision_id == revision.id:
            raise ValueError("Target revision is already active")
        if revision.state == AgentRevisionState.ARCHIVED:
            raise ValueError("Archived revisions cannot be rolled back into service")
        if revision.published_at is None:
            raise ValueError("Only previously published revisions can be rolled back")

    def deactivate_revision(
        self,
        agent_id: str,
        revision_id: str,
        *,
        actor_context: ActorContext,
        notes: str | None = None,
    ) -> ReleaseTransitionResponse | None:
        agent = self.agents_repository.get_agent(agent_id)
        if agent is None or agent.org_id != actor_context.org_id:
            return None
        revision = self.agents_repository.get_revision(revision_id)
        if revision is None or revision.agent_id != agent_id:
            return None

        result = self.release_management_repository.deactivate_revision(
            agent_id,
            revision_id,
            actor_id=actor_context.actor_id,
            actor_type=actor_context.actor_type,
            notes=notes,
        )
        if result is None:
            return None
        updated_agent, _, event = result
        audit_service.append_event(
            event_type="agent_release_deactivated",
            summary=f"Deactivated release event {event.id}",
            resource_type="agent_release_event",
            resource_id=event.id,
            agent_id=updated_agent.id,
            agent_revision_id=event.target_revision_id,
            actor_context=actor_context,
            metadata={
                "previous_active_revision_id": event.previous_active_revision_id,
                "resulting_active_revision_id": event.resulting_active_revision_id,
            },
        )
        return ReleaseTransitionResponse(
            agent=updated_agent,
            revisions=self.agents_repository.list_revisions(agent_id),
            event=event,
        )


release_management_service = ReleaseManagementService()
