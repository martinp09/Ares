from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.organizations import MembershipRecord


class MembershipsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def upsert(
        self,
        *,
        org_id: str,
        actor_id: str,
        actor_type: str,
        member_id: str | None = None,
        name: str | None = None,
        role_name: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MembershipRecord:
        now = utc_now()
        resolved_member_id = member_id or actor_id
        lookup_key = (org_id, actor_id)
        with self.client.transaction() as store:
            existing_id = store.membership_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.memberships[existing_id]
                updated = existing.model_copy(
                    update={
                        "actor_type": actor_type,
                        "member_id": resolved_member_id,
                        "name": name,
                        "role_name": role_name,
                        "metadata": dict(metadata or {}),
                        "updated_at": now,
                    }
                )
                store.memberships[existing_id] = updated
                return updated

            record = MembershipRecord(
                id=generate_id("mbr"),
                org_id=org_id,
                actor_id=actor_id,
                actor_type=actor_type,
                member_id=resolved_member_id,
                name=name,
                role_name=role_name,
                metadata=dict(metadata or {}),
                created_at=now,
                updated_at=now,
            )
            store.memberships[record.id] = record
            store.membership_keys[lookup_key] = record.id
            store.membership_ids_by_org.setdefault(org_id, []).append(record.id)
            store.membership_ids_by_actor.setdefault(actor_id, []).append(record.id)
            return record

    def get(self, membership_id: str) -> MembershipRecord | None:
        with self.client.transaction() as store:
            membership = store.memberships.get(membership_id)
            return membership if membership is None else MembershipRecord.model_validate(membership)

    def get_by_actor(self, *, org_id: str, actor_id: str) -> MembershipRecord | None:
        with self.client.transaction() as store:
            membership_id = store.membership_keys.get((org_id, actor_id))
            if membership_id is None:
                return None
            membership = store.memberships.get(membership_id)
            return membership if membership is None else MembershipRecord.model_validate(membership)

    def list(self, *, org_id: str | None = None, actor_id: str | None = None) -> list[MembershipRecord]:
        with self.client.transaction() as store:
            memberships = list(store.memberships.values())
        if org_id is not None:
            memberships = [membership for membership in memberships if membership.org_id == org_id]
        if actor_id is not None:
            memberships = [membership for membership in memberships if membership.actor_id == actor_id]
        memberships.sort(key=lambda membership: (membership.org_id, membership.actor_id, membership.created_at))
        return memberships

    def list_for_org(self, org_id: str) -> list[MembershipRecord]:
        return self.list(org_id=org_id)

    def list_for_actor(self, actor_id: str) -> list[MembershipRecord]:
        return self.list(actor_id=actor_id)
