from __future__ import annotations

from typing import Any
from urllib import error as url_error

from app.core.config import Settings, get_settings
from app.db.client import ControlPlaneClient, InMemoryControlPlaneClient, get_control_plane_client, utc_now
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
from app.models.provider_links import (
    ProviderLinkStatus,
    ProviderObjectLink,
    ProviderSyncCursor,
    ProviderSyncRun,
    ProviderSyncRunStatus,
)


class ProviderLinksRepository:
    def __init__(
        self,
        client: ControlPlaneClient | None = None,
        settings: Settings | None = None,
        force_memory: bool | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._force_memory = (
            bool(force_memory)
            if force_memory is not None
            else client is not None and getattr(client, "backend", "memory") != "supabase"
        )
        self.client = client or (InMemoryControlPlaneClient() if self._force_memory else get_control_plane_client(self.settings))

    def upsert_link(self, link: ProviderObjectLink) -> ProviderObjectLink:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_link_in_supabase(link)
        now = utc_now()
        normalized_link = self._normalize_link_identity(link)
        provider_key = normalized_link.provider_identity_key()
        ares_key = normalized_link.ares_identity_key()
        with self.client.transaction() as store:
            provider_existing_id = store.provider_object_link_provider_keys.get(provider_key)
            ares_existing_id = store.provider_object_link_ares_keys.get(ares_key)
            if provider_existing_id and ares_existing_id and provider_existing_id != ares_existing_id:
                raise ValueError("provider object and Ares object are already linked to different records")
            existing_id = provider_existing_id or ares_existing_id
            if existing_id is not None:
                existing = store.provider_object_links[existing_id]
                if (
                    existing.ares_object_type.casefold() != normalized_link.ares_object_type.casefold()
                    or existing.ares_object_id != normalized_link.ares_object_id
                    or existing.provider_object_id != normalized_link.provider_object_id
                ):
                    raise ValueError("provider object link conflict")
                updates = normalized_link.model_dump(exclude={"id", "business_id", "environment", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.provider_object_links[existing_id] = updated
                return updated
            link_id = normalized_link.id or generate_stable_id("plink", *provider_key, normalized_link.ares_object_type.casefold(), normalized_link.ares_object_id)
            created = normalized_link.model_copy(update={"id": link_id, "updated_at": now})
            store.provider_object_links[link_id] = created
            store.provider_object_link_provider_keys[provider_key] = link_id
            store.provider_object_link_ares_keys[ares_key] = link_id
            return created

    def get_by_provider_object(
        self,
        *,
        business_id: str,
        environment: str,
        provider: str,
        provider_object_type: str,
        provider_object_id: str,
    ) -> ProviderObjectLink | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            provider_norm = self._identity_value(provider)
            provider_type_norm = self._identity_value(provider_object_type)
            rows = fetch_rows(
                "provider_object_links",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "provider": f"eq.{provider_norm}",
                    "provider_object_type": f"eq.{provider_type_norm}",
                    "provider_object_id": f"eq.{provider_object_id}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            return self._link_from_supabase(rows[0]) if rows else None
        key = (business_id, environment, provider.casefold(), provider_object_type.casefold(), provider_object_id)
        with self.client.transaction() as store:
            link_id = store.provider_object_link_provider_keys.get(key)
            return store.provider_object_links.get(link_id) if link_id else None

    def get_by_ares_object(
        self,
        *,
        business_id: str,
        environment: str,
        provider: str,
        ares_object_type: str,
        ares_object_id: str,
        provider_object_type: str | None = None,
    ) -> ProviderObjectLink | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            provider_norm = self._identity_value(provider)
            ares_type_norm = self._identity_value(ares_object_type)
            params = {
                "select": "*",
                "business_id": f"eq.{tenant.business_pk}",
                "environment": f"eq.{tenant.environment}",
                "provider": f"eq.{provider_norm}",
                "ares_object_type": f"eq.{ares_type_norm}",
                "ares_object_id": f"eq.{ares_object_id}",
                "limit": "1",
            }
            if provider_object_type is not None:
                params["provider_object_type"] = f"eq.{self._identity_value(provider_object_type)}"
            rows = fetch_rows(
                "provider_object_links",
                params=params,
                settings=self.settings,
            )
            return self._link_from_supabase(rows[0]) if rows else None
        if provider_object_type is None:
            with self.client.transaction() as store:
                matches = [
                    link
                    for link in store.provider_object_links.values()
                    if link.business_id == business_id
                    and link.environment == environment
                    and link.provider.casefold() == provider.casefold()
                    and link.ares_object_type.casefold() == ares_object_type.casefold()
                    and link.ares_object_id == ares_object_id
                ]
            matches.sort(key=lambda link: (link.provider_object_type.casefold(), link.id or ""))
            return matches[0] if matches else None
        key = (business_id, environment, provider.casefold(), ares_object_type.casefold(), ares_object_id, provider_object_type.casefold())
        with self.client.transaction() as store:
            link_id = store.provider_object_link_ares_keys.get(key)
            return store.provider_object_links.get(link_id) if link_id else None

    def mark_conflict(self, link_id: str, *, reason: str) -> ProviderObjectLink | None:
        return self._patch_link(link_id, {"link_status": ProviderLinkStatus.CONFLICT, "conflict_reason": reason})

    def archive_link(self, link_id: str) -> ProviderObjectLink | None:
        return self._patch_link(link_id, {"link_status": ProviderLinkStatus.ARCHIVED})

    def upsert_cursor(self, cursor: ProviderSyncCursor) -> ProviderSyncCursor:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._upsert_cursor_in_supabase(cursor)
        now = utc_now()
        normalized_cursor = cursor.model_copy(update={"provider": self._identity_value(cursor.provider)})
        key = normalized_cursor.identity_key()
        with self.client.transaction() as store:
            existing_id = store.provider_sync_cursor_keys.get(key)
            if existing_id is not None:
                existing = store.provider_sync_cursors[existing_id]
                updates = normalized_cursor.model_dump(exclude={"id", "business_id", "environment", "created_at", "updated_at"})
                updated = existing.model_copy(update={**updates, "updated_at": now})
                store.provider_sync_cursors[existing_id] = updated
                return updated
            cursor_id = normalized_cursor.id or generate_stable_id("pscur", *key)
            created = normalized_cursor.model_copy(update={"id": cursor_id, "updated_at": now})
            store.provider_sync_cursors[cursor_id] = created
            store.provider_sync_cursor_keys[key] = cursor_id
            return created

    def get_cursor(self, *, business_id: str, environment: str, provider: str, sync_name: str) -> ProviderSyncCursor | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            tenant = resolve_tenant(business_id, environment, settings=self.settings)
            rows = fetch_rows(
                "provider_sync_cursors",
                params={
                    "select": "*",
                    "business_id": f"eq.{tenant.business_pk}",
                    "environment": f"eq.{tenant.environment}",
                    "provider": f"eq.{self._identity_value(provider)}",
                    "sync_name": f"eq.{sync_name}",
                    "limit": "1",
                },
                settings=self.settings,
            )
            return self._cursor_from_supabase(rows[0]) if rows else None
        key = (business_id, environment, provider.casefold(), sync_name)
        with self.client.transaction() as store:
            cursor_id = store.provider_sync_cursor_keys.get(key)
            return store.provider_sync_cursors.get(cursor_id) if cursor_id else None

    def start_sync_run(self, sync_run: ProviderSyncRun) -> ProviderSyncRun:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            return self._start_sync_run_in_supabase(sync_run)
        now = utc_now()
        normalized_run = sync_run.model_copy(update={"provider": self._identity_value(sync_run.provider)})
        key = normalized_run.identity_key()
        with self.client.transaction() as store:
            existing_id = store.provider_sync_run_keys.get(key)
            if existing_id is not None:
                return store.provider_sync_runs[existing_id]
            run_id = normalized_run.id or generate_stable_id("psrun", *key)
            created = normalized_run.model_copy(
                update={"id": run_id, "status": ProviderSyncRunStatus.IN_PROGRESS, "started_at": normalized_run.started_at or now, "updated_at": now}
            )
            store.provider_sync_runs[run_id] = created
            store.provider_sync_run_keys[key] = run_id
            return created

    def complete_sync_run(self, sync_run_id: str, **updates: Any) -> ProviderSyncRun | None:
        payload = {**updates, "status": ProviderSyncRunStatus.COMPLETED, "completed_at": updates.get("completed_at") or utc_now()}
        return self._patch_sync_run(sync_run_id, payload)

    def fail_sync_run(self, sync_run_id: str, *, error_message: str, **updates: Any) -> ProviderSyncRun | None:
        payload = {**updates, "status": ProviderSyncRunStatus.FAILED, "error_message": error_message, "completed_at": updates.get("completed_at") or utc_now()}
        return self._patch_sync_run(sync_run_id, payload)

    def list_sync_runs(
        self,
        *,
        business_id: str | None = None,
        environment: str | None = None,
        provider: str | None = None,
        sync_name: str | None = None,
        status: ProviderSyncRunStatus | None = None,
    ) -> list[ProviderSyncRun]:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            params: dict[str, str] = {"select": "*", "order": "started_at.desc,id.desc"}
            if business_id is not None and environment is not None:
                tenant = resolve_tenant(business_id, environment, settings=self.settings)
                params["business_id"] = f"eq.{tenant.business_pk}"
                params["environment"] = f"eq.{tenant.environment}"
            elif business_id is not None and business_id.isdigit():
                params["business_id"] = f"eq.{business_id}"
            if environment is not None and "environment" not in params:
                params["environment"] = f"eq.{environment}"
            if provider is not None:
                params["provider"] = f"eq.{self._identity_value(provider)}"
            if sync_name is not None:
                params["sync_name"] = f"eq.{sync_name}"
            if status is not None:
                params["status"] = f"eq.{status.value}"
            return [self._sync_run_from_supabase(row) for row in fetch_rows("provider_sync_runs", params=params, settings=self.settings)]
        with self.client.transaction() as store:
            runs = list(store.provider_sync_runs.values())
        if business_id is not None:
            runs = [run for run in runs if run.business_id == business_id]
        if environment is not None:
            runs = [run for run in runs if run.environment == environment]
        if provider is not None:
            provider_norm = self._identity_value(provider)
            runs = [run for run in runs if run.provider.casefold() == provider_norm]
        if sync_name is not None:
            runs = [run for run in runs if run.sync_name == sync_name]
        if status is not None:
            runs = [run for run in runs if run.status == status]
        return sorted(runs, key=lambda run: (run.started_at or run.created_at, run.id or ""), reverse=True)

    def _patch_link(self, link_id: str, updates: dict[str, Any]) -> ProviderObjectLink | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(link_id, "plink")
            if row_id is None:
                return None
            payload = self._json_payload(updates)
            rows = patch_rows("provider_object_links", params={"id": f"eq.{row_id}"}, row=payload, select="*", settings=self.settings)
            return self._link_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            current = store.provider_object_links.get(link_id)
            if current is None:
                return None
            updated = current.model_copy(update={**updates, "updated_at": utc_now()})
            store.provider_object_links[link_id] = updated
            return updated

    def _patch_sync_run(self, sync_run_id: str, updates: dict[str, Any]) -> ProviderSyncRun | None:
        if lead_machine_backend_enabled(self.settings) and not self._force_memory:
            row_id = row_id_from_external_id(sync_run_id, "psrun")
            if row_id is None:
                return None
            rows = patch_rows("provider_sync_runs", params={"id": f"eq.{row_id}"}, row=self._json_payload(updates), select="*", settings=self.settings)
            return self._sync_run_from_supabase(rows[0]) if rows else None
        with self.client.transaction() as store:
            current = store.provider_sync_runs.get(sync_run_id)
            if current is None:
                return None
            updated = current.model_copy(update={**updates, "updated_at": utc_now()})
            store.provider_sync_runs[sync_run_id] = updated
            return updated

    def _upsert_link_in_supabase(self, link: ProviderObjectLink) -> ProviderObjectLink:
        tenant = resolve_tenant(link.business_id, link.environment, settings=self.settings)
        normalized_link = self._normalize_link_identity(link)
        provider_rows = self._fetch_provider_link(
            tenant.business_pk,
            tenant.environment,
            normalized_link.provider,
            normalized_link.provider_object_type,
            normalized_link.provider_object_id,
        )
        ares_rows = self._fetch_ares_link(
            tenant.business_pk,
            tenant.environment,
            normalized_link.provider,
            normalized_link.ares_object_type,
            normalized_link.ares_object_id,
            normalized_link.provider_object_type,
        )
        if provider_rows and ares_rows and provider_rows[0]["id"] != ares_rows[0]["id"]:
            raise ValueError("provider object and Ares object are already linked to different records")
        existing = (provider_rows or ares_rows or [None])[0]
        if existing and (str(existing["ares_object_id"]) != normalized_link.ares_object_id or str(existing["provider_object_id"]) != normalized_link.provider_object_id):
            raise ValueError("provider object link conflict")
        payload = self._link_payload_for_supabase(normalized_link, business_pk=tenant.business_pk, environment=tenant.environment)
        if existing:
            row = patch_rows("provider_object_links", params={"id": f"eq.{existing['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._link_from_supabase(row)
        provided_id = row_id_from_external_id(normalized_link.id, "plink")
        if provided_id is not None:
            payload["id"] = provided_id
        try:
            row = insert_rows("provider_object_links", [payload], select="*", settings=self.settings)[0]
        except Exception as exc:
            if not self._is_duplicate_insert_error(exc):
                raise
            return self._refetch_patch_link_after_duplicate(tenant.business_pk, tenant.environment, normalized_link, payload)
        return self._link_from_supabase(row)

    def _upsert_cursor_in_supabase(self, cursor: ProviderSyncCursor) -> ProviderSyncCursor:
        tenant = resolve_tenant(cursor.business_id, cursor.environment, settings=self.settings)
        normalized_cursor = cursor.model_copy(update={"provider": self._identity_value(cursor.provider)})
        existing = fetch_rows(
            "provider_sync_cursors",
            params={"select": "*", "business_id": f"eq.{tenant.business_pk}", "environment": f"eq.{tenant.environment}", "provider": f"eq.{normalized_cursor.provider}", "sync_name": f"eq.{normalized_cursor.sync_name}", "limit": "1"},
            settings=self.settings,
        )
        payload = self._cursor_payload_for_supabase(normalized_cursor, business_pk=tenant.business_pk, environment=tenant.environment)
        if existing:
            row = patch_rows("provider_sync_cursors", params={"id": f"eq.{existing[0]['id']}"}, row=payload, select="*", settings=self.settings)[0]
            return self._cursor_from_supabase(row)
        provided_id = row_id_from_external_id(normalized_cursor.id, "pscur")
        if provided_id is not None:
            payload["id"] = provided_id
        try:
            row = insert_rows("provider_sync_cursors", [payload], select="*", settings=self.settings)[0]
        except Exception as exc:
            if not self._is_duplicate_insert_error(exc):
                raise
            refetched = fetch_rows(
                "provider_sync_cursors",
                params={"select": "*", "business_id": f"eq.{tenant.business_pk}", "environment": f"eq.{tenant.environment}", "provider": f"eq.{normalized_cursor.provider}", "sync_name": f"eq.{normalized_cursor.sync_name}", "limit": "1"},
                settings=self.settings,
            )
            if not refetched:
                raise
            row = patch_rows("provider_sync_cursors", params={"id": f"eq.{refetched[0]['id']}"}, row=payload, select="*", settings=self.settings)[0]
        return self._cursor_from_supabase(row)

    def _start_sync_run_in_supabase(self, sync_run: ProviderSyncRun) -> ProviderSyncRun:
        tenant = resolve_tenant(sync_run.business_id, sync_run.environment, settings=self.settings)
        normalized_run = sync_run.model_copy(update={"provider": self._identity_value(sync_run.provider)})
        existing = fetch_rows(
            "provider_sync_runs",
            params={"select": "*", "business_id": f"eq.{tenant.business_pk}", "environment": f"eq.{tenant.environment}", "provider": f"eq.{normalized_run.provider}", "sync_name": f"eq.{normalized_run.sync_name}", "idempotency_key": f"eq.{normalized_run.idempotency_key}", "limit": "1"},
            settings=self.settings,
        )
        if existing:
            return self._sync_run_from_supabase(existing[0])
        payload = self._sync_run_payload_for_supabase(normalized_run, business_pk=tenant.business_pk, environment=tenant.environment)
        payload["status"] = ProviderSyncRunStatus.IN_PROGRESS.value
        payload["started_at"] = (normalized_run.started_at or utc_now()).isoformat()
        provided_id = row_id_from_external_id(normalized_run.id, "psrun")
        if provided_id is not None:
            payload["id"] = provided_id
        try:
            row = insert_rows("provider_sync_runs", [payload], select="*", settings=self.settings)[0]
        except Exception as exc:
            if not self._is_duplicate_insert_error(exc):
                raise
            refetched = fetch_rows(
                "provider_sync_runs",
                params={"select": "*", "business_id": f"eq.{tenant.business_pk}", "environment": f"eq.{tenant.environment}", "provider": f"eq.{normalized_run.provider}", "sync_name": f"eq.{normalized_run.sync_name}", "idempotency_key": f"eq.{normalized_run.idempotency_key}", "limit": "1"},
                settings=self.settings,
            )
            if not refetched:
                raise
            row = refetched[0]
        return self._sync_run_from_supabase(row)

    def _fetch_provider_link(self, business_pk: int, environment: str, provider: str, object_type: str, object_id: str) -> list[dict[str, Any]]:
        provider_norm = self._identity_value(provider)
        object_type_norm = self._identity_value(object_type)
        return fetch_rows(
            "provider_object_links",
            params={"select": "*", "business_id": f"eq.{business_pk}", "environment": f"eq.{environment}", "provider": f"eq.{provider_norm}", "provider_object_type": f"eq.{object_type_norm}", "provider_object_id": f"eq.{object_id}", "limit": "1"},
            settings=self.settings,
        )

    def _fetch_ares_link(self, business_pk: int, environment: str, provider: str, ares_type: str, ares_id: str, provider_type: str) -> list[dict[str, Any]]:
        provider_norm = self._identity_value(provider)
        ares_type_norm = self._identity_value(ares_type)
        provider_type_norm = self._identity_value(provider_type)
        return fetch_rows(
            "provider_object_links",
            params={"select": "*", "business_id": f"eq.{business_pk}", "environment": f"eq.{environment}", "provider": f"eq.{provider_norm}", "ares_object_type": f"eq.{ares_type_norm}", "ares_object_id": f"eq.{ares_id}", "provider_object_type": f"eq.{provider_type_norm}", "limit": "1"},
            settings=self.settings,
        )

    def _refetch_patch_link_after_duplicate(
        self,
        business_pk: int,
        environment: str,
        link: ProviderObjectLink,
        payload: dict[str, Any],
    ) -> ProviderObjectLink:
        provider_rows = self._fetch_provider_link(business_pk, environment, link.provider, link.provider_object_type, link.provider_object_id)
        ares_rows = self._fetch_ares_link(business_pk, environment, link.provider, link.ares_object_type, link.ares_object_id, link.provider_object_type)
        if provider_rows and ares_rows and provider_rows[0]["id"] != ares_rows[0]["id"]:
            raise ValueError("provider object and Ares object are already linked to different records")
        existing = (provider_rows or ares_rows or [None])[0]
        if not existing:
            raise RuntimeError("provider object link insert conflict could not be refetched")
        if str(existing["ares_object_id"]) != link.ares_object_id or str(existing["provider_object_id"]) != link.provider_object_id:
            raise ValueError("provider object link conflict")
        row = patch_rows("provider_object_links", params={"id": f"eq.{existing['id']}"}, row=payload, select="*", settings=self.settings)[0]
        return self._link_from_supabase(row)

    @staticmethod
    def _identity_value(value: str) -> str:
        return value.casefold()

    @classmethod
    def _normalize_link_identity(cls, link: ProviderObjectLink) -> ProviderObjectLink:
        return link.model_copy(
            update={
                "provider": cls._identity_value(link.provider),
                "provider_object_type": cls._identity_value(link.provider_object_type),
                "ares_object_type": cls._identity_value(link.ares_object_type),
            }
        )

    @staticmethod
    def _is_duplicate_insert_error(exc: Exception) -> bool:
        if not isinstance(exc, url_error.HTTPError):
            return False
        if exc.code == 409:
            return True
        if exc.code != 400:
            return False
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            return False
        lowered = body.lower()
        return "duplicate key" in lowered or "unique constraint" in lowered or "23505" in lowered

    @staticmethod
    def _json_payload(payload: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in payload.items():
            if hasattr(value, "value"):
                normalized[key] = value.value
            elif hasattr(value, "isoformat"):
                normalized[key] = value.isoformat()
            else:
                normalized[key] = value
        return normalized

    @staticmethod
    def _link_payload_for_supabase(link: ProviderObjectLink, *, business_pk: int, environment: str) -> dict[str, Any]:
        payload = link.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["provider"] = str(payload["provider"]).casefold()
        payload["provider_object_type"] = str(payload["provider_object_type"]).casefold()
        payload["ares_object_type"] = str(payload["ares_object_type"]).casefold()
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["link_status"] = link.link_status.value
        return payload

    @staticmethod
    def _cursor_payload_for_supabase(cursor: ProviderSyncCursor, *, business_pk: int, environment: str) -> dict[str, Any]:
        payload = cursor.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["provider"] = str(payload["provider"]).casefold()
        payload["business_id"] = business_pk
        payload["environment"] = environment
        return payload

    @staticmethod
    def _sync_run_payload_for_supabase(sync_run: ProviderSyncRun, *, business_pk: int, environment: str) -> dict[str, Any]:
        payload = sync_run.model_dump(mode="json", exclude={"id", "business_id", "environment", "created_at", "updated_at"})
        payload["provider"] = str(payload["provider"]).casefold()
        payload["business_id"] = business_pk
        payload["environment"] = environment
        payload["direction"] = sync_run.direction.value
        payload["status"] = sync_run.status.value
        payload["command_id"] = row_id_from_external_id(sync_run.command_id, "cmd")
        payload["run_id"] = row_id_from_external_id(sync_run.run_id, "run")
        return payload

    @staticmethod
    def _link_from_supabase(row: dict[str, Any]) -> ProviderObjectLink:
        allowed = set(ProviderObjectLink.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed}
        payload["id"] = external_id("plink", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        return ProviderObjectLink.model_validate(payload)

    @staticmethod
    def _cursor_from_supabase(row: dict[str, Any]) -> ProviderSyncCursor:
        allowed = set(ProviderSyncCursor.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed}
        payload["id"] = external_id("pscur", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        return ProviderSyncCursor.model_validate(payload)

    @staticmethod
    def _sync_run_from_supabase(row: dict[str, Any]) -> ProviderSyncRun:
        allowed = set(ProviderSyncRun.model_fields)
        payload = {key: value for key, value in dict(row).items() if key in allowed}
        payload["id"] = external_id("psrun", row["id"])
        payload["business_id"] = str(row["business_id"])
        payload["environment"] = str(row["environment"])
        if row.get("command_id") is not None:
            payload["command_id"] = external_id("cmd", row["command_id"])
        if row.get("run_id") is not None:
            payload["run_id"] = external_id("run", row["run_id"])
        return ProviderSyncRun.model_validate(payload)
