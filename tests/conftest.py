import os

import pytest
from fastapi.testclient import TestClient

# Tests must not inherit a developer/runtime .env that points the control plane at
# Supabase. Several API modules construct service singletons while app.main is
# imported, so force the in-memory backend before importing the FastAPI app.
os.environ["CONTROL_PLANE_BACKEND"] = "memory"
os.environ["MARKETING_BACKEND"] = "memory"
os.environ["LEAD_MACHINE_BACKEND"] = "memory"
os.environ["SITE_EVENTS_BACKEND"] = "memory"
os.environ["RUNTIME_API_KEY"] = "dev-runtime-key"
os.environ["INSTANTLY_API_KEY"] = ""
os.environ["INSTANTLY_WEBHOOK_SECRET"] = ""
os.environ["INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED"] = "false"
os.environ["VAPI_API_KEY"] = ""
os.environ["VAPI_PRIVATE_KEY"] = ""
os.environ["VAPI_PROVIDER_LIVE_SENDS_ENABLED"] = "false"
os.environ["VAPI_WEBHOOK_SECRET"] = ""
os.environ["PROVIDER_WEBHOOK_SIGNATURES_REQUIRED"] = "false"
os.environ["VAPI_DEFAULT_ASSISTANT_ID"] = ""
os.environ["VAPI_DEFAULT_PHONE_NUMBER_ID"] = ""
os.environ["HUBSPOT_ACCESS_TOKEN"] = ""
os.environ["PROVIDER_LIVE_SENDS_ENABLED"] = "false"
os.environ["HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED"] = "false"

SLACK_ENV_VARS = (
    "SLACK_NOTIFICATIONS_ENABLED",
    "SLACK_BOT_TOKEN",
    "SLACK_CHANNEL_LEAD_RUNS",
    "SLACK_CHANNEL_HOT_LEADS",
    "SLACK_CHANNEL_INSTANTLY_REPLIES",
    "SLACK_CHANNEL_LEASE_OPTION_INBOUND",
    "SLACK_CHANNEL_SMS_CALLS",
    "SLACK_CHANNEL_ERRORS",
    "SLACK_CHANNEL_LEADS",
    "SLACK_CHANNEL_INTAKE",
    "SLACK_CHANNEL_CHIEF_OF_STAFF",
)

for name in SLACK_ENV_VARS:
    os.environ.pop(name, None)
os.environ["SLACK_NOTIFICATIONS_ENABLED"] = "false"
os.environ["ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED"] = "false"

from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def test_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CONTROL_PLANE_BACKEND", "memory")
    monkeypatch.setenv("MARKETING_BACKEND", "memory")
    monkeypatch.setenv("LEAD_MACHINE_BACKEND", "memory")
    monkeypatch.setenv("SITE_EVENTS_BACKEND", "memory")
    monkeypatch.setenv("RUNTIME_API_KEY", "dev-runtime-key")
    monkeypatch.setenv("RUNTIME_ACTOR_HEADER_OVERRIDES_ENABLED", "true")
    monkeypatch.setenv("INSTANTLY_API_KEY", "")
    monkeypatch.setenv("INSTANTLY_WEBHOOK_SECRET", "")
    monkeypatch.setenv("INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED", "false")
    monkeypatch.setenv("VAPI_API_KEY", "")
    monkeypatch.setenv("VAPI_PRIVATE_KEY", "")
    monkeypatch.setenv("VAPI_PROVIDER_LIVE_SENDS_ENABLED", "false")
    monkeypatch.setenv("VAPI_WEBHOOK_SECRET", "")
    monkeypatch.setenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", "false")
    monkeypatch.setenv("VAPI_DEFAULT_ASSISTANT_ID", "")
    monkeypatch.setenv("VAPI_DEFAULT_PHONE_NUMBER_ID", "")
    monkeypatch.setenv("HUBSPOT_ACCESS_TOKEN", "")
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "false")
    monkeypatch.setenv("HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED", "false")
    for name in SLACK_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SLACK_NOTIFICATIONS_ENABLED", "false")
    monkeypatch.setenv("ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def fake_supabase_control_plane(monkeypatch: pytest.MonkeyPatch):
    rows_by_table: dict[str, dict[str, dict]] = {}
    insert_failures: dict[str, int] = {}
    patch_failures: dict[str, int] = {}

    def _consume_failure(budget: dict[str, int], table: str, action: str) -> None:
        remaining = budget.get(table, 0)
        if remaining <= 0:
            return
        budget[table] = remaining - 1
        raise RuntimeError(f"{table} {action} failure")

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        table_rows = list(rows_by_table.get(table, {}).values())
        filtered: list[dict] = []
        for row in table_rows:
            matches = True
            for key, value in params.items():
                if key in {"select", "order", "limit", "offset"}:
                    continue
                if isinstance(value, str) and value.startswith("eq.") and str(row.get(key)) != value[3:]:
                    matches = False
                    break
            if matches:
                filtered.append(dict(row))
        order = params.get("order")
        if isinstance(order, str) and order.endswith(".asc"):
            sort_key = order[:-4]
            filtered.sort(key=lambda row: str(row.get(sort_key) or ""))
        return filtered

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        _consume_failure(insert_failures, table, "insert")
        table_rows = rows_by_table.setdefault(table, {})
        inserted = []
        for row in rows:
            payload = dict(row)
            row_id = str(payload.get("id", len(table_rows) + 1))
            payload["id"] = row_id
            table_rows[row_id] = payload
            inserted.append(payload)
        return inserted

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        _consume_failure(patch_failures, table, "patch")
        table_rows = rows_by_table.setdefault(table, {})
        row_id = params.get("id", "")
        existing_id = row_id[3:] if row_id.startswith("eq.") else str(row.get("id", len(table_rows) + 1))
        payload = dict(table_rows.get(existing_id, {}))
        payload.update(row)
        payload["id"] = existing_id
        table_rows[existing_id] = payload
        return [payload]

    def fake_delete_rows(table: str, *, params: dict[str, str], settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        row_id = params.get("id", "")
        if row_id.startswith("eq."):
            table_rows.pop(row_id[3:], None)
        return []

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.delete_rows", fake_delete_rows)

    def configure(
        *,
        reset: bool = True,
        fail_on_insert: dict[str, int] | None = None,
        fail_on_patch: dict[str, int] | None = None,
    ) -> dict[str, dict[str, dict]]:
        if reset:
            rows_by_table.clear()
        insert_failures.clear()
        patch_failures.clear()
        if fail_on_insert is not None:
            insert_failures.update(fail_on_insert)
        if fail_on_patch is not None:
            patch_failures.update(fail_on_patch)
        monkeypatch.setenv("CONTROL_PLANE_BACKEND", "supabase")
        monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role")
        get_settings.cache_clear()
        return rows_by_table

    return configure
