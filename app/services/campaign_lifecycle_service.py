from __future__ import annotations

from collections.abc import Mapping

from app.db.campaigns import CampaignsRepository
from app.db.lead_machine_supabase import resolve_tenant
from app.models.campaigns import CampaignRecord, CampaignStatus


class CampaignLifecycleError(ValueError):
    pass


class CampaignNotFoundError(KeyError):
    pass


class InvalidCampaignTransitionError(CampaignLifecycleError):
    pass


class InactiveCampaignEnrollmentError(CampaignLifecycleError):
    pass


class CampaignLifecycleService:
    ALLOWED_STATUS_TRANSITIONS: Mapping[CampaignStatus, frozenset[CampaignStatus]] = {
        CampaignStatus.DRAFT: frozenset({CampaignStatus.DRAFT, CampaignStatus.ACTIVE, CampaignStatus.ARCHIVED}),
        CampaignStatus.ACTIVE: frozenset({CampaignStatus.ACTIVE, CampaignStatus.PAUSED, CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED}),
        CampaignStatus.PAUSED: frozenset({CampaignStatus.PAUSED, CampaignStatus.ACTIVE, CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED}),
        CampaignStatus.COMPLETED: frozenset({CampaignStatus.COMPLETED, CampaignStatus.ARCHIVED}),
        CampaignStatus.ARCHIVED: frozenset({CampaignStatus.ARCHIVED}),
    }
    INITIAL_STATUSES: frozenset[CampaignStatus] = frozenset({CampaignStatus.DRAFT, CampaignStatus.ACTIVE})

    def __init__(self, campaigns_repository: CampaignsRepository | None = None) -> None:
        self.campaigns_repository = campaigns_repository or CampaignsRepository()

    def create_or_upsert(self, record: CampaignRecord, *, dedupe_key: str | None = None) -> CampaignRecord:
        resolved_key = dedupe_key or record.identity_key()
        existing = self.campaigns_repository.get_by_key(
            business_id=record.business_id,
            environment=record.environment,
            dedupe_key=resolved_key,
        )
        if existing is None:
            if record.status not in self.INITIAL_STATUSES:
                raise InvalidCampaignTransitionError(
                    f"campaigns may only be created as draft or active; got {record.status.value}"
                )
            return self.campaigns_repository.upsert(record, dedupe_key=resolved_key)

        target_status = record.status if "status" in record.model_fields_set else existing.status
        self._validate_transition(existing.status, target_status)
        return self.campaigns_repository.upsert(
            record.model_copy(
                update={
                    "id": existing.id,
                    "status": target_status,
                    "created_at": existing.created_at,
                }
            ),
            dedupe_key=resolved_key,
        )

    def activate(self, campaign_id: str) -> CampaignRecord:
        return self._transition(campaign_id, target_status=CampaignStatus.ACTIVE, allowed_from={CampaignStatus.DRAFT}, action="activate")

    def start(self, campaign_id: str) -> CampaignRecord:
        return self.activate(campaign_id)

    def pause(self, campaign_id: str) -> CampaignRecord:
        return self._transition(campaign_id, target_status=CampaignStatus.PAUSED, allowed_from={CampaignStatus.ACTIVE}, action="pause")

    def resume(self, campaign_id: str) -> CampaignRecord:
        return self._transition(campaign_id, target_status=CampaignStatus.ACTIVE, allowed_from={CampaignStatus.PAUSED}, action="resume")

    def complete(self, campaign_id: str) -> CampaignRecord:
        return self._transition(
            campaign_id,
            target_status=CampaignStatus.COMPLETED,
            allowed_from={CampaignStatus.ACTIVE, CampaignStatus.PAUSED},
            action="complete",
        )

    def archive(self, campaign_id: str) -> CampaignRecord:
        return self._transition(
            campaign_id,
            target_status=CampaignStatus.ARCHIVED,
            allowed_from={
                CampaignStatus.DRAFT,
                CampaignStatus.ACTIVE,
                CampaignStatus.PAUSED,
                CampaignStatus.COMPLETED,
            },
            action="archive",
        )

    def require_active_campaign(self, *, campaign_id: str, business_id: str, environment: str) -> CampaignRecord:
        campaign = self._require_campaign(campaign_id)
        if not self._campaign_matches_tenant(campaign=campaign, business_id=business_id, environment=environment):
            raise InactiveCampaignEnrollmentError(
                f"campaign {campaign_id} does not belong to {business_id}/{environment}"
            )
        if campaign.status != CampaignStatus.ACTIVE:
            raise InactiveCampaignEnrollmentError(
                f"campaign {campaign_id} must be active before enrollment; current status={campaign.status.value}"
            )
        return campaign

    def _transition(
        self,
        campaign_id: str,
        *,
        target_status: CampaignStatus,
        allowed_from: set[CampaignStatus],
        action: str,
    ) -> CampaignRecord:
        campaign = self._require_campaign(campaign_id)
        if campaign.status not in allowed_from:
            allowed = ", ".join(sorted(status.value for status in allowed_from))
            raise InvalidCampaignTransitionError(
                f"cannot {action} campaign {campaign_id} from {campaign.status.value}; allowed from: {allowed}"
            )
        return self.campaigns_repository.upsert(campaign.model_copy(update={"status": target_status}))

    def _require_campaign(self, campaign_id: str) -> CampaignRecord:
        campaign = self.campaigns_repository.get(campaign_id)
        if campaign is None:
            raise CampaignNotFoundError(campaign_id)
        return campaign

    def _validate_transition(self, current_status: CampaignStatus, target_status: CampaignStatus) -> None:
        allowed_targets = self.ALLOWED_STATUS_TRANSITIONS[current_status]
        if target_status not in allowed_targets:
            allowed = ", ".join(sorted(status.value for status in allowed_targets))
            raise InvalidCampaignTransitionError(
                f"cannot move campaign from {current_status.value} to {target_status.value}; allowed targets: {allowed}"
            )

    @staticmethod
    def _campaign_matches_tenant(*, campaign: CampaignRecord, business_id: str, environment: str) -> bool:
        if campaign.environment != environment:
            return False
        if campaign.business_id == business_id:
            return True
        if campaign.business_id.isdigit() and not business_id.isdigit():
            try:
                tenant = resolve_tenant(business_id, environment)
            except RuntimeError:
                return False
            return campaign.business_id == str(tenant.business_pk)
        return False


campaign_lifecycle_service = CampaignLifecycleService()
