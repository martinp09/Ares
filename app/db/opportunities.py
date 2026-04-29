from __future__ import annotations

from typing import Any

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.lead_machine_supabase import (
    external_id,
    fetch_rows,
    insert_rows,
    lead_machine_backend_enabled,
    patch_rows,
    resolve_tenant,
    row_id_from_external_id,
)
from app.models.commands import generate_stable_id
from app.models.opportunities import (
    OpportunityPipelineConfig,
    OpportunityRecord,
    OpportunityStageHistoryRecord,
)


class OpportunitiesRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = False
        self.settings = settings or get_settings()

    def upsert(self, record: OpportunityRecord, *, dedupe_key: str | None = None) -> OpportunityRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_in_supabase(record)

        now = utc_now()
        resolved_key = dedupe_key or f"{record.source_lane}:{record.identity_key()}"
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            rows: dict[str, OpportunityRecord] = getattr(store, "opportunity_rows", {})
            keys: dict[tuple[str, str, str], str] = getattr(store, "opportunity_keys", {})
            setattr(store, "opportunity_rows", rows)
            setattr(store, "opportunity_keys", keys)

            existing_id = keys.get(lookup_key)
            if existing_id is not None:
                existing = rows[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                rows[existing_id] = updated
                return updated

            opportunity_id = record.id or generate_stable_id("opp", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": opportunity_id, "updated_at": now})
            rows[opportunity_id] = created
            keys[lookup_key] = opportunity_id
            return created

    def get(self, opportunity_id: str) -> OpportunityRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(opportunity_id, "opp")
            if row_id is None:
                return None
            rows = fetch_rows("opportunities", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None

        with self.client.transaction() as store:
            rows: dict[str, OpportunityRecord] = getattr(store, "opportunity_rows", {})
            return rows.get(opportunity_id)

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[OpportunityRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params: dict[str, str] = {"select": "*", "order": "created_at.asc"}
            if business_id is not None:
                if business_id.isdigit():
                    params["business_id"] = f"eq.{business_id}"
                else:
                    if environment is None:
                        raise ValueError("environment is required when business_id is not numeric")
                    tenant = resolve_tenant(business_id, environment, settings=self.settings)
                    params["business_id"] = f"eq.{tenant.business_pk}"
                    params["environment"] = f"eq.{tenant.environment}"
            elif environment is not None:
                params["environment"] = f"eq.{environment}"
            return [self._record_from_supabase(row) for row in fetch_rows("opportunities", params=params, settings=self.settings)]

        with self.client.transaction() as store:
            rows: dict[str, OpportunityRecord] = getattr(store, "opportunity_rows", {})
            records = list(rows.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records

    def upsert_pipeline_config(self, config: OpportunityPipelineConfig) -> OpportunityPipelineConfig:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_pipeline_config_in_supabase(config)
        now = utc_now()
        lookup_key = (config.business_id, config.environment, config.identity_key())
        with self.client.transaction() as store:
            rows: dict[str, OpportunityPipelineConfig] = getattr(store, "opportunity_pipeline_configs", {})
            keys: dict[tuple[str, str, str], str] = getattr(store, "opportunity_pipeline_config_keys", {})
            setattr(store, "opportunity_pipeline_configs", rows)
            setattr(store, "opportunity_pipeline_config_keys", keys)
            existing_id = keys.get(lookup_key)
            if existing_id is not None:
                existing = rows[existing_id]
                updates = config.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                rows[existing_id] = updated
                return updated
            config_id = config.id or generate_stable_id("opppipe", config.business_id, config.environment, config.identity_key())
            created = config.model_copy(update={"id": config_id, "updated_at": now})
            rows[config_id] = created
            keys[lookup_key] = config_id
            return created

    def get_active_pipeline_config(
        self,
        *,
        business_id: str,
        environment: str,
        source_lane: str,
    ) -> OpportunityPipelineConfig | None:
        configs = self.list_pipeline_configs(business_id=business_id, environment=environment)
        for config in configs:
            if config.source_lane.value == source_lane and config.is_active:
                return config
        return None

    def list_pipeline_configs(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[OpportunityPipelineConfig]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._list_pipeline_configs_in_supabase(business_id=business_id, environment=environment)
        with self.client.transaction() as store:
            rows: dict[str, OpportunityPipelineConfig] = getattr(store, "opportunity_pipeline_configs", {})
            configs = list(rows.values())
        if business_id is not None:
            configs = [config for config in configs if config.business_id == business_id]
        if environment is not None:
            configs = [config for config in configs if config.environment == environment]
        configs.sort(key=lambda config: (config.business_id, config.environment, config.source_lane.value))
        return configs

    def append_stage_history(self, event: OpportunityStageHistoryRecord) -> OpportunityStageHistoryRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._insert_stage_history_in_supabase(event)
        event_id = event.id or generate_stable_id(
            "opphist",
            event.business_id,
            event.environment,
            event.opportunity_id,
            event.to_stage.value,
            event.created_at.isoformat(),
        )
        created = event.model_copy(update={"id": event_id})
        with self.client.transaction() as store:
            rows: dict[str, OpportunityStageHistoryRecord] = getattr(store, "opportunity_stage_history", {})
            setattr(store, "opportunity_stage_history", rows)
            rows[event_id] = created
        return created

    def list_stage_history(self, opportunity_id: str) -> list[OpportunityStageHistoryRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(opportunity_id, "opp")
            if row_id is None:
                return []
            rows = fetch_rows(
                "opportunity_stage_history",
                params={"select": "*", "opportunity_id": f"eq.{row_id}", "order": "created_at.asc,id.asc"},
                settings=self.settings,
            )
            return [self._stage_history_from_supabase(row) for row in rows]
        with self.client.transaction() as store:
            rows: dict[str, OpportunityStageHistoryRecord] = getattr(store, "opportunity_stage_history", {})
            history = [event for event in rows.values() if event.opportunity_id == opportunity_id]
        history.sort(key=lambda event: (event.created_at, event.id or ""))
        return history

    def _upsert_in_supabase(self, record: OpportunityRecord) -> OpportunityRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        lead_row_id = row_id_from_external_id(record.lead_id, "lead")
        contact_row_id = row_id_from_external_id(record.contact_id, "ctc")
        payload = record.model_dump(
            mode="json",
            exclude={"id", "business_id", "environment", "created_at", "updated_at"},
        )
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["lead_id"] = lead_row_id
        payload["contact_id"] = contact_row_id

        params = {
            "select": "*",
            "business_id": f"eq.{tenant.business_pk}",
            "environment": f"eq.{tenant.environment}",
            "source_lane": f"eq.{record.source_lane}",
            "limit": "1",
        }
        if lead_row_id is not None:
            params["lead_id"] = f"eq.{lead_row_id}"
        elif contact_row_id is not None:
            params["contact_id"] = f"eq.{contact_row_id}"
        rows = fetch_rows("opportunities", params=params, settings=self.settings)
        if rows:
            row = patch_rows(
                "opportunities",
                params={"id": f"eq.{rows[0]['id']}"},
                row=payload,
                select="*",
                settings=self.settings,
            )[0]
            return self._record_from_supabase(row)

        row = insert_rows("opportunities", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    def _upsert_pipeline_config_in_supabase(self, config: OpportunityPipelineConfig) -> OpportunityPipelineConfig:
        tenant = resolve_tenant(config.business_id, config.environment, settings=self.settings)
        payload = config.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["source_lane"] = config.source_lane.value
        existing = fetch_rows(
            "opportunity_pipeline_configs",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "source_lane": f"eq.{config.source_lane.value}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            row = patch_rows(
                "opportunity_pipeline_configs",
                params={"id": f"eq.{existing[0]['id']}"},
                row=payload,
                select="*",
                settings=self.settings,
            )[0]
            return self._pipeline_config_from_supabase(row)
        row = insert_rows("opportunity_pipeline_configs", [payload], select="*", settings=self.settings)[0]
        return self._pipeline_config_from_supabase(row)

    def _list_pipeline_configs_in_supabase(
        self,
        *,
        business_id: str | None,
        environment: str | None,
    ) -> list[OpportunityPipelineConfig]:
        params: dict[str, str] = {"select": "*", "order": "source_lane.asc"}
        if business_id is not None and environment is not None:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            params["business_id"] = f"eq.{tenant.business_pk}"
            params["environment"] = f"eq.{tenant.environment}"
        elif business_id is not None and business_id.isdigit():
            params["business_id"] = f"eq.{business_id}"
            if environment is not None:
                params["environment"] = f"eq.{environment}"
        elif environment is not None:
            params["environment"] = f"eq.{environment}"
        return [self._pipeline_config_from_supabase(row) for row in fetch_rows("opportunity_pipeline_configs", params=params, settings=self.settings)]

    def _insert_stage_history_in_supabase(self, event: OpportunityStageHistoryRecord) -> OpportunityStageHistoryRecord:
        tenant = resolve_tenant(event.business_id, event.environment, settings=self.settings)
        payload = event.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["opportunity_id"] = row_id_from_external_id(event.opportunity_id, "opp")
        payload["from_stage"] = event.from_stage.value if event.from_stage is not None else None
        payload["to_stage"] = event.to_stage.value
        row = insert_rows("opportunity_stage_history", [payload], select="*", settings=self.settings)[0]
        return self._stage_history_from_supabase(row)

    @staticmethod
    def _record_from_supabase(row: dict[str, Any]) -> OpportunityRecord:
        payload = dict(row)
        payload["id"] = external_id("opp", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("lead_id") is not None:
            payload["lead_id"] = external_id("lead", row["lead_id"])
        if row.get("contact_id") is not None:
            payload["contact_id"] = external_id("ctc", row["contact_id"])
        return OpportunityRecord.model_validate(payload)

    @staticmethod
    def _pipeline_config_from_supabase(row: dict[str, Any]) -> OpportunityPipelineConfig:
        payload = dict(row)
        payload["id"] = external_id("opppipe", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        return OpportunityPipelineConfig.model_validate(payload)

    @staticmethod
    def _stage_history_from_supabase(row: dict[str, Any]) -> OpportunityStageHistoryRecord:
        payload = dict(row)
        payload["id"] = external_id("opphist", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["opportunity_id"] = external_id("opp", row["opportunity_id"])
        return OpportunityStageHistoryRecord.model_validate(payload)
