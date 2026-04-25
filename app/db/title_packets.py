from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_stable_id
from app.models.title_packets import TitlePacketRecord, TitlePacketStatus


class TitlePacketsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def upsert(self, record: TitlePacketRecord, *, dedupe_key: str | None = None) -> TitlePacketRecord:
        now = utc_now()
        resolved_key = dedupe_key or record.identity_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.title_packet_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.title_packets[existing_id]
                updates = record.model_dump(exclude={"id", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.title_packets[existing_id] = updated
                return updated

            packet_id = record.id or generate_stable_id("tpkt", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": packet_id, "updated_at": now})
            store.title_packets[packet_id] = created
            store.title_packet_keys[lookup_key] = packet_id
            return created

    def get(self, packet_id: str) -> TitlePacketRecord | None:
        with self.client.transaction() as store:
            return store.title_packets.get(packet_id)

    def get_by_key(self, *, business_id: str, environment: str, dedupe_key: str) -> TitlePacketRecord | None:
        with self.client.transaction() as store:
            packet_id = store.title_packet_keys.get((business_id, environment, dedupe_key))
            if packet_id is None:
                return None
            return store.title_packets.get(packet_id)

    def list(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        lead_id: str | None = None,
        status: TitlePacketStatus | None = None,
    ) -> list[TitlePacketRecord]:
        with self.client.transaction() as store:
            records = list(store.title_packets.values())
        if business_id is not None:
            records = [record for record in records if record.business_id == business_id]
        if environment is not None:
            records = [record for record in records if record.environment == environment]
        if lead_id is not None:
            records = [record for record in records if record.lead_id == lead_id]
        if status is not None:
            records = [record for record in records if record.status == status]
        records.sort(key=lambda record: (record.business_id, record.environment, record.created_at, record.id or ""))
        return records
