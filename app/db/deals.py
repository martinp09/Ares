from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_stable_id
from app.models.deals import (
    Deal,
    DealAuditEvent,
    DealDetail,
    DealDocumentRequirement,
    DealDocumentRequirementStatus,
    DealParty,
    DealRiskFlag,
    DealStage,
    DealStageEvent,
    DealStrategyLane,
    DealTask,
    DealTaskStatus,
)


class DealsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)

    def upsert_deal(self, record: Deal, *, dedupe_key: str | None = None) -> Deal:
        now = utc_now()
        resolved_key = dedupe_key or record.identity_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.deal_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.deals[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.deals[existing_id] = updated
                return updated
            deal_id = record.id or generate_stable_id("deal", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": deal_id, "updated_at": now, "metadata": {**record.metadata, "dedupe_key": resolved_key}})
            store.deals[deal_id] = created
            store.deal_keys[lookup_key] = deal_id
            return created

    def get_deal(self, deal_id: str) -> Deal | None:
        with self.client.transaction() as store:
            return store.deals.get(deal_id)

    def get_deal_by_identity(self, *, business_id: str, environment: str, dedupe_key: str) -> Deal | None:
        with self.client.transaction() as store:
            deal_id = store.deal_keys.get((business_id, environment, dedupe_key))
            if deal_id is None:
                return None
            return store.deals.get(deal_id)

    def list_deals(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        strategy_lane: DealStrategyLane | str | None = None,
        stage: DealStage | str | None = None,
        blocked: bool | None = None,
    ) -> list[Deal]:
        with self.client.transaction() as store:
            records = list(store.deals.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        if strategy_lane is not None:
            lane_value = strategy_lane.value if isinstance(strategy_lane, DealStrategyLane) else str(strategy_lane)
            records = [record for record in records if record.strategy_lane.value == lane_value]
        if stage is not None:
            stage_value = stage.value if isinstance(stage, DealStage) else str(stage)
            records = [record for record in records if record.stage.value == stage_value]
        if blocked is not None:
            records = [record for record in records if bool(record.blocking_reason) is blocked]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records

    def add_party(self, party: DealParty, *, dedupe_key: str | None = None) -> DealParty:
        now = utc_now()
        resolved_key = dedupe_key or party.identity_key()
        lookup_key = (party.business_id, party.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.deal_party_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.deal_parties[existing_id]
                updates = party.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.deal_parties[existing_id] = updated
                return updated
            party_id = party.id or generate_stable_id("dealparty", party.business_id, party.environment, resolved_key)
            created = party.model_copy(update={"id": party_id, "updated_at": now})
            store.deal_parties[party_id] = created
            store.deal_party_keys[lookup_key] = party_id
            return created

    def list_parties(self, deal_id: str) -> list[DealParty]:
        with self.client.transaction() as store:
            records = [party for party in store.deal_parties.values() if party.deal_id == deal_id]
        records.sort(key=lambda party: (party.created_at, party.id or ""))
        return records

    def upsert_task(self, task: DealTask, *, dedupe_key: str | None = None) -> DealTask:
        now = utc_now()
        resolved_key = dedupe_key or task.identity_key()
        lookup_key = (task.business_id, task.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.deal_task_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.deal_tasks[existing_id]
                updates = task.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.deal_tasks[existing_id] = updated
                return updated
            task_id = task.id or generate_stable_id("dealtask", task.business_id, task.environment, resolved_key)
            created = task.model_copy(update={"id": task_id, "updated_at": now})
            store.deal_tasks[task_id] = created
            store.deal_task_keys[lookup_key] = task_id
            return created

    def list_tasks(self, deal_id: str, status: DealTaskStatus | str | None = None) -> list[DealTask]:
        with self.client.transaction() as store:
            records = [task for task in store.deal_tasks.values() if task.deal_id == deal_id]
        if status is not None:
            status_value = status.value if isinstance(status, DealTaskStatus) else str(status)
            records = [task for task in records if task.status.value == status_value]
        records.sort(key=lambda task: (task.due_at is None, task.due_at or task.created_at, task.id or ""))
        return records

    def upsert_document_requirement(
        self,
        requirement: DealDocumentRequirement,
        *,
        dedupe_key: str | None = None,
    ) -> DealDocumentRequirement:
        now = utc_now()
        resolved_key = dedupe_key or requirement.identity_key()
        lookup_key = (requirement.business_id, requirement.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.deal_document_requirement_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.deal_document_requirements[existing_id]
                updates = requirement.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.deal_document_requirements[existing_id] = updated
                return updated
            requirement_id = requirement.id or generate_stable_id(
                "dealdocreq",
                requirement.business_id,
                requirement.environment,
                resolved_key,
            )
            created = requirement.model_copy(update={"id": requirement_id, "updated_at": now})
            store.deal_document_requirements[requirement_id] = created
            store.deal_document_requirement_keys[lookup_key] = requirement_id
            return created

    def list_document_requirements(
        self,
        deal_id: str,
        status: DealDocumentRequirementStatus | str | None = None,
    ) -> list[DealDocumentRequirement]:
        with self.client.transaction() as store:
            records = [row for row in store.deal_document_requirements.values() if row.deal_id == deal_id]
        if status is not None:
            status_value = status.value if isinstance(status, DealDocumentRequirementStatus) else str(status)
            records = [row for row in records if row.status.value == status_value]
        records.sort(key=lambda row: (row.required_stage.value, row.document_type, row.id or ""))
        return records

    def add_audit_event(self, event: DealAuditEvent, *, dedupe_key: str | None = None) -> DealAuditEvent:
        resolved_key = dedupe_key
        lookup_key = (event.business_id, event.environment, resolved_key) if resolved_key is not None else None
        with self.client.transaction() as store:
            if lookup_key is not None:
                existing_id = store.deal_audit_event_keys.get(lookup_key)
                if existing_id is not None:
                    return store.deal_audit_events[existing_id]
            event_id = event.id or generate_stable_id(
                "dealaudit",
                event.business_id,
                event.environment,
                event.deal_id,
                event.event_type.value,
                event.created_at.isoformat(),
            )
            metadata = {**event.metadata, "dedupe_key": resolved_key} if resolved_key is not None else event.metadata
            created = event.model_copy(update={"id": event_id, "metadata": metadata})
            store.deal_audit_events[event_id] = created
            if lookup_key is not None:
                store.deal_audit_event_keys[lookup_key] = event_id
            return created

    def list_audit_events(self, deal_id: str) -> list[DealAuditEvent]:
        with self.client.transaction() as store:
            records = [event for event in store.deal_audit_events.values() if event.deal_id == deal_id]
        records.sort(key=lambda event: (event.created_at, event.id or ""))
        return records

    def add_stage_event(self, event: DealStageEvent, *, dedupe_key: str | None = None) -> DealStageEvent:
        event_id = event.id or generate_stable_id(
            "dealstage",
            event.business_id,
            event.environment,
            event.deal_id,
            event.to_stage.value,
            dedupe_key or event.created_at.isoformat(),
        )
        created = event.model_copy(update={"id": event_id})
        with self.client.transaction() as store:
            if event_id not in store.deal_stage_events:
                store.deal_stage_events[event_id] = created
            return store.deal_stage_events[event_id]

    def list_stage_events(self, deal_id: str) -> list[DealStageEvent]:
        with self.client.transaction() as store:
            records = [event for event in store.deal_stage_events.values() if event.deal_id == deal_id]
        records.sort(key=lambda event: (event.created_at, event.id or ""))
        return records

    def upsert_risk_flag(self, flag: DealRiskFlag, *, dedupe_key: str | None = None) -> DealRiskFlag:
        now = utc_now()
        resolved_key = dedupe_key or flag.identity_key()
        lookup_key = (flag.business_id, flag.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.deal_risk_flag_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.deal_risk_flags[existing_id]
                updates = flag.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.deal_risk_flags[existing_id] = updated
                return updated
            flag_id = flag.id or generate_stable_id("dealrisk", flag.business_id, flag.environment, resolved_key)
            created = flag.model_copy(update={"id": flag_id, "updated_at": now})
            store.deal_risk_flags[flag_id] = created
            store.deal_risk_flag_keys[lookup_key] = flag_id
            return created

    def list_risk_flags(self, deal_id: str, active: bool | None = None) -> list[DealRiskFlag]:
        with self.client.transaction() as store:
            records = [flag for flag in store.deal_risk_flags.values() if flag.deal_id == deal_id]
        if active is not None:
            records = [flag for flag in records if flag.active is active]
        records.sort(key=lambda flag: (flag.severity.value, flag.code, flag.id or ""))
        return records

    def get_detail(self, deal_id: str) -> DealDetail | None:
        deal = self.get_deal(deal_id)
        if deal is None:
            return None
        return DealDetail(
            deal=deal,
            parties=self.list_parties(deal_id),
            tasks=self.list_tasks(deal_id),
            document_requirements=self.list_document_requirements(deal_id),
            risk_flags=self.list_risk_flags(deal_id),
            stage_events=self.list_stage_events(deal_id),
            audit_events=self.list_audit_events(deal_id),
        )
