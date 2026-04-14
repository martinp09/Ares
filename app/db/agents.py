from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from app.db.client import ControlPlaneClient, SupabaseControlPlaneClient, get_control_plane_client, utc_now
from app.models.agents import AgentRecord, AgentRevisionRecord, AgentRevisionState
from app.models.commands import generate_id


def agent_record_from_row(row: Mapping[str, Any]) -> AgentRecord:
    return AgentRecord(
        id=str(row.get("runtime_id") or row["id"]),
        business_id=str(row["business_id"]),
        environment=str(row["environment"]),
        name=str(row["name"]),
        description=str(row["description"]) if row.get("description") is not None else None,
        active_revision_id=(
            str(row["active_revision_runtime_id"])
            if row.get("active_revision_runtime_id") is not None
            else None
        ),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def agent_revision_record_from_row(row: Mapping[str, Any]) -> AgentRevisionRecord:
    return AgentRevisionRecord(
        id=str(row.get("runtime_id") or row["id"]),
        agent_id=str(row["agent_runtime_id"]),
        revision_number=int(row["revision_number"]),
        state=AgentRevisionState(str(row["state"])),
        config=dict(row["config"]) if isinstance(row.get("config"), Mapping) else {},
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row.get("published_at"),
        archived_at=row.get("archived_at"),
        cloned_from_revision_id=(
            str(row["cloned_from_revision_runtime_id"])
            if row.get("cloned_from_revision_runtime_id") is not None
            else None
        ),
    )


class AgentsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def _select_supabase_agent(self, agent_id: str) -> AgentRecord | None:
        rows = self._supabase_client().select(
            "agents",
            columns="id,runtime_id,business_id,environment,name,description,active_revision_runtime_id,created_at,updated_at",
            filters={"runtime_id": agent_id},
            limit=1,
        )
        if not rows:
            return None
        return agent_record_from_row(rows[0])

    def _select_supabase_revision(self, revision_id: str) -> AgentRevisionRecord | None:
        rows = self._supabase_client().select(
            "agent_revisions",
            columns=(
                "id,runtime_id,agent_runtime_id,revision_number,state,config,created_at,updated_at,"
                "published_at,archived_at,cloned_from_revision_runtime_id"
            ),
            filters={"runtime_id": revision_id},
            limit=1,
        )
        if not rows:
            return None
        return agent_revision_record_from_row(rows[0])

    def create_agent(
        self,
        *,
        business_id: str,
        environment: str,
        name: str,
        description: str | None,
        config: dict,
    ) -> tuple[AgentRecord, AgentRevisionRecord]:
        now = utc_now()
        agent = AgentRecord(
            id=generate_id("agt"),
            business_id=business_id,
            environment=environment,
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
        if self._is_supabase():
            agent_rows = self._supabase_client().insert(
                "agents",
                rows=[
                    {
                        "runtime_id": agent.id,
                        "business_id": agent.business_id,
                        "environment": agent.environment,
                        "name": agent.name,
                        "description": agent.description,
                        "active_revision_runtime_id": agent.active_revision_id,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    }
                ],
                columns=(
                    "id,runtime_id,business_id,environment,name,description,"
                    "active_revision_runtime_id,created_at,updated_at"
                ),
            )
            if not agent_rows:
                raise RuntimeError("Supabase agent insert failed without returning a row")

            revision_rows = self._supabase_client().insert(
                "agent_revisions",
                rows=[
                    {
                        "runtime_id": revision.id,
                        "agent_runtime_id": agent.id,
                        "revision_number": revision.revision_number,
                        "state": revision.state.value,
                        "config": revision.config,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "published_at": None,
                        "archived_at": None,
                        "cloned_from_revision_runtime_id": None,
                    }
                ],
                columns=(
                    "id,runtime_id,agent_runtime_id,revision_number,state,config,created_at,updated_at,"
                    "published_at,archived_at,cloned_from_revision_runtime_id"
                ),
            )
            if not revision_rows:
                raise RuntimeError("Supabase agent revision insert failed without returning a row")
            return agent_record_from_row(agent_rows[0]), agent_revision_record_from_row(revision_rows[0])

        with self.client.transaction() as store:
            store.agents[agent.id] = agent
            store.agent_revisions[revision.id] = revision
            store.agent_revision_ids_by_agent[agent.id] = [revision.id]
        return agent, revision

    def get_agent(self, agent_id: str) -> AgentRecord | None:
        if self._is_supabase():
            return self._select_supabase_agent(agent_id)
        with self.client.transaction() as store:
            return store.agents.get(agent_id)

    def list_agents(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[AgentRecord]:
        if self._is_supabase():
            filters: dict[str, str] = {}
            if business_id is not None:
                filters["business_id"] = business_id
            if environment is not None:
                filters["environment"] = environment
            rows = self._supabase_client().select(
                "agents",
                columns=(
                    "id,runtime_id,business_id,environment,name,description,"
                    "active_revision_runtime_id,created_at,updated_at"
                ),
                filters=filters,
                order="created_at.asc",
            )
            return [agent_record_from_row(row) for row in rows]

        with self.client.transaction() as store:
            agents = list(store.agents.values())
        if business_id is not None:
            agents = [agent for agent in agents if agent.business_id == business_id]
        if environment is not None:
            agents = [agent for agent in agents if agent.environment == environment]
        return agents

    def get_revision(self, revision_id: str) -> AgentRevisionRecord | None:
        if self._is_supabase():
            return self._select_supabase_revision(revision_id)
        with self.client.transaction() as store:
            return store.agent_revisions.get(revision_id)

    def list_revisions(self, agent_id: str) -> list[AgentRevisionRecord]:
        if self._is_supabase():
            rows = self._supabase_client().select(
                "agent_revisions",
                columns=(
                    "id,runtime_id,agent_runtime_id,revision_number,state,config,created_at,updated_at,"
                    "published_at,archived_at,cloned_from_revision_runtime_id"
                ),
                filters={"agent_runtime_id": agent_id},
                order="revision_number.asc",
            )
            return [agent_revision_record_from_row(row) for row in rows]

        with self.client.transaction() as store:
            revision_ids = store.agent_revision_ids_by_agent.get(agent_id, [])
            return [store.agent_revisions[revision_id] for revision_id in revision_ids]

    def publish_revision(self, agent_id: str, revision_id: str) -> tuple[AgentRecord, AgentRevisionRecord] | None:
        if self._is_supabase():
            agent = self._select_supabase_agent(agent_id)
            revision = self._select_supabase_revision(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None
            if revision.state == AgentRevisionState.ARCHIVED:
                raise ValueError("Archived revisions cannot be published")

            now = utc_now()
            active_revision_id = agent.active_revision_id
            if active_revision_id and active_revision_id != revision_id:
                archived_rows = self._supabase_client().update(
                    "agent_revisions",
                    values={
                        "state": AgentRevisionState.ARCHIVED.value,
                        "archived_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                    },
                    filters={"runtime_id": active_revision_id},
                    columns=(
                        "id,runtime_id,agent_runtime_id,revision_number,state,config,created_at,updated_at,"
                        "published_at,archived_at,cloned_from_revision_runtime_id"
                    ),
                )
                if not archived_rows:
                    raise RuntimeError(f"Supabase active revision archive failed for runtime_id '{active_revision_id}'")

            published_rows = self._supabase_client().update(
                "agent_revisions",
                values={
                    "state": AgentRevisionState.PUBLISHED.value,
                    "published_at": (revision.published_at or now).isoformat(),
                    "archived_at": None,
                    "updated_at": now.isoformat(),
                },
                filters={"runtime_id": revision_id},
                columns=(
                    "id,runtime_id,agent_runtime_id,revision_number,state,config,created_at,updated_at,"
                    "published_at,archived_at,cloned_from_revision_runtime_id"
                ),
            )
            if not published_rows:
                raise RuntimeError(f"Supabase revision publish failed for runtime_id '{revision_id}'")

            agent_rows = self._supabase_client().update(
                "agents",
                values={
                    "active_revision_runtime_id": revision_id,
                    "updated_at": now.isoformat(),
                },
                filters={"runtime_id": agent_id},
                columns=(
                    "id,runtime_id,business_id,environment,name,description,"
                    "active_revision_runtime_id,created_at,updated_at"
                ),
            )
            if not agent_rows:
                raise RuntimeError(f"Supabase agent publish update failed for runtime_id '{agent_id}'")
            return agent_record_from_row(agent_rows[0]), agent_revision_record_from_row(published_rows[0])

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
        if self._is_supabase():
            agent = self._select_supabase_agent(agent_id)
            revision = self._select_supabase_revision(revision_id)
            if agent is None or revision is None or revision.agent_id != agent_id:
                return None

            now = utc_now()
            archived_rows = self._supabase_client().update(
                "agent_revisions",
                values={
                    "state": AgentRevisionState.ARCHIVED.value,
                    "archived_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                },
                filters={"runtime_id": revision_id},
                columns=(
                    "id,runtime_id,agent_runtime_id,revision_number,state,config,created_at,updated_at,"
                    "published_at,archived_at,cloned_from_revision_runtime_id"
                ),
            )
            if not archived_rows:
                raise RuntimeError(f"Supabase revision archive failed for runtime_id '{revision_id}'")

            updated_agent = agent
            if agent.active_revision_id == revision_id:
                agent_rows = self._supabase_client().update(
                    "agents",
                    values={
                        "active_revision_runtime_id": None,
                        "updated_at": now.isoformat(),
                    },
                    filters={"runtime_id": agent_id},
                    columns=(
                        "id,runtime_id,business_id,environment,name,description,"
                        "active_revision_runtime_id,created_at,updated_at"
                    ),
                )
                if not agent_rows:
                    raise RuntimeError(f"Supabase agent archive update failed for runtime_id '{agent_id}'")
                updated_agent = agent_record_from_row(agent_rows[0])
            return updated_agent, agent_revision_record_from_row(archived_rows[0])

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
        if self._is_supabase():
            agent = self._select_supabase_agent(agent_id)
            source_revision = self._select_supabase_revision(revision_id)
            if agent is None or source_revision is None or source_revision.agent_id != agent_id:
                return None

            latest_rows = self._supabase_client().select(
                "agent_revisions",
                columns="revision_number",
                filters={"agent_runtime_id": agent_id},
                order="revision_number.desc",
                limit=1,
            )
            next_revision_number = (int(latest_rows[0]["revision_number"]) if latest_rows else 0) + 1

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
            cloned_rows = self._supabase_client().insert(
                "agent_revisions",
                rows=[
                    {
                        "runtime_id": cloned_revision.id,
                        "agent_runtime_id": agent_id,
                        "revision_number": cloned_revision.revision_number,
                        "state": cloned_revision.state.value,
                        "config": cloned_revision.config,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "published_at": None,
                        "archived_at": None,
                        "cloned_from_revision_runtime_id": source_revision.id,
                    }
                ],
                columns=(
                    "id,runtime_id,agent_runtime_id,revision_number,state,config,created_at,updated_at,"
                    "published_at,archived_at,cloned_from_revision_runtime_id"
                ),
            )
            if not cloned_rows:
                raise RuntimeError(f"Supabase revision clone insert failed for runtime_id '{revision_id}'")

            agent_rows = self._supabase_client().update(
                "agents",
                values={"updated_at": now.isoformat()},
                filters={"runtime_id": agent_id},
                columns=(
                    "id,runtime_id,business_id,environment,name,description,"
                    "active_revision_runtime_id,created_at,updated_at"
                ),
            )
            if not agent_rows:
                raise RuntimeError(f"Supabase agent clone update failed for runtime_id '{agent_id}'")
            return agent_record_from_row(agent_rows[0]), agent_revision_record_from_row(cloned_rows[0])

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
