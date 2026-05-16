from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.dependencies import actor_context_dependency
from app.models.actors import ActorContext
from app.models.deals import (
    DealDetail,
    DealFireListResponse,
    DealListResponse,
    DealPromotionRequest,
    DealStage,
    DealStageTransitionRequest,
    DealStrategyLane,
)
from app.services.deal_fire_list_service import deal_fire_list_service
from app.services.deal_promotion_service import deal_promotion_service
from app.services.deal_stage_service import deal_stage_service
from app.db.deals import DealsRepository

router = APIRouter(prefix="/deals", tags=["deals"])


@router.post("/promote/lead", response_model=DealDetail, response_model_exclude_none=True)
def promote_lead_to_deal(
    payload: DealPromotionRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> DealDetail:
    try:
        return deal_promotion_service.promote_lead_to_deal(
            payload.lead_id,
            business_id=payload.business_id,
            environment=payload.environment,
            source_lane=payload.source_lane,
            strategy_lane=payload.strategy_lane,
            actor_id=actor_context.actor_id,
            actor_type=actor_context.actor_type,
            promotion_reason=payload.promotion_reason,
            operator_notes=payload.operator_notes,
            no_send=payload.no_send,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/fire-list", response_model=DealFireListResponse, response_model_exclude_none=True)
def list_deal_fire_list(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> DealFireListResponse:
    del actor_context
    return DealFireListResponse(
        items=deal_fire_list_service.get_fire_list(business_id=business_id, environment=environment, limit=limit)
    )


@router.get("", response_model=DealListResponse, response_model_exclude_none=True)
def list_deals(
    business_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    strategy_lane: DealStrategyLane | None = Query(default=None),
    stage: DealStage | None = Query(default=None),
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> DealListResponse:
    del actor_context
    return DealListResponse(
        deals=DealsRepository().list_deals(
            business_id=business_id,
            environment=environment,
            strategy_lane=strategy_lane,
            stage=stage,
        )
    )


@router.get("/{deal_id}", response_model=DealDetail, response_model_exclude_none=True)
def get_deal_detail(
    deal_id: str,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> DealDetail:
    del actor_context
    detail = DealsRepository().get_detail(deal_id)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"deal {deal_id} not found")
    return detail


@router.post("/{deal_id}/stage", response_model=DealDetail, response_model_exclude_none=True)
def transition_deal_stage(
    deal_id: str,
    payload: DealStageTransitionRequest,
    actor_context: ActorContext = Depends(actor_context_dependency),
) -> DealDetail:
    try:
        return deal_stage_service.transition_stage(
            deal_id,
            payload.target_stage,
            actor_id=actor_context.actor_id,
            actor_type=actor_context.actor_type,
            reason=payload.reason,
            metadata=payload.metadata,
            manual_override=payload.manual_override,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
