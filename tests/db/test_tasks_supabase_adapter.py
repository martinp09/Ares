from app.core.config import Settings
from app.db.tasks import TasksRepository
from app.models.tasks import TaskPriority, TaskRecord, TaskStatus, TaskType


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def test_tasks_repository_round_trips_generic_contract_through_supabase_adapter(monkeypatch) -> None:
    settings = build_settings()
    rows_by_table: dict[str, dict[str, dict]] = {}
    tenant_by_scope = {("limitless", "dev"): 7, ("otherco", "prod"): 8}

    def fake_resolve_tenant(business_id: str, environment: str, *, settings=None):
        return type(
            "Tenant",
            (),
            {"business_pk": tenant_by_scope[(business_id, environment)], "environment": environment},
        )()

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
        limit = params.get("limit")
        if isinstance(limit, str) and limit.isdigit():
            return filtered[: int(limit)]
        return filtered

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        inserted = []
        for row in rows:
            payload = dict(row)
            row_id = str(payload.get("id", len(table_rows) + 1))
            payload["id"] = row_id
            payload.setdefault("created_at", "2026-04-23T00:00:00Z")
            payload.setdefault("updated_at", payload["created_at"])
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
        payload.setdefault("created_at", "2026-04-23T00:00:00Z")
        payload.setdefault("updated_at", "2026-04-23T00:00:00Z")
        table_rows[existing_id] = payload
        return [payload]

    monkeypatch.setattr("app.db.tasks.resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr("app.db.tasks.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.tasks.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.tasks.patch_rows", fake_patch_rows)

    repository = TasksRepository(settings=settings)
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
            assigned_to="operator_1",
            idempotency_key="task-101",
            details={"source": "instantly_reply"},
        )
    )
    deduped = repository.create(
        TaskRecord(
            business_id="limitless",
            environment="dev",
            title="Should dedupe",
            status=TaskStatus.OPEN,
            task_type=TaskType.MANUAL_CALL,
            priority=TaskPriority.NORMAL,
            idempotency_key="task-101",
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
    assert reloaded.title == "Call lead after probate reply"
    assert reloaded.run_id == "run_101"
    assert reloaded.automation_run_id == "aut_101"
    assert reloaded.source_event_id == "evt_101"
    assert reloaded.assigned_to == "operator_1"
    assert deduped.id == created.id
    assert deduped.deduped is True

    listed = repository.list(business_id="limitless", environment="dev", lead_id="lead_101")
    assert [task.id for task in listed] == [created.id]
    assert all(task.id != other_scope.id for task in listed)

    updated = repository.update(
        created.id or "",
        {"status": TaskStatus.IN_PROGRESS, "assigned_to": "operator_2"},
    )
    assert updated is not None
    assert updated.status == TaskStatus.IN_PROGRESS
    assert updated.assigned_to == "operator_2"
    assert rows_by_table["tasks"]["1"]["assignee"] == "operator_2"


def test_create_manual_call_uses_generic_supabase_create_path(monkeypatch) -> None:
    settings = build_settings()
    rows_by_table: dict[str, dict[str, dict]] = {}

    def fake_resolve_tenant(business_id: str, environment: str, *, settings=None):
        return type("Tenant", (), {"business_pk": 7, "environment": environment})()

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
        limit = params.get("limit")
        if isinstance(limit, str) and limit.isdigit():
            return filtered[: int(limit)]
        return filtered

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        table_rows = rows_by_table.setdefault(table, {})
        inserted = []
        for row in rows:
            payload = dict(row)
            row_id = str(len(table_rows) + 1)
            payload["id"] = row_id
            payload.setdefault("created_at", "2026-04-23T00:00:00Z")
            payload.setdefault("updated_at", payload["created_at"])
            table_rows[row_id] = payload
            inserted.append(payload)
        return inserted

    monkeypatch.setattr("app.db.tasks.resolve_tenant", fake_resolve_tenant)
    monkeypatch.setattr("app.db.tasks.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.tasks.insert_rows", fake_insert_rows)

    repository = TasksRepository(settings=settings)
    first = repository.create_manual_call(
        business_id="limitless",
        environment="dev",
        contact_id="ctc_123",
        title="Call lead after high-intent reply",
    )
    second = repository.create_manual_call(
        business_id="limitless",
        environment="dev",
        contact_id="ctc_123",
        title="Call lead after high-intent reply",
    )

    assert first.id == "tsk_1"
    assert second.id == first.id
    assert second.deduped is True
    assert len(rows_by_table["tasks"]) == 1
    stored = rows_by_table["tasks"]["1"]
    assert stored["title"] == "Call lead after high-intent reply"
    assert stored["lead_id"] == "ctc_123"
    assert stored["run_external_id"] == "ctc_123"
