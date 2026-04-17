from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.marketing_supabase import (
    fetch_rows,
    insert_rows,
    marketing_backend_enabled,
    patch_rows,
    resolve_tenant,
)
from app.models.marketing_leads import LeadUpsertRequest, MarketingLeadRecord


class ContactsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def upsert_lead(self, request: LeadUpsertRequest) -> MarketingLeadRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_lead_in_supabase(request)
        with self.client.transaction() as store:
            contact_rows: dict[str, MarketingLeadRecord] = getattr(
                store, "marketing_contact_rows", {}
            )
            contact_keys: dict[tuple[str, str, str], str] = getattr(
                store, "marketing_contact_keys", {}
            )
            setattr(store, "marketing_contact_rows", contact_rows)
            setattr(store, "marketing_contact_keys", contact_keys)

            dedupe_key = (request.business_id, request.environment, request.phone)
            existing_id = contact_keys.get(dedupe_key)
            if existing_id is not None:
                updated = contact_rows[existing_id].model_copy(
                    update={
                        "first_name": request.first_name,
                        "email": request.email,
                        "property_address": request.property_address,
                        "booking_status": request.booking_status,
                        "updated_at": utc_now(),
                    }
                )
                contact_rows[existing_id] = updated
                return updated

            record = MarketingLeadRecord(
                business_id=request.business_id,
                environment=request.environment,
                first_name=request.first_name,
                phone=request.phone,
                email=request.email,
                property_address=request.property_address,
                booking_status=request.booking_status,
            )
            contact_rows[record.id] = record
            contact_keys[dedupe_key] = record.id
            return record

    def get_lead(self, lead_id: str) -> MarketingLeadRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._get_lead_in_supabase(lead_id)
        with self.client.transaction() as store:
            contact_rows: dict[str, MarketingLeadRecord] = getattr(
                store, "marketing_contact_rows", {}
            )
            return contact_rows.get(lead_id)

    def find_by_phone(
        self,
        *,
        phone: str,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MarketingLeadRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._find_by_phone_in_supabase(
                phone=phone,
                business_id=business_id,
                environment=environment,
            )
        with self.client.transaction() as store:
            contact_rows: dict[str, MarketingLeadRecord] = getattr(
                store, "marketing_contact_rows", {}
            )
            for record in contact_rows.values():
                if record.phone == phone:
                    if business_id is not None and record.business_id != business_id:
                        continue
                    if environment is not None and record.environment != environment:
                        continue
                    return record
            return None

    def update_booking_status(self, lead_id: str, booking_status: str) -> MarketingLeadRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._update_booking_status_in_supabase(lead_id, booking_status)
        with self.client.transaction() as store:
            contact_rows: dict[str, MarketingLeadRecord] = getattr(
                store, "marketing_contact_rows", {}
            )
            existing = contact_rows.get(lead_id)
            if existing is None:
                return None
            updated = existing.model_copy(
                update={
                    "booking_status": booking_status,
                    "updated_at": utc_now(),
                }
            )
            contact_rows[lead_id] = updated
            return updated

    def _upsert_lead_in_supabase(self, request: LeadUpsertRequest) -> MarketingLeadRecord:
        tenant = resolve_tenant(request.business_id, request.environment, settings=self.settings)
        existing_rows = fetch_rows(
            "contacts",
            params={
                "select": "id,external_contact_id,name,email,phone,metadata,created_at,updated_at",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "phone": f"eq.{request.phone}",
                "limit": "1",
            },
            settings=self.settings,
        )
        payload = {
            "business_id": tenant.business_pk,
            "environment": tenant.environment,
            "name": request.first_name,
            "email": request.email,
            "phone": request.phone,
            "channel": "sms",
            "metadata": {
                "property_address": request.property_address,
                "booking_status": request.booking_status,
            },
        }
        if existing_rows:
            row = existing_rows[0]
            updated = patch_rows(
                "contacts",
                params={"id": f"eq.{row['id']}"},
                row=payload,
                select="id,external_contact_id,name,email,phone,metadata,created_at,updated_at",
                settings=self.settings,
            )[0]
            external_id = updated.get("external_contact_id") or f"ctc_{updated['id']}"
            if not updated.get("external_contact_id"):
                updated = patch_rows(
                    "contacts",
                    params={"id": f"eq.{updated['id']}"},
                    row={"external_contact_id": external_id},
                    select="id,external_contact_id,name,email,phone,metadata,created_at,updated_at",
                    settings=self.settings,
                )[0]
            return self._record_from_supabase(updated, request.business_id, request.environment)

        inserted = insert_rows(
            "contacts",
            [
                {
                    **payload,
                    "external_contact_id": "pending",
                }
            ],
            select="id,external_contact_id,name,email,phone,metadata,created_at,updated_at",
            settings=self.settings,
        )[0]
        external_id = f"ctc_{inserted['id']}"
        inserted = patch_rows(
            "contacts",
            params={"id": f"eq.{inserted['id']}"},
            row={"external_contact_id": external_id},
            select="id,external_contact_id,name,email,phone,metadata,created_at,updated_at",
            settings=self.settings,
        )[0]
        return self._record_from_supabase(inserted, request.business_id, request.environment)

    def _get_lead_in_supabase(self, lead_id: str) -> MarketingLeadRecord | None:
        rows = fetch_rows(
            "contacts",
            params={
                "select": "id,external_contact_id,name,email,phone,metadata,business_id,environment,created_at,updated_at",
                "external_contact_id": f"eq.{lead_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        return self._record_from_supabase(row, str(row["business_id"]), str(row["environment"]))

    def _find_by_phone_in_supabase(
        self,
        *,
        phone: str,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> MarketingLeadRecord | None:
        params = {
            "select": "id,external_contact_id,name,email,phone,metadata,business_id,environment,created_at,updated_at",
            "phone": f"eq.{phone}",
            "limit": "1",
        }
        if business_id is not None and environment is not None:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            params["business_id"] = f"eq.{tenant.business_pk}"
            params["environment"] = f"eq.{tenant.environment}"
        rows = fetch_rows(
            "contacts",
            params=params,
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        return self._record_from_supabase(row, str(row["business_id"]), str(row["environment"]))

    def _update_booking_status_in_supabase(self, lead_id: str, booking_status: str) -> MarketingLeadRecord | None:
        lead = self._get_lead_in_supabase(lead_id)
        if lead is None:
            return None
        tenant = resolve_tenant(lead.business_id, lead.environment, settings=self.settings)
        rows = fetch_rows(
            "contacts",
            params={
                "select": "id,external_contact_id,name,email,phone,metadata,created_at,updated_at",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "external_contact_id": f"eq.{lead_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        metadata = dict(row.get("metadata") or {})
        metadata["booking_status"] = booking_status
        updated = patch_rows(
            "contacts",
            params={"id": f"eq.{row['id']}"},
            row={"metadata": metadata},
            select="id,external_contact_id,name,email,phone,metadata,created_at,updated_at",
            settings=self.settings,
        )[0]
        return self._record_from_supabase(updated, lead.business_id, lead.environment)

    @staticmethod
    def _record_from_supabase(row: dict, business_id: str, environment: str) -> MarketingLeadRecord:
        metadata = dict(row.get("metadata") or {})
        return MarketingLeadRecord(
            id=str(row.get("external_contact_id") or f"ctc_{row['id']}"),
            business_id=business_id,
            environment=environment,
            first_name=str(row.get("name") or ""),
            phone=str(row.get("phone") or ""),
            email=row.get("email"),
            property_address=str(metadata.get("property_address") or ""),
            booking_status=str(metadata.get("booking_status") or "pending"),
            created_at=row.get("created_at") or utc_now(),
            updated_at=row.get("updated_at") or utc_now(),
        )
