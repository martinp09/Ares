from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.db.control_plane_supabase import fetch_rows, insert_rows, patch_rows
from app.models.agent_installs import AgentInstallRecord
from app.models.agent_assets import AgentAssetRecord
from app.models.agents import AgentRecord, AgentRevisionRecord
from app.models.approvals import ApprovalRecord, ApprovalStatus
from app.models.audit import AuditRecord
from app.models.catalog import CatalogEntryRecord
from app.models.commands import CommandPolicy, CommandRecord, CommandStatus
from app.models.host_adapters import HostAdapterDispatchRecord
from app.models.mission_control import MissionControlThreadRecord
from app.models.organizations import MembershipRecord, OrganizationRecord
from app.models.outcomes import OutcomeRecord
from app.models.permissions import PermissionRecord
from app.models.rbac import OrgPolicyRecord, OrgRoleAssignmentRecord, OrgRoleGrantRecord, OrgRoleRecord
from app.models.release_management import ReleaseEventRecord
from app.models.runs import RunRecord, RunStatus
from app.models.secrets import SecretBindingRecord, SecretRecord
from app.models.session_journal import SessionMemorySummary
from app.models.sessions import SessionRecord
from app.models.skills import SkillRecord
from app.models.turns import TurnEventRecord, TurnRecord
from app.models.usage import UsageRecord

if TYPE_CHECKING:
    from app.db.client import InMemoryControlPlaneStore


TEXT_TABLES: dict[str, tuple[str, object]] = {
    "agents_runtime": ("agents", AgentRecord),
    "agent_revisions_runtime": ("agent_revisions", AgentRevisionRecord),
    "sessions_runtime": ("sessions", SessionRecord),
    "session_memory_summaries_runtime": ("session_memory_summaries", SessionMemorySummary),
    "turns_runtime": ("turns", TurnRecord),
    "turn_events_runtime": ("turn_events", TurnEventRecord),
    "permissions_runtime": ("permissions", PermissionRecord),
    "org_roles_runtime": ("roles", OrgRoleRecord),
    "org_role_grants_runtime": ("role_grants", OrgRoleGrantRecord),
    "org_role_assignments_runtime": ("role_assignments", OrgRoleAssignmentRecord),
    "org_policies_runtime": ("org_policies", OrgPolicyRecord),
    "secrets_runtime": ("secrets", SecretRecord),
    "secret_bindings_runtime": ("secret_bindings", SecretBindingRecord),
    "audit_events_runtime": ("audit_events", AuditRecord),
    "usage_events_runtime": ("usage_events", UsageRecord),
    "outcomes_runtime": ("outcomes", OutcomeRecord),
    "agent_assets_runtime": ("agent_assets", AgentAssetRecord),
    "mission_control_threads_runtime": ("mission_control_threads", MissionControlThreadRecord),
    "skills_runtime": ("skills", SkillRecord),
    "host_adapter_dispatches_runtime": ("host_adapter_dispatches", HostAdapterDispatchRecord),
}

COMMON_NORMALIZED_FIELDS = (
    "org_id",
    "business_id",
    "environment",
    "agent_id",
    "agent_revision_id",
    "session_id",
    "turn_id",
    "tool_name",
    "name",
    "role_id",
    "binding_name",
    "status",
    "event_type",
    "kind",
)

TABLE_NORMALIZED_FIELDS: dict[str, tuple[str, ...]] = {
    "organizations_runtime": ("slug", "is_internal"),
    "memberships_runtime": ("actor_id", "actor_type", "role_name"),
    "catalog_entries_runtime": ("slug",),
    "agent_installs_runtime": ("catalog_entry_id", "installed_agent_id"),
}


