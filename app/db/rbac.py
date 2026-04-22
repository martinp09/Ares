from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.permissions import ToolPermissionMode
from app.models.rbac import (
    CANONICAL_ORG_ROLE_NAMES,
    EffectivePermissionRecord,
    EffectivePermissionSourceRecord,
    OrgPolicyRecord,
    OrgRoleAssignmentRecord,
    OrgRoleGrantRecord,
    OrgRoleRecord,
    normalize_org_role_name,
    normalize_stored_org_role_name,
    org_role_sort_key,
)


class RBACRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    @staticmethod
    def _canonicalish_role_name(name: str) -> str | None:
        normalized_name = normalize_stored_org_role_name(name)
        return normalized_name if normalized_name in CANONICAL_ORG_ROLE_NAMES else None

    @classmethod
    def _present_role_record(cls, role: OrgRoleRecord) -> OrgRoleRecord:
        canonical_name = cls._canonicalish_role_name(role.name)
        if canonical_name is None or role.name == canonical_name:
            return OrgRoleRecord.model_validate(role)
        return role.model_copy(update={"name": canonical_name})

    @classmethod
    def _collapse_roles(cls, roles: list[OrgRoleRecord]) -> list[OrgRoleRecord]:
        collapsed_roles: dict[tuple[str, str], OrgRoleRecord] = {}
        sorted_roles = sorted(roles, key=lambda role: (org_role_sort_key(role.name), role.created_at, role.id))
        for role in sorted_roles:
            canonical_name = cls._canonicalish_role_name(role.name)
            logical_name = canonical_name or f"__role_id__:{role.id}"
            logical_key = (role.org_id, logical_name)
            if logical_key in collapsed_roles:
                continue
            collapsed_roles[logical_key] = cls._present_role_record(role)
        return list(collapsed_roles.values())

    @staticmethod
    def _find_role_by_normalized_name(store, *, org_id: str, normalized_name: str) -> tuple[str, OrgRoleRecord] | None:
        matches = [
            (role.id, role)
            for role in store.roles.values()
            if role.org_id == org_id and normalize_stored_org_role_name(role.name) == normalized_name
        ]
        if not matches:
            return None

        matches.sort(key=lambda item: (item[1].created_at, item[1].id))
        matched_role_id, matched_role = matches[0]
        store.role_keys[(org_id, normalized_name)] = matched_role_id
        return matched_role_id, matched_role

    def create_role(self, *, org_id: str, name: str, description: str | None = None) -> OrgRoleRecord:
        now = utc_now()
        normalized_name = normalize_org_role_name(name)
        lookup_key = (org_id, normalized_name)
        with self.client.transaction() as store:
            existing_match = self._find_role_by_normalized_name(store, org_id=org_id, normalized_name=normalized_name)
            if existing_match is not None:
                existing_id, existing = existing_match
                updated = existing.model_copy(
                    update={"name": normalized_name, "description": description, "updated_at": now}
                )
                store.roles[existing_id] = updated
                store.role_keys[lookup_key] = existing_id
                return updated

            record = OrgRoleRecord(
                id=generate_id("role"),
                org_id=org_id,
                name=normalized_name,
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
        normalized_name = normalize_org_role_name(name)
        with self.client.transaction() as store:
            match = self._find_role_by_normalized_name(store, org_id=org_id, normalized_name=normalized_name)
            if match is None:
                return None
            _, role = match
            return self._present_role_record(role)

    def list_roles(self, *, org_id: str | None = None) -> list[OrgRoleRecord]:
        with self.client.transaction() as store:
            roles = list(store.roles.values())
        if org_id is not None:
            roles = [role for role in roles if role.org_id == org_id]
        return self._collapse_roles(roles)

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
        grants.sort(key=lambda grant: (grant.tool_name, grant.created_at, grant.id))
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
            assignment_role_sort_keys = {
                assignment.id: (
                    org_role_sort_key(role.name) if (role := store.roles.get(assignment.role_id)) is not None else (10_000, assignment.role_id)
                )
                for assignment in assignments
            }
        assignments.sort(
            key=lambda assignment: (
                assignment_role_sort_keys[assignment.id],
                assignment.created_at,
                assignment.id,
            )
        )
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
        policies.sort(key=lambda policy: (policy.tool_name, policy.created_at, policy.id))
        return policies

    def resolve_tool_mode(
        self,
        *,
        org_id: str,
        agent_revision_id: str,
        tool_name: str,
        default_mode: ToolPermissionMode,
    ) -> EffectivePermissionRecord:
        sources: list[EffectivePermissionSourceRecord] = []
        with self.client.transaction() as store:
            scoped_assignments: list[tuple[OrgRoleAssignmentRecord, OrgRoleRecord]] = []
            for assignment in store.role_assignments.values():
                if assignment.agent_revision_id != agent_revision_id:
                    continue
                role = store.roles.get(assignment.role_id)
                if role is None or role.org_id != org_id:
                    continue
                scoped_assignments.append((assignment, role))

            scoped_assignments.sort(
                key=lambda item: (
                    org_role_sort_key(item[1].name),
                    item[1].created_at,
                    item[1].id,
                    item[0].created_at,
                    item[0].id,
                )
            )
            grouped_role_sources: dict[str, EffectivePermissionSourceRecord] = {}
            grouped_role_source_order: list[str] = []
            for assignment, role in scoped_assignments:
                grant_id = store.role_grant_keys.get((assignment.role_id, tool_name))
                if grant_id is None:
                    continue
                grant = store.role_grants[grant_id]
                canonical_name = self._canonicalish_role_name(role.name)
                logical_role_key = canonical_name or f"__role_id__:{role.id}"
                if logical_role_key not in grouped_role_sources:
                    grouped_role_sources[logical_role_key] = EffectivePermissionSourceRecord(
                        source=f"role:{canonical_name or role.name}",
                        mode=grant.mode,
                    )
                    grouped_role_source_order.append(logical_role_key)
                    continue

                existing_source = grouped_role_sources[logical_role_key]
                grouped_role_sources[logical_role_key] = existing_source.model_copy(
                    update={"mode": self._combine_modes(existing_source.mode, grant.mode)}
                )

            sources.extend(grouped_role_sources[key] for key in grouped_role_source_order)

            org_policy_id = store.org_policy_keys.get((org_id, tool_name))
            if org_policy_id is not None:
                policy = store.org_policies[org_policy_id]
                sources.append(EffectivePermissionSourceRecord(source=f"org:{org_id}", mode=policy.mode))

        mode = default_mode
        for source in sources:
            mode = self._combine_modes(mode, source.mode)

        return EffectivePermissionRecord(
            agent_revision_id=agent_revision_id,
            tool_name=tool_name,
            mode=mode,
            source_modes=[source.mode for source in sources],
            sources=sources,
        )

    def list_effective_tool_names(self, *, org_id: str, agent_revision_id: str) -> list[str]:
        with self.client.transaction() as store:
            scoped_role_ids = {
                assignment.role_id
                for assignment in store.role_assignments.values()
                if assignment.agent_revision_id == agent_revision_id
                and (role := store.roles.get(assignment.role_id)) is not None
                and role.org_id == org_id
            }
            tool_names = {grant.tool_name for grant in store.role_grants.values() if grant.role_id in scoped_role_ids}
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
