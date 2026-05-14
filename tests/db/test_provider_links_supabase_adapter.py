from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.core.config import Settings
from app.db import provider_links as provider_links_module
from app.db.lead_machine_supabase import LeadMachineTenant
from app.db.provider_links import ProviderLinksRepository
from app.models.provider_links import ProviderObjectLink, ProviderSyncCursor, ProviderSyncDirection, ProviderSyncRun, ProviderSyncRunStatus


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def _filter_rows(rows_by_table: dict[str, dict[str, dict]], table: str, params: dict[str, str]) -> list[dict]:
    matches: list[dict] = []
    for row in rows_by_table.get(table, {}).values():
        if all(key in {"select", "order", "limit"} or not value.startswith("eq.") or str(row.get(key)) == value[3:] for key, value in params.items()):
            matches.append(dict(row))
    return matches


def test_link_from_supabase_maps_external_id_and_tenant_fields() -> None:
    record = ProviderLinksRepository._link_from_supabase(
        {
            "id": 7,
            "business_id": 1,
            "environment": "dev",
            "provider": "hubspot",
            "provider_object_type": "contact",
            "provider_object_id": "123",
            "ares_object_type": "crm_record",
            "ares_object_id": "crmrec_abc",
            "link_status": "active",
            "raw_payload": {"email": "seller@example.com"},
            "created_at": "2026-05-14T09:00:00+00:00",
            "updated_at": "2026-05-14T09:00:00+00:00",
        }
    )

    assert record.id == "plink_7"
    assert record.business_id == "1"
    assert record.provider_object_id == "123"
    assert record.raw_payload == {"email": "seller@example.com"}


def test_cursor_from_supabase_maps_external_id() -> None:
    cursor = ProviderLinksRepository._cursor_from_supabase(
        {
            "id": 8,
            "business_id": 1,
            "environment": "dev",
            "provider": "hubspot",
            "sync_name": "contacts_delta",
            "cursor_value": "abc",
            "cursor_payload": {"after": "abc"},
            "created_at": "2026-05-14T09:00:00+00:00",
            "updated_at": "2026-05-14T09:00:00+00:00",
        }
    )

    assert cursor.id == "pscur_8"
    assert cursor.business_id == "1"
    assert cursor.cursor_payload == {"after": "abc"}


def test_sync_run_from_supabase_maps_external_ids_and_enums() -> None:
    sync_run = ProviderLinksRepository._sync_run_from_supabase(
        {
            "id": 9,
            "business_id": 1,
            "environment": "dev",
            "provider": "hubspot",
            "sync_name": "contacts_push",
            "direction": "dry_run",
            "status": "completed",
            "idempotency_key": "run-1",
            "scanned_count": 2,
            "created_count": 0,
            "updated_count": 1,
            "skipped_count": 1,
            "conflict_count": 0,
            "error_count": 0,
            "input_payload": {},
            "output_payload": {"ok": True},
            "command_id": 4,
            "run_id": 5,
            "created_at": "2026-05-14T09:00:00+00:00",
            "updated_at": "2026-05-14T09:00:00+00:00",
        }
    )

    assert sync_run.id == "psrun_9"
    assert sync_run.command_id == "cmd_4"
    assert sync_run.run_id == "run_5"
    assert sync_run.direction == ProviderSyncDirection.DRY_RUN
    assert sync_run.status == ProviderSyncRunStatus.COMPLETED
    assert sync_run.output_payload == {"ok": True}


def test_payload_converters_strip_external_ids_for_supabase() -> None:
    payload = ProviderLinksRepository._sync_run_payload_for_supabase(
        sync_run=ProviderLinksRepository._sync_run_from_supabase(
            {
                "id": 9,
                "business_id": 1,
                "environment": "dev",
                "provider": "hubspot",
                "sync_name": "contacts_push",
                "direction": "ares_to_provider",
                "status": "queued",
                "idempotency_key": "run-1",
                "input_payload": {},
                "output_payload": {},
                "command_id": 4,
                "run_id": 5,
                "created_at": "2026-05-14T09:00:00+00:00",
                "updated_at": "2026-05-14T09:00:00+00:00",
            }
        ),
        business_pk=1,
        environment="dev",
    )

    assert payload["command_id"] == 4
    assert payload["run_id"] == 5
    assert payload["business_id"] == 1
    assert payload["environment"] == "dev"


def test_link_payload_for_supabase_lowercases_identity_fields_only() -> None:
    payload = ProviderLinksRepository._link_payload_for_supabase(
        ProviderObjectLink(
            business_id="1",
            environment="dev",
            provider="HubSpot",
            provider_object_type="Contact",
            provider_object_id="HS-ABC",
            ares_object_type="CRM_Record",
            ares_object_id="crmrec_ABC",
            raw_payload={"Email": "Seller@Example.com"},
        ),
        business_pk=42,
        environment="prod",
    )

    assert payload["provider"] == "hubspot"
    assert payload["provider_object_type"] == "contact"
    assert payload["ares_object_type"] == "crm_record"
    assert payload["provider_object_id"] == "HS-ABC"
    assert payload["ares_object_id"] == "crmrec_ABC"
    assert payload["business_id"] == 42
    assert payload["environment"] == "prod"