def hydrate_control_plane_store(settings: Settings) -> InMemoryControlPlaneStore:
    from app.db.client import InMemoryControlPlaneStore

    store = InMemoryControlPlaneStore()
    _hydrate_core_commands(store, settings)
    _hydrate_text_table(store.agents, "agents_runtime", AgentRecord, settings)
    _hydrate_text_table(store.agent_revisions, "agent_revisions_runtime", AgentRevisionRecord, settings)
    for revision in store.agent_revisions.values():
        store.agent_revision_ids_by_agent.setdefault(revision.agent_id, []).append(revision.id)
    for values in store.agent_revision_ids_by_agent.values():
        values.sort(key=lambda revision_id: store.agent_revisions[revision_id].revision_number)
    _hydrate_text_table(store.sessions, "sessions_runtime", SessionRecord, settings)
    _hydrate_text_table(store.session_memory_summaries, "session_memory_summaries_runtime", SessionMemorySummary, settings)
    _hydrate_text_table(store.turns, "turns_runtime", TurnRecord, settings)
    _hydrate_text_table(store.permissions, "permissions_runtime", PermissionRecord, settings)
    for record in store.permissions.values():
        store.permission_keys[(record.agent_revision_id, record.tool_name)] = record.id
    _hydrate_text_table(store.roles, "org_roles_runtime", OrgRoleRecord, settings)
    for record in store.roles.values():
        store.role_keys[(record.org_id, record.name)] = record.id
    _hydrate_text_table(store.organizations, "organizations_runtime", OrganizationRecord, settings)
    store.organization_keys.clear()
    for record in store.organizations.values():
        if record.slug:
            store.organization_keys[record.slug.strip().casefold()] = record.id
    _hydrate_text_table(store.memberships, "memberships_runtime", MembershipRecord, settings)
    store.membership_keys.clear()
    store.membership_ids_by_org.clear()
    store.membership_ids_by_actor.clear()
    for record in store.memberships.values():
        store.membership_keys[(record.org_id, record.actor_id)] = record.id
        store.membership_ids_by_org.setdefault(record.org_id, []).append(record.id)
        store.membership_ids_by_actor.setdefault(record.actor_id, []).append(record.id)
    for membership_ids in store.membership_ids_by_org.values():
        membership_ids.sort(key=lambda membership_id: (store.memberships[membership_id].created_at, membership_id))
    for membership_ids in store.membership_ids_by_actor.values():
        membership_ids.sort(key=lambda membership_id: (store.memberships[membership_id].created_at, membership_id))
    _hydrate_text_table(store.catalog_entries, "catalog_entries_runtime", CatalogEntryRecord, settings)
    store.catalog_entry_keys.clear()
    store.catalog_entry_ids_by_org.clear()
    for record in store.catalog_entries.values():
        store.catalog_entry_keys[(record.org_id, record.slug.strip().casefold())] = record.id
        store.catalog_entry_ids_by_org.setdefault(record.org_id, []).append(record.id)
    for entry_ids in store.catalog_entry_ids_by_org.values():
        entry_ids.sort(key=lambda entry_id: (store.catalog_entries[entry_id].created_at, entry_id))
    _hydrate_text_table(store.agent_installs, "agent_installs_runtime", AgentInstallRecord, settings)
    store.agent_install_ids_by_org.clear()
    for record in store.agent_installs.values():
        store.agent_install_ids_by_org.setdefault(record.org_id, []).append(record.id)
    for install_ids in store.agent_install_ids_by_org.values():
        install_ids.sort(key=lambda install_id: (store.agent_installs[install_id].created_at, install_id))
    _hydrate_text_table(store.release_events, "release_events_runtime", ReleaseEventRecord, settings)
    store.release_event_ids_by_agent.clear()
    for record in store.release_events.values():
        store.release_event_ids_by_agent.setdefault(record.agent_id, []).append(record.id)
    for event_ids in store.release_event_ids_by_agent.values():
        event_ids.sort(key=lambda event_id: (store.release_events[event_id].created_at, event_id))
    _hydrate_text_table(store.role_grants, "org_role_grants_runtime", OrgRoleGrantRecord, settings)
    for record in store.role_grants.values():
        store.role_grant_keys[(record.role_id, record.tool_name)] = record.id
    _hydrate_text_table(store.role_assignments, "org_role_assignments_runtime", OrgRoleAssignmentRecord, settings)
    for record in store.role_assignments.values():
        store.role_assignment_keys[(record.agent_revision_id, record.role_id)] = record.id
    _hydrate_text_table(store.org_policies, "org_policies_runtime", OrgPolicyRecord, settings)
    for record in store.org_policies.values():
        store.org_policy_keys[(record.org_id, record.tool_name)] = record.id
    _hydrate_text_table(store.secrets, "secrets_runtime", SecretRecord, settings)
    for record in store.secrets.values():
        store.secret_keys[(record.org_id, record.name)] = record.id
    _hydrate_text_table(store.secret_bindings, "secret_bindings_runtime", SecretBindingRecord, settings)
    for record in store.secret_bindings.values():
        store.secret_binding_keys[(record.agent_revision_id, record.binding_name)] = record.id
    _hydrate_text_table(store.audit_events, "audit_events_runtime", AuditRecord, settings)
    _hydrate_text_table(store.usage_events, "usage_events_runtime", UsageRecord, settings)
    _hydrate_text_table(store.outcomes, "outcomes_runtime", OutcomeRecord, settings)
    _hydrate_text_table(store.agent_assets, "agent_assets_runtime", AgentAssetRecord, settings)
    _hydrate_text_table(store.mission_control_threads, "mission_control_threads_runtime", MissionControlThreadRecord, settings)
    _hydrate_text_table(store.skills, "skills_runtime", SkillRecord, settings)
    for record in store.skills.values():
        store.skill_keys[record.name.strip().lower()] = record.id
    _hydrate_text_table(store.host_adapter_dispatches, "host_adapter_dispatches_runtime", HostAdapterDispatchRecord, settings)
    _hydrate_scope_snapshots(store.ares_plans_by_scope, "ares_plans_runtime", settings)
    _hydrate_scope_snapshots(store.ares_execution_runs_by_scope, "ares_execution_runs_runtime", settings)
    _hydrate_scope_snapshots(store.ares_operator_runs_by_scope, "ares_operator_runs_runtime", settings)
    _hydrate_text_table(store.turn_events, "turn_events_runtime", TurnEventRecord, settings, grouped=True)
    for turn_id, events in store.turn_events.items():
        events.sort(key=lambda event: event.sequence_number)
        if turn_id in store.turns:
            store.turn_ids_by_session.setdefault(store.turns[turn_id].session_id, []).append(turn_id)
    for session_id, turn_ids in store.turn_ids_by_session.items():
        turn_ids.sort(key=lambda turn_id: store.turns[turn_id].turn_number)
    return store


