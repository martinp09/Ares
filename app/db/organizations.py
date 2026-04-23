from __future__ import annotations

from app.db.client import ControlPlaneClient, get_control_plane_client, utc_now
from app.models.commands import generate_id
from app.models.organizations import OrganizationRecord


class OrganizationsRepository:
    def __init__(self, client: ControlPlaneClient | None = None):
        self.client = client or get_control_plane_client()

    def create(
        self,
        *,
        id: str | None = None,
        name: str,
        slug: str | None = None,
        metadata: dict[str, object] | None = None,
        is_internal: bool = False,
    ) -> OrganizationRecord:
        now = utc_now()
        normalized_key = self._lookup_key(slug=slug, name=name)
        with self.client.transaction() as store:
            existing_id = None
            if id is not None:
                existing_id = id if id in store.organizations else None
            elif normalized_key is not None:
                existing_id = store.organization_keys.get(normalized_key)

            if existing_id is not None:
                existing = store.organizations[existing_id]
                resolved_slug = slug or existing.slug or self._default_slug(name)
                normalized_existing_slug = self._normalize_key(existing.slug) if existing.slug is not None else None
                normalized_resolved_slug = self._normalize_key(resolved_slug) if resolved_slug is not None else None
                slug_owner_id = (
                    store.organization_keys.get(normalized_resolved_slug)
                    if normalized_resolved_slug is not None
                    else None
                )
                if slug_owner_id is not None and slug_owner_id != existing_id:
                    raise ValueError("Organization slug already exists")
                updated = existing.model_copy(
                    update={
                        "name": name,
                        "slug": resolved_slug,
                        "metadata": dict(metadata or {}),
                        "is_internal": is_internal,
                        "updated_at": now,
                    }
                )
                store.organizations[existing_id] = updated
                if normalized_existing_slug is not None and normalized_existing_slug != normalized_resolved_slug:
                    store.organization_keys.pop(normalized_existing_slug, None)
                if normalized_resolved_slug is not None:
                    store.organization_keys[normalized_resolved_slug] = existing_id
                return updated

            org_id = id or generate_id("org")
            resolved_slug = slug or self._default_slug(name)
            normalized_resolved_slug = self._normalize_key(resolved_slug) if resolved_slug is not None else None
            slug_owner_id = (
                store.organization_keys.get(normalized_resolved_slug)
                if normalized_resolved_slug is not None
                else None
            )
            if slug_owner_id is not None and slug_owner_id != org_id:
                raise ValueError("Organization slug already exists")
            record = OrganizationRecord(
                id=org_id,
                name=name,
                slug=resolved_slug,
                metadata=dict(metadata or {}),
                is_internal=is_internal,
                created_at=now,
                updated_at=now,
            )
            store.organizations[org_id] = record
            if normalized_resolved_slug is not None:
                store.organization_keys[normalized_resolved_slug] = org_id
            return record

    def get(self, org_id: str) -> OrganizationRecord | None:
        with self.client.transaction() as store:
            organization = store.organizations.get(org_id)
            return organization if organization is None else OrganizationRecord.model_validate(organization)

    def list(self) -> list[OrganizationRecord]:
        with self.client.transaction() as store:
            organizations = list(store.organizations.values())
        organizations.sort(key=lambda organization: (not organization.is_internal, organization.name.casefold(), organization.created_at))
        return organizations

    @classmethod
    def _lookup_key(cls, *, slug: str | None, name: str) -> str | None:
        candidate = slug or cls._default_slug(name)
        if candidate is None:
            return None
        return cls._normalize_key(candidate)

    @staticmethod
    def _default_slug(name: str) -> str | None:
        normalized = "-".join(part for part in name.strip().lower().split() if part)
        return normalized or None

    @staticmethod
    def _normalize_key(value: str) -> str:
        return value.strip().lower()
