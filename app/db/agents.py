from __future__ import annotations

from copy import deepcopy

from app.core.config import DEFAULT_INTERNAL_ORG_ID
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.agents import (
    AgentLifecycleStatus,
    AgentRecord,
    AgentRevisionRecord,
    AgentRevisionState,
    AgentVisibility,
    default_agent_slug,
)
from app.models.commands import generate_id
from app.models.host_adapters import HostAdapterKind
from app.models.providers import ProviderCapability, ProviderKind


_DRAFT_LIKE_REVISION_STATES = frozenset({AgentRevisionState.DRAFT, AgentRevisionState.CANDIDATE})


def _derive_agent_lifecycle_status(
    revisions: list[AgentRevisionRecord],
    *,
    active_revision_id: str | None,
) -> AgentLifecycleStatus:
    revisions_by_id = {revision.id: revision for revision in revisions}
    active_revision = revisions_by_id.get(active_revision_id) if active_revision_id is not None else None
    if active_revision is not None and active_revision.state == AgentRevisionState.PUBLISHED:
        return AgentLifecycleStatus.ACTIVE
    if any(revision.state in _DRAFT_LIKE_REVISION_STATES for revision in revisions):
        return AgentLifecycleStatus.DRAFT
    if any(revision.state == AgentRevisionState.DEPRECATED for revision in revisions):
        return AgentLifecycleStatus.DEPRECATED
    if any(revision.state == AgentRevisionState.PUBLISHED for revision in revisions):
        return AgentLifecycleStatus.ACTIVE
    return AgentLifecycleStatus.ARCHIVED


class AgentsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create_agent(
        self,
        *,
        org_id: str = DEFAULT_INTERNAL_ORG_ID,
        business_id: str,
        environment: str,
        name: str,
        slug: str | None = None,
        description: str | None,
        visibility: AgentVisibility = AgentVisibility.INTERNAL,
        lifecycle_status: AgentLifecycleStatus = AgentLifecycleStatus.DRAFT,
        packaging_metadata: dict | None = None,
        config: dict,
        host_adapter_kind: HostAdapterKind = HostAdapterKind.TRIGGER_DEV,
        skill_ids: list[str] | None = None,
        host_adapter_config: dict | None = None,
        provider_kind: ProviderKind = ProviderKind.ANTHROPIC,
        provider_config: dict | None = None,
        provider_capabilities: list[ProviderCapability] | None = None,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        release_notes: str | None = None,
        compatibility_metadata: dict | None = None,
        release_channel: str = "internal",
    ) -> tuple[AgentRecord, AgentRevisionRecord]:
        if lifecycle_status != AgentLifecycleStatus.DRAFT:
            raise ValueError("New agents must start with lifecycle_status='draft'")
        now = utc_now()
        agent = AgentRecord(
            id=generate_id("agt"),
            org_id=org_id,
            business_id=business_id,
            environment=environment,
            name=name,
            slug=slug or default_agent_slug(name),
            description=description,
            visibility=visibility,
            lifecycle_status=lifecycle_status,
            packaging_metadata=deepcopy(packaging_metadata or {}),
            active_revision_id=None,
            created_at=now,
            updated_at=now,
        )
        revision = AgentRevisionRecord(
            id=generate_id("rev"),
            agent_id=agent.id,
            revision_number=1,
            state=AgentRevisionState.DRAFT,
            config=deepcopy(config),
            host_adapter_kind=host_adapter_kind,
            host_adapter_config=deepcopy(host_adapter_config or {}),
            provider_kind=provider_kind,
            provider_config=deepcopy(provider_config or {}),
            provider_capabilities=deepcopy(provider_capabilities or []),
            skill_ids=deepcopy(skill_ids or []),
            input_schema=deepcopy(input_schema or {}),
            output_schema=deepcopy(output_schema or {}),
            release_notes=release_notes,
            compatibility_metadata=deepcopy(compatibility_metadata or {}),
            release_channel=release_channel,
            created_at=now,
            updated_at=now,
        )
        with self.client.transaction() as store:
            store.agents[agent.id] = agent
            store.agent_revisions[revision.id] = revision
            store.agent_revision_ids_by_agent[agent.id] = [revision.id]
        return agent, revision

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        with self.client.transaction() as store:
            return store.agents.get(agent_id)

    def list_agents(
        self,
        *,
        org_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[AgentRecord]:
        with self.client.transaction() as store:
            agents = list(store.agents.values())
        if org_id is not None:
            agents = [agent for agent in agents if agent.org_id == org_id]
        if business_id is not None:
            agents = [agent for agent in agents if agent.business_id == business_id]
        if environment is not None:
            agents = [agent for agent in agents if agent.environment == environment]
        return agents

    def get_revision(self, revision_id: str) -> AgentRevisionRecord | None:
        with self.client.transaction() as store:
            return store.agent_revisions.get(revision_id)

    def list_revisions(self, agent_id: str) -> list[AgentRevisionRecord]:
        with self.client.transaction() as store:
            revision_ids = store.agent_revision_ids_by_agent.get(agent_id, [])
            return [store.agent_revisions[revision_id] for revision_id in revision_ids]

    def promote_revision_to_candidate(self, agent_id: str, revision_id: str) -> tuple[AgentRecord, AgentRevisionRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            revision = store.agent_revisions.get(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None
            if revision.state == AgentRevisionState.ARCHIVED:
                raise ValueError("Archived revisions cannot become candidates")
            if revision.state == AgentRevisionState.PUBLISHED:
                raise ValueError("Published revisions cannot become candidates")
            if revision.state == AgentRevisionState.DEPRECATED:
                raise ValueError("Deprecated revisions cannot become candidates")
            if revision.state == AgentRevisionState.CANDIDATE:
                return agent, revision

            now = utc_now()
            candidate_revision = revision.model_copy(
                update={
                    "state": AgentRevisionState.CANDIDATE,
                    "archived_at": None,
                    "updated_at": now,
                }
            )
            store.agent_revisions[revision_id] = candidate_revision
            remaining_revisions = [
                store.agent_revisions[candidate_id]
                for candidate_id in store.agent_revision_ids_by_agent.get(agent_id, [])
                if store.agent_revisions[candidate_id].state != AgentRevisionState.ARCHIVED
            ]
            updated_agent = agent.model_copy(
                update={
                    "lifecycle_status": _derive_agent_lifecycle_status(
                        remaining_revisions,
                        active_revision_id=agent.active_revision_id,
                    ),
                    "updated_at": now,
                }
            )
            store.agents[agent_id] = updated_agent
            return updated_agent, candidate_revision

    def publish_revision(self, agent_id: str, revision_id: str) -> tuple[AgentRecord, AgentRevisionRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            revision = store.agent_revisions.get(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None
            if revision.state == AgentRevisionState.ARCHIVED:
                raise ValueError("Archived revisions cannot be published")
            if revision.state == AgentRevisionState.DEPRECATED:
                raise ValueError("Deprecated revisions cannot be republished; create a new candidate instead")

            now = utc_now()
            active_revision_id = agent.active_revision_id
            if active_revision_id and active_revision_id != revision_id:
                active_revision = store.agent_revisions[active_revision_id]
                store.agent_revisions[active_revision_id] = active_revision.model_copy(
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
            store.agent_revisions[revision_id] = published_revision
            store.agents[agent_id] = updated_agent
            return updated_agent, published_revision

    def archive_revision(self, agent_id: str, revision_id: str) -> tuple[AgentRecord, AgentRevisionRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            revision = store.agent_revisions.get(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None

            now = utc_now()
            archived_revision = revision.model_copy(
                update={
                    "state": AgentRevisionState.ARCHIVED,
                    "archived_at": now,
                    "updated_at": now,
                }
            )
            store.agent_revisions[revision_id] = archived_revision

            active_revision_id = agent.active_revision_id
            next_active_revision_id = None if active_revision_id == revision_id else active_revision_id
            remaining_non_archived = [
                candidate
                for candidate_id in store.agent_revision_ids_by_agent.get(agent_id, [])
                if candidate_id != revision_id
                if (candidate := store.agent_revisions[candidate_id]).state != AgentRevisionState.ARCHIVED
            ]
            updated_agent = agent.model_copy(
                update={
                    "active_revision_id": next_active_revision_id,
                    "lifecycle_status": _derive_agent_lifecycle_status(
                        remaining_non_archived,
                        active_revision_id=next_active_revision_id,
                    ),
                    "updated_at": now,
                }
            )
            store.agents[agent_id] = updated_agent
            return updated_agent, archived_revision

    def clone_revision(self, agent_id: str, revision_id: str) -> tuple[AgentRecord, AgentRevisionRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            source_revision = store.agent_revisions.get(revision_id)
            if agent is None or source_revision is None or source_revision.agent_id != agent_id:
                return None

            next_revision_number = len(store.agent_revision_ids_by_agent.get(agent_id, [])) + 1
            now = utc_now()
            cloned_revision = AgentRevisionRecord(
                id=generate_id("rev"),
                agent_id=agent_id,
                revision_number=next_revision_number,
                state=AgentRevisionState.DRAFT,
                config=deepcopy(source_revision.config),
                host_adapter_kind=source_revision.host_adapter_kind,
                host_adapter_config=deepcopy(source_revision.host_adapter_config),
                provider_kind=source_revision.provider_kind,
                provider_config=deepcopy(source_revision.provider_config),
                provider_capabilities=deepcopy(source_revision.provider_capabilities),
                skill_ids=deepcopy(source_revision.skill_ids),
                input_schema=deepcopy(source_revision.input_schema),
                output_schema=deepcopy(source_revision.output_schema),
                release_notes=source_revision.release_notes,
                compatibility_metadata=deepcopy(source_revision.compatibility_metadata),
                release_channel=source_revision.release_channel,
                created_at=now,
                updated_at=now,
                cloned_from_revision_id=source_revision.id,
            )
            store.agent_revisions[cloned_revision.id] = cloned_revision
            store.agent_revision_ids_by_agent.setdefault(agent_id, []).append(cloned_revision.id)
            remaining_non_archived = [
                store.agent_revisions[candidate_id]
                for candidate_id in store.agent_revision_ids_by_agent.get(agent_id, [])
                if store.agent_revisions[candidate_id].state != AgentRevisionState.ARCHIVED
            ]
            store.agents[agent_id] = agent.model_copy(
                update={
                    "lifecycle_status": _derive_agent_lifecycle_status(
                        remaining_non_archived,
                        active_revision_id=agent.active_revision_id,
                    ),
                    "updated_at": now,
                }
            )
            return store.agents[agent_id], cloned_revision
