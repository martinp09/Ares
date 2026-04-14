from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from app.db.client import ControlPlaneClient, SupabaseControlPlaneClient, get_control_plane_client, utc_now
from app.models.agent_assets import AgentAssetRecord, AgentAssetStatus, AgentAssetType
from app.models.commands import generate_id


def agent_asset_record_from_row(row: Mapping[str, Any]) -> AgentAssetRecord:
    raw_metadata = row.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    return AgentAssetRecord(
        id=str(row.get("runtime_id") or row["id"]),
        agent_id=str(row["agent_id"]),
        business_id=str(row["business_id"]),
        environment=str(row["environment"]),
        asset_type=AgentAssetType(str(row["asset_type"])),
        label=str(row["label"]),
        connect_later=bool(row.get("connect_later", False)),
        status=AgentAssetStatus(str(row["status"])),
        metadata=metadata,
        binding_reference=str(row["binding_reference"]) if row.get("binding_reference") is not None else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        bound_at=row.get("bound_at"),
    )


class AgentAssetsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def _is_supabase(self) -> bool:
        return getattr(self.client, "backend", None) == "supabase"

    def _supabase_client(self) -> SupabaseControlPlaneClient:
        if not isinstance(self.client, SupabaseControlPlaneClient):
            return self.client  # type: ignore[return-value]
        return self.client

    def _select_supabase_assets(
        self,
        *,
        runtime_id: str | None = None,
        agent_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
        limit: int | None = None,
    ) -> list[AgentAssetRecord]:
        filters: dict[str, str] = {}
        if runtime_id is not None:
            filters["runtime_id"] = runtime_id
        if agent_id is not None:
            filters["agent_id"] = agent_id
        if business_id is not None:
            filters["business_id"] = business_id
        if environment is not None:
            filters["environment"] = environment
        rows = self._supabase_client().select(
            "agent_operational_assets",
            columns=(
                "id,runtime_id,agent_id,business_id,environment,asset_type,label,connect_later,status,"
                "metadata,binding_reference,created_at,updated_at,bound_at"
            ),
            filters=filters,
            order="created_at.asc",
            limit=limit,
        )
        return [agent_asset_record_from_row(row) for row in rows]

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
        if self._is_supabase():
            rows = self._supabase_client().insert(
                "agent_operational_assets",
                rows=[
                    {
                        "runtime_id": asset.id,
                        "agent_id": asset.agent_id,
                        "business_id": asset.business_id,
                        "environment": asset.environment,
                        "asset_type": asset.asset_type.value,
                        "label": asset.label,
                        "connect_later": asset.connect_later,
                        "status": asset.status.value,
                        "metadata": asset.metadata,
                        "binding_reference": asset.binding_reference,
                        "created_at": now.isoformat(),
                        "updated_at": now.isoformat(),
                        "bound_at": asset.bound_at,
                    }
                ],
                columns=(
                    "id,runtime_id,agent_id,business_id,environment,asset_type,label,connect_later,status,"
                    "metadata,binding_reference,created_at,updated_at,bound_at"
                ),
            )
            if not rows:
                raise RuntimeError("Supabase agent asset insert failed without returning a row")
            return agent_asset_record_from_row(rows[0])

        with self.client.transaction() as store:
            store.agent_assets[asset.id] = asset
        return asset

    def get(self, asset_id: str) -> AgentAssetRecord | None:
        if self._is_supabase():
            assets = self._select_supabase_assets(runtime_id=asset_id, limit=1)
            if not assets:
                return None
            return assets[0]

        with self.client.transaction() as store:
            return store.agent_assets.get(asset_id)

    def list(
        self,
        *,
        agent_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[AgentAssetRecord]:
        if self._is_supabase():
            return self._select_supabase_assets(
                agent_id=agent_id,
                business_id=business_id,
                environment=environment,
            )

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
        if self._is_supabase():
            existing_assets = self._select_supabase_assets(runtime_id=asset_id, limit=1)
            if not existing_assets:
                return None

            asset = existing_assets[0]
            now = utc_now()
            merged_metadata = {**asset.metadata, **deepcopy(metadata or {})}
            rows = self._supabase_client().update(
                "agent_operational_assets",
                values={
                    "binding_reference": binding_reference,
                    "connect_later": False,
                    "status": AgentAssetStatus.BOUND.value,
                    "metadata": merged_metadata,
                    "updated_at": now.isoformat(),
                    "bound_at": now.isoformat(),
                },
                filters={"runtime_id": asset_id},
                columns=(
                    "id,runtime_id,agent_id,business_id,environment,asset_type,label,connect_later,status,"
                    "metadata,binding_reference,created_at,updated_at,bound_at"
                ),
            )
            if not rows:
                raise RuntimeError(f"Supabase agent asset bind failed for runtime_id '{asset_id}'")
            return agent_asset_record_from_row(rows[0])

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