def persist_control_plane_store(store: InMemoryControlPlaneStore, settings: Settings) -> None:
    for table, rows in (
        ("agents_runtime", store.agents.values()),
        ("agent_revisions_runtime", store.agent_revisions.values()),
        ("organizations_runtime", store.organizations.values()),
        ("memberships_runtime", store.memberships.values()),
        ("catalog_entries_runtime", store.catalog_entries.values()),
        ("agent_installs_runtime", store.agent_installs.values()),
        ("release_events_runtime", store.release_events.values()),
        ("sessions_runtime", store.sessions.values()),
        ("session_memory_summaries_runtime", store.session_memory_summaries.values()),
        ("turns_runtime", store.turns.values()),
        ("permissions_runtime", store.permissions.values()),
        ("org_roles_runtime", store.roles.values()),
        ("org_role_grants_runtime", store.role_grants.values()),
        ("org_role_assignments_runtime", store.role_assignments.values()),
        ("org_policies_runtime", store.org_policies.values()),
        ("secrets_runtime", store.secrets.values()),
        ("secret_bindings_runtime", store.secret_bindings.values()),
        ("audit_events_runtime", store.audit_events.values()),
        ("usage_events_runtime", store.usage_events.values()),
        ("outcomes_runtime", store.outcomes.values()),
        ("agent_assets_runtime", store.agent_assets.values()),
        ("mission_control_threads_runtime", store.mission_control_threads.values()),
        ("skills_runtime", store.skills.values()),
        ("host_adapter_dispatches_runtime", store.host_adapter_dispatches.values()),
    ):
        _persist_rows(table, rows, settings)
    _persist_scope_snapshots("ares_plans_runtime", store.ares_plans_by_scope, settings)
    _persist_scope_snapshots("ares_execution_runs_runtime", store.ares_execution_runs_by_scope, settings)
    _persist_scope_snapshots("ares_operator_runs_runtime", store.ares_operator_runs_by_scope, settings)
    _persist_rows(
        "turn_events_runtime",
        [event for events in store.turn_events.values() for event in events],
        settings,
    )


