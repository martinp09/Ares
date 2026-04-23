from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.catalog import CatalogEntryCreateRequest, CatalogEntryListResponse, CatalogEntryRecord
from app.services.catalog_service import catalog_service

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post("", response_model=CatalogEntryRecord)
def create_catalog_entry(
    request: CatalogEntryCreateRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> CatalogEntryRecord:
    try:
        return catalog_service.create_entry(request, org_id=actor_context.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=CatalogEntryListResponse)
def list_catalog_entries(
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> CatalogEntryListResponse:
    return catalog_service.list_entries(org_id=actor_context.org_id)


@router.get("/{entry_id}", response_model=CatalogEntryRecord)
def get_catalog_entry(
    entry_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> CatalogEntryRecord:
    entry = catalog_service.get_entry(entry_id, org_id=actor_context.org_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Catalog entry not found")
    return entry
