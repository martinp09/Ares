from __future__ import annotations

from copy import deepcopy

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.agent_assets import AgentAssetRecord, AgentAssetStatus, AgentAssetType
from app.models.commands import generate_id


class AgentAssetsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(self, *, agent_id: str, asset_type: AgentAssetType, label: str, metadata: dict) -> AgentAssetRecord:
        now = utc_now()
        asset = AgentAssetRecord(
            id=generate_id("asset"),
            agent_id=agent_id,
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
