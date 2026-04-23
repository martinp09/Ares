from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient
from app.db.tasks import TasksRepository
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def test_tasks_repository_round_trips_generic_contract_through_supabase_transactions(monkeypatch) -> None:
    settings = build_settings()
    rows_by_table: dict[str, dict[str, dict]] = {}

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
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
        return filtered

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
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
        table_rows = rows_by_table.setdefault(table, {})
        row_id = params.get("id", "")
        if row_id.startswith("eq."):
            existing_id = row_id[3:]
        else:
            existing_id = str(row.get("id", len(table_rows) + 1))
        payload = dict(table_rows.get(existing_id, {}))
        payload.update(row)
        payload["id"] = existing_id
        table_rows[existing_id] = payload
        return [payload]

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)

    repository = TasksRepository(client=SupabaseControlPlaneClient(settings), settings=settings)
    created = repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            title="Call lead after probate reply",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.HIGH,
            run_id="run_101",
            lead_id="lead_101",
            automation_run_id="aut_101",
            source_event_id="evt_101",
            idempotency_key="task-101",
            details={"source": "instantly_reply"},
        )
    )
    other_scope = repository.create(
        TaskRecord(
            business_id="otherco",
            environment="prod",
            title="Different scope task",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_REVIEW,
            priority=TaskPriority.NORMAL,
            lead_id="lead_other",
            idempotency_key="task-other",
            details={"source": "other"},
        )
    )

    reloaded = repository.get(created.id or "")
    assert reloaded is not None
    assert reloaded.id == created.id

    listed = repository.list(business_id="limitless", environment="dev", lead_id="lead_101")
    assert [task.id for task in listed] == [created.id]
    assert all(task.id != other_scope.id for task in listed)

    updated = repository.update(created.id or "", {"status": TaskStatus.IN_PROGRESS})
    assert updated is not None
    assert updated.status == TaskStatus.IN_PROGRESS
