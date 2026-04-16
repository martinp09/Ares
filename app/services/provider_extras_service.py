from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.models.leads import LeadInterestStatus, LeadSource
from app.models.provider_extras import (
    InstantlyProviderExtrasSnapshot,
    ProviderExtraFamilyStatus,
    ProviderExtrasSummary,
)


class ProviderExtrasService:
    def __init__(
        self,
        settings: Settings | None = None,
        client: ControlPlaneClient | None = None,
    ) -> None:
        self.settings = settings
        self.client = client

    def get_instantly_snapshot(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> InstantlyProviderExtrasSnapshot:
        settings = self.settings or get_settings()
        campaigns, leads, suppressions, lead_events, provider_webhooks = self._load_projection_records(
            settings=settings,
            business_id=business_id,
            environment=environment,
        )

        instantly_campaigns = [campaign for campaign in campaigns if self._is_instantly_campaign(campaign)]
        instantly_leads = [lead for lead in leads if self._is_instantly_lead(lead)]
        instantly_suppressions = [record for record in suppressions if self._is_instantly_suppression(record)]
        instantly_events = [event for event in lead_events if self._normalized_provider(getattr(event, "provider_name", None)) == "instantly"]
        instantly_webhook_receipts = [
            receipt
            for receipt in provider_webhooks
            if self._normalized_provider(getattr(receipt, "provider", None)) == "instantly"
        ]

        configured = bool(settings.instantly_api_key)
        webhook_signing_configured = bool(settings.instantly_webhook_secret)

        unique_tags = sorted(
            {
                tag.strip()
                for campaign in instantly_campaigns
                for tag in getattr(campaign, "email_tag_list", [])
                if isinstance(tag, str) and tag.strip()
            }
        )
        verification_statuses = sorted(
            {
                str(lead.verification_status).strip()
                for lead in instantly_leads
                if getattr(lead, "verification_status", None)
                and str(lead.verification_status).strip()
            }
        )
        label_events = [event for event in instantly_events if str(getattr(event, "event_type", "")).startswith("lead.label.")]
        bounced_events = [event for event in instantly_events if getattr(event, "event_type", None) == "lead.email.bounced"]
        unsubscribe_events = [event for event in instantly_events if getattr(event, "event_type", None) == "lead.suppressed.unsubscribe"]
        provider_blocklist_ids = sorted(
            {
                record.provider_blocklist_id.strip()
                for record in instantly_suppressions
                if getattr(record, "provider_blocklist_id", None)
                and str(record.provider_blocklist_id).strip()
            }
        )
        workspace_ids = sorted(
            {
                workspace_id
                for workspace_id in [
                    *[
                        str(campaign.provider_workspace_id).strip()
                        for campaign in instantly_campaigns
                        if getattr(campaign, "provider_workspace_id", None)
                        and str(campaign.provider_workspace_id).strip()
                    ],
                    *[
                        str(lead.provider_workspace_id).strip()
                        for lead in instantly_leads
                        if getattr(lead, "provider_workspace_id", None)
                        and str(lead.provider_workspace_id).strip()
                    ],
                ]
                if workspace_id
            }
        )

        actionable_leads = [lead for lead in instantly_leads if self._is_actionable_lead(lead)]
        actionable_status_counts = Counter(
            str(getattr(lead, "lt_interest_status", LeadInterestStatus.NEUTRAL))
            for lead in actionable_leads
            if getattr(lead, "lt_interest_status", LeadInterestStatus.NEUTRAL) != LeadInterestStatus.NEUTRAL
        )

        labels = self._build_family_status(
            configured=configured,
            projection_mode="internal_projection",
            projected_record_count=len(label_events),
            counts={
                "label_events": len(label_events),
                "distinct_event_types": len({getattr(event, "event_type", None) for event in label_events}),
            },
            notes=["Custom labels are surfaced from canonical lead-event projections only."],
        )
        tags = self._build_family_status(
            configured=configured,
            projection_mode="internal_projection",
            projected_record_count=len(unique_tags),
            counts={
                "campaigns_with_tags": sum(
                    1
                    for campaign in instantly_campaigns
                    if any(isinstance(tag, str) and tag.strip() for tag in getattr(campaign, "email_tag_list", []))
                ),
                "unique_tags": len(unique_tags),
            },
            notes=["Tag coverage is derived from campaign.email_tag_list projections."],
        )
        verification = self._build_family_status(
            configured=configured,
            projection_mode="internal_projection",
            projected_record_count=sum(1 for lead in instantly_leads if getattr(lead, "verification_status", None)),
            counts={
                "leads_with_verification_status": sum(
                    1 for lead in instantly_leads if getattr(lead, "verification_status", None)
                ),
                "distinct_statuses": len(verification_statuses),
            },
            notes=["Verification coverage is derived from lead.verification_status values."],
        )
        deliverability = self._build_family_status(
            configured=configured,
            projection_mode="internal_projection",
            projected_record_count=len(bounced_events) + len(unsubscribe_events),
            counts={
                "bounced_events": len(bounced_events),
                "unsubscribe_events": len(unsubscribe_events),
                "deliverability_events": len(bounced_events) + len(unsubscribe_events),
            },
            notes=["Deliverability is intentionally limited to projected bounce and unsubscribe signals."],
        )
        blocklists = self._build_family_status(
            configured=configured,
            projection_mode="internal_projection",
            projected_record_count=len(instantly_suppressions),
            counts={
                "active_suppressions": len(instantly_suppressions),
                "provider_blocklists": len(provider_blocklist_ids),
            },
            notes=["Blocklist coverage is projected from active suppressions with provider_blocklist_id values."],
        )
        inbox_placement = self._build_family_status(
            configured=configured,
            projection_mode="scaffold",
            projected_record_count=0,
            counts={"placement_observations": 0},
            notes=["Inbox placement is scaffolded only; no in-memory projection exists yet."],
        )
        crm_actions = self._build_family_status(
            configured=configured,
            projection_mode="internal_projection",
            projected_record_count=len(actionable_leads),
            counts={
                "actionable_leads": len(actionable_leads),
                "assigned_leads": sum(1 for lead in actionable_leads if getattr(lead, "assigned_to", None)),
                "meeting_booked_leads": sum(
                    1 for lead in actionable_leads if getattr(lead, "lt_interest_status", None) == LeadInterestStatus.MEETING_BOOKED
                ),
                **{status: count for status, count in sorted(actionable_status_counts.items())},
            },
            notes=["CRM actions remain an internal projection slice and do not call live CRM endpoints."],
        )
        workspace_resources = self._build_family_status(
            configured=configured,
            projection_mode="internal_projection",
            projected_record_count=len(workspace_ids),
            counts={
                "workspace_count": len(workspace_ids),
                "campaigns": len(instantly_campaigns),
                "leads": len(instantly_leads),
                "webhook_receipts": len(instantly_webhook_receipts),
            },
            notes=["Workspace resources are inferred from provider_workspace_id fields and stored webhook receipts."],
        )

        families = [
            labels,
            tags,
            verification,
            deliverability,
            blocklists,
            inbox_placement,
            crm_actions,
            workspace_resources,
        ]

        return InstantlyProviderExtrasSnapshot(
            configured=configured,
            transport_ready=configured,
            webhook_signing_configured=webhook_signing_configured,
            base_url=settings.instantly_base_url,
            batch_size=settings.instantly_batch_size,
            batch_wait_seconds=settings.instantly_batch_wait_seconds,
            summary=ProviderExtrasSummary(
                configured_family_count=sum(1 for family in families if family.configured),
                projected_family_count=sum(1 for family in families if family.projected_record_count > 0),
                campaign_count=len(instantly_campaigns),
                lead_count=len(instantly_leads),
                workspace_count=len(workspace_ids),
                webhook_receipt_count=len(instantly_webhook_receipts),
                blocklist_count=len(provider_blocklist_ids),
            ),
            labels=labels,
            tags=tags,
            verification=verification,
            deliverability=deliverability,
            blocklists=blocklists,
            inbox_placement=inbox_placement,
            crm_actions=crm_actions,
            workspace_resources=workspace_resources,
            checked_at=datetime.now(UTC),
        )

    def _build_family_status(
        self,
        *,
        configured: bool,
        projection_mode: str,
        projected_record_count: int,
        counts: dict[str, int],
        notes: list[str],
    ) -> ProviderExtraFamilyStatus:
        if not configured:
            status = "configuration_missing"
        elif projected_record_count > 0:
            status = "projected"
        else:
            status = "scaffolded"
        return ProviderExtraFamilyStatus(
            configured=configured,
            status=status,
            projection_mode=projection_mode,
            projected_record_count=projected_record_count,
            counts=counts,
            notes=notes,
        )

    def _load_projection_records(
        self,
        *,
        settings: Settings,
        business_id: str | None,
        environment: str | None,
    ) -> tuple[list[Any], list[Any], list[Any], list[Any], list[Any]]:
        client = self.client
        if client is None:
            if settings.control_plane_backend == "supabase":
                return [], [], [], [], []
            client = get_control_plane_client(settings)
        try:
            with client.transaction() as store:
                campaigns = [
                    campaign
                    for campaign in store.campaigns.values()
                    if self._matches_scope(campaign, business_id=business_id, environment=environment)
                ]
                leads = [
                    lead for lead in store.leads.values() if self._matches_scope(lead, business_id=business_id, environment=environment)
                ]
                suppressions = [
                    record
                    for record in store.suppressions.values()
                    if self._matches_scope(record, business_id=business_id, environment=environment)
                ]
                lead_events = [
                    event
                    for event in store.lead_events.values()
                    if self._matches_scope(event, business_id=business_id, environment=environment)
                ]
                provider_webhooks = [
                    receipt
                    for receipt in store.provider_webhooks.values()
                    if self._matches_scope(receipt, business_id=business_id, environment=environment)
                ]
        except NotImplementedError:
            return [], [], [], [], []
        return campaigns, leads, suppressions, lead_events, provider_webhooks

    @staticmethod
    def _matches_scope(record: Any, *, business_id: str | None, environment: str | None) -> bool:
        if business_id is not None and getattr(record, "business_id", None) != business_id:
            return False
        if environment is not None and getattr(record, "environment", None) != environment:
            return False
        return True

    @staticmethod
    def _normalized_provider(value: Any) -> str:
        return str(value or "").strip().casefold()

    def _is_instantly_campaign(self, campaign: Any) -> bool:
        return self._normalized_provider(getattr(campaign, "provider_name", None)) == "instantly" or bool(
            getattr(campaign, "provider_campaign_id", None) or getattr(campaign, "provider_workspace_id", None)
        )

    def _is_instantly_lead(self, lead: Any) -> bool:
        source = getattr(lead, "source", None)
        return (
            self._normalized_provider(getattr(lead, "provider_name", None)) == "instantly"
            or source in {LeadSource.INSTANTLY_IMPORT, LeadSource.INSTANTLY_SYNC}
            or bool(getattr(lead, "provider_lead_id", None) or getattr(lead, "provider_workspace_id", None))
        )

    @staticmethod
    def _is_instantly_suppression(record: Any) -> bool:
        return bool(getattr(record, "provider_blocklist_id", None))

    @staticmethod
    def _is_actionable_lead(lead: Any) -> bool:
        status = getattr(lead, "lt_interest_status", LeadInterestStatus.NEUTRAL)
        return status != LeadInterestStatus.NEUTRAL or bool(getattr(lead, "assigned_to", None))


provider_extras_service = ProviderExtrasService()
