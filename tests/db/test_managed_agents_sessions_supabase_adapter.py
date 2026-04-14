from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.db.agents import AgentsRepository
from app.db.sessions import SessionsRepository
from app.models.agents import AgentCreateRequest
from app.models.sessions import SessionAppendEventRequest, SessionCreateRequest
from app.services.agent_registry_service import AgentRegistryService
from app.services.session_service import SessionService


def _matches(row: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    for key, value in filters.items():
        if row.get(key) != value:
            return False
    return True


@dataclass
class FakeManagedSupabaseClient:
    backend: str = "supabase"
    agents: list[dict[str, Any]] = field(default_factory=list)
    agent_revisions: list[dict[str, Any]] = field(default_factory=list)
    agent_sessions: list[dict[str, Any]] = field(default_factory=list)
    agent_session_events: list[dict[str, Any]] = field(default_factory=list)
    _counters: dict[str, int] = field(
        default_factory=lambda: {
            "agents": 0,
            "agent_revisions": 0,
            "agent_sessions": 0,
            "agent_session_events": 0,
        }
    )

    def _table(self, name: str) -> list[dict[str, Any]]:
        return getattr(self, name)

    def select(
        self,
        table: str,
        *,
        columns: str,
        filters: dict[str, Any] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        del columns
        rows = [dict(row) for row in self._table(table) if _matches(row, filters)]
        if order:
            key, _, direction = order.partition(".")
            rows.sort(key=lambda item: item.get(key))
            if direction == "desc":
                rows.reverse()
        if limit is not None:
            rows = rows[:limit]
        return rows

    def insert(
        self,
        table: str,
        *,
        rows: list[dict[str, Any]],
        columns: str,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> list[dict[str, Any]]:
        del columns, on_conflict, ignore_duplicates
        inserted: list[dict[str, Any]] = []
        for row in rows:
            self._counters[table] += 1
            enriched = dict(row)
            enriched.setdefault("id", self._counters[table])
            now = datetime.now(UTC).isoformat()
            enriched.setdefault("created_at", now)
            enriched.setdefault("updated_at", now)
            self._table(table).append(enriched)
            inserted.append(dict(enriched))
        return inserted

    def update(
        self,
        table: str,
        *,
        values: dict[str, Any],
        filters: dict[str, Any],
        columns: str,
    ) -> list[dict[str, Any]]:
        del columns
        rows = self._table(table)
        updated: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            if not _matches(row, filters):
                continue
            next_row = dict(row)
            next_row.update(values)
            if "updated_at" not in values:
                next_row["updated_at"] = datetime.now(UTC).isoformat()
            rows[index] = next_row
            updated.append(dict(next_row))
        return updated


def _build_managed_repositories(client: FakeManagedSupabaseClient) -> tuple[AgentsRepository, SessionsRepository]:
    return AgentsRepository(client), SessionsRepository(client)


def test_supabase_agents_create_publish_and_clone_persist_revision_state() -> None:
    client = FakeManagedSupabaseClient()
    agents_repository, _ = _build_managed_repositories(client)

    agent, first_revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Research Agent",
        description="Managed research worker",
        config={"prompt": "find seller leads"},
    )
    agents_repository.publish_revision(agent.id, first_revision.id)
    _, cloned_revision = agents_repository.clone_revision(agent.id, first_revision.id) or (None, None)
    assert cloned_revision is not None
    agents_repository.publish_revision(agent.id, cloned_revision.id)

    loaded_agent = agents_repository.get_agent(agent.id)
    revisions = agents_repository.list_revisions(agent.id)
    revisions_by_id = {revision.id: revision for revision in revisions}

    assert loaded_agent is not None
    assert loaded_agent.active_revision_id == cloned_revision.id
    assert revisions_by_id[first_revision.id].state.value == "archived"
    assert revisions_by_id[cloned_revision.id].state.value == "published"
    assert revisions_by_id[cloned_revision.id].revision_number == 2
    assert revisions_by_id[cloned_revision.id].cloned_from_revision_id == first_revision.id
    assert client.agents[0]["runtime_id"].startswith("agt_")
    assert all(row["runtime_id"].startswith("rev_") for row in client.agent_revisions)


def test_supabase_sessions_create_and_append_event_persist_timeline() -> None:
    client = FakeManagedSupabaseClient()
    agents_repository, sessions_repository = _build_managed_repositories(client)

    agent, revision = agents_repository.create_agent(
        business_id="limitless",
        environment="dev",
        name="Session Agent",
        description=None,
        config={"prompt": "coordinate outreach"},
    )
    created = sessions_repository.create(
        agent_id=agent.id,
        agent_revision_id=revision.id,
        business_id="limitless",
        environment="dev",
        initial_message="Handle landlord outreach",
    )
    sessions_repository.append_event(
        created.id,
        event_type="assistant_note",
        payload={"message": "draft ready"},
    )

    loaded = sessions_repository.get(created.id)

    assert loaded is not None
    assert [entry.event_type for entry in loaded.timeline] == [
        "session_created",
        "message",
        "assistant_note",
    ]
    assert loaded.timeline[-1].payload["message"] == "draft ready"
    assert loaded.updated_at == loaded.timeline[-1].created_at
    assert len(client.agent_session_events) == 3
    assert all(row["runtime_id"].startswith("sev_") for row in client.agent_session_events)


def test_supabase_services_persist_session_events_through_repositories() -> None:
    client = FakeManagedSupabaseClient()
    agents_repository, sessions_repository = _build_managed_repositories(client)
    agent_registry_service = AgentRegistryService(agents_repository)
    session_service = SessionService(sessions_repository, agents_repository)

    created = agent_registry_service.create_agent(
        AgentCreateRequest(name="Ops Agent", config={"prompt": "keep pipeline moving"})
    )
    first_revision_id = created.revisions[0].id
    agent_registry_service.publish_revision(created.agent.id, first_revision_id)

    session = session_service.create_session(
        SessionCreateRequest(
            agent_revision_id=first_revision_id,
            business_id="limitless",
            environment="dev",
            initial_message="Queue next sequence",
        )
    )
    session_service.append_event(
        session.id,
        SessionAppendEventRequest(
            event_type="assistant_note",
            payload={"message": "ready for review"},
        ),
    )
    persisted = session_service.get_session(session.id)

    assert persisted is not None
    assert persisted.agent_revision_id == first_revision_id
    assert [entry.event_type for entry in persisted.timeline] == [
        "session_created",
        "message",
        "assistant_note",
    ]