def _hydrate_text_table(target: dict, table: str, model_cls, settings: Settings, *, grouped: bool = False) -> None:
    rows = fetch_rows(table, params={"select": "payload_json", "order": "updated_at.asc"}, settings=settings)
    if grouped:
        for row in rows:
            event = model_cls.model_validate(row["payload_json"])
            target.setdefault(event.turn_id, []).append(event)
        return
    for row in rows:
        record = model_cls.model_validate(row["payload_json"])
        record_id = getattr(record, "id", None) or getattr(record, "session_id")
        target[record_id] = record


def _persist_rows(table: str, rows: Iterable, settings: Settings) -> None:
    existing = {
        row["id"]: row
        for row in fetch_rows(table, params={"select": "id", "order": "id.asc"}, settings=settings)
    }
    for record in rows:
        payload = record.model_dump(mode="json", exclude_computed_fields=True)
        row = {
            "id": payload["id"] if "id" in payload else payload["session_id"],
            "payload_json": payload,
            "created_at": payload.get("created_at") or payload.get("updated_at"),
            "updated_at": payload.get("updated_at") or payload.get("created_at"),
        }
        normalized_fields = (*COMMON_NORMALIZED_FIELDS, *TABLE_NORMALIZED_FIELDS.get(table, ()))
        for field in normalized_fields:
            if field in payload and payload[field] is not None:
                row[field] = payload[field]
        if row["id"] in existing:
            patch_rows(table, params={"id": f"eq.{row['id']}"}, row=row, select="id", settings=settings)
        else:
            insert_rows(table, [row], select="id", settings=settings)


def _hydrate_scope_snapshots(target: dict[tuple[str, str], dict[str, object]], table: str, settings: Settings) -> None:
    rows = fetch_rows(
        table,
        params={"select": "business_id,environment,payload_json", "order": "updated_at.asc"},
        settings=settings,
    )
    for row in rows:
        payload = row.get("payload_json")
        if not isinstance(payload, dict):
            continue
        business_id = payload.get("business_id") or row.get("business_id")
        environment = payload.get("environment") or row.get("environment")
        if not isinstance(business_id, str) or not business_id:
            continue
        if not isinstance(environment, str) or not environment:
            continue
        snapshot = dict(payload)
        snapshot.setdefault("business_id", business_id)
        snapshot.setdefault("environment", environment)
        target[(business_id, environment)] = snapshot


def _persist_scope_snapshots(table: str, snapshots: dict[tuple[str, str], object], settings: Settings) -> None:
    existing = {
        row["id"]: row
        for row in fetch_rows(table, params={"select": "id", "order": "id.asc"}, settings=settings)
    }
    for (business_id, environment), snapshot in snapshots.items():
        payload: dict[str, object]
        if hasattr(snapshot, "model_dump"):
            payload = snapshot.model_dump(mode="json")
        elif isinstance(snapshot, dict):
            payload = dict(snapshot)
        else:
            continue
        payload.setdefault("business_id", business_id)
        payload.setdefault("environment", environment)
        row_id = f"{business_id}:{environment}"
        row = {
            "id": row_id,
            "business_id": business_id,
            "environment": environment,
            "payload_json": payload,
        }
        created_at = payload.get("created_at") or payload.get("updated_at") or payload.get("generated_at")
        updated_at = payload.get("updated_at") or payload.get("created_at") or payload.get("generated_at")
        if created_at is not None:
            row["created_at"] = created_at
        if updated_at is not None:
            row["updated_at"] = updated_at
        if row_id in existing:
            patch_rows(table, params={"id": f"eq.{row_id}"}, row=row, select="id", settings=settings)
        else:
            insert_rows(table, [row], select="id", settings=settings)


