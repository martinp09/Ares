from fastapi import APIRouter, HTTPException

from app.models.agent_assets import AgentAssetBindRequest, AgentAssetCreateRequest, AgentAssetRecord
from app.services.agent_asset_service import agent_asset_service

router = APIRouter(prefix="/agent-assets", tags=["agent-assets"])


@router.post("", response_model=AgentAssetRecord)
def create_asset(request: AgentAssetCreateRequest) -> AgentAssetRecord:
    try:
        return agent_asset_service.create_asset(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{asset_id}", response_model=AgentAssetRecord)
def get_asset(asset_id: str) -> AgentAssetRecord:
    asset = agent_asset_service.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Agent asset not found")
    return asset


@router.post("/{asset_id}/bind", response_model=AgentAssetRecord)
def bind_asset(asset_id: str, request: AgentAssetBindRequest) -> AgentAssetRecord:
    asset = agent_asset_service.bind_asset(asset_id, request)
    if asset is None:
        raise HTTPException(status_code=404, detail="Agent asset not found")
    return asset
