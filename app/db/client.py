from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Iterator, Literal, Protocol

from app.core.config import Settings, get_settings
from app.models.approvals import ApprovalRecord
from app.models.commands import CommandRecord
from app.models.runs import RunRecord


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class InMemoryControlPlaneStore:
    commands: dict[str, CommandRecord] = field(default_factory=dict)
    command_keys: dict[tuple[int, str, str, str], str] = field(default_factory=dict)
    command_runtime_to_sql_id: dict[str, int] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    approval_runtime_to_sql_id: dict[str, int] = field(default_factory=dict)
    runs: dict[str, RunRecord] = field(default_factory=dict)
    run_runtime_to_sql_id: dict[str, int] = field(default_factory=dict)
    event_runtime_to_sql_id: dict[str, int] = field(default_factory=dict)
    artifact_runtime_to_sql_id: dict[str, int] = field(default_factory=dict)
    agents: dict[str, object] = field(default_factory=dict)
    agent_revisions: dict[str, object] = field(default_factory=dict)
    agent_revision_ids_by_agent: dict[str, list[str]] = field(default_factory=dict)
    sessions: dict[str, object] = field(default_factory=dict)
    permissions: dict[str, object] = field(default_factory=dict)
    permission_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    outcomes: dict[str, object] = field(default_factory=dict)
    agent_assets: dict[str, object] = field(default_factory=dict)
    mission_control_threads: dict[str, object] = field(default_factory=dict)
    sql_identity_counters: dict[str, int] = field(
        default_factory=lambda: {
            "commands": 0,
            "approvals": 0,
            "runs": 0,
            "events": 0,
            "artifacts": 0,
        }
    )


STORE = InMemoryControlPlaneStore()


def reset_control_plane_store(store: InMemoryControlPlaneStore | None = None) -> None:
    target = store or STORE
    target.commands.clear()
    target.command_keys.clear()
    target.command_runtime_to_sql_id.clear()
    target.approvals.clear()
    target.approval_runtime_to_sql_id.clear()
    target.runs.clear()
    target.run_runtime_to_sql_id.clear()
    target.event_runtime_to_sql_id.clear()
    target.artifact_runtime_to_sql_id.clear()
    target.agents.clear()
    target.agent_revisions.clear()
    target.agent_revision_ids_by_agent.clear()
    target.sessions.clear()
    target.permissions.clear()
    target.permission_keys.clear()
    target.outcomes.clear()
    target.agent_assets.clear()
    target.mission_control_threads.clear()
    target.sql_identity_counters.clear()
    target.sql_identity_counters.update(
        {
            "commands": 0,
            "approvals": 0,
            "runs": 0,
            "events": 0,
            "artifacts": 0,
        }
    )


def register_runtime_sql_identity(
    store: InMemoryControlPlaneStore,
    *,
    table: Literal["commands", "approvals", "runs", "events", "artifacts"],
    runtime_id: str,
) -> int:
    runtime_maps = {
        "commands": store.command_runtime_to_sql_id,
        "approvals": store.approval_runtime_to_sql_id,
        "runs": store.run_runtime_to_sql_id,
        "events": store.event_runtime_to_sql_id,
        "artifacts": store.artifact_runtime_to_sql_id,
    }
    runtime_map = runtime_maps[table]
    existing = runtime_map.get(runtime_id)
    if existing is not None:
        return existing

    next_sql_id = store.sql_identity_counters[table] + 1
    store.sql_identity_counters[table] = next_sql_id
    runtime_map[runtime_id] = next_sql_id
    return next_sql_id


class ControlPlaneClient(Protocol):
    backend: str

    def transaction(self) -> Iterator[InMemoryControlPlaneStore]: ...


class InMemoryControlPlaneClient:
    backend: Literal["memory"] = "memory"

    def __init__(self, store: InMemoryControlPlaneStore | None = None):
        self.store = store or STORE

    @contextmanager
    def transaction(self) -> Iterator[InMemoryControlPlaneStore]:
        yield self.store


class SupabaseControlPlaneClient:
    backend: Literal["supabase"] = "supabase"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @contextmanager
    def transaction(self) -> Iterator[InMemoryControlPlaneStore]:
        raise NotImplementedError(
            "Live Supabase wiring is deferred in this environment; use the in-memory control-plane adapter for now."
        )
        yield STORE


def get_control_plane_client(settings: Settings | None = None) -> ControlPlaneClient:
    active_settings = settings or get_settings()
    if active_settings.control_plane_backend == "supabase":
        return SupabaseControlPlaneClient(active_settings)
    return InMemoryControlPlaneClient()
