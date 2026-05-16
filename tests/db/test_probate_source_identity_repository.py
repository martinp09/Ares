from __future__ import annotations

import json

from app.core.config import Settings
from app.db.lead_machine_supabase import LeadMachineTenant
from app.db.probate_source_identities import ProbateSourceIdentityRepository
from app.models.source_runs import SourceRun, SourceRunArtifact, SourceRunStatus


def _key(char: str) -> str:
    return "probate_case_sha256:" + (char * 64)


def test_source_identity_repository_lists_scope_isolated_remote_keys(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.db.probate_source_identities.resolve_tenant",
        lambda business_id, environment, settings=None: LeadMachineTenant(business_pk=101, environment="prod"),
    )

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        captured["table"] = table
        captured["params"] = dict(params)
        return [
            {"county": "harris", "source_identity_key": _key("a")},
            {"county": "montgomery", "source_identity_key": _key("b")},
        ]

    monkeypatch.setattr("app.db.probate_source_identities.fetch_rows", fake_fetch_rows)

    result = ProbateSourceIdentityRepository(settings=settings).list_identity_keys(
        business_id="limitless",
        environment="prod",
        run_scope="autonomous",
        counties=("harris", "montgomery"),
    )

    assert result == {"harris": {_key("a")}, "montgomery": {_key("b")}}
    assert captured["table"] == "probate_source_identities"
    assert captured["params"] == {
        "select": "county,source_identity_key",
        "business_id": "eq.101",
        "environment": "eq.prod",
        "source_run_scope": "eq.autonomous",
        "county": "in.(harris,montgomery)",
    }


