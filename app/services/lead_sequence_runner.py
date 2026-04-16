from __future__ import annotations

from app.db.campaign_memberships import CampaignMembershipsRepository
from app.models.campaigns import CampaignMembershipRecord, CampaignMembershipStatus
from app.models.lead_events import LeadEventRecord


class LeadSequenceRunner:
    def __init__(self, memberships_repository: CampaignMembershipsRepository | None = None) -> None:
        self.memberships_repository = memberships_repository or CampaignMembershipsRepository()

    def handle_event(
        self,
        *,
        business_id: str,
        environment: str,
        lead_id: str | None,
        campaign_id: str | None,
        event: LeadEventRecord,
    ) -> CampaignMembershipRecord | None:
        if not lead_id or not campaign_id:
            return None
        existing = next(
            (record for record in self.memberships_repository.list_for_lead(lead_id) if record.campaign_id == campaign_id),
            None,
        )
        status = self._status_for_event(event.event_type)
        if status is None:
            return existing
        membership = CampaignMembershipRecord(
            id=existing.id if existing is not None else None,
            business_id=business_id,
            environment=environment,
            lead_id=lead_id,
            campaign_id=campaign_id,
            provider_membership_id=existing.provider_membership_id if existing is not None else None,
            provider_lead_id=existing.provider_lead_id if existing is not None else None,
            assigned_to=existing.assigned_to if existing is not None else None,
            status=status,
            idempotency_key=existing.idempotency_key if existing is not None else None,
            metadata={
                **(existing.metadata if existing is not None else {}),
                "last_event_id": event.id,
                "last_event_type": event.event_type,
            },
            subscribed_at=existing.subscribed_at if existing is not None else event.event_timestamp,
            unsubscribed_at=event.event_timestamp if status == CampaignMembershipStatus.SUPPRESSED else (existing.unsubscribed_at if existing is not None else None),
            last_synced_at=event.received_at,
        )
        return self.memberships_repository.upsert(membership)

    @staticmethod
    def _status_for_event(canonical_event_type: str) -> CampaignMembershipStatus | None:
        if canonical_event_type in {"lead.email.sent", "lead.email.opened", "lead.email.clicked", "lead.status.interested", "lead.status.neutral"}:
            return CampaignMembershipStatus.ACTIVE
        if canonical_event_type in {
            "lead.reply.received",
            "lead.reply.auto_received",
            "lead.email.bounced",
            "lead.suppressed.unsubscribe",
            "lead.status.not_interested",
            "lead.status.wrong_person",
            "lead.status.closed",
            "lead.meeting.booked",
            "lead.meeting.completed",
        }:
            return CampaignMembershipStatus.SUPPRESSED
        if canonical_event_type == "campaign.completed":
            return CampaignMembershipStatus.COMPLETED
        return None


lead_sequence_runner = LeadSequenceRunner()
