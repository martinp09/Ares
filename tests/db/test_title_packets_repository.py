from app.core.config import Settings
from app.db.title_packets import TitlePacketsRepository
from app.models.title_packets import TitlePacketPriority, TitlePacketRecord, TitlePacketStatus


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


def test_title_packets_repository_round_trips_through_supabase_adapter(monkeypatch) -> None:
    settings = build_settings()
    rows_by_table: dict[str, dict[str, dict]] = {
        "businesses": {
            "1": {"business_id": 7, "environment": "dev", "slug": "limitless"},
            "2": {"business_id": 9, "environment": "prod", "slug": "limitless"},
        }
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
            payload.setdefault("created_at", "2026-04-25T00:00:00Z")
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
        payload.setdefault("created_at", "2026-04-25T00:00:00Z")
        payload.setdefault("updated_at", "2026-04-25T00:00:00Z")
        table_rows[existing_id] = payload
        return [payload]

    def fake_resolve_tenant(business_id: str, environment: str, *, settings=None):
        return type("Tenant", (), {"business_pk": 7 if environment == "dev" else 9, "environment": environment})()

    monkeypatch.setattr("app.db.title_packets.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.title_packets.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.title_packets.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.title_packets.resolve_tenant", fake_resolve_tenant)

    repository = TitlePacketsRepository(settings=settings)
    created = repository.upsert(
        TitlePacketRecord(
            business_id="limitless",
            environment="dev",
            external_key="harris-hot18:0611340530007",
            lead_id="lead_11",
            status=TitlePacketStatus.NEEDS_REVIEW,
            priority=TitlePacketPriority.HIGH,
            owner_name="PLUMMER LETITIA W ESTATE OF",
            property_address="3324 S MACGREGOR WAY 77021",
            hctax_account="0611340530007",
            operator_lane="A - probate-first estate lead",
            facts={"tax_due": 63829.57},
        )
    )
    updated = repository.upsert(
        created.model_copy(update={"status": TitlePacketStatus.IN_REVIEW, "review_notes": "Docs pulled"})
    )

    assert created.id == "tpkt_1"
    assert updated.id == created.id
    assert updated.status == TitlePacketStatus.IN_REVIEW
    assert updated.review_notes == "Docs pulled"
    assert repository.get(created.id or "") == updated
    assert repository.get_by_key(
        business_id="limitless",
        environment="dev",
        dedupe_key="title-packet:harris-hot18:0611340530007",
    ) == updated
    assert [packet.id for packet in repository.list(business_id="limitless", environment="dev")] == [created.id]
    assert rows_by_table["title_packets"]["1"]["business_id"] == 7
    assert rows_by_table["title_packets"]["1"]["lead_id"] == 11


def test_record_from_supabase_maps_storage_columns_to_external_ids() -> None:
    record = TitlePacketsRepository._record_from_supabase(
        {
            "id": 42,
            "business_id": 7,
            "environment": "dev",
            "identity_key": "title-packet:harris-hot18:0611340530007",
            "external_key": "harris-hot18:0611340530007",
            "lead_id": 11,
            "status": "needs_review",
            "priority": "high",
            "artifact_refs": ["HOT_18_report.md"],
            "facts": {"tax_due": 63829.57},
            "raw_payload": {},
            "created_at": "2026-04-25T00:00:00Z",
            "updated_at": "2026-04-25T00:00:00Z",
        }
    )

    assert record.id == "tpkt_42"
    assert record.business_id == "7"
    assert record.lead_id == "lead_11"
    assert record.priority == TitlePacketPriority.HIGH
