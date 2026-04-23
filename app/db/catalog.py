from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.catalog import CatalogEntryRecord
from app.models.commands import generate_id


class CatalogRepository:
    def __init__(self, client: ControlPlaneClient | None = None) -> None:
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        org_id: str,
        agent_id: str,
        agent_revision_id: str,
        slug: str,
        name: str,
        summary: str,
        description: str | None,
        visibility,
        host_adapter_kind,
        provider_kind,
        provider_capabilities: list,
        required_skill_ids: list[str] | None = None,
        required_secret_names: list[str] | None = None,
        release_channel: str = "internal",
        metadata: dict[str, object] | None = None,
    ) -> CatalogEntryRecord:
        now = utc_now()
        normalized_slug = slug.strip().lower()
        with self.client.transaction() as store:
            key = (org_id, normalized_slug)
            if key in store.catalog_entry_keys:
                raise ValueError("Catalog entry slug already exists")
            entry = CatalogEntryRecord(
                id=generate_id("cat"),
                org_id=org_id,
                agent_id=agent_id,
                agent_revision_id=agent_revision_id,
                slug=slug,
                name=name,
                summary=summary,
                description=description,
                visibility=visibility,
                host_adapter_kind=host_adapter_kind,
                provider_kind=provider_kind,
                provider_capabilities=list(provider_capabilities),
                required_skill_ids=list(required_skill_ids or []),
                required_secret_names=list(required_secret_names or []),
                release_channel=release_channel,
                metadata=dict(metadata or {}),
                created_at=now,
                updated_at=now,
            )
            store.catalog_entries[entry.id] = entry
            store.catalog_entry_keys[key] = entry.id
            store.catalog_entry_ids_by_org.setdefault(org_id, []).append(entry.id)
            return entry

    def get(self, entry_id: str) -> CatalogEntryRecord | None:
        with self.client.transaction() as store:
            entry = store.catalog_entries.get(entry_id)
            return entry if entry is None else CatalogEntryRecord.model_validate(entry)

    def list(self, *, org_id: str | None = None) -> list[CatalogEntryRecord]:
        with self.client.transaction() as store:
            if org_id is None:
                entries = list(store.catalog_entries.values())
            else:
                entry_ids = store.catalog_entry_ids_by_org.get(org_id, [])
                entries = [store.catalog_entries[entry_id] for entry_id in entry_ids]
        return sorted(entries, key=lambda entry: (entry.name.casefold(), entry.created_at, entry.id))
