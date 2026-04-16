from __future__ import annotations

from app.db.suppression import SuppressionRepository
from app.models.lead_events import LeadEventRecord
from app.models.suppression import SuppressionRecord, SuppressionScope, SuppressionSource


_SUPPRESSION_REASON_BY_EVENT = {
    "lead.reply.received": "replied",
    "lead.reply.auto_received": "auto_replied",
    "lead.email.bounced": "bounced",
    "lead.suppressed.unsubscribe": "unsubscribed",
    "lead.status.not_interested": "not_interested",
    "lead.status.wrong_person": "wrong_person",
    "lead.status.closed": "closed",
}


class LeadSuppressionService:
    def __init__(self, suppression_repository: SuppressionRepository | None = None) -> None:
        self.suppression_repository = suppression_repository or SuppressionRepository()

    def apply_event(
        self,
        *,
        business_id: str,
        environment: str,
        lead_id: str | None,
        lead_email: str | None,
        campaign_id: str | None,
        event: LeadEventRecord,
    ) -> SuppressionRecord | None:
        reason = _SUPPRESSION_REASON_BY_EVENT.get(event.event_type)
        if reason is None:
            return None
        return self.suppression_repository.upsert(
            SuppressionRecord(
                business_id=business_id,
                environment=environment,
                lead_id=lead_id,
                email=lead_email,
                campaign_id=campaign_id,
                scope=SuppressionScope.GLOBAL,
                reason=reason,
                source=SuppressionSource.WEBHOOK,
                idempotency_key=f"suppression:{event.idempotency_key}",
                metadata={
                    "source_event_id": event.id,
                    "provider": event.provider_name,
                    "provider_event_id": event.provider_event_id,
                    "provider_event_type": event.metadata.get("provider_event_type"),
                    "canonical_event_type": event.event_type,
                },
            )
        )

    def is_suppressed(
        self,
        *,
        business_id: str,
        environment: str,
        lead_id: str | None = None,
        email: str | None = None,
        campaign_id: str | None = None,
        list_id: str | None = None,
    ) -> bool:
        normalized_email = str(email or "").strip().casefold() or None
        for record in self.suppression_repository.list_active(business_id=business_id, environment=environment):
            if lead_id is not None and record.lead_id == lead_id:
                if record.scope == SuppressionScope.CAMPAIGN and campaign_id is not None and record.campaign_id not in {None, campaign_id}:
                    continue
                return True
            if normalized_email is not None and (record.email or "").strip().casefold() == normalized_email:
                if record.scope == SuppressionScope.CAMPAIGN and campaign_id is not None and record.campaign_id not in {None, campaign_id}:
                    continue
                return True
        return False


lead_suppression_service = LeadSuppressionService()
