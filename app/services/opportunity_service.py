from __future__ import annotations

from app.db.opportunities import OpportunitiesRepository
from app.models.opportunities import OpportunityLaneStageSummary, OpportunityRecord, OpportunitySourceLane, OpportunityStage

_STAGE_ORDER = {
    OpportunityStage.QUALIFIED_OPPORTUNITY: 0,
    OpportunityStage.OFFER_PATH_SELECTED: 1,
    OpportunityStage.UNDER_NEGOTIATION: 2,
    OpportunityStage.CONTRACT_SENT: 3,
    OpportunityStage.CONTRACT_SIGNED: 4,
    OpportunityStage.TITLE_OPEN: 5,
    OpportunityStage.CURATIVE_REVIEW: 6,
    OpportunityStage.DISPO_READY: 7,
    OpportunityStage.CLOSED: 8,
    OpportunityStage.DEAD: 8,
}


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

    def advance_stage(self, opportunity_id: str, stage: OpportunityStage) -> OpportunityRecord:
        record = self.opportunities_repository.get(opportunity_id)
        if record is None:
            raise KeyError(opportunity_id)
        current_rank = _STAGE_ORDER[record.stage]
        target_rank = _STAGE_ORDER[stage]
        if target_rank < current_rank:
            raise ValueError(f"cannot move opportunity backward from {record.stage} to {stage}")
        if record.stage in {OpportunityStage.CLOSED, OpportunityStage.DEAD} and stage != record.stage:
            raise ValueError(f"cannot move terminal opportunity from {record.stage} to {stage}")
        return self.opportunities_repository.upsert(record.model_copy(update={"stage": stage}))

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
