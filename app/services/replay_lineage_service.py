from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.db.agents import AgentsRepository
from app.db.host_adapter_dispatches import HostAdapterDispatchesRepository
from app.db.release_management import ReleaseManagementRepository
from app.models.actors import ActorContext
from app.models.release_management import ReleaseEventRecord
from app.models.runs import ReplayActorRecord, ReplayLineageContext, ReplayRevisionContext

REPLAY_APPROVAL_METADATA_KEY = "__ares_replay_lineage"


class ReplayApprovalMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_run_id: str
    replay_reason: str | None = None
    agent_revision_id: str | None = None
    parent_created_at: datetime
    triggering_actor: ReplayActorRecord


class ReplayLineageService:
    def __init__(
        self,
        host_adapter_dispatches_repository: HostAdapterDispatchesRepository | None = None,
        agents_repository: AgentsRepository | None = None,
        release_management_repository: ReleaseManagementRepository | None = None,
    ) -> None:
        self.host_adapter_dispatches_repository = host_adapter_dispatches_repository or HostAdapterDispatchesRepository()
        self.agents_repository = agents_repository or AgentsRepository()
        self.release_management_repository = release_management_repository or ReleaseManagementRepository()

    def agent_revision_id_for_run(self, run_id: str) -> str | None:
        dispatch = self.host_adapter_dispatches_repository.get_by_run_id(run_id)
        if dispatch is None:
            return None
        return dispatch.agent_revision_id

    def build_lineage(
        self,
        *,
        agent_revision_id: str | None,
        parent_created_at: datetime,
        replayed_at: datetime,
        actor_context: ActorContext,
    ) -> ReplayLineageContext:
        lineage = ReplayLineageContext(
            triggering_actor=ReplayActorRecord(
                org_id=actor_context.org_id,
                actor_id=actor_context.actor_id,
                actor_type=actor_context.actor_type,
            )
        )
        if agent_revision_id is None:
            return lineage
        return lineage.model_copy(
            update={
                "source": self._source_revision_context(agent_revision_id, parent_created_at),
                "replay": self._replay_revision_context(agent_revision_id, replayed_at),
            }
        )

    def build_approval_payload_snapshot(
        self,
        payload_snapshot: dict[str, Any] | None,
        *,
        parent_run_id: str,
        replay_reason: str | None,
        agent_revision_id: str | None,
        parent_created_at: datetime,
        actor_context: ActorContext,
    ) -> dict[str, Any]:
        snapshot = dict(payload_snapshot or {})
        snapshot[REPLAY_APPROVAL_METADATA_KEY] = ReplayApprovalMetadata(
            parent_run_id=parent_run_id,
            replay_reason=replay_reason,
            agent_revision_id=agent_revision_id,
            parent_created_at=parent_created_at,
            triggering_actor=ReplayActorRecord(
                org_id=actor_context.org_id,
                actor_id=actor_context.actor_id,
                actor_type=actor_context.actor_type,
            ),
        ).model_dump(mode="json")
        return snapshot

    def approval_metadata(self, payload_snapshot: dict[str, Any] | None) -> ReplayApprovalMetadata | None:
        raw_metadata = (payload_snapshot or {}).get(REPLAY_APPROVAL_METADATA_KEY)
        if not isinstance(raw_metadata, dict):
            return None
        return ReplayApprovalMetadata.model_validate(raw_metadata)

    def _source_revision_context(self, agent_revision_id: str, occurred_at: datetime) -> ReplayRevisionContext | None:
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            return ReplayRevisionContext(agent_revision_id=agent_revision_id, active_revision_id=agent_revision_id)
        release_event = self._latest_release_event_for_revision_at_time(revision.agent_id, agent_revision_id, occurred_at)
        return self._revision_context(
            agent_revision_id,
            release_event=release_event,
            fallback_active_revision_id=agent_revision_id,
        )

    def _replay_revision_context(self, agent_revision_id: str, occurred_at: datetime) -> ReplayRevisionContext | None:
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            return ReplayRevisionContext(agent_revision_id=agent_revision_id, active_revision_id=agent_revision_id)
        release_event = self._latest_release_event_for_agent_at_time(revision.agent_id, occurred_at)
        agent = self.agents_repository.get_agent(revision.agent_id)
        return self._revision_context(
            agent_revision_id,
            release_event=release_event,
            fallback_active_revision_id=(
                release_event.resulting_active_revision_id
                if release_event is not None
                else (agent.active_revision_id if agent is not None else agent_revision_id)
            ),
        )

    def _revision_context(
        self,
        agent_revision_id: str,
        *,
        release_event: ReleaseEventRecord | None,
        fallback_active_revision_id: str | None,
    ) -> ReplayRevisionContext | None:
        revision = self.agents_repository.get_revision(agent_revision_id)
        if revision is None:
            return ReplayRevisionContext(
                agent_revision_id=agent_revision_id,
                active_revision_id=fallback_active_revision_id,
                release_event_id=release_event.id if release_event is not None else None,
                release_event_type=release_event.event_type if release_event is not None else None,
                release_channel=release_event.release_channel if release_event is not None else None,
            )
        return ReplayRevisionContext(
            agent_id=revision.agent_id,
            agent_revision_id=revision.id,
            active_revision_id=(
                release_event.resulting_active_revision_id if release_event is not None else fallback_active_revision_id
            ),
            revision_state=revision.state,
            release_channel=(release_event.release_channel if release_event is not None else revision.release_channel),
            release_event_id=release_event.id if release_event is not None else None,
            release_event_type=release_event.event_type if release_event is not None else None,
        )

    def _latest_release_event_for_revision_at_time(
        self,
        agent_id: str,
        revision_id: str,
        occurred_at: datetime,
    ) -> ReleaseEventRecord | None:
        relevant_events = [
            event
            for event in self.release_management_repository.list_events(agent_id)
            if event.created_at <= occurred_at
            and (
                event.target_revision_id == revision_id
                or event.resulting_active_revision_id == revision_id
                or event.previous_active_revision_id == revision_id
            )
        ]
        if not relevant_events:
            return None
        relevant_events.sort(key=lambda event: (event.created_at, event.updated_at, event.id))
        return relevant_events[-1]

    def _latest_release_event_for_agent_at_time(
        self,
        agent_id: str,
        occurred_at: datetime,
    ) -> ReleaseEventRecord | None:
        relevant_events = [
            event for event in self.release_management_repository.list_events(agent_id) if event.created_at <= occurred_at
        ]
        if not relevant_events:
            return None
        relevant_events.sort(key=lambda event: (event.created_at, event.updated_at, event.id))
        return relevant_events[-1]


replay_lineage_service = ReplayLineageService()
