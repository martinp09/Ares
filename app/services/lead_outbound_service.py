from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.db.automation_runs import AutomationRunsRepository
from app.db.campaign_memberships import CampaignMembershipsRepository
from app.db.campaigns import CampaignsRepository
from app.db.client import utc_now
from app.db.leads import LeadsRepository
from app.models.automation_runs import AutomationRunRecord, AutomationRunStatus
from app.models.campaigns import CampaignMembershipRecord, CampaignMembershipStatus
from app.models.leads import LeadLifecycleStatus, LeadRecord
from app.providers.instantly import InstantlyClient
from app.services.lead_suppression_service import LeadSuppressionService


@dataclass(slots=True)
class OutboundEnrollmentRequest:
    business_id: str
    environment: str
    lead_ids: list[str]
    campaign_id: str | None = None
    list_id: str | None = None
    skip_if_in_workspace: bool = True
    skip_if_in_campaign: bool = True
    skip_if_in_list: bool = True
    blocklist_id: str | None = None
    assigned_to: str | None = None
    verify_leads_on_import: bool = False
    chunk_size: int | None = None
    wait_seconds: float | None = None


@dataclass(slots=True)
class OutboundEnrollmentResult:
    automation_runs: list[AutomationRunRecord] = field(default_factory=list)
    memberships: list[CampaignMembershipRecord] = field(default_factory=list)
    suppressed_lead_ids: list[str] = field(default_factory=list)
    provider_batches: list[dict[str, Any]] = field(default_factory=list)


