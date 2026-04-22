from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Iterator, Literal, Protocol

from app.core.config import (
    DEFAULT_INTERNAL_ACTOR_ID,
    DEFAULT_INTERNAL_ACTOR_TYPE,
    DEFAULT_INTERNAL_ORG_ID,
    Settings,
    get_settings,
)
from app.models.approvals import ApprovalRecord
from app.models.commands import CommandRecord
from app.models.organizations import MembershipRecord, OrganizationRecord
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
    session_memory_summaries: dict[str, object] = field(default_factory=dict)
    turns: dict[str, object] = field(default_factory=dict)
    turn_events: dict[str, list[object]] = field(default_factory=dict)
    turn_ids_by_session: dict[str, list[str]] = field(default_factory=dict)
    permissions: dict[str, object] = field(default_factory=dict)
    permission_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    roles: dict[str, object] = field(default_factory=dict)
    role_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    organizations: dict[str, object] = field(default_factory=dict)
    organization_keys: dict[str, str] = field(default_factory=dict)
    memberships: dict[str, object] = field(default_factory=dict)
    membership_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    membership_ids_by_org: dict[str, list[str]] = field(default_factory=dict)
    membership_ids_by_actor: dict[str, list[str]] = field(default_factory=dict)
    role_grants: dict[str, object] = field(default_factory=dict)
    role_grant_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    role_assignments: dict[str, object] = field(default_factory=dict)
    role_assignment_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    org_policies: dict[str, object] = field(default_factory=dict)
    org_policy_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    secrets: dict[str, object] = field(default_factory=dict)
    secret_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    secret_bindings: dict[str, object] = field(default_factory=dict)
    secret_binding_keys: dict[tuple[str, str], str] = field(default_factory=dict)
    audit_events: dict[str, object] = field(default_factory=dict)
    usage_events: dict[str, object] = field(default_factory=dict)
    outcomes: dict[str, object] = field(default_factory=dict)
    probate_leads: dict[str, object] = field(default_factory=dict)
    probate_lead_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    leads: dict[str, object] = field(default_factory=dict)
    lead_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    lead_events: dict[str, object] = field(default_factory=dict)
    lead_event_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    lead_event_ids_by_lead: dict[str, list[str]] = field(default_factory=dict)
    campaigns: dict[str, object] = field(default_factory=dict)
    campaign_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    campaign_memberships: dict[str, object] = field(default_factory=dict)
    campaign_membership_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    campaign_membership_ids_by_campaign: dict[str, list[str]] = field(default_factory=dict)
    campaign_membership_ids_by_lead: dict[str, list[str]] = field(default_factory=dict)
    automation_runs: dict[str, object] = field(default_factory=dict)
    automation_run_keys: dict[tuple[str, str, str, str], str] = field(default_factory=dict)
    suppressions: dict[str, object] = field(default_factory=dict)
    suppression_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    provider_webhooks: dict[str, object] = field(default_factory=dict)
    provider_webhook_keys: dict[tuple[str, str, str, str], str] = field(default_factory=dict)
    tasks: dict[str, object] = field(default_factory=dict)
    task_keys: dict[tuple[str, str, str], str] = field(default_factory=dict)
    marketing_task_rows: dict[str, object] = field(init=False, repr=False)
    marketing_task_scope: dict[str, tuple[str, str, str]] = field(init=False, repr=False)
    skills: dict[str, object] = field(default_factory=dict)
    skill_keys: dict[str, str] = field(default_factory=dict)
    host_adapter_dispatches: dict[str, object] = field(default_factory=dict)
    agent_assets: dict[str, object] = field(default_factory=dict)
    mission_control_threads: dict[str, object] = field(default_factory=dict)
    ares_plans_by_scope: dict[tuple[str, str], object] = field(default_factory=dict)
    ares_execution_runs_by_scope: dict[tuple[str, str], object] = field(default_factory=dict)
    ares_operator_runs_by_scope: dict[tuple[str, str], object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.marketing_task_rows = self.tasks
        self.marketing_task_scope = self.task_keys
        seed_control_plane_defaults(self)


def seed_control_plane_defaults(store: InMemoryControlPlaneStore) -> None:
    now = utc_now()
    internal_org = OrganizationRecord(
        id=DEFAULT_INTERNAL_ORG_ID,
        name="Internal",
        slug="internal",
        metadata={"seeded": True},
        is_internal=True,
        created_at=now,
        updated_at=now,
    )
    store.organizations[internal_org.id] = internal_org
    store.organization_keys["internal"] = internal_org.id

    internal_membership = MembershipRecord(
        id="mbr_internal_runtime",
        org_id=DEFAULT_INTERNAL_ORG_ID,
        actor_id=DEFAULT_INTERNAL_ACTOR_ID,
        actor_type=DEFAULT_INTERNAL_ACTOR_TYPE,
        member_id=DEFAULT_INTERNAL_ACTOR_ID,
        name="Ares Runtime",
        role_name="owner",
        metadata={"seeded": True},
        created_at=now,
        updated_at=now,
    )
    store.memberships[internal_membership.id] = internal_membership
    store.membership_keys[(internal_membership.org_id, internal_membership.actor_id)] = internal_membership.id
    store.membership_ids_by_org[internal_membership.org_id] = [internal_membership.id]
    store.membership_ids_by_actor[internal_membership.actor_id] = [internal_membership.id]


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
    target.session_memory_summaries.clear()
    target.turns.clear()
    target.turn_events.clear()
    target.turn_ids_by_session.clear()
    target.permissions.clear()
    target.permission_keys.clear()
    target.roles.clear()
    target.role_keys.clear()
    target.organizations.clear()
    target.organization_keys.clear()
    target.memberships.clear()
    target.membership_keys.clear()
    target.membership_ids_by_org.clear()
    target.membership_ids_by_actor.clear()
    target.role_grants.clear()
    target.role_grant_keys.clear()
    target.role_assignments.clear()
    target.role_assignment_keys.clear()
    target.org_policies.clear()
    target.org_policy_keys.clear()
    target.secrets.clear()
    target.secret_keys.clear()
    target.secret_bindings.clear()
    target.secret_binding_keys.clear()
    target.audit_events.clear()
    target.usage_events.clear()
    target.outcomes.clear()
    target.probate_leads.clear()
    target.probate_lead_keys.clear()
    target.leads.clear()
    target.lead_keys.clear()
    target.lead_events.clear()
    target.lead_event_keys.clear()
    target.lead_event_ids_by_lead.clear()
    target.campaigns.clear()
    target.campaign_keys.clear()
    target.campaign_memberships.clear()
    target.campaign_membership_keys.clear()
    target.campaign_membership_ids_by_campaign.clear()
    target.campaign_membership_ids_by_lead.clear()
    target.automation_runs.clear()
    target.automation_run_keys.clear()
    target.suppressions.clear()
    target.suppression_keys.clear()
    target.provider_webhooks.clear()
    target.provider_webhook_keys.clear()
    target.tasks.clear()
    target.task_keys.clear()
    if hasattr(target, "opportunity_rows"):
        target.opportunity_rows.clear()
    if hasattr(target, "opportunity_keys"):
        target.opportunity_keys.clear()
    target.skills.clear()
    target.skill_keys.clear()
    target.host_adapter_dispatches.clear()
    target.agent_assets.clear()
    target.mission_control_threads.clear()
    target.ares_plans_by_scope.clear()
    target.ares_execution_runs_by_scope.clear()
    target.ares_operator_runs_by_scope.clear()
    seed_control_plane_defaults(target)


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
        from app.db.control_plane_store_supabase import hydrate_control_plane_store, persist_control_plane_store

        store = hydrate_control_plane_store(self.settings)
        try:
            yield store
        finally:
            persist_control_plane_store(store, self.settings)


def get_control_plane_client(settings: Settings | None = None) -> ControlPlaneClient:
    active_settings = settings or get_settings()
    if active_settings.control_plane_backend == "supabase":
        return SupabaseControlPlaneClient(active_settings)
    return InMemoryControlPlaneClient()