def test_cursor_and_sync_run_payloads_lowercase_provider_only() -> None:
    cursor_payload = ProviderLinksRepository._cursor_payload_for_supabase(
        ProviderSyncCursor(
            business_id="1",
            environment="dev",
            provider="HubSpot",
            sync_name="Contacts_Delta",
            cursor_value="AFTER",
        ),
        business_pk=42,
        environment="prod",
    )
    run_payload = ProviderLinksRepository._sync_run_payload_for_supabase(
        ProviderSyncRun(
            business_id="1",
            environment="dev",
            provider="HubSpot",
            sync_name="Contacts_Push",
            idempotency_key="Run-ABC",
        ),
        business_pk=42,
        environment="prod",
    )

    assert cursor_payload["provider"] == "hubspot"
    assert cursor_payload["sync_name"] == "Contacts_Delta"
    assert cursor_payload["cursor_value"] == "AFTER"
    assert run_payload["provider"] == "hubspot"
    assert run_payload["sync_name"] == "Contacts_Push"
    assert run_payload["idempotency_key"] == "Run-ABC"


def _duplicate_http_error(status: int) -> HTTPError:
    body = b'{"code":"23505","message":"duplicate key value violates unique constraint"}'
    return HTTPError("https://example.supabase.co/rest/v1/provider_object_links", status, "duplicate", {}, BytesIO(body))


@pytest.mark.parametrize("status", [409, 400])
def test_supabase_link_duplicate_insert_race_refetches_and_patches(monkeypatch: pytest.MonkeyPatch, status: int) -> None:
    settings = build_settings()
    repo = ProviderLinksRepository(settings=settings)
    existing_row = {
        "id": 77,
        "business_id": 42,
        "environment": "dev",
        "provider": "hubspot",
        "provider_object_type": "contact",
        "provider_object_id": "HS-ABC",
        "ares_object_type": "crm_record",
        "ares_object_id": "crmrec_ABC",
        "link_status": "active",
        "sync_hash": "old",
        "raw_payload": {},
    }
    calls = {"fetch": 0, "patch_payload": None}

    def fake_resolve_tenant(business_id: str, environment: str, *, settings: Settings | None = None) -> LeadMachineTenant:
        assert business_id == "1"
        assert environment == "dev"
        return LeadMachineTenant(business_pk=42, environment="dev")

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings: Settings | None = None) -> list[dict]:
        assert table == "provider_object_links"
        calls["fetch"] += 1
        if calls["fetch"] <= 2:
            return []
        assert params["provider"] == "eq.hubspot"
        return [dict(existing_row)]

    def fake_insert_rows(table: str, rows: list[dict], *, select: str | None = None, prefer: str = "return=representation", settings: Settings | None = None) -> list[dict]:
        assert table == "provider_object_links"
        assert rows[0]["provider"] == "hubspot"
        assert rows[0]["provider_object_type"] == "contact"
        assert rows[0]["ares_object_type"] == "crm_record"
        raise _duplicate_http_error(status)

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select: str | None = None, settings: Settings | None = None) -> list[dict]:
        assert table == "provider_object_links"
        assert params == {"id": "eq.77"}
        calls["patch_payload"] = dict(row)
        return [{**existing_row, **row}]

    monkeypatch.setattr(provider_links_module, "resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr(provider_links_module, "fetch_rows", fake_fetch_rows)
    monkeypatch.setattr(provider_links_module, "insert_rows", fake_insert_rows)
    monkeypatch.setattr(provider_links_module, "patch_rows", fake_patch_rows)

    result = repo.upsert_link(
        ProviderObjectLink(
            business_id="1",
            environment="dev",
            provider="HubSpot",
            provider_object_type="Contact",
            provider_object_id="HS-ABC",
            ares_object_type="CRM_Record",
            ares_object_id="crmrec_ABC",
            sync_hash="new",
            raw_payload={"email": "seller@example.com"},
        )
    )

    assert result.id == "plink_77"
    assert result.provider == "hubspot"
    assert result.provider_object_type == "contact"
    assert result.ares_object_type == "crm_record"
    assert result.sync_hash == "new"
    assert calls["fetch"] == 4
    assert calls["patch_payload"] is not None
    assert calls["patch_payload"]["provider"] == "hubspot"
    assert calls["patch_payload"]["provider_object_id"] == "HS-ABC"
    assert calls["patch_payload"]["ares_object_id"] == "crmrec_ABC"
