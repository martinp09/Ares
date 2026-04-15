from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.agent_assets import AgentAssetRecord, AgentAssetStatus, AgentAssetType
from app.models.commands import generate_id


class AgentAssetsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        agent_id: str,
        business_id: str,
        environment: str,
        asset_type: AgentAssetType,
        label: str,
        metadata: dict,
    ) -> AgentAssetRecord:
        now = utc_now()
        asset = AgentAssetRecord(
            id=generate_id("asset"),
            agent_id=agent_id,
            business_id=business_id,
            environment=environment,
            asset_type=asset_type,
            label=label,
            connect_later=True,
            status=AgentAssetStatus.UNBOUND,
            metadata=deepcopy(metadata),
            created_at=now,
            updated_at=now,
        )
        with self.client.transaction() as store:
            store.agent_assets[asset.id] = asset
        return asset

    def get(self, asset_id: str) -> AgentAssetRecord | None:
        with self.client.transaction() as store:
            return store.agent_assets.get(asset_id)

    def list(
        self,
        *,
        agent_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[AgentAssetRecord]:
        with self.client.transaction() as store:
            assets = list(store.agent_assets.values())
        if agent_id is None:
            filtered_assets = assets
        else:
            filtered_assets = [asset for asset in assets if asset.agent_id == agent_id]
        if business_id is not None:
            filtered_assets = [asset for asset in filtered_assets if asset.business_id == business_id]
        if environment is not None:
            filtered_assets = [asset for asset in filtered_assets if asset.environment == environment]
        return filtered_assets

    def bind(self, asset_id: str, *, binding_reference: str, metadata: dict | None = None) -> AgentAssetRecord | None:
        with self.client.transaction() as store:
            asset = store.agent_assets.get(asset_id)
            if asset is None:
                return None
            now = utc_now()
            updated = asset.model_copy(
                update={
                    "binding_reference": binding_reference,
                    "connect_later": False,
                    "status": AgentAssetStatus.BOUND,
                    "metadata": {**asset.metadata, **deepcopy(metadata or {})},
                    "updated_at": now,
                    "bound_at": now,
                }
            )
            store.agent_assets[asset_id] = updated
            return updated
