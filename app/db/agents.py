from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.agents import AgentRecord, AgentRevisionRecord, AgentRevisionState
from app.models.commands import generate_id


class AgentsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create_agent(self, *, name: str, description: str | None, config: dict) -> tuple[AgentRecord, AgentRevisionRecord]:
        now = utc_now()
        agent = AgentRecord(
            id=generate_id("agt"),
            name=name,
            description=description,
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

    def get_revision(self, revision_id: str) -> AgentRevisionRecord | None:
        with self.client.transaction() as store:
            return store.agent_revisions.get(revision_id)

    def list_revisions(self, agent_id: str) -> list[AgentRevisionRecord]:
        with self.client.transaction() as store:
            revision_ids = store.agent_revision_ids_by_agent.get(agent_id, [])
            return [store.agent_revisions[revision_id] for revision_id in revision_ids]

    def publish_revision(self, agent_id: str, revision_id: str) -> tuple[AgentRecord, AgentRevisionRecord] | None:
        with self.client.transaction() as store:
            agent = store.agents.get(agent_id)
            revision = store.agent_revisions.get(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None
            if revision.state == AgentRevisionState.ARCHIVED:
                raise ValueError("Archived revisions cannot be published")

            now = utc_now()
            active_revision_id = agent.active_revision_id
            if active_revision_id and active_revision_id != revision_id:
                active_revision = store.agent_revisions[active_revision_id]
                store.agent_revisions[active_revision_id] = active_revision.model_copy(
                    update={
                        "state": AgentRevisionState.ARCHIVED,
                        "archived_at": now,
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
            updated_agent = agent.model_copy(update={"active_revision_id": revision_id, "updated_at": now})
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
            active_revision_id = agent.active_revision_id
            updated_agent = agent
            if active_revision_id == revision_id:
                updated_agent = agent.model_copy(update={"active_revision_id": None, "updated_at": now})
                store.agents[agent_id] = updated_agent
            store.agent_revisions[revision_id] = archived_revision
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
                created_at=now,
                updated_at=now,
                cloned_from_revision_id=source_revision.id,
            )
            store.agent_revisions[cloned_revision.id] = cloned_revision
            store.agent_revision_ids_by_agent.setdefault(agent_id, []).append(cloned_revision.id)
            store.agents[agent_id] = agent.model_copy(update={"updated_at": now})
            return store.agents[agent_id], cloned_revision
