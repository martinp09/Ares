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
from app.models.crm_records import (
    CrmRecord,
    CrmRecordPromotion,
    CrmRecordSavedView,
    CrmRecordSourceMembership,
    CrmRecordStatus,
    CrmRecordStatusHistory,
    CrmSourceRecord,
)


class CrmRecordsRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        if force_memory is None:
            self._force_memory = client is not None and getattr(client, "backend", "memory") != "supabase"
        else:
            self._force_memory = force_memory

    def upsert_record(self, record: CrmRecord, *, dedupe_key: str | None = None) -> CrmRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_record_in_supabase(record, dedupe_key=dedupe_key)
        now = utc_now()
        resolved_key = dedupe_key or record.resolved_identity_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.crm_record_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.crm_records[existing_id]
                updates = record.model_dump(exclude={"id", "business_id", "environment", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "identity_key": resolved_key, "updated_at": now})
                store.crm_records[existing_id] = updated
                return updated
            record_id = record.id or generate_stable_id("crmrec", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": record_id, "identity_key": resolved_key, "updated_at": now})
            store.crm_records[record_id] = created
            store.crm_record_keys[lookup_key] = record_id
            return created

    def get_record(self, record_id: str) -> CrmRecord | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(record_id, "crmrec")
            if row_id is None:
                return None
            rows = fetch_rows("crm_records", params={"select": "*", "id": f"eq.{row_id}", "limit": "1"}, settings=self.settings)
            return self._record_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            return store.crm_records.get(record_id)

    def list_records(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        status: CrmRecordStatus | None = None,
    ) -> list[CrmRecord]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._list_records_in_supabase(business_id=business_id, environment=environment, status=status)
        with self.client.transaction() as store:
            records = list(store.crm_records.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        if status is not None:
            records = [record for record in records if record.status == status]
        records.sort(key=lambda record: (record.business_id, record.environment, record.updated_at, record.id or ""), reverse=True)
        return records

    def upsert_saved_view(self, saved_view: CrmRecordSavedView) -> CrmRecordSavedView:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_saved_view_in_supabase(saved_view)
        now = utc_now()
        lookup_key = (saved_view.business_id, saved_view.environment, saved_view.identity_key())
        with self.client.transaction() as store:
            existing_id = store.crm_record_saved_view_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.crm_record_saved_views[existing_id]
                updates = saved_view.model_dump(exclude={"id", "business_id", "environment", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.crm_record_saved_views[existing_id] = updated
                return updated
            saved_view_id = saved_view.id or generate_stable_id("crmvw", saved_view.business_id, saved_view.environment, saved_view.identity_key())
            created = saved_view.model_copy(update={"id": saved_view_id, "updated_at": now})
            store.crm_record_saved_views[saved_view_id] = created
            store.crm_record_saved_view_keys[lookup_key] = saved_view_id
            return created

    def list_saved_views(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[CrmRecordSavedView]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._list_saved_views_in_supabase(business_id=business_id, environment=environment)
        with self.client.transaction() as store:
            views = list(store.crm_record_saved_views.values())
        if business_id is not None:
            views = [view for view in views if view.business_id == business_id]
        if environment is not None:
            views = [view for view in views if view.environment == environment]
        views.sort(key=lambda view: (not view.is_default, view.name.casefold(), view.id or ""))
        return views

    def upsert_source_record(self, source_record: CrmSourceRecord, *, dedupe_key: str | None = None) -> CrmSourceRecord:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_source_record_in_supabase(source_record, dedupe_key=dedupe_key)
        now = utc_now()
        resolved_key = dedupe_key or source_record.identity_key()
        lookup_key = (source_record.business_id, source_record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.crm_source_record_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.crm_source_records[existing_id]
                updates = source_record.model_dump(exclude={"id", "business_id", "environment", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.crm_source_records[existing_id] = updated
                return updated
            source_id = source_record.id or generate_stable_id("crmsrc", source_record.business_id, source_record.environment, resolved_key)
            created = source_record.model_copy(update={"id": source_id, "updated_at": now})
            store.crm_source_records[source_id] = created
            store.crm_source_record_keys[lookup_key] = source_id
            return created

    def add_source_membership(self, membership: CrmRecordSourceMembership) -> CrmRecordSourceMembership:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._add_membership_in_supabase(membership)
        resolved_key = membership.identity_key()
        lookup_key = (membership.business_id, membership.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.crm_record_source_membership_keys.get(lookup_key)
            if existing_id is not None:
                return store.crm_record_source_memberships[existing_id]
            membership_id = membership.id or generate_stable_id("crmmbr", membership.business_id, membership.environment, resolved_key)
            created = membership.model_copy(update={"id": membership_id})
            store.crm_record_source_memberships[membership_id] = created
            store.crm_record_source_membership_keys[lookup_key] = membership_id
            return created

    def list_source_memberships(self, record_id: str) -> list[CrmRecordSourceMembership]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(record_id, "crmrec")
            if row_id is None:
                return []
            return [
                self._membership_from_supabase(row)
                for row in fetch_rows(
                    "crm_record_source_memberships",
                    params={"select": "*", "record_id": f"eq.{row_id}", "order": "created_at.asc,id.asc"},
                    settings=self.settings,
                )
            ]
        with self.client.transaction() as store:
            memberships = list(store.crm_record_source_memberships.values())
        return [membership for membership in memberships if membership.record_id == record_id]

    def append_status_history(self, event: CrmRecordStatusHistory) -> CrmRecordStatusHistory:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._insert_status_history_in_supabase(event)
        event_id = event.id or generate_stable_id(
            "crmst",
            event.business_id,
            event.environment,
            event.record_id,
            event.to_status.value,
            event.created_at.isoformat(),
        )
        created = event.model_copy(update={"id": event_id})
        with self.client.transaction() as store:
            store.crm_record_status_history[event_id] = created
        return created

    def update_record_status(
        self,
        record_id: str,
        *,
        status: CrmRecordStatus,
        actor_id: str | None = None,
        actor_type: str | None = None,
        reason: str | None = None,
    ) -> CrmRecord:
        current = self.get_record(record_id)
        if current is None:
            raise KeyError(f"CRM record {record_id} not found")
        updated = self.upsert_record(current.model_copy(update={"status": status, "last_activity_at": utc_now()}))
        self.append_status_history(
            CrmRecordStatusHistory(
                business_id=updated.business_id,
                environment=updated.environment,
                record_id=updated.id or record_id,
                from_status=current.status,
                to_status=status,
                actor_id=actor_id,
                actor_type=actor_type,
                reason=reason,
            )
        )
        return updated

    def promote_record(
        self,
        promotion: CrmRecordPromotion,
        *,
        actor_id: str | None = None,
        actor_type: str | None = None,
    ) -> CrmRecordPromotion:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            created = self._insert_promotion_in_supabase(promotion)
            self.update_record_status(
                promotion.record_id,
                status=CrmRecordStatus.PROMOTED,
                actor_id=actor_id,
                actor_type=actor_type,
                reason=promotion.reason,
            )
            return created
        promotion_key = (promotion.business_id, promotion.environment, promotion.record_id, promotion.opportunity_id)
        with self.client.transaction() as store:
            existing_id = store.crm_record_promotion_keys.get(promotion_key)
            if existing_id is not None:
                return store.crm_record_promotions[existing_id]
            promotion_id = promotion.id or generate_stable_id("crmpromo", *promotion_key)
            created = promotion.model_copy(update={"id": promotion_id})
            store.crm_record_promotions[promotion_id] = created
            store.crm_record_promotion_keys[promotion_key] = promotion_id
        self.update_record_status(
            promotion.record_id,
            status=CrmRecordStatus.PROMOTED,
            actor_id=actor_id,
            actor_type=actor_type,
            reason=promotion.reason,
        )
        return created

    def _upsert_record_in_supabase(self, record: CrmRecord, *, dedupe_key: str | None = None) -> CrmRecord:
        tenant = resolve_tenant(record.business_id, record.environment, settings=self.settings)
        resolved_key = dedupe_key or record.resolved_identity_key()
        existing = fetch_rows(
            "crm_records",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "identity_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        payload = self._record_payload_for_supabase(record, business_pk=tenant.business_pk, environment=tenant.environment)
        payload["identity_key"] = resolved_key
        if existing:
            row = patch_rows("crm_records", params={"id": f"eq.{existing[0]['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._record_from_supabase(row)
        provided_id = row_id_from_external_id(record.id, "crmrec")
        if provided_id is not None:
            payload["id"] = provided_id
        row = insert_rows("crm_records", [payload], select="*", settings=self.settings)[0]
        return self._record_from_supabase(row)

    def _upsert_saved_view_in_supabase(self, saved_view: CrmRecordSavedView) -> CrmRecordSavedView:
        tenant = resolve_tenant(saved_view.business_id, saved_view.environment, settings=self.settings)
        payload = saved_view.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        existing = fetch_rows(
            "crm_record_saved_views",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "slug": f"eq.{saved_view.slug}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            row = patch_rows("crm_record_saved_views", params={"id": f"eq.{existing[0]['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._saved_view_from_supabase(row)
        row = insert_rows("crm_record_saved_views", [payload], select="*", settings=self.settings)[0]
        return self._saved_view_from_supabase(row)

    def _list_saved_views_in_supabase(
        self,
        *,
        business_id: str | None,
        environment: str | None,
    ) -> list[CrmRecordSavedView]:
        params: dict[str, str] = {"select": "*", "order": "is_default.desc,name.asc"}
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
        return [self._saved_view_from_supabase(row) for row in fetch_rows("crm_record_saved_views", params=params, settings=self.settings)]

    def _list_records_in_supabase(
        self,
        *,
        business_id: str | None,
        environment: str | None,
        status: CrmRecordStatus | None,
    ) -> list[CrmRecord]:
        params = {"select": "*", "order": "updated_at.desc,id.desc"}
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
        if status is not None:
            params["status"] = f"eq.{status.value}"
        return [self._record_from_supabase(row) for row in fetch_rows("crm_records", params=params, settings=self.settings)]

    def _upsert_source_record_in_supabase(self, source_record: CrmSourceRecord, *, dedupe_key: str | None = None) -> CrmSourceRecord:
        tenant = resolve_tenant(source_record.business_id, source_record.environment, settings=self.settings)
        resolved_key = dedupe_key or source_record.identity_key()
        payload = source_record.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["identity_key"] = resolved_key
        existing = fetch_rows(
            "crm_source_records",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "identity_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            row = patch_rows("crm_source_records", params={"id": f"eq.{existing[0]['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._source_record_from_supabase(row)
        row = insert_rows("crm_source_records", [payload], select="*", settings=self.settings)[0]
        return self._source_record_from_supabase(row)

    def _add_membership_in_supabase(self, membership: CrmRecordSourceMembership) -> CrmRecordSourceMembership:
        tenant = resolve_tenant(membership.business_id, membership.environment, settings=self.settings)
        resolved_key = membership.identity_key()
        existing = fetch_rows(
            "crm_record_source_memberships",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "identity_key": f"eq.{resolved_key}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            return self._membership_from_supabase(existing[0])
        payload = membership.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["identity_key"] = resolved_key
        payload["record_id"] = row_id_from_external_id(membership.record_id, "crmrec")
        payload["source_record_id"] = row_id_from_external_id(membership.source_record_id, "crmsrc")
        row = insert_rows("crm_record_source_memberships", [payload], select="*", settings=self.settings)[0]
        return self._membership_from_supabase(row)

    def _insert_status_history_in_supabase(self, event: CrmRecordStatusHistory) -> CrmRecordStatusHistory:
        tenant = resolve_tenant(event.business_id, event.environment, settings=self.settings)
        payload = event.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["record_id"] = row_id_from_external_id(event.record_id, "crmrec")
        payload["from_status"] = event.from_status.value if event.from_status is not None else None
        payload["to_status"] = event.to_status.value
        row = insert_rows("crm_record_status_history", [payload], select="*", settings=self.settings)[0]
        return self._status_history_from_supabase(row)

    def _insert_promotion_in_supabase(self, promotion: CrmRecordPromotion) -> CrmRecordPromotion:
        tenant = resolve_tenant(promotion.business_id, promotion.environment, settings=self.settings)
        record_row_id = row_id_from_external_id(promotion.record_id, "crmrec")
        opportunity_row_id = row_id_from_external_id(promotion.opportunity_id, "opp")
        existing = fetch_rows(
            "crm_record_promotions",
            params={
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "record_id": f"eq.{record_row_id}",
                "opportunity_id": f"eq.{opportunity_row_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if existing:
            return self._promotion_from_supabase(existing[0])
        payload = promotion.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at"})
        payload["business_id"] = tenant.business_pk
        payload["environment"] = tenant.environment
        payload["record_id"] = record_row_id
        payload["opportunity_id"] = opportunity_row_id
        row = insert_rows("crm_record_promotions", [payload], select="*", settings=self.settings)[0]
        return self._promotion_from_supabase(row)

    @staticmethod
    def _record_payload_for_supabase(record: CrmRecord, *, business_pk: int, environment: str) -> dict[str, Any]:
        payload = record.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["record_type"] = record.record_type.value
        payload["status"] = record.status.value
        payload["source_record_ids"] = [row_id_from_external_id(source_id, "crmsrc") for source_id in record.source_record_ids]
        return payload

    @staticmethod
    def _record_from_supabase(row: dict[str, Any]) -> CrmRecord:
        allowed_fields = set(CrmRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("crmrec", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("record_type") is not None:
            payload["record_type"] = str(row["record_type"])
        if row.get("status") is not None:
            payload["status"] = str(row["status"])
        payload["source_record_ids"] = [external_id("crmsrc", source_id) for source_id in row.get("source_record_ids") or []]
        return CrmRecord.model_validate(payload)

    @staticmethod
    def _saved_view_from_supabase(row: dict[str, Any]) -> CrmRecordSavedView:
        allowed_fields = set(CrmRecordSavedView.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("crmvw", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        return CrmRecordSavedView.model_validate(payload)

    @staticmethod
    def _source_record_from_supabase(row: dict[str, Any]) -> CrmSourceRecord:
        allowed_fields = set(CrmSourceRecord.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("crmsrc", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        return CrmSourceRecord.model_validate(payload)

    @staticmethod
    def _membership_from_supabase(row: dict[str, Any]) -> CrmRecordSourceMembership:
        allowed_fields = set(CrmRecordSourceMembership.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("crmmbr", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["record_id"] = external_id("crmrec", row["record_id"])
        if row.get("source_record_id") is not None:
            payload["source_record_id"] = external_id("crmsrc", row["source_record_id"])
        return CrmRecordSourceMembership.model_validate(payload)

    @staticmethod
    def _status_history_from_supabase(row: dict[str, Any]) -> CrmRecordStatusHistory:
        allowed_fields = set(CrmRecordStatusHistory.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("crmst", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["record_id"] = external_id("crmrec", row["record_id"])
        return CrmRecordStatusHistory.model_validate(payload)

    @staticmethod
    def _promotion_from_supabase(row: dict[str, Any]) -> CrmRecordPromotion:
        allowed_fields = set(CrmRecordPromotion.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed_fields}
        payload["id"] = external_id("crmpromo", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        payload["record_id"] = external_id("crmrec", row["record_id"])
        payload["opportunity_id"] = external_id("opp", row["opportunity_id"])
        return CrmRecordPromotion.model_validate(payload)
