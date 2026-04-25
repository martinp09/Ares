from pathlib import Path

from scripts.production_promotion_readiness import production_promotion_readiness
from scripts.rollout_evidence import TODO_STATUS, build_evidence_skeleton


def _completed_staging_evidence(commit: str = "abc123") -> str:
    evidence = build_evidence_skeleton(
        environment="preview",
        commit=commit,
        generated_at="2026-04-24T18:00:00Z",
    )
    for key, value in list(evidence.items()):
        if value == TODO_STATUS:
            evidence[key] = "yes" if key.endswith("_present") else "passed"
    evidence.update(
        {
            "supabase_project_ref": "preview_project",
            "ares_runtime_url": "https://preview-ares.example.com",
            "mission_control_url": "https://preview-mc.example.com",
            "trigger_project_ref": "trigger_preview",
            "textgrid_status_callback_url": "https://preview-ares.example.com/marketing/webhooks/textgrid",
            "provider_webhook_urls": {
                "textgrid": "https://preview-ares.example.com/marketing/webhooks/textgrid",
                "calcom": "https://preview-ares.example.com/marketing/webhooks/calcom",
                "instantly": "https://preview-ares.example.com/lead-machine/webhooks/instantly",
            },
            "operator_owned_phone": "provided",
            "operator_owned_email": "provided",
        }
    )
    import json

    return json.dumps(evidence)


def test_production_promotion_blocks_without_acknowledgement(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text(_completed_staging_evidence(), encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(readiness, "_run_command", lambda command, timeout_seconds=120: {"command": command, "ok": True})
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=False,
        run_linked_dry_run=True,
    )

    assert result["status"] == "blocked"
    assert result["evidence"]["production_acknowledged"] is False
    assert result["gates"]["can_apply_production_migrations"] is False


def test_production_promotion_refuses_unverified_dry_run(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(readiness, "_run_command", lambda command, timeout_seconds=120: {"command": command, "ok": True})

    result = production_promotion_readiness(
        expected_project_ref="different_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=Path("/tmp/staging.json"),
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["supabase"]["linked_target_verified"] is False
    assert result["supabase"]["dry_run_executed"] is False
    assert result["supabase"]["commands"] == []
    assert result["status"] == "blocked"


def test_production_promotion_requires_same_commit_as_staging(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text('{"commit": "staging_commit"}', encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(readiness, "_run_command", lambda command, timeout_seconds=120: {"command": command, "ok": True})
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="staging_commit",
        current_commit="different_commit",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["git"]["same_commit_as_staging"] is False
    assert result["status"] == "blocked"


def test_production_promotion_requires_passed_linked_dry_run(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text(_completed_staging_evidence(), encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=False,
    )

    assert result["supabase"]["dry_run_executed"] is False
    assert result["status"] == "blocked"


def test_production_promotion_ready_after_all_non_live_gates(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text(_completed_staging_evidence(), encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command, timeout_seconds=120: {"command": command, "ok": True},
    )
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["status"] == "ready"
    assert result["evidence"]["staging_evidence_environment"] == "preview"
    assert result["evidence"]["staging_evidence_targets_verified"] is True
    assert result["evidence"]["staging_evidence_commit_matches"] is True
    assert result["gates"]["can_apply_production_migrations"] is True
    assert result["gates"]["can_deploy_production_runtime"] is True
    assert result["gates"]["can_run_live_provider_smoke"] is False


def test_production_promotion_live_smoke_requires_recipient_flags(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text(_completed_staging_evidence(), encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command, timeout_seconds=120: {"command": command, "ok": True},
    )
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")
    monkeypatch.setenv("ARES_SMOKE_SEND_SMS", "1")
    monkeypatch.setenv("ARES_SMOKE_TO_PHONE", "+15551234567")
    monkeypatch.setenv("ARES_SMOKE_SEND_EMAIL", "1")
    monkeypatch.setenv("ARES_SMOKE_TO_EMAIL", "operator@example.com")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        allow_live_provider_smoke=True,
        run_linked_dry_run=True,
    )

    assert result["status"] == "ready"
    assert result["gates"]["can_run_live_provider_smoke"] is True


def test_production_promotion_rejects_evidence_for_different_commit(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text('{"commit": "other_commit"}', encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command, timeout_seconds=120: {"command": command, "ok": True},
    )
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["evidence"]["staging_evidence_exists"] is True
    assert result["evidence"]["staging_evidence_commit"] == "other_commit"
    assert result["evidence"]["staging_evidence_commit_matches"] is False
    assert result["status"] == "blocked"


def test_production_promotion_rejects_invalid_evidence(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text("not-json", encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command, timeout_seconds=120: {"command": command, "ok": True},
    )
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["evidence"]["staging_evidence_exists"] is False
    assert result["status"] == "blocked"


def test_production_promotion_rejects_staging_evidence_with_todos(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text('{"commit": "abc123", "environment": "preview", "runtime_health": "TODO"}', encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command, timeout_seconds=120: {"command": command, "ok": True},
    )
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["evidence"]["staging_evidence_complete"] is False
    assert "runtime_health" in result["evidence"]["staging_evidence_todo_fields"]
    assert result["status"] == "blocked"


def test_production_promotion_rejects_production_evidence_as_staging(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text(_completed_staging_evidence().replace('"environment": "preview"', '"environment": "production"'), encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command, timeout_seconds=120: {"command": command, "ok": True},
    )
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["evidence"]["staging_evidence_environment"] == "production"
    assert result["evidence"]["staging_evidence_environment_ready"] is False
    assert result["status"] == "blocked"


def test_production_promotion_rejects_unexpected_staging_project(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text(_completed_staging_evidence(), encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command, timeout_seconds=120: {"command": command, "ok": True},
    )
    for name in readiness.REQUIRED_PRODUCTION_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = production_promotion_readiness(
        expected_project_ref="prod_project",
        staging_commit="abc123",
        current_commit="abc123",
        staging_evidence_path=evidence,
        expected_staging_project_ref="different_preview_project",
        expected_staging_runtime_url="https://preview-ares.example.com",
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["evidence"]["staging_evidence_project_ref_matches"] is False
    assert result["evidence"]["staging_evidence_targets_verified"] is False
    assert result["status"] == "blocked"
