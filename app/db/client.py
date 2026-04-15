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
    command_keys: dict[tuple[str, str, str, str], str] = field(default_factory=dict)
    approvals: dict[str, ApprovalRecord] = field(default_factory=dict)
    runs: dict[str, RunRecord] = field(default_factory=dict)
    agents: dict[str, object] = field(default_factory=dict)
    agent_revisions: dict[str, object] = field(default_factory=dict)
    agent_revision_ids_by_agent: dict[str, list[str]] = field(default_factory=dict)
    sessions: dict[str, object] = field(default_factory=dict)
    permissions: dict[str, object] = field(default_factory=dict)
    permission_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    outcomes: dict[str, object] = field(default_factory=dict)
    skills: dict[str, object] = field(default_factory=dict)
    skill_keys: dict[str, str] = field(default_factory=dict)
    host_adapter_dispatches: dict[str, object] = field(default_factory=dict)
    agent_assets: dict[str, object] = field(default_factory=dict)
    mission_control_threads: dict[str, object] = field(default_factory=dict)


STORE = InMemoryControlPlaneStore()


def reset_control_plane_store(store: InMemoryControlPlaneStore | None = None) -> None:
    target = store or STORE
    target.commands.clear()
    target.command_keys.clear()
    target.approvals.clear()
    target.runs.clear()
    target.agents.clear()
    target.agent_revisions.clear()
    target.agent_revision_ids_by_agent.clear()
    target.sessions.clear()
    target.permissions.clear()
    target.permission_keys.clear()
    target.outcomes.clear()
    target.skills.clear()
    target.skill_keys.clear()
    target.host_adapter_dispatches.clear()
    target.agent_assets.clear()
    target.mission_control_threads.clear()


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