def test_source_identity_repository_records_completed_probate_source_run(monkeypatch, tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    existing_key = _key("c")
    new_key = _key("d")
    artifact_path = tmp_path / "normalized_source_rows.jsonl"
    artifact_path.write_text(
        json.dumps({"case_number": "H-100", "source_identity_key": existing_key, "keep_now": True, "raw": {"pii": "omit"}})
        + "\n"
        + json.dumps({"case_number": "H-200", "source_identity_key": new_key, "keep_now": False, "raw": {"pii": "omit"}})
        + "\n",
        encoding="utf-8",
    )
    run = SourceRun(
        id="source_run_1",
        business_id="limitless",
        environment="prod",
        source_key="harris_county_probate:midday:2026-05-16",
        source_label="Harris probate",
        source_lane="harris_county_probate",
        county="harris",
        run_kind="midday",
        idempotency_key="idem-1:harris",
        record_count=2,
        keep_now_count=1,
        status=SourceRunStatus.COMPLETED,
        artifacts=[SourceRunArtifact(path=str(artifact_path), artifact_type="normalized_source_rows", record_count=2)],
        metadata={"source_run_scope": "autonomous", "source_identity_version": "county_case_sha256_v1"},
    )
    patches: list[dict] = []
    inserts: list[dict] = []

    monkeypatch.setattr(
        "app.db.probate_source_identities.resolve_tenant",
        lambda business_id, environment, settings=None: LeadMachineTenant(business_pk=101, environment="prod"),
    )

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        assert table == "probate_source_identities"
        if params.get("source_identity_key") == f"eq.{existing_key}":
            return [{"id": "existing-row", "seen_count": 2}]
        return []

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        patches.append({"table": table, "params": dict(params), "row": dict(row), "select": select})
        return [{"id": params["id"].removeprefix("eq.")}]

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        for row in rows:
            inserts.append(dict(row))
        return [{"id": "new-row"} for _ in rows]

    monkeypatch.setattr("app.db.probate_source_identities.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.probate_source_identities.patch_rows", fake_patch_rows)
    monkeypatch.setattr("app.db.probate_source_identities.insert_rows", fake_insert_rows)

    result = ProbateSourceIdentityRepository(settings=settings).record_source_run(run)

    assert result == 2
    assert patches == [
        {
            "table": "probate_source_identities",
            "params": {"id": "eq.existing-row"},
            "row": {
                "last_source_run_id": "source_run_1",
                "last_source_key": "harris_county_probate:midday:2026-05-16",
                "last_idempotency_key": "idem-1:harris",
                "seen_count": 3,
                "latest_record_count": 2,
                "latest_keep_now": True,
                "latest_metadata": {
                    "source_lane": "harris_county_probate",
                    "run_kind": "midday",
                    "source_identity_version": "county_case_sha256_v1",
                    "source_run_scope": "autonomous",
                },
            },
            "select": "id",
        }
    ]
    assert inserts == [
        {
            "business_id": 101,
            "environment": "prod",
            "source_run_scope": "autonomous",
            "county": "harris",
            "source_identity_key": new_key,
            "source_identity_version": "county_case_sha256_v1",
            "first_source_run_id": "source_run_1",
            "first_source_key": "harris_county_probate:midday:2026-05-16",
            "first_idempotency_key": "idem-1:harris",
            "last_source_run_id": "source_run_1",
            "last_source_key": "harris_county_probate:midday:2026-05-16",
            "last_idempotency_key": "idem-1:harris",
            "seen_count": 1,
            "latest_record_count": 2,
            "latest_keep_now": False,
            "latest_metadata": {
                "source_lane": "harris_county_probate",
                "run_kind": "midday",
                "source_identity_version": "county_case_sha256_v1",
                "source_run_scope": "autonomous",
            },
        }
    ]


def test_source_identity_repository_records_from_metadata_when_artifact_file_is_absent(monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    new_key = _key("e")
    run = SourceRun(
        id="source_run_metadata",
        business_id="limitless",
        environment="prod",
        source_key="harris_county_probate:midday:metadata",
        source_label="Harris probate",
        source_lane="harris_county_probate",
        county="harris",
        run_kind="midday",
        record_count=1,
        status=SourceRunStatus.COMPLETED,
        artifacts=[SourceRunArtifact(path="/opt/ares/lead-data/missing/normalized_source_rows.jsonl", artifact_type="normalized_source_rows", record_count=1)],
        metadata={
            "source_run_scope": "autonomous",
            "source_identity_version": "county_case_sha256_v1",
            "source_identity_records": [{"source_identity_key": new_key, "keep_now": True}],
        },
    )
    inserts: list[dict] = []

    monkeypatch.setattr(
        "app.db.probate_source_identities.resolve_tenant",
        lambda business_id, environment, settings=None: LeadMachineTenant(business_pk=101, environment="prod"),
    )
    monkeypatch.setattr("app.db.probate_source_identities.fetch_rows", lambda *args, **kwargs: [])

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        inserts.extend(dict(row) for row in rows)
        return [{"id": "new-row"} for _ in rows]

    monkeypatch.setattr("app.db.probate_source_identities.insert_rows", fake_insert_rows)

    assert ProbateSourceIdentityRepository(settings=settings).record_source_run(run) == 1
    assert inserts[0]["source_identity_key"] == new_key
    assert inserts[0]["latest_keep_now"] is True


def test_source_identity_repository_skips_isolated_manual_environment(monkeypatch, tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )
    called = False

    def fake_resolve_tenant(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("manual-isolated environment should not resolve remote tenant")

    monkeypatch.setattr("app.db.probate_source_identities.resolve_tenant", fake_resolve_tenant)
    repo = ProbateSourceIdentityRepository(settings=settings)

    assert repo.list_identity_keys(
        business_id="limitless",
        environment="prod-manual",
        run_scope="manual",
        counties=("harris",),
    ) == {"harris": set()}
    assert repo.record_source_run(
        SourceRun(
            id="source_run_manual",
            business_id="limitless",
            environment="prod-manual",
            source_key="manual",
            source_label="Manual",
            source_lane="harris_county_probate",
            county="harris",
            metadata={"source_run_scope": "manual"},
        )
    ) == 0
    assert called is False
