from app.db.automation_runs import AutomationRunsRepository
from app.models.automation_runs import AutomationRunRecord, AutomationRunStatus


def test_upsert_in_supabase_excludes_runtime_only_deduped_flag(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(
        "app.db.automation_runs.resolve_tenant",
        lambda business_id, environment, settings=None: type("Tenant", (), {"business_pk": 1, "environment": environment})(),
    )
    monkeypatch.setattr("app.db.automation_runs.fetch_rows", lambda *args, **kwargs: [])

    def fake_insert_rows(table, rows, *, select=None, settings=None):
        captured["table"] = table
        captured["row"] = rows[0]
        return [
            {
                "id": 1,
                "business_id": 1,
                "environment": "dev",
                "workflow_name": "lead-outbound",
                "status": "in_progress",
                "idempotency_key": "smoke",
                "replay_key": "smoke",
                "input_payload": {},
                "output_payload": {},
                "metadata": {},
                "deduped": False,
            }
        ]

    monkeypatch.setattr("app.db.automation_runs.insert_rows", fake_insert_rows)

    repo = AutomationRunsRepository()
    repo._upsert_in_supabase(
        AutomationRunRecord(
            business_id="limitless",
            environment="dev",
            workflow_name="lead-outbound",
            status=AutomationRunStatus.IN_PROGRESS,
            idempotency_key="smoke",
            replay_key="smoke",
            deduped=True,
        )
    )

    assert captured["table"] == "automation_runs"
    assert "deduped" not in captured["row"]

