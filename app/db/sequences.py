from __future__ import annotations

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.db.marketing_supabase import fetch_rows, insert_rows, marketing_backend_enabled, patch_rows, resolve_tenant
from app.models.sequences import SequenceEnrollmentRecord, SequenceEnrollmentStatus


class SequencesRepository:
    def __init__(self, client: ControlPlaneClient | None = None, settings: Settings | None = None):
        self.client = client or get_control_plane_client()
        self._force_memory = client is not None
        self.settings = settings or get_settings()

    def create(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        sequence_key: str,
    ) -> SequenceEnrollmentRecord:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._create_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                sequence_key=sequence_key,
            )
        with self.client.transaction() as store:
            enrollment_rows: dict[str, SequenceEnrollmentRecord] = getattr(
                store, "marketing_sequence_rows", {}
            )
            enrollment_keys: dict[tuple[str, str, str, str], str] = getattr(
                store, "marketing_sequence_keys", {}
            )
            setattr(store, "marketing_sequence_rows", enrollment_rows)
            setattr(store, "marketing_sequence_keys", enrollment_keys)

            dedupe_key = (business_id, environment, contact_id, sequence_key)
            existing_id = enrollment_keys.get(dedupe_key)
            if existing_id is not None:
                return enrollment_rows[existing_id]

            record = SequenceEnrollmentRecord(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                sequence_key=sequence_key,
                status=SequenceEnrollmentStatus.ACTIVE,
            )
            enrollment_rows[record.id] = record
            enrollment_keys[dedupe_key] = record.id
            return record

    def find_active(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        sequence_key: str,
    ) -> SequenceEnrollmentRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._find_active_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                sequence_key=sequence_key,
            )
        with self.client.transaction() as store:
            enrollment_keys: dict[tuple[str, str, str, str], str] = getattr(
                store, "marketing_sequence_keys", {}
            )
            enrollment_rows: dict[str, SequenceEnrollmentRecord] = getattr(
                store, "marketing_sequence_rows", {}
            )
            enrollment_id = enrollment_keys.get((business_id, environment, contact_id, sequence_key))
            if enrollment_id is None:
                return None
            record = enrollment_rows.get(enrollment_id)
            if record is None or record.status != SequenceEnrollmentStatus.ACTIVE:
                return None
            return record

    def find_latest(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        sequence_key: str,
    ) -> SequenceEnrollmentRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._find_latest_in_supabase(
                business_id=business_id,
                environment=environment,
                contact_id=contact_id,
                sequence_key=sequence_key,
            )
        with self.client.transaction() as store:
            enrollment_rows: dict[str, SequenceEnrollmentRecord] = getattr(
                store, "marketing_sequence_rows", {}
            )
            matches = [
                record
                for record in enrollment_rows.values()
                if record.business_id == business_id
                and record.environment == environment
                and record.contact_id == contact_id
                and record.sequence_key == sequence_key
            ]
            if not matches:
                return None
            matches.sort(key=lambda record: (record.updated_at, record.created_at, record.id))
            return matches[-1]

    def pause(
        self,
        enrollment_id: str,
        *,
        business_id: str,
        environment: str,
    ) -> SequenceEnrollmentRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._update_status_in_supabase(
                enrollment_id,
                business_id=business_id,
                environment=environment,
                status=SequenceEnrollmentStatus.PAUSED,
            )
        return self._update_status(
            enrollment_id,
            business_id=business_id,
            environment=environment,
            status=SequenceEnrollmentStatus.PAUSED,
        )

    def complete(
        self,
        enrollment_id: str,
        *,
        business_id: str,
        environment: str,
    ) -> SequenceEnrollmentRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._update_status_in_supabase(
                enrollment_id,
                business_id=business_id,
                environment=environment,
                status=SequenceEnrollmentStatus.COMPLETED,
            )
        return self._update_status(
            enrollment_id,
            business_id=business_id,
            environment=environment,
            status=SequenceEnrollmentStatus.COMPLETED,
        )

    def stop(
        self,
        enrollment_id: str,
        *,
        business_id: str,
        environment: str,
    ) -> SequenceEnrollmentRecord | None:
        if marketing_backend_enabled(self.settings) and not self._force_memory:
            return self._update_status_in_supabase(
                enrollment_id,
                business_id=business_id,
                environment=environment,
                status=SequenceEnrollmentStatus.STOPPED,
            )
        return self._update_status(
            enrollment_id,
            business_id=business_id,
            environment=environment,
            status=SequenceEnrollmentStatus.STOPPED,
        )

    def _update_status(
        self,
        enrollment_id: str,
        *,
        business_id: str,
        environment: str,
        status: SequenceEnrollmentStatus,
    ) -> SequenceEnrollmentRecord | None:
        with self.client.transaction() as store:
            enrollment_rows: dict[str, SequenceEnrollmentRecord] = getattr(
                store, "marketing_sequence_rows", {}
            )
            existing = enrollment_rows.get(enrollment_id)
            if existing is None:
                return None
            if existing.business_id != business_id or existing.environment != environment:
                return None

            updated = existing.model_copy(update={"status": status, "updated_at": utc_now()})
            enrollment_rows[enrollment_id] = updated
            return updated

    def _create_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        sequence_key: str,
    ) -> SequenceEnrollmentRecord:
        existing = self._find_active_in_supabase(
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            sequence_key=sequence_key,
        )
        if existing is not None:
            return existing
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
        row = insert_rows(
            "sequence_enrollments",
            [
                {
                    "business_id": tenant.business_pk,
                    "environment": tenant.environment,
                    "contact_id": contact_pk,
                    "sequence_key": sequence_key,
                    "status": "active",
                }
            ],
            select="id,status,created_at,updated_at",
            settings=self.settings,
        )[0]
        return SequenceEnrollmentRecord(
            id=f"seq_{row['id']}",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            sequence_key=sequence_key,
            status=SequenceEnrollmentStatus.ACTIVE,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _find_active_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        sequence_key: str,
    ) -> SequenceEnrollmentRecord | None:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        contact_rows = fetch_rows(
            "contacts",
            params={
                "select": "id",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "external_contact_id": f"eq.{contact_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not contact_rows:
            return None
        rows = fetch_rows(
            "sequence_enrollments",
            params={
                "select": "id,status,created_at,updated_at",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "contact_id": f"eq.{contact_rows[0]['id']}",
                "sequence_key": f"eq.{sequence_key}",
                "status": "eq.active",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        return SequenceEnrollmentRecord(
            id=f"seq_{row['id']}",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            sequence_key=sequence_key,
            status=SequenceEnrollmentStatus(str(row["status"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _find_latest_in_supabase(
        self,
        *,
        business_id: str,
        environment: str,
        contact_id: str,
        sequence_key: str,
    ) -> SequenceEnrollmentRecord | None:
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        contact_rows = fetch_rows(
            "contacts",
            params={
                "select": "id",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "external_contact_id": f"eq.{contact_id}",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not contact_rows:
            return None
        rows = fetch_rows(
            "sequence_enrollments",
            params={
                "select": "id,status,created_at,updated_at",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "contact_id": f"eq.{contact_rows[0]['id']}",
                "sequence_key": f"eq.{sequence_key}",
                "order": "updated_at.desc,created_at.desc,id.desc",
                "limit": "1",
            },
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        return SequenceEnrollmentRecord(
            id=f"seq_{row['id']}",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            sequence_key=sequence_key,
            status=SequenceEnrollmentStatus(str(row["status"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _update_status_in_supabase(
        self,
        enrollment_id: str,
        *,
        business_id: str,
        environment: str,
        status: SequenceEnrollmentStatus,
    ) -> SequenceEnrollmentRecord | None:
        numeric_id = enrollment_id.removeprefix("seq_")
        tenant = resolve_tenant(business_id, environment, settings=self.settings)
        rows = patch_rows(
            "sequence_enrollments",
            params={
                "id": f"eq.{numeric_id}",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
            },
            row={"status": status.value},
            select="id,status,created_at,updated_at,sequence_key,contact_id",
            settings=self.settings,
        )
        if not rows:
            return None
        row = rows[0]
        contact_id = str(row.get("contact_id") or "")
        if contact_id:
            contact_rows = fetch_rows(
                "contacts",
                params={
                    "select": "external_contact_id",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "id": f"eq.{contact_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            if contact_rows:
                contact_id = str(contact_rows[0].get("external_contact_id") or f"ctc_{contact_id}")
            else:
                contact_id = f"ctc_{contact_id}"
        return SequenceEnrollmentRecord(
            id=f"seq_{row['id']}",
            business_id=business_id,
            environment=environment,
            contact_id=contact_id,
            sequence_key=str(row.get("sequence_key") or ""),
            status=SequenceEnrollmentStatus(str(row["status"])),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
