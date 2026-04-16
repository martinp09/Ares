from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.campaigns import CampaignMembershipRecord
from app.models.commands import generate_stable_id


class CampaignMembershipsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def upsert(self, record: CampaignMembershipRecord, *, dedupe_key: str | None = None) -> CampaignMembershipRecord:
        now = utc_now()
        resolved_key = dedupe_key or record.replay_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.campaign_membership_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.campaign_memberships[existing_id]
                updates = record.model_dump(exclude={"id", "subscribed_at"})
                updated = existing.model_copy(update={**updates, "last_synced_at": now})
                store.campaign_memberships[existing_id] = updated
                return updated

            membership_id = record.id or generate_stable_id(
                "cmem",
                record.business_id,
                record.environment,
                resolved_key,
            )
            created = record.model_copy(update={"id": membership_id, "last_synced_at": now})
            store.campaign_memberships[membership_id] = created
            store.campaign_membership_keys[lookup_key] = membership_id
            store.campaign_membership_ids_by_campaign.setdefault(record.campaign_id, []).append(membership_id)
            store.campaign_membership_ids_by_lead.setdefault(record.lead_id, []).append(membership_id)
            return created

    def get(self, membership_id: str) -> CampaignMembershipRecord | None:
        with self.client.transaction() as store:
            return store.campaign_memberships.get(membership_id)

    def list_for_campaign(self, campaign_id: str) -> list[CampaignMembershipRecord]:
        with self.client.transaction() as store:
            membership_ids = list(store.campaign_membership_ids_by_campaign.get(campaign_id, []))
            memberships = [store.campaign_memberships[membership_id] for membership_id in membership_ids]
        memberships.sort(key=lambda record: (record.subscribed_at, record.id or ""))
        return memberships

    def list_for_lead(self, lead_id: str) -> list[CampaignMembershipRecord]:
        with self.client.transaction() as store:
            membership_ids = list(store.campaign_membership_ids_by_lead.get(lead_id, []))
            memberships = [store.campaign_memberships[membership_id] for membership_id in membership_ids]
        memberships.sort(key=lambda record: (record.subscribed_at, record.id or ""))
        return memberships
