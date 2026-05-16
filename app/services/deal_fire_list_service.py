from __future__ import annotations

from app.db.client import utc_now
from app.db.deals import DealsRepository
from app.models.deals import (
    DealDocumentRequirementStatus,
    DealFireListItem,
    DealRiskSeverity,
    DealTaskStatus,
)

_SEVERITY_RANK = {
    DealRiskSeverity.CRITICAL: 0,
    DealRiskSeverity.HIGH: 1,
    DealRiskSeverity.MEDIUM: 2,
    DealRiskSeverity.LOW: 3,
}
_ITEM_RANK = {"risk": 0, "task": 1, "document": 2, "provider_gate": 3}


class DealFireListService:
    def __init__(self, *, deals_repository: DealsRepository | None = None) -> None:
        self.deals_repository = deals_repository or DealsRepository()

    def get_fire_list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        limit: int | None = None,
    ) -> list[DealFireListItem]:
        now = utc_now()
        items: list[DealFireListItem] = []
        for deal in self.deals_repository.list_deals(business_id=business_id, environment=environment):
            assert deal.id is not None
            for flag in self.deals_repository.list_risk_flags(deal.id, active=True):
                if flag.severity in {DealRiskSeverity.HIGH, DealRiskSeverity.CRITICAL}:
                    items.append(
                        DealFireListItem(
                            deal_id=deal.id,
                            item_type="risk",
                            severity=flag.severity,
                            reason=flag.label,
                            recommended_action="Resolve or explicitly override this risk before advancing the deal",
                            source_id=flag.id,
                            action_enabled=False,
                            metadata={"code": flag.code},
                        )
                    )
            for task in self.deals_repository.list_tasks(deal.id):
                if task.status in {DealTaskStatus.OPEN, DealTaskStatus.BLOCKED} and task.due_at is not None and task.due_at <= now:
                    items.append(
                        DealFireListItem(
                            deal_id=deal.id,
                            item_type="task",
                            severity=DealRiskSeverity.HIGH if task.status == DealTaskStatus.BLOCKED else DealRiskSeverity.MEDIUM,
                            reason=f"Task due: {task.title}",
                            recommended_action="Complete or update the task status",
                            due_at=task.due_at,
                            source_id=task.id,
                            action_enabled=False,
                            metadata={"task_type": task.task_type.value, "status": task.status.value},
                        )
                    )
            for requirement in self.deals_repository.list_document_requirements(deal.id):
                if requirement.status in {DealDocumentRequirementStatus.MISSING, DealDocumentRequirementStatus.REQUESTED}:
                    items.append(
                        DealFireListItem(
                            deal_id=deal.id,
                            item_type="document",
                            severity=requirement.blocker_severity,
                            reason=f"Missing document: {requirement.document_type}",
                            recommended_action="Request, upload, or review the required document",
                            due_at=requirement.due_at,
                            source_id=requirement.id,
                            action_enabled=False,
                            metadata={"required_stage": requirement.required_stage.value, "status": requirement.status.value},
                        )
                    )
            if deal.no_send or not deal.provider_sends_enabled:
                items.append(
                    DealFireListItem(
                        deal_id=deal.id,
                        item_type="provider_gate",
                        severity=DealRiskSeverity.MEDIUM,
                        reason="Provider sends remain disabled until explicit approval gates are opened",
                        recommended_action="Review deal facts and approvals; do not send or enroll automatically",
                        source_id=deal.id,
                        action_enabled=False,
                        metadata=deal.provider_gate_snapshot,
                    )
                )
        items.sort(
            key=lambda item: (
                _SEVERITY_RANK[item.severity],
                _ITEM_RANK.get(item.item_type, 99),
                item.due_at or now,
                item.deal_id,
                item.source_id or "",
            )
        )
        if limit is not None:
            return items[:limit]
        return items


deal_fire_list_service = DealFireListService()
