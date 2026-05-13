from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.hubspot_crm import HubSpotCustomizationRequest, HubSpotProviderActionResponse, HubSpotRecordSyncRequest
from app.services.hubspot_crm_service import HubSpotCrmService

router = APIRouter(prefix="/crm/hubspot", tags=["crm", "hubspot"])


def hubspot_crm_service_dependency() -> HubSpotCrmService:
    return HubSpotCrmService()


@router.post("/customization", response_model=HubSpotProviderActionResponse, status_code=status.HTTP_201_CREATED)
def configure_hubspot_crm(
    request: HubSpotCustomizationRequest,
    service: HubSpotCrmService = Depends(hubspot_crm_service_dependency),
) -> HubSpotProviderActionResponse:
    try:
        return service.configure_crm(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/records/sync", response_model=HubSpotProviderActionResponse, status_code=status.HTTP_201_CREATED)
def sync_hubspot_record(
    request: HubSpotRecordSyncRequest,
    service: HubSpotCrmService = Depends(hubspot_crm_service_dependency),
) -> HubSpotProviderActionResponse:
    try:
        return service.sync_record(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
