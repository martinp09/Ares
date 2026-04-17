from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, resolve_tenant
from app.models.bookings import BookingEventRecord, BookingEventType


class BookingsRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def append_event(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        conversation_id: str | None,
        event_type: BookingEventType,
        provider: str,
        external_booking_id: str | None = None,
        metadata: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> BookingEventRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._append_event_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                conversation_id=conversation_id,
                event_type=event_type,
                provider=provider,
                external_booking_id=external_booking_id,
                metadata=metadata,
                idempotency_key=idempotency_key,
            )
        with self.client.transaction() as store:
            booking_rows: dict[str, BookingEventRecord] = getattr(
                store, "marketing_booking_rows", {}
            )
            booking_keys: dict[tuple[str, str, str, str], str] = getattr(
                store, "marketing_booking_keys", {}
            )
            setattr(store, "marketing_booking_rows", booking_rows)
            setattr(store, "marketing_booking_keys", booking_keys)

            replay_key = idempotency_key or (
                f"{provider}:{event_type}:{external_booking_id}" if external_booking_id else None
            )
            if replay_key is not None:
                dedupe_key = (business_id, environment, provider, replay_key)
                existing_id = booking_keys.get(dedupe_key)
                if existing_id is not None:
                    return booking_rows[existing_id]

            record = BookingEventRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                conversation_id=conversation_id,
                event_type=event_type,
                provider=provider,
                external_booking_id=external_booking_id,
                metadata=metadata or {},
            )
            booking_rows[record.id] = record
            if replay_key is not None:
                booking_keys[dedupe_key] = record.id
        return record

    def _append_event_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        conversation_id: str | None,
        event_type: BookingEventType,
        provider: str,
        external_booking_id: str | None = None,
        metadata: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> BookingEventRecord:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        contact_pk = int(
            fetch_rows(
                "contacts",
                params={
                    "select": "id",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "external_contact_id": f"eq.{contact_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )[0]["id"]
        )
        conversation_pk = None
        if conversation_id:
            rows = fetch_rows(
                "conversations",
                params={
                    "select": "id",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "external_conversation_id": f"eq.{conversation_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            conversation_pk = int(rows[0]["id"]) if rows else None
        if external_booking_id is not None:
            existing_rows = fetch_rows(
                "booking_events",
                params={
                    "select": "id,created_at",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "provider": f"eq.{provider}",
                    "event_type": f"eq.{event_type}",
                    "external_booking_id": f"eq.{external_booking_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            if existing_rows:
                row = existing_rows[0]
                return BookingEventRecord(
                    id=f"bkg_{row['id']}",
                    business_id=business_id,
                    environment=environment,
                    contact_id=contact_id,
                    conversation_id=conversation_id,
                    event_type=event_type,
                    provider=provider,
                    external_booking_id=external_booking_id,
                    metadata=metadata or {},
                    created_at=row["created_at"],
                )
        row = insert_rows(
            "booking_events",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "contact_id": contact_pk,
                    "conversation_id": conversation_pk,
                    "event_type": event_type,
                    "provider": provider,
                    "external_booking_id": external_booking_id,
                    "details": {
                        **(metadata or {}),
                        **({"idempotency_key": idempotency_key} if idempotency_key else {}),
                    },
                }
            ],
            select="id,created_at",
            settings=self.settings,
        )[0]
        return BookingEventRecord(
            id=f"bkg_{row['id']}",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            conversation_id=conversation_id,
            event_type=event_type,
            provider=provider,
            external_booking_id=external_booking_id,
            metadata=metadata or {},
            created_at=row["created_at"],
        )
