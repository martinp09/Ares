from app.core.config import Settings
from app.services.title_packet_import_service import TitlePacketImportService


def test_title_packet_import_writes_lead_packet_and_review_task_with_supabase_settings(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        control_plane_backend="memory",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    rows_by_table: dict[str, dict[str, dict]] = {
        "businesses": {
            "1": {"business_id": 7, "environment": "dev", "slug": "limitless"},
        }
    }

    def filter_rows(table: str, params: dict[str, str]) -> list[dict]:
        filtered = []
        for row in rows_by_table.get(table, {}).values():
            matches = True
            for key, value in params.items():
                if key in {"select", "order", "limit", "offset"}:
                    continue
                if isinstance(value, str) and value.startswith("eq.") and str(row.get(key)) != value[3:]:
                    matches = False
                    break
            if matches:
                filtered.append(row)
        limit = params.get("limit")
        if isinstance(limit, str) and limit.isdigit():
            return filtered[: int(limit)]
        return filtered

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        return filter_rows(table, params)

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        inserted = []
        for row in rows:
            payload = dict(row)
            row_id = str(payload.get("id", len(table_rows) + 1))
            payload["id"] = row_id
            payload.setdefault("created_at", "2026-04-25T00:00:00Z")
            payload.setdefault("updated_at", payload["created_at"])
            if table == "leads":
                payload.setdefault("source", "manual")
                payload.setdefault("lifecycle_status", "ready")
                payload.setdefault("lt_interest_status", "neutral")
            table_rows[row_id] = payload
            inserted.append(payload)
        return inserted

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        existing_id = params["id"][3:]
        payload = dict(table_rows[existing_id])
        payload.update(row)
        payload["id"] = existing_id
        table_rows[existing_id] = payload
        return [payload]

    def fake_resolve_tenant(business_id: str, environment: str, *, settings=None):
        return type("Tenant", (), {"business_pk": 7, "environment": environment})()

    for module in ("app.db.leads", "app.db.title_packets"):
        monkeypatch.setattr(f"{module}.fetch_rows", fake_fetch_rows)
        monkeypatch.setattr(f"{module}.insert_rows", fake_insert_rows)
        monkeypatch.setattr(f"{module}.patch_rows", fake_patch_rows)
        monkeypatch.setattr(f"{module}.resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr("app.db.tasks.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.tasks.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.tasks.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.tasks.resolve_tenant", fake_resolve_tenant)

    result = TitlePacketImportService(settings=settings).import_payload(
        {
            "schema": "ares.lead_import.v1",
            "source": "hermes.harris_hot18_title_packet_run",
            "records": [
                {
                    "business_id": "limitless",
                    "environment": "dev",
                    "source": "manual",
                    "lifecycle_status": "ready",
                    "external_key": "harris-hot18:0611340530007",
                    "company_name": "PLUMMER LETITIA W ESTATE OF",
                    "mailing_address": "3324 S MACGREGOR WAY HOUSTON TX 77021-1107",
                    "property_address": "3324 S MACGREGOR WAY 77021",
                    "probate_case_number": "500741",
                    "score": 93,
                    "verification_status": "operator_packet_built",
                    "enrichment_status": "hcad_tax_clerk_probate_enriched",
                    "upload_method": "hermes_hot18_packet_import",
                    "personalization": {
                        "operator_lane": "A - probate-first estate lead",
                        "why_now": "estate owner on tax roll",
                    },
                    "custom_variables": {
                        "hctax_account": "0611340530007",
                        "tax_due": 63829.57,
                        "manual_pull_queue": "Probate case 500741: pull application/order docs",
                    },
                    "raw_payload": {
                        "packet_source_files": ["HOT_18_title_packet_report.md"],
                        "source_row": {"owner_tax": "PLUMMER LETITIA W ESTATE OF"},
                    },
                }
            ],
        }
    )

    assert result.imported_count == 1
    assert result.updated_count == 0
    assert result.lead_ids == ["lead_1"]
    assert result.title_packet_ids == ["tpkt_1"]
    assert result.task_ids == ["tsk_1"]
    assert rows_by_table["title_packets"]["1"]["lead_id"] == 1
    assert rows_by_table["tasks"]["1"]["lead_id"] == "lead_1"
    assert rows_by_table["tasks"]["1"]["idempotency_key"] == "title-packet-review:title-packet:harris-hot18:0611340530007"