def _hydrate_core_commands(store: InMemoryControlPlaneStore, settings: Settings) -> None:
    command_rows = fetch_rows("commands", params={"select": "*", "order": "created_at.asc"}, settings=settings)
    command_type_by_id = {int(row["id"]): str(row["command_type"]) for row in command_rows}
    policy_by_id = {
        int(row["id"]): _policy_from_db(str(row.get("policy_result") or "pending"))
        for row in command_rows
    }
    approvals = fetch_rows("approvals", params={"select": "*", "order": "created_at.asc"}, settings=settings)
    runs = fetch_rows("runs", params={"select": "*", "order": "created_at.asc"}, settings=settings)
    events_by_run: dict[int, list[dict]] = {}
    for row in fetch_rows("events", params={"select": "*", "order": "created_at.asc"}, settings=settings):
        run_id = row.get("run_id")
        if run_id is not None:
            events_by_run.setdefault(int(run_id), []).append(
                {
                    "id": f"evt_{row['id']}",
                    "run_id": f"run_{run_id}",
                    "event_type": row["event_type"],
                    "payload": dict(row.get("payload") or {}),
                    "created_at": row["created_at"],
                }
            )
    artifacts_by_run: dict[int, list[dict]] = {}
    for row in fetch_rows("artifacts", params={"select": "*", "order": "created_at.asc"}, settings=settings):
        run_id = row.get("run_id")
        if run_id is not None:
            artifacts_by_run.setdefault(int(run_id), []).append(
                {
                    "id": f"art_{row['id']}",
                    "run_id": f"run_{run_id}",
                    "artifact_type": row["artifact_type"],
                    "payload": dict(row.get("data") or {}),
                    "created_at": row["created_at"],
                }
            )
    latest_approval_by_command: dict[int, dict] = {}
    for row in approvals:
        latest_approval_by_command[int(row["command_id"])] = row
    latest_run_by_command: dict[int, dict] = {}
    for row in runs:
        latest_run_by_command[int(row["command_id"])] = row
    for row in command_rows:
        command_id = int(row["id"])
        approval = latest_approval_by_command.get(command_id)
        run = latest_run_by_command.get(command_id)
        record = CommandRecord(
            id=f"cmd_{command_id}",
            business_id=str(row["business_id"]),
            environment=str(row["environment"]),
            command_type=str(row["command_type"]),
            payload=dict(row.get("payload") or {}),
            idempotency_key=str(row["idempotency_key"]),
            policy=policy_by_id[command_id],
            status=_command_status_from_db(str(row.get("status") or "queued")),
            approval_id=f"apr_{approval['id']}" if approval else None,
            run_id=f"run_{run['id']}" if run else None,
            deduped=False,
            created_at=row["created_at"],
        )
        store.commands[record.id] = record
        store.command_keys[(record.business_id, record.environment, record.command_type, record.idempotency_key)] = record.id
    for row in approvals:
        approval = ApprovalRecord(
            id=f"apr_{row['id']}",
            command_id=f"cmd_{row['command_id']}",
            business_id=str(row["business_id"]),
            environment=str(row["environment"]),
            command_type=command_type_by_id.get(int(row["command_id"]), ""),
            status=ApprovalStatus(str(row["status"])),
            payload_snapshot=dict(row.get("approved_payload") or {}),
            created_at=row["created_at"],
            approved_at=row.get("decided_at"),
            actor_id=row.get("approved_by"),
        )
        store.approvals[approval.id] = approval
    for row in runs:
        run_id = int(row["id"])
        record = RunRecord(
            id=f"run_{run_id}",
            command_id=f"cmd_{row['command_id']}",
            business_id=str(row["business_id"]),
            environment=str(row["environment"]),
            command_type=command_type_by_id.get(int(row["command_id"]), ""),
            command_policy=policy_by_id.get(int(row["command_id"]), CommandPolicy.FORBIDDEN),
            status=_run_status_from_db(str(row["status"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            trigger_run_id=row.get("trigger_run_id"),
            parent_run_id=f"run_{row['parent_run_id']}" if row.get("parent_run_id") is not None else None,
            replay_reason=row.get("replay_reason"),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            error_classification=row.get("error_classification"),
            error_message=row.get("error_message"),
            artifacts=artifacts_by_run.get(run_id, []),
            events=events_by_run.get(run_id, []),
        )
        store.runs[record.id] = record


def _policy_from_db(value: str) -> CommandPolicy:
    if value == "safe_autonomous":
        return CommandPolicy.SAFE_AUTONOMOUS
    if value == "approval_required":
        return CommandPolicy.APPROVAL_REQUIRED
    return CommandPolicy.FORBIDDEN


def _command_status_from_db(value: str) -> CommandStatus:
    if value == "approval_required":
        return CommandStatus.AWAITING_APPROVAL
    if value == "rejected":
        return CommandStatus.REJECTED
    return CommandStatus.QUEUED


def _run_status_from_db(value: str) -> RunStatus:
    if value == "running":
        return RunStatus.IN_PROGRESS
    return RunStatus(value)
