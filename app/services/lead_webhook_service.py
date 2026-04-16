from __future__ import annotations

from typing import Any, Mapping

from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.lead_events import LeadEventsRepository
from app.db.leads import LeadsRepository
from app.db.provider_webhooks import ProviderWebhooksRepository
from app.db.client import utc_now
from app.models.campaigns import CampaignRecord, CampaignStatus
from app.models.lead_events import LeadEventRecord, ProviderWebhookReceiptRecord
from app.models.leads import LeadInterestStatus, LeadLifecycleStatus, LeadRecord, LeadSource
from app.providers.instantly import normalize_webhook_payload
from app.services.campaign_lifecycle_service import CampaignLifecycleService
from app.services.lead_sequence_runner import LeadSequenceRunner
from app.services.lead_suppression_service import LeadSuppressionService
from app.services.lead_task_service import LeadTaskService


class LeadWebhookService:
    def __init__(
        self,
        *,
        leads_repository: LeadsRepository | None = None,
        lead_events_repository: LeadEventsRepository | None = None,
        campaigns_repository: CampaignsRepository | None = None,
        memberships_repository: CampaignMembershipsRepository | None = None,
        provider_webhooks_repository: ProviderWebhooksRepository | None = None,
        suppression_service: LeadSuppressionService | None = None,
        sequence_runner: LeadSequenceRunner | None = None,
        task_service: LeadTaskService | None = None,
        campaign_lifecycle_service: CampaignLifecycleService | None = None,
    ) -> None:
        self.leads_repository = leads_repository or LeadsRepository()
        self.lead_events_repository = lead_events_repository or LeadEventsRepository()
        self.campaigns_repository = campaigns_repository or CampaignsRepository()
        self.memberships_repository = memberships_repository or CampaignMembershipsRepository()
        self.provider_webhooks_repository = provider_webhooks_repository or ProviderWebhooksRepository()
        self.suppression_service = suppression_service or LeadSuppressionService()
        self.sequence_runner = sequence_runner or LeadSequenceRunner(self.memberships_repository)
        self.task_service = task_service or LeadTaskService()
        self.campaign_lifecycle_service = campaign_lifecycle_service or CampaignLifecycleService(self.campaigns_repository)

    def handle_instantly_webhook(
        self,
        *,
        business_id: str,
        environment: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, Any] | None = None,
        trusted: bool = False,
        trust_reason: str | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_webhook_payload(payload)
        receipt = self.provider_webhooks_repository.record(
            ProviderWebhookReceiptRecord(
                business_id=business_id,
                environment=environment,
                provider="instantly",
                event_type=str(normalized["provider_event_type"]),
                idempotency_key=str(normalized["idempotency_key"]),
                provider_event_id=normalized.get("provider_event_id"),
                provider_receipt_id=normalized.get("provider_email_id"),
                lead_email=normalized.get("lead_email"),
                payload={"headers": dict(headers or {}), "body": dict(payload), "trusted": trusted, "trust_reason": trust_reason},
            )
        )
        if receipt.deduped:
            return {"status": "duplicate", "receipt_id": receipt.id, "event_id": receipt.lead_event_id}

        lead = self._resolve_lead(business_id=business_id, environment=environment, normalized=normalized)
        campaign = self._resolve_campaign(business_id=business_id, environment=environment, normalized=normalized)
        event = self.lead_events_repository.append(
            LeadEventRecord(
                business_id=business_id,
                environment=environment,
                lead_id=lead.id or "",
                campaign_id=campaign.id if campaign is not None else normalized.get("campaign_id"),
                provider_name="instantly",
                provider_event_id=normalized.get("provider_event_id"),
                provider_receipt_id=receipt.id,
                event_type=str(normalized["canonical_event_type"]),
                event_timestamp=normalized["occurred_at"],
                idempotency_key=str(normalized["idempotency_key"]),
                payload=dict(payload),
                metadata={
                    **dict(normalized["metadata"]),
                    "provider_event_type": normalized["provider_event_type"],
                    "trust_reason": trust_reason,
                    "trusted": trusted,
                },
            )
        )
        if event.deduped:
            self.provider_webhooks_repository.mark_processed(receipt.id, lead_event_id=event.id)
            return {"status": "duplicate", "receipt_id": receipt.id, "event_id": event.id}

        updated_campaign = self._apply_event_to_campaign(campaign, event)
        resolved_campaign = updated_campaign or campaign
        updated_lead = self._apply_event_to_lead(lead, event)
        suppression = self.suppression_service.apply_event(
            business_id=business_id,
            environment=environment,
            lead_id=updated_lead.id,
            lead_email=updated_lead.email,
            campaign_id=resolved_campaign.id if resolved_campaign is not None else event.campaign_id,
            event=event,
        )
        membership = self.sequence_runner.handle_event(
            business_id=business_id,
            environment=environment,
            lead_id=updated_lead.id,
            campaign_id=resolved_campaign.id if resolved_campaign is not None else event.campaign_id,
            event=event,
        )
        task = self.task_service.create_task_for_event(
            business_id=business_id,
            environment=environment,
            lead_id=updated_lead.id,
            automation_run_id=event.automation_run_id,
            event=event,
        )
        self.provider_webhooks_repository.mark_processed(receipt.id, lead_event_id=event.id)
        return {
            "status": "processed",
            "receipt_id": receipt.id,
            "event_id": event.id,
            "lead_id": updated_lead.id,
            "suppression_id": suppression.id if suppression is not None else None,
            "membership_id": membership.id if membership is not None else None,
            "task_id": task.id if task is not None else None,
        }

    def _resolve_lead(self, *, business_id: str, environment: str, normalized: Mapping[str, Any]) -> LeadRecord:
        lead_email = str(normalized.get("lead_email") or "").strip()
        if lead_email:
            existing = self.leads_repository.get_by_key(
                business_id=business_id,
                environment=environment,
                dedupe_key=f"email:{lead_email.casefold()}",
            )
            if existing is not None:
                return existing
            return self.leads_repository.upsert(
                LeadRecord(
                    business_id=business_id,
                    environment=environment,
                    source=LeadSource.INSTANTLY_SYNC,
                    lifecycle_status=LeadLifecycleStatus.ACTIVE,
                    provider_name="instantly",
                    campaign_id=normalized.get("campaign_id"),
                    email=lead_email,
                    raw_payload=dict(normalized["metadata"].get("provider_payload") or {}),
                )
            )
        external_key = f"instantly-webhook:{normalized.get('campaign_id') or '-'}:{normalized.get('provider_event_id') or normalized['idempotency_key']}"
        existing = self.leads_repository.get_by_key(
            business_id=business_id,
            environment=environment,
            dedupe_key=f"external:{external_key.casefold()}",
        )
        if existing is not None:
            return existing
        return self.leads_repository.upsert(
            LeadRecord(
                business_id=business_id,
                environment=environment,
                source=LeadSource.INSTANTLY_SYNC,
                lifecycle_status=LeadLifecycleStatus.ACTIVE,
                provider_name="instantly",
                external_key=external_key,
                campaign_id=normalized.get("campaign_id"),
                raw_payload=dict(normalized["metadata"].get("provider_payload") or {}),
            )
        )

    def _resolve_campaign(self, *, business_id: str, environment: str, normalized: Mapping[str, Any]) -> CampaignRecord | None:
        provider_campaign_id = normalized.get("campaign_id")
        if not provider_campaign_id:
            return None
        provider_campaign_id = str(provider_campaign_id)
        dedupe_key = f"provider:instantly:{provider_campaign_id.strip().casefold()}"
        existing = self.campaigns_repository.get_by_key(
            business_id=business_id,
            environment=environment,
            dedupe_key=dedupe_key,
        )
        if existing is not None:
            return existing
        return self.campaign_lifecycle_service.create_or_upsert(
            CampaignRecord(
                business_id=business_id,
                environment=environment,
                name=str(normalized.get("campaign_name") or f"Instantly {provider_campaign_id}"),
                provider_name="instantly",
                provider_campaign_id=provider_campaign_id,
                status=CampaignStatus.ACTIVE,
                raw_payload={"source": "webhook_seed"},
            )
        )

    def _apply_event_to_campaign(self, campaign: CampaignRecord | None, event: LeadEventRecord) -> CampaignRecord | None:
        if campaign is None or event.event_type != "campaign.completed" or not campaign.id:
            return campaign
        if campaign.status in {CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED}:
            return campaign
        if campaign.status == CampaignStatus.DRAFT:
            campaign = self.campaign_lifecycle_service.activate(campaign.id)
        if campaign.status in {CampaignStatus.ACTIVE, CampaignStatus.PAUSED}:
            return self.campaign_lifecycle_service.complete(campaign.id)
        return campaign

    def _apply_event_to_lead(self, lead: LeadRecord, event: LeadEventRecord) -> LeadRecord:
        updates: dict[str, Any] = {
            "provider_name": "instantly",
            "campaign_id": event.campaign_id or lead.campaign_id,
            "last_touched_at": event.event_timestamp,
        }
        if event.event_type == "lead.email.sent":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.ACTIVE,
                    "last_contacted_at": event.event_timestamp,
                    "last_step": str(event.metadata.get("step")) if event.metadata.get("step") is not None else lead.last_step,
                    "last_step_variant": str(event.metadata.get("variant")) if event.metadata.get("variant") is not None else lead.last_step_variant,
                }
            )
        elif event.event_type == "lead.email.opened":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.ACTIVE,
                    "open_count": lead.open_count + 1,
                    "email_opened_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.email.clicked":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.ACTIVE,
                    "click_count": lead.click_count + 1,
                    "email_clicked_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.reply.received":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                    "reply_count": lead.reply_count + 1,
                    "email_replied_at": event.event_timestamp,
                    "lt_interest_status": LeadInterestStatus.INTERESTED,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.reply.auto_received":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                    "reply_count": lead.reply_count + 1,
                    "email_replied_at": event.event_timestamp,
                    "lt_interest_status": LeadInterestStatus.AUTO_REPLY,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.suppressed.unsubscribe":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                    "lt_interest_status": LeadInterestStatus.UNSUBSCRIBED,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.status.not_interested":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                    "lt_interest_status": LeadInterestStatus.NOT_INTERESTED,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.status.interested":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.ACTIVE,
                    "lt_interest_status": LeadInterestStatus.INTERESTED,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.status.neutral":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.ACTIVE,
                    "lt_interest_status": LeadInterestStatus.NEUTRAL,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.meeting.booked":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.CLOSED,
                    "lt_interest_status": LeadInterestStatus.MEETING_BOOKED,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.meeting.completed":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.CLOSED,
                    "lt_interest_status": LeadInterestStatus.MEETING_COMPLETED,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.status.closed":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.CLOSED,
                    "lt_interest_status": LeadInterestStatus.CLOSED,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.status.out_of_office":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                    "lt_interest_status": LeadInterestStatus.OUT_OF_OFFICE,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "lead.status.wrong_person":
            updates.update(
                {
                    "lifecycle_status": LeadLifecycleStatus.SUPPRESSED,
                    "lt_interest_status": LeadInterestStatus.WRONG_PERSON,
                    "last_interest_changed_at": event.event_timestamp,
                }
            )
        elif event.event_type == "campaign.completed":
            updates["lifecycle_status"] = LeadLifecycleStatus.CLOSED
        elif event.event_type == "lead.email.bounced":
            updates["lifecycle_status"] = LeadLifecycleStatus.SUPPRESSED
        return self.leads_repository.upsert(lead.model_copy(update=updates))


lead_webhook_service = LeadWebhookService()
