from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.agents import _derive_agent_lifecycle_status
from app.models.actors import ActorType
from app.models.agents import AgentLifecycleStatus, AgentRecord, AgentRevisionRecord, AgentRevisionState
from app.models.commands import generate_id
from app.models.outcomes import ReleaseDecisionEvaluationSummary
from app.models.release_management import ReleaseEventRecord, ReleaseEventType


class ReleaseManagementRepository:
    def __init__(self, client: ControlPlaneClient | None = None) -> None:
        self.client = client or get_control_plane_client()

    def list_events(self, agent_id: str, *, org_id: str | None = None) -> list[ReleaseEventRecord]:
        with self.client.transaction() as store:
            event_ids = list(store.release_event_ids_by_agent.get(agent_id, []))
            events = [store.release_events[event_id] for event_id in event_ids]
        if org_id is not None:
            events = [event for event in events if event.org_id == org_id]
        return events

    def publish_revision(
        self,
        agent_id: str,
        revision_id: str,
        *,
        actor_id: str,
        actor_type: str | ActorType,
        notes: str | None = None,
        evaluation_summary: ReleaseDecisionEvaluationSummary | None = None,
    ) -> tuple[AgentRecord, AgentRevisionRecord, ReleaseEventRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            revision = store.agent_revisions.get(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None
            if revision.state == AgentRevisionState.ARCHIVED:
                raise ValueError("Archived revisions cannot be published")
            if revision.state == AgentRevisionState.DEPRECATED:
                raise ValueError("Deprecated revisions cannot be republished; create a new candidate instead")
            if agent.active_revision_id == revision_id and revision.state == AgentRevisionState.PUBLISHED:
                raise ValueError("Revision is already the active published revision")

            now = utc_now()
            previous_active_revision_id = agent.active_revision_id
            if previous_active_revision_id and previous_active_revision_id != revision_id:
                active_revision = store.agent_revisions[previous_active_revision_id]
                store.agent_revisions[previous_active_revision_id] = active_revision.model_copy(
                    update={
                        "state": AgentRevisionState.DEPRECATED,
                        "archived_at": None,
                        "updated_at": now,
                    }
                )

            published_revision = revision.model_copy(
                update={
                    "state": AgentRevisionState.PUBLISHED,
                    "published_at": revision.published_at or now,
                    "archived_at": None,
                    "updated_at": now,
                }
            )
            updated_agent = agent.model_copy(
                update={
                    "active_revision_id": revision_id,
                    "lifecycle_status": AgentLifecycleStatus.ACTIVE,
                    "updated_at": now,
                }
            )
            event = ReleaseEventRecord(
                id=generate_id("rle"),
                org_id=agent.org_id,
                agent_id=agent.id,
                event_type=ReleaseEventType.PUBLISH,
                actor_id=actor_id,
                actor_type=ActorType(actor_type),
                previous_active_revision_id=previous_active_revision_id,
                target_revision_id=revision_id,
                resulting_active_revision_id=revision_id,
                release_channel=published_revision.release_channel,
                notes=notes,
                evaluation_summary=evaluation_summary,
                created_at=now,
                updated_at=now,
            )
            store.agent_revisions[revision_id] = published_revision
            store.agents[agent_id] = updated_agent
            store.release_events[event.id] = event
            store.release_event_ids_by_agent.setdefault(agent_id, []).append(event.id)
            return updated_agent, published_revision, event

    def rollback_revision(
        self,
        agent_id: str,
        revision_id: str,
        *,
        actor_id: str,
        actor_type: str | ActorType,
        notes: str | None = None,
        evaluation_summary: ReleaseDecisionEvaluationSummary | None = None,
    ) -> tuple[AgentRecord, AgentRevisionRecord, ReleaseEventRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            revision = store.agent_revisions.get(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None
            if agent.active_revision_id is None:
                raise ValueError("No active revision to roll back")
            if agent.active_revision_id == revision_id:
                raise ValueError("Target revision is already active")
            if revision.state == AgentRevisionState.ARCHIVED:
                raise ValueError("Archived revisions cannot be rolled back into service")
            if revision.published_at is None:
                raise ValueError("Only previously published revisions can be rolled back")

            current_active_revision = store.agent_revisions.get(agent.active_revision_id)
            if current_active_revision is None:
                raise ValueError("Active revision not found")

            now = utc_now()
            store.agent_revisions[current_active_revision.id] = current_active_revision.model_copy(
                update={
                    "state": AgentRevisionState.DEPRECATED,
                    "archived_at": None,
                    "updated_at": now,
                }
            )
            next_revision_number = len(store.agent_revision_ids_by_agent.get(agent_id, [])) + 1
            rolled_back_revision = AgentRevisionRecord(
                id=generate_id("rev"),
                agent_id=agent_id,
                revision_number=next_revision_number,
                state=AgentRevisionState.PUBLISHED,
                config=deepcopy(revision.config),
                host_adapter_kind=revision.host_adapter_kind,
                host_adapter_config=deepcopy(revision.host_adapter_config),
                provider_kind=revision.provider_kind,
                provider_config=deepcopy(revision.provider_config),
                provider_capabilities=deepcopy(revision.provider_capabilities),
                skill_ids=deepcopy(revision.skill_ids),
                input_schema=deepcopy(revision.input_schema),
                output_schema=deepcopy(revision.output_schema),
                release_notes=revision.release_notes,
                compatibility_metadata=deepcopy(revision.compatibility_metadata),
                release_channel=revision.release_channel,
                created_at=now,
                updated_at=now,
                published_at=now,
                archived_at=None,
                cloned_from_revision_id=revision.id,
            )
            updated_agent = agent.model_copy(
                update={
                    "active_revision_id": rolled_back_revision.id,
                    "lifecycle_status": AgentLifecycleStatus.ACTIVE,
                    "updated_at": now,
                }
            )
            event = ReleaseEventRecord(
                id=generate_id("rle"),
                org_id=agent.org_id,
                agent_id=agent.id,
                event_type=ReleaseEventType.ROLLBACK,
                actor_id=actor_id,
                actor_type=ActorType(actor_type),
                previous_active_revision_id=current_active_revision.id,
                target_revision_id=revision_id,
                resulting_active_revision_id=rolled_back_revision.id,
                release_channel=rolled_back_revision.release_channel,
                notes=notes,
                evaluation_summary=evaluation_summary,
                created_at=now,
                updated_at=now,
            )
            store.agent_revisions[rolled_back_revision.id] = rolled_back_revision
            store.agent_revision_ids_by_agent.setdefault(agent_id, []).append(rolled_back_revision.id)
            store.agents[agent_id] = updated_agent
            store.release_events[event.id] = event
            store.release_event_ids_by_agent.setdefault(agent_id, []).append(event.id)
            return updated_agent, rolled_back_revision, event

    def deactivate_revision(
        self,
        agent_id: str,
        revision_id: str,
        *,
        actor_id: str,
        actor_type: str | ActorType,
        notes: str | None = None,
    ) -> tuple[AgentRecord, AgentRevisionRecord, ReleaseEventRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            revision = store.agent_revisions.get(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None
            if agent.active_revision_id is None:
                raise ValueError("No active revision to deactivate")
            if agent.active_revision_id != revision_id:
                raise ValueError("Only the active revision can be deactivated")
            if revision.state != AgentRevisionState.PUBLISHED:
                raise ValueError("Only active published revisions can be deactivated")

            now = utc_now()
            archived_revision = revision.model_copy(
                update={
                    "state": AgentRevisionState.ARCHIVED,
                    "archived_at": now,
                    "updated_at": now,
                }
            )
            store.agent_revisions[revision_id] = archived_revision
            remaining_non_archived = [
                candidate
                for candidate_id in store.agent_revision_ids_by_agent.get(agent_id, [])
                if candidate_id != revision_id
                if (candidate := store.agent_revisions[candidate_id]).state != AgentRevisionState.ARCHIVED
            ]
            updated_agent = agent.model_copy(
                update={
                    "active_revision_id": None,
                    "lifecycle_status": _derive_agent_lifecycle_status(
                        remaining_non_archived,
                        active_revision_id=None,
                    ),
                    "updated_at": now,
                }
            )
            event = ReleaseEventRecord(
                id=generate_id("rle"),
                org_id=agent.org_id,
                agent_id=agent.id,
                event_type=ReleaseEventType.DEACTIVATE,
                actor_id=actor_id,
                actor_type=ActorType(actor_type),
                previous_active_revision_id=revision_id,
                target_revision_id=revision_id,
                resulting_active_revision_id=None,
                release_channel=archived_revision.release_channel,
                notes=notes,
                evaluation_summary=None,
                created_at=now,
                updated_at=now,
            )
            store.agents[agent_id] = updated_agent
            store.release_events[event.id] = event
            store.release_event_ids_by_agent.setdefault(agent_id, []).append(event.id)
            return updated_agent, archived_revision, event
