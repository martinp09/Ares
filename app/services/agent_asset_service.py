from __future__ import annotations

from app.db.agent_assets import AgentAssetsRepository
from app.db.agents import AgentsRepository
from app.models.agent_assets import AgentAssetBindRequest, AgentAssetCreateRequest, AgentAssetRecord, AgentAssetType

OPERATIONAL_ASSET_TYPES = {
    AgentAssetType.CALENDAR,
    AgentAssetType.FORM,
    AgentAssetType.PHONE_NUMBER,
    AgentAssetType.INBOX,
    AgentAssetType.WEBHOOK,
}


class AgentAssetService:
    def __init__(
        self,
        agent_assets_repository: AgentAssetsRepository | None = None,
        agents_repository: AgentsRepository | None = None,
    ) -> None:
        self.agent_assets_repository = agent_assets_repository or AgentAssetsRepository()
        self.agents_repository = agents_repository or AgentsRepository()

    def create_asset(self, request: AgentAssetCreateRequest) -> AgentAssetRecord:
        agent = self.agents_repository.get_agent(request.agent_id)
        if agent is None:
            raise ValueError("Agent not found")
        if request.asset_type not in OPERATIONAL_ASSET_TYPES:
            raise ValueError(f"Asset type '{request.asset_type}' is outside operational scope")
        return self.agent_assets_repository.create(
            agent_id=request.agent_id,
            business_id=agent.business_id,
            environment=agent.environment,
            asset_type=request.asset_type,
            label=request.label,
            metadata=request.metadata,
        )

    def bind_asset(self, asset_id: str, request: AgentAssetBindRequest) -> AgentAssetRecord | None:
        return self.agent_assets_repository.bind(
            asset_id,
            binding_reference=request.binding_reference,
            metadata=request.metadata,
        )

    def get_asset(self, asset_id: str) -> AgentAssetRecord | None:
        return self.agent_assets_repository.get(asset_id)

    def list_assets(
        self,
        *,
        agent_id: str | None = None,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[AgentAssetRecord]:
        return self.agent_assets_repository.list(
            agent_id=agent_id,
            business_id=business_id,
            environment=environment,
        )


agent_asset_service = AgentAssetService()
