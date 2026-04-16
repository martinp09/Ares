import pytest

from app.db.campaigns import CampaignsRepository
from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.models.campaigns import CampaignRecord, CampaignStatus
from app.services.campaign_lifecycle_service import (
    CampaignLifecycleService,
    InactiveCampaignEnrollmentError,
    InvalidCampaignTransitionError,
)


def build_service() -> CampaignLifecycleService:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return CampaignLifecycleService(CampaignsRepository(client))


def test_create_or_upsert_defaults_to_draft_and_preserves_existing_status() -> None:
    service = build_service()

    created = service.create_or_upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate",
            provider_name="instantly",
            provider_campaign_id="camp_123",
        )
    )

    assert created.status == CampaignStatus.DRAFT

    active = service.start(created.id or "")
    updated = service.create_or_upsert(
        CampaignRecord(
            business_id="limitless",
            environment="dev",
            name="Probate",
            provider_name="instantly",
            provider_campaign_id="camp_123",
            raw_payload={"source": "sync"},
        )
    )

    assert updated.id == created.id
    assert updated.status == CampaignStatus.ACTIVE
    assert updated.status == active.status
    assert updated.raw_payload == {"source": "sync"}


def test_campaign_lifecycle_supports_valid_transitions() -> None:
    service = build_service()
    created = service.create_or_upsert(
        CampaignRecord(business_id="limitless", environment="dev", name="Probate", provider_campaign_id="camp_234")
    )

    active = service.activate(created.id or "")
    paused = service.pause(active.id or "")
    resumed = service.resume(paused.id or "")
    completed = service.complete(resumed.id or "")
    archived = service.archive(completed.id or "")

    assert active.status == CampaignStatus.ACTIVE
    assert paused.status == CampaignStatus.PAUSED
    assert resumed.status == CampaignStatus.ACTIVE
    assert completed.status == CampaignStatus.COMPLETED
    assert archived.status == CampaignStatus.ARCHIVED


def test_campaign_lifecycle_rejects_invalid_transitions_and_status_regressions() -> None:
    service = build_service()
    created = service.create_or_upsert(
        CampaignRecord(business_id="limitless", environment="dev", name="Probate", provider_campaign_id="camp_345")
    )

    with pytest.raises(InvalidCampaignTransitionError, match="cannot pause campaign"):
        service.pause(created.id or "")

    active = service.activate(created.id or "")
    completed = service.complete(active.id or "")

    with pytest.raises(InvalidCampaignTransitionError, match="cannot resume campaign"):
        service.resume(completed.id or "")

    with pytest.raises(InvalidCampaignTransitionError, match="cannot move campaign from completed to draft"):
        service.create_or_upsert(
            CampaignRecord(
                business_id="limitless",
                environment="dev",
                name="Probate",
                provider_campaign_id="camp_345",
                status=CampaignStatus.DRAFT,
            )
        )

    with pytest.raises(InvalidCampaignTransitionError, match="created as draft or active"):
        service.create_or_upsert(
            CampaignRecord(
                business_id="limitless",
                environment="dev",
                name="Archive Me",
                provider_campaign_id="camp_346",
                status=CampaignStatus.PAUSED,
            )
        )


def test_require_active_campaign_rejects_inactive_campaigns() -> None:
    service = build_service()
    created = service.create_or_upsert(
        CampaignRecord(business_id="limitless", environment="dev", name="Probate", provider_campaign_id="camp_456")
    )

    with pytest.raises(InactiveCampaignEnrollmentError, match="must be active before enrollment"):
        service.require_active_campaign(
            campaign_id=created.id or "",
            business_id="limitless",
            environment="dev",
        )
