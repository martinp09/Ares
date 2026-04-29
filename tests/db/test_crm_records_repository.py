from app.core.config import Settings
from app.db.crm_records import CrmRecordsRepository
from app.models.crm_records import (
    CrmRecord,
    CrmRecordPromotion,
    CrmRecordSourceMembership,
    CrmRecordStatus,
    CrmRecordType,
    CrmSourceRecord,
)


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def _filter_rows(rows_by_table: dict[str, dict[str, dict]], table: str, params: dict[str, str]) -> list[dict]:
    table_rows = list(rows_by_table.get(table, {}).values())
    filtered = []
    for row in table_rows:
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


def test_crm_records_repository_round_trips_registry_records(monkeypatch) -> None:
    settings = build_settings()
    rows_by_table: dict[str, dict[str, dict]] = {
        "businesses": {"1": {"business_id": 7, "environment": "dev", "slug": "limitless"}}
    }

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        return _filter_rows(rows_by_table, table, params)

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        inserted = []
        for row in rows:
            payload = dict(row)
            row_id = str(payload.get("id", len(table_rows) + 1))
            payload["id"] = row_id
            payload.setdefault("created_at", "2026-04-29T00:00:00Z")
            payload.setdefault("updated_at", payload["created_at"])
            table_rows[row_id] = payload
            inserted.append(payload)
        return inserted

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        existing_id = params["id"][3:]
        payload = dict(table_rows[existing_id])
        payload.update(row)
        payload["id"] = existing_id
        payload.setdefault("created_at", "2026-04-29T00:00:00Z")
        payload.setdefault("updated_at", "2026-04-29T00:00:00Z")
        table_rows[existing_id] = payload
        return [payload]

    def fake_resolve_tenant(business_id: str, environment: str, *, settings=None):
        return type("Tenant", (), {"business_pk": 7, "environment": environment})()

    monkeypatch.setattr("app.db.crm_records.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.crm_records.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.crm_records.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.crm_records.resolve_tenant", fake_resolve_tenant)

    repository = CrmRecordsRepository(settings=settings)
    source_record = repository.upsert_source_record(
        CrmSourceRecord(
            business_id="limitless",
            environment="dev",
            source_system="harris_probate",
            source_key="case-123",
            payload={"case_number": "123"},
            confidence=0.95,
        )
    )
    record = repository.upsert_record(
        CrmRecord(
            business_id="limitless",
            environment="dev",
            record_type=CrmRecordType.PROBATE_CASE,
            status=CrmRecordStatus.NEEDS_SKIP_TRACE,
            display_name="Estate of Avery Stone",
            owner_name="Avery Stone Estate",
            property_address="123 Skyview Dr",
            source_record_ids=[source_record.id or ""],
            data_quality_score=80,
        )
    )
    membership = repository.add_source_membership(
        CrmRecordSourceMembership(
            business_id="limitless",
            environment="dev",
            record_id=record.id or "",
            source_record_id=source_record.id,
            source_system="harris_probate",
            source_key="case-123",
            list_name="April probate",
        )
    )
    updated = repository.update_record_status(record.id or "", status=CrmRecordStatus.MARKETABLE, reason="phone found")

    assert source_record.id == "crmsrc_1"
    assert record.id == "crmrec_1"
    assert membership.id == "crmmbr_1"
    assert updated.status == CrmRecordStatus.MARKETABLE
    assert repository.get_record(record.id or "") == updated
    assert [item.id for item in repository.list_records(business_id="limitless", environment="dev")] == [record.id]
    assert rows_by_table["crm_records"]["1"]["business_id"] == 7
    assert rows_by_table["crm_records"]["1"]["source_record_ids"] == [1]
    assert rows_by_table["crm_record_status_history"]["1"]["to_status"] == "marketable"


def test_promote_record_persists_history_and_marks_record_promoted() -> None:
    repository = CrmRecordsRepository(force_memory=True)
    record = repository.upsert_record(
        CrmRecord(
            business_id="limitless",
            environment="dev",
            record_type=CrmRecordType.PROPERTY,
            display_name="123 Skyview Dr",
            property_address="123 Skyview Dr",
        )
    )

    promotion = repository.promote_record(
        CrmRecordPromotion(
            business_id="limitless",
            environment="dev",
            record_id=record.id or "",
            opportunity_id="opp_42",
            reason="qualified seller conversation",
        )
    )

    assert promotion.id is not None
    assert repository.get_record(record.id or "").status == CrmRecordStatus.PROMOTED