class LeadOutboundService:
    def __init__(
        self,
        *,
        instantly_client: InstantlyClient,
        leads_repository: LeadsRepository | None = None,
        campaigns_repository: CampaignsRepository | None = None,
        memberships_repository: CampaignMembershipsRepository | None = None,
        automation_runs_repository: AutomationRunsRepository | None = None,
        suppression_service: LeadSuppressionService | None = None,
    ) -> None:
        self.instantly_client = instantly_client
        self.leads_repository = leads_repository or LeadsRepository()
        self.campaigns_repository = campaigns_repository or CampaignsRepository()
        self.memberships_repository = memberships_repository or CampaignMembershipsRepository()
        self.automation_runs_repository = automation_runs_repository or AutomationRunsRepository()
        self.suppression_service = suppression_service or LeadSuppressionService()

    def enqueue_leads(self, request: OutboundEnrollmentRequest) -> OutboundEnrollmentResult:
        if request.campaign_id and request.list_id:
            raise ValueError("campaign_id or list_id may be set, not both")
        if not request.lead_ids:
            raise ValueError("at least one lead_id is required")

        result = OutboundEnrollmentResult()
        outbound_rows: list[dict[str, Any]] = []
        eligible_leads: list[LeadRecord] = []
        runs_by_lead_id: dict[str, AutomationRunRecord] = {}

        for lead_id in request.lead_ids:
            lead = self.leads_repository.get(lead_id)
            if lead is None:
                raise KeyError(lead_id)
            run = self.automation_runs_repository.create(
                AutomationRunRecord(
                    business_id=request.business_id,
                    environment=request.environment,
                    workflow_name="lead-outbound",
                    workflow_version="v1",
                    workflow_step="enroll",
                    phase="transport",
                    lead_id=lead.id,
                    campaign_id=request.campaign_id,
                    status=AutomationRunStatus.IN_PROGRESS,
                    idempotency_key=self._idempotency_key(
                        business_id=request.business_id,
                        environment=request.environment,
                        lead_id=lead.id or lead_id,
                        campaign_id=request.campaign_id,
                        list_id=request.list_id,
                    ),
                    replay_key=self._idempotency_key(
                        business_id=request.business_id,
                        environment=request.environment,
                        lead_id=lead.id or lead_id,
                        campaign_id=request.campaign_id,
                        list_id=request.list_id,
                    ),
                    input_payload={
                        "campaign_id": request.campaign_id,
                        "list_id": request.list_id,
                        "assigned_to": request.assigned_to,
                    },
                    started_at=utc_now(),
                )
            )
            result.automation_runs.append(run)
            runs_by_lead_id[lead.id or lead_id] = run

            if self.suppression_service.is_suppressed(
                business_id=request.business_id,
                environment=request.environment,
                lead_id=lead.id,
                email=lead.email,
                campaign_id=request.campaign_id,
            ):
                result.suppressed_lead_ids.append(lead.id or lead_id)
                self.automation_runs_repository.save(
                    run.model_copy(
                        update={
                            "status": AutomationRunStatus.CANCELLED,
                            "completed_at": utc_now(),
                            "output_payload": {"action": "suppressed"},
                        }
                    )
                )
                continue

            eligible_leads.append(lead)
            outbound_rows.append(self._lead_payload(lead))

        if outbound_rows:
            result.provider_batches = self.instantly_client.bulk_add_leads(
                outbound_rows,
                campaign_id=request.campaign_id,
                list_id=request.list_id,
                skip_if_in_workspace=request.skip_if_in_workspace,
                skip_if_in_campaign=request.skip_if_in_campaign,
                skip_if_in_list=request.skip_if_in_list,
                blocklist_id=request.blocklist_id,
                assigned_to=request.assigned_to,
                verify_leads_on_import=request.verify_leads_on_import,
                chunk_size=request.chunk_size,
                wait_seconds=request.wait_seconds,
            )

        for lead in eligible_leads:
            if request.campaign_id:
                membership = self.memberships_repository.upsert(
                    CampaignMembershipRecord(
                        business_id=request.business_id,
                        environment=request.environment,
                        lead_id=lead.id or "",
                        campaign_id=request.campaign_id,
                        assigned_to=request.assigned_to,
                        status=CampaignMembershipStatus.PENDING,
                        idempotency_key=self._idempotency_key(
                            business_id=request.business_id,
                            environment=request.environment,
                            lead_id=lead.id or "",
                            campaign_id=request.campaign_id,
                            list_id=request.list_id,
                        ),
                        metadata={
                            "provider": "instantly",
                            "list_id": request.list_id,
                        },
                        last_synced_at=utc_now(),
                    )
                )
                result.memberships.append(membership)

            updated_lead = self.leads_repository.upsert(
                lead.model_copy(
                    update={
                        "provider_name": "instantly",
                        "campaign_id": request.campaign_id or lead.campaign_id,
                        "list_id": request.list_id or lead.list_id,
                        "assigned_to": request.assigned_to or lead.assigned_to,
                        "lifecycle_status": LeadLifecycleStatus.ROUTED,
                        "last_touched_at": utc_now(),
                    }
                )
            )
            run = runs_by_lead_id.get(lead.id or "")
            if run is not None:
                self.automation_runs_repository.save(
                    run.model_copy(
                        update={
                            "status": AutomationRunStatus.COMPLETED,
                            "completed_at": utc_now(),
                            "output_payload": {
                                "campaign_id": request.campaign_id,
                                "list_id": request.list_id,
                                "provider_batches": len(result.provider_batches),
                                "lead_id": updated_lead.id,
                            },
                        }
                    )
                )
        return result

    @staticmethod
    def _lead_payload(lead: LeadRecord) -> dict[str, Any]:
        return {
            "email": lead.email,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "phone": lead.phone,
            "website": lead.website,
            "company_name": lead.company_name,
            "job_title": lead.job_title,
            "lt_interest_status": lead.lt_interest_status.value if hasattr(lead.lt_interest_status, "value") else lead.lt_interest_status,
            "custom_variables": dict(lead.custom_variables),
            "personalization": dict(lead.personalization),
            "assigned_to": lead.assigned_to,
        }

    @staticmethod
    def _idempotency_key(
        *,
        business_id: str,
        environment: str,
        lead_id: str,
        campaign_id: str | None,
        list_id: str | None,
    ) -> str:
        return f"lead-outbound:{business_id}:{environment}:{lead_id}:{campaign_id or '-'}:{list_id or '-'}:enroll"
