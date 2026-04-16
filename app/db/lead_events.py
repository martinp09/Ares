from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client
from app.models.commands import generate_stable_id
from app.models.lead_events import LeadEventRecord


class LeadEventsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def append(self, record: LeadEventRecord, *, replay_key: str | None = None) -> LeadEventRecord:
        resolved_key = replay_key or record.replay_key()
        lookup_key = (record.business_id, record.environment, resolved_key)
        with self.client.transaction() as store:
            existing_id = store.lead_event_keys.get(lookup_key)
            if existing_id is not None:
                existing = store.lead_events[existing_id]
                return existing.model_copy(update={"deduped": True})

            event_id = record.id or generate_stable_id("levt", record.business_id, record.environment, resolved_key)
            created = record.model_copy(update={"id": event_id})
            store.lead_events[event_id] = created
            store.lead_event_keys[lookup_key] = event_id
            store.lead_event_ids_by_lead.setdefault(record.lead_id, []).append(event_id)
            return created

    def get(self, event_id: str) -> LeadEventRecord | None:
        with self.client.transaction() as store:
            return store.lead_events.get(event_id)

    def list_for_lead(self, lead_id: str) -> list[LeadEventRecord]:
        with self.client.transaction() as store:
            event_ids = list(store.lead_event_ids_by_lead.get(lead_id, []))
            events = [store.lead_events[event_id] for event_id in event_ids]
        events.sort(key=lambda record: (record.event_timestamp, record.received_at, record.id or ""))
        return events
