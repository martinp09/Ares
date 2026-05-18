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
from app.providers.textgrid import normalize_phone_number


_LANDING_CONTEXT_FIELDS = (
    "last_name",
    "property_type",
    "timeline_to_sell",
    "monthly_payment_goal",
    "asking_price_goal",
    "seller_goal",
    "notes",
    "sms_consent",
    "consent_page_url",
    "consent_ip",
    "consent_user_agent",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "lp_var",
)


class ContactsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = client or get_control_plane_client(self.settings)
        self._force_memory = client is not None and getattr(client, "backend", "memory") != "supabase"

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
                        "last_name": request.last_name,
                        "property_type": request.property_type,
                        "timeline_to_sell": request.timeline_to_sell,
                        "monthly_payment_goal": request.monthly_payment_goal,
                        "asking_price_goal": request.asking_price_goal,
                        "seller_goal": request.seller_goal,
                        "notes": request.notes,
                        "sms_consent": request.sms_consent,
                        "consent_page_url": request.consent_page_url,
                        "consent_ip": request.consent_ip,
                        "consent_user_agent": request.consent_user_agent,
                        "utm_source": request.utm_source,
                        "utm_medium": request.utm_medium,
                        "utm_campaign": request.utm_campaign,
                        "utm_term": request.utm_term,
                        "utm_content": request.utm_content,
                        "lp_var": request.lp_var,
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
                last_name=request.last_name,
                property_type=request.property_type,
                timeline_to_sell=request.timeline_to_sell,
                monthly_payment_goal=request.monthly_payment_goal,
                asking_price_goal=request.asking_price_goal,
                seller_goal=request.seller_goal,
                notes=request.notes,
                sms_consent=request.sms_consent,
                consent_page_url=request.consent_page_url,
                consent_ip=request.consent_ip,
                consent_user_agent=request.consent_user_agent,
                utm_source=request.utm_source,
                utm_medium=request.utm_medium,
                utm_campaign=request.utm_campaign,
                utm_term=request.utm_term,
                utm_content=request.utm_content,
                lp_var=request.lp_var,
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
        matches = self.find_all_by_phone(
            phone=phone,
            business_id=business_id,
            environment=environment,
        )
        return matches[0] if matches else None

    def find_all_by_phone(
        self,
        *,
        phone: str,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[MarketingLeadRecord]:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._find_all_by_phone_in_supabase(
                phone=phone,
                business_id=business_id,
                environment=environment,
            )
        with self.client.transaction() as store:
            contact_rows: dict[str, MarketingLeadRecord] = getattr(
                store, "marketing_contact_rows", {}
            )
            lookup_variants = _phone_lookup_variants(phone)
            matches: list[MarketingLeadRecord] = []
            for record in contact_rows.values():
                if record.phone in lookup_variants or normalize_phone_number(record.phone) in lookup_variants:
                    if business_id is not None and record.business_id != business_id:
                        continue
                    if environment is not None and record.environment != environment:
                        continue
                    matches.append(record)
            return matches

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
            "metadata": self._metadata_from_request(request),
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

    def _find_all_by_phone_in_supabase(
        self,
        *,
        phone: str,
        business_id: str | None = None,
        environment: str | None = None,
    ) -> list[MarketingLeadRecord]:
        base_params = {
            "select": "id,external_contact_id,name,email,phone,metadata,business_id,environment,created_at,updated_at",
        }
        if business_id is not None and environment is not None:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            base_params["business_id"] = f"eq.{tenant.business_pk}"
            base_params["environment"] = f"eq.{tenant.environment}"
        rows_by_id: dict[str, dict] = {}
        for variant in _phone_lookup_variants(phone):
            rows = fetch_rows(
                "contacts",
                params={**base_params, "phone": f"eq.{variant}"},
                settings=self.settings,
            )
            for row in rows:
                rows_by_id[str(row["id"])] = row
        return [
            self._record_from_supabase(row, str(row["business_id"]), str(row["environment"]))
            for row in rows_by_id.values()
        ]

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
            last_name=metadata.get("last_name"),
            property_type=metadata.get("property_type"),
            timeline_to_sell=metadata.get("timeline_to_sell"),
            monthly_payment_goal=metadata.get("monthly_payment_goal"),
            asking_price_goal=metadata.get("asking_price_goal"),
            seller_goal=metadata.get("seller_goal"),
            notes=metadata.get("notes"),
            sms_consent=bool(metadata.get("sms_consent") or False),
            consent_page_url=metadata.get("consent_page_url"),
            consent_ip=metadata.get("consent_ip"),
            consent_user_agent=metadata.get("consent_user_agent"),
            utm_source=metadata.get("utm_source"),
            utm_medium=metadata.get("utm_medium"),
            utm_campaign=metadata.get("utm_campaign"),
            utm_term=metadata.get("utm_term"),
            utm_content=metadata.get("utm_content"),
            lp_var=metadata.get("lp_var"),
            created_at=row.get("created_at") or utc_now(),
            updated_at=row.get("updated_at") or utc_now(),
        )

    @staticmethod
    def _metadata_from_request(request: LeadUpsertRequest) -> dict:
        metadata = {
            "property_address": request.property_address,
            "booking_status": request.booking_status,
        }
        for field in _LANDING_CONTEXT_FIELDS:
            value = getattr(request, field)
            if value is not None:
                metadata[field] = value
        return metadata


def _phone_lookup_variants(phone: str) -> set[str]:
    raw = str(phone or "").strip()
    normalized = normalize_phone_number(raw)
    digits = "".join(ch for ch in raw if ch.isdigit())
    variants = {value for value in (raw, normalized, digits) if value}
    if normalized.startswith("+1") and len(normalized) == 12:
        national = normalized[2:]
        variants.add(national)
        variants.add(f"{national[:3]}-{national[3:6]}-{national[6:]}")
        variants.add(f"({national[:3]}) {national[3:6]}-{national[6:]}")
    if len(digits) == 11 and digits.startswith("1"):
        national = digits[1:]
        variants.add(national)
        variants.add(f"+{digits}")
        variants.add(f"{national[:3]}-{national[3:6]}-{national[6:]}")
    return variants
