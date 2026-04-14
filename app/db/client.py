from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Iterator, Literal, Protocol
from urllib import error, parse, request

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

    def __init__(self, settings: Settings | None = None, store: InMemoryControlPlaneStore | None = None):
        self.settings = settings or get_settings()
        self.store = store or STORE

    def _base_url(self) -> str:
        if not self.settings.supabase_url:
            raise RuntimeError("SUPABASE_URL is required for control-plane supabase persistence")
        return self.settings.supabase_url.rstrip("/")

    def _headers(self, *, prefer: str | None = None) -> dict[str, str]:
        if not self.settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required for control-plane supabase persistence")
        headers = {
            "Content-Type": "application/json",
            "apikey": self.settings.supabase_service_role_key,
            "Authorization": f"Bearer {self.settings.supabase_service_role_key}",
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _request_rows(
        self,
        *,
        method: str,
        table: str,
        query: dict[str, str] | None = None,
        payload: list[dict] | dict | None = None,
        prefer: str | None = None,
    ) -> list[dict]:
        query_string = parse.urlencode(query or {})
        endpoint = f"{self._base_url()}/rest/v1/{table}"
        url = f"{endpoint}?{query_string}" if query_string else endpoint
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = request.Request(
            url,
            data=data,
            headers=self._headers(prefer=prefer),
            method=method,
        )
        try:
            with request.urlopen(req, timeout=5) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:  # pragma: no cover - networked failure path
            detail = exc.read().decode("utf-8")
            raise RuntimeError(f"Supabase {table} {method} failed: {detail}") from exc

        if not raw:
            return []
        rows = json.loads(raw)
        if isinstance(rows, list):
            return rows
        if isinstance(rows, dict):
            return [rows]
        raise RuntimeError(f"Unexpected Supabase response for {table}: {rows!r}")

    def select(
        self,
        table: str,
        *,
        columns: str,
        filters: dict[str, str | int] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        query: dict[str, str] = {"select": columns}
        for key, value in (filters or {}).items():
            query[key] = f"eq.{value}"
        if order:
            query["order"] = order
        if limit is not None:
            query["limit"] = str(limit)
        return self._request_rows(method="GET", table=table, query=query)

    def insert(
        self,
        table: str,
        *,
        rows: list[dict],
        columns: str,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> list[dict]:
        query: dict[str, str] = {"select": columns}
        if on_conflict:
            query["on_conflict"] = on_conflict
        prefer_parts = ["return=representation"]
        if ignore_duplicates:
            prefer_parts.insert(0, "resolution=ignore-duplicates")
        prefer = ",".join(prefer_parts)
        return self._request_rows(
            method="POST",
            table=table,
            query=query,
            payload=rows,
            prefer=prefer,
        )

    def update(
        self,
        table: str,
        *,
        values: dict,
        filters: dict[str, str | int],
        columns: str,
    ) -> list[dict]:
        query: dict[str, str] = {"select": columns}
        for key, value in filters.items():
            query[key] = f"eq.{value}"
        return self._request_rows(
            method="PATCH",
            table=table,
            query=query,
            payload=values,
            prefer="return=representation",
        )

    @contextmanager
    def transaction(self) -> Iterator[InMemoryControlPlaneStore]:
        yield self.store


def get_control_plane_client(settings: Settings | None = None) -> ControlPlaneClient:
    active_settings = settings or get_settings()
    if active_settings.control_plane_backend == "supabase":
        return SupabaseControlPlaneClient(active_settings)
    return InMemoryControlPlaneClient()
