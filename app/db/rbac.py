from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.rbac import (
    EffectivePermissionRecord,
    EffectivePermissionSourceRecord,
    OrgPolicyRecord,
    OrgRoleAssignmentRecord,
    OrgRoleGrantRecord,
    OrgRoleRecord,
)
from app.models.permissions import ToolPermissionMode


class RBACRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create_role(self, *, org_id: str, name: str, description: str | None = None) -> OrgRoleRecord:
        now = utc_now()
        lookup_key = (org_id, name)
        with self.client.transaction() as store:
            existing_id = store.role_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.roles[existing_id]
                updated = existing.model_copy(update={"description": description, "updated_at": now})
                store.roles[existing_id] = updated
                return updated

            record = OrgRoleRecord(
                id=generate_id("role"),
                org_id=org_id,
                name=name,
                description=description,
                created_at=now,
                updated_at=now,
            )
            store.roles[record.id] = record
            store.role_keys[lookup_key] = record.id
            return record

    def get_role(self, role_id: str) -> OrgRoleRecord | None:
        with self.client.transaction() as store:
            role = store.roles.get(role_id)
            return role if role is None else OrgRoleRecord.model_validate(role)

    def get_role_by_name(self, *, org_id: str, name: str) -> OrgRoleRecord | None:
        with self.client.transaction() as store:
            role_id = store.role_keys.get((org_id, name))
            if role_id is None:
                return None
            return store.roles.get(role_id)

    def list_roles(self, *, org_id: str | None = None) -> list[OrgRoleRecord]:
        with self.client.transaction() as store:
            roles = list(store.roles.values())
        if org_id is not None:
            roles = [role for role in roles if role.org_id == org_id]
        roles.sort(key=lambda role: (role.name, role.created_at))
        return roles

    def grant_role_permission(self, role_id: str, *, tool_name: str, mode: ToolPermissionMode) -> OrgRoleGrantRecord:
        now = utc_now()
        with self.client.transaction() as store:
            role = store.roles.get(role_id)
            if role is None:
                raise ValueError("Role not found")
            lookup_key = (role_id, tool_name)
            existing_id = store.role_grant_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.role_grants[existing_id]
                updated = existing.model_copy(update={"mode": mode, "updated_at": now})
                store.role_grants[existing_id] = updated
                return updated

            record = OrgRoleGrantRecord(
                id=generate_id("rgrant"),
                role_id=role_id,
                tool_name=tool_name,
                mode=mode,
                created_at=now,
                updated_at=now,
            )
            store.role_grants[record.id] = record
            store.role_grant_keys[lookup_key] = record.id
            return record

    def list_grants(self, role_id: str) -> list[OrgRoleGrantRecord]:
        with self.client.transaction() as store:
            grants = [grant for grant in store.role_grants.values() if grant.role_id == role_id]
        grants.sort(key=lambda grant: (grant.tool_name, grant.created_at))
        return grants

    def assign_role(self, *, agent_revision_id: str, role_id: str) -> OrgRoleAssignmentRecord:
        now = utc_now()
        with self.client.transaction() as store:
            role = store.roles.get(role_id)
            if role is None:
                raise ValueError("Role not found")
            lookup_key = (agent_revision_id, role_id)
            existing_id = store.role_assignment_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.role_assignments[existing_id]
                updated = existing.model_copy(update={"updated_at": now})
                store.role_assignments[existing_id] = updated
                return updated

            record = OrgRoleAssignmentRecord(
                id=generate_id("rassign"),
                agent_revision_id=agent_revision_id,
                role_id=role_id,
                created_at=now,
                updated_at=now,
            )
            store.role_assignments[record.id] = record
            store.role_assignment_keys[lookup_key] = record.id
            return record

    def list_assignments(self, agent_revision_id: str) -> list[OrgRoleAssignmentRecord]:
        with self.client.transaction() as store:
            assignments = [assignment for assignment in store.role_assignments.values() if assignment.agent_revision_id == agent_revision_id]
        assignments.sort(key=lambda assignment: (assignment.role_id, assignment.created_at))
        return assignments

    def upsert_org_policy(self, *, org_id: str, tool_name: str, mode: ToolPermissionMode) -> OrgPolicyRecord:
        now = utc_now()
        lookup_key = (org_id, tool_name)
        with self.client.transaction() as store:
            existing_id = store.org_policy_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.org_policies[existing_id]
                updated = existing.model_copy(update={"mode": mode, "updated_at": now})
                store.org_policies[existing_id] = updated
                return updated

            record = OrgPolicyRecord(
                id=generate_id("opol"),
                org_id=org_id,
                tool_name=tool_name,
                mode=mode,
                created_at=now,
                updated_at=now,
            )
            store.org_policies[record.id] = record
            store.org_policy_keys[lookup_key] = record.id
            return record

    def list_org_policies(self, *, org_id: str | None = None) -> list[OrgPolicyRecord]:
        with self.client.transaction() as store:
            policies = list(store.org_policies.values())
        if org_id is not None:
            policies = [policy for policy in policies if policy.org_id == org_id]
        policies.sort(key=lambda policy: (policy.tool_name, policy.created_at))
        return policies

    def resolve_tool_mode(
        self,
        *,
        org_id: str,
        agent_revision_id: str,
        tool_name: str,
        default_mode: ToolPermissionMode,
    ) -> EffectivePermissionRecord:
        role_modes: list[ToolPermissionMode] = []
        sources: list[EffectivePermissionSourceRecord] = []
        with self.client.transaction() as store:
            assignments = [
                assignment
                for assignment in store.role_assignments.values()
                if assignment.agent_revision_id == agent_revision_id
            ]
            for assignment in sorted(assignments, key=lambda item: (item.role_id, item.created_at)):
                grant_ids = [
                    grant_id
                    for grant_id in store.role_grant_keys.values()
                    if store.role_grants[grant_id].role_id == assignment.role_id and store.role_grants[grant_id].tool_name == tool_name
                ]
                for grant_id in grant_ids:
                    grant = store.role_grants[grant_id]
                    role_modes.append(grant.mode)
                    sources.append(EffectivePermissionSourceRecord(source=f"role:{assignment.role_id}", mode=grant.mode))

            org_policy_id = store.org_policy_keys.get((org_id, tool_name))
            if org_policy_id is not None:
                policy = store.org_policies[org_policy_id]
                role_modes.append(policy.mode)
                sources.append(EffectivePermissionSourceRecord(source=f"org:{org_id}", mode=policy.mode))

        mode = default_mode
        for source_mode in role_modes:
            mode = self._combine_modes(mode, source_mode)

        return EffectivePermissionRecord(
            agent_revision_id=agent_revision_id,
            tool_name=tool_name,
            mode=mode,
            source_modes=role_modes,
            sources=sources,
        )

    def list_effective_tool_names(self, *, org_id: str, agent_revision_id: str) -> list[str]:
        with self.client.transaction() as store:
            tool_names = {
                grant.tool_name
                for assignment in store.role_assignments.values()
                if assignment.agent_revision_id == agent_revision_id
                for grant in store.role_grants.values()
                if grant.role_id == assignment.role_id
            }
            tool_names.update(policy.tool_name for policy in store.org_policies.values() if policy.org_id == org_id)
        return sorted(tool_names)

    @staticmethod
    def _combine_modes(left: ToolPermissionMode, right: ToolPermissionMode) -> ToolPermissionMode:
        order = {
            ToolPermissionMode.ALWAYS_ALLOW: 0,
            ToolPermissionMode.ALWAYS_ASK: 1,
            ToolPermissionMode.FORBIDDEN: 2,
        }
        return left if order[left] >= order[right] else right
