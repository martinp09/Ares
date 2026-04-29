from __future__ import annotations

from app.db.opportunities import OpportunitiesRepository
from app.models.opportunities import (
    OpportunityLaneStageSummary,
    OpportunityPipelineConfig,
    OpportunityPipelineStageConfig,
    OpportunityRecord,
    OpportunitySourceLane,
    OpportunityStage,
    OpportunityStageHistoryRecord,
)

_DEFAULT_STAGE_CONFIGS = [
    OpportunityPipelineStageConfig(stage=OpportunityStage.QUALIFIED_OPPORTUNITY, label="Qualified Opportunity", order=0),
    OpportunityPipelineStageConfig(stage=OpportunityStage.OFFER_PATH_SELECTED, label="Offer Path Selected", order=1),
    OpportunityPipelineStageConfig(stage=OpportunityStage.UNDER_NEGOTIATION, label="Under Negotiation", order=2),
    OpportunityPipelineStageConfig(stage=OpportunityStage.CONTRACT_SENT, label="Contract Sent", order=3),
    OpportunityPipelineStageConfig(stage=OpportunityStage.CONTRACT_SIGNED, label="Contract Signed", order=4),
    OpportunityPipelineStageConfig(stage=OpportunityStage.TITLE_OPEN, label="Title Open", order=5),
    OpportunityPipelineStageConfig(stage=OpportunityStage.CURATIVE_REVIEW, label="Curative Review", order=6),
    OpportunityPipelineStageConfig(stage=OpportunityStage.DISPO_READY, label="Dispo Ready", order=7),
    OpportunityPipelineStageConfig(stage=OpportunityStage.CLOSED, label="Closed", order=8, terminal=True),
    OpportunityPipelineStageConfig(stage=OpportunityStage.DEAD, label="Dead", order=9, terminal=True),
]


class OpportunityService:
    def __init__(self, opportunities_repository: OpportunitiesRepository | None = None) -> None:
        self.opportunities_repository = opportunities_repository or OpportunitiesRepository()

    def create_for_lead(
        self,
        *,
        business_id: str,
        environment: str,
        lead_id: str,
        source_lane: OpportunitySourceLane,
        strategy_lane: str | None = None,
        metadata: dict | None = None,
    ) -> OpportunityRecord:
        return self.opportunities_repository.upsert(
            OpportunityRecord(
                business_id=business_id,
                environment=environment,
                source_lane=source_lane,
                strategy_lane=strategy_lane,
                lead_id=lead_id,
                metadata=dict(metadata or {}),
            )
        )

    def create_for_contact(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        source_lane: OpportunitySourceLane,
        strategy_lane: str | None = None,
        metadata: dict | None = None,
    ) -> OpportunityRecord:
        return self.opportunities_repository.upsert(
            OpportunityRecord(
                business_id=business_id,
                environment=environment,
                source_lane=source_lane,
                strategy_lane=strategy_lane,
                contact_id=contact_id,
                metadata=dict(metadata or {}),
            )
        )

    def upsert_pipeline_config(self, config: OpportunityPipelineConfig) -> OpportunityPipelineConfig:
        return self.opportunities_repository.upsert_pipeline_config(config)

    def get_pipeline_config(
        self,
        *,
        business_id: str,
        environment: str,
        source_lane: OpportunitySourceLane,
    ) -> OpportunityPipelineConfig:
        configured = self.opportunities_repository.get_active_pipeline_config(
            business_id=business_id,
            environment=environment,
            source_lane=source_lane.value,
        )
        if configured is not None:
            return configured
        return OpportunityPipelineConfig(
            business_id=business_id,
            environment=environment,
            source_lane=source_lane,
            name=f"{source_lane.value.replace('_', ' ').title()} Pipeline",
            stages=list(_DEFAULT_STAGE_CONFIGS),
        )

    def list_pipeline_configs(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[OpportunityPipelineConfig]:
        return self.opportunities_repository.list_pipeline_configs(business_id=business_id, environment=environment)

    def advance_stage(
        self,
        opportunity_id: str,
        stage: OpportunityStage,
        *,
        actor_id: str | None = None,
        actor_type: str | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> OpportunityRecord:
        record = self.opportunities_repository.get(opportunity_id)
        if record is None:
            raise KeyError(opportunity_id)
        config = self.get_pipeline_config(
            business_id=record.business_id,
            environment=record.environment,
            source_lane=record.source_lane,
        )
        current_rank = config.stage_rank(record.stage)
        target_rank = config.stage_rank(stage)
        if target_rank < current_rank:
            raise ValueError(f"cannot move opportunity backward from {record.stage} to {stage}")
        if config.is_terminal_stage(record.stage) and stage != record.stage:
            raise ValueError(f"cannot move terminal opportunity from {record.stage} to {stage}")
        updated = self.opportunities_repository.upsert(record.model_copy(update={"stage": stage}))
        if record.stage != stage:
            self.opportunities_repository.append_stage_history(
                OpportunityStageHistoryRecord(
                    business_id=record.business_id,
                    environment=record.environment,
                    opportunity_id=record.id or opportunity_id,
                    from_stage=record.stage,
                    to_stage=stage,
                    actor_id=actor_id,
                    actor_type=actor_type,
                    reason=reason,
                    metadata=dict(metadata or {}),
                )
            )
        return updated

    def list_stage_history(self, opportunity_id: str) -> list[OpportunityStageHistoryRecord]:
        return self.opportunities_repository.list_stage_history(opportunity_id)

    def summarize_by_lane_and_stage(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[OpportunityLaneStageSummary]:
        opportunities = self.opportunities_repository.list(business_id=business_id, environment=environment)
        counts: dict[tuple[str, str], int] = {}
        for opportunity in opportunities:
            key = (str(opportunity.source_lane), str(opportunity.stage))
            counts[key] = counts.get(key, 0) + 1
        return [
            OpportunityLaneStageSummary(source_lane=lane, stage=stage, count=count)
            for (lane, stage), count in sorted(counts.items())
        ]


opportunity_service = OpportunityService()
