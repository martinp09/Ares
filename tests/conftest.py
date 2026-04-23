import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app


@pytest.fixture(autouse=True)
def test_settings(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SITE_EVENTS_BACKEND", "memory")
    monkeypatch.setenv("RUNTIME_API_KEY", "dev-runtime-key")
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
