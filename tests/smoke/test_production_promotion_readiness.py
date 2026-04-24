from pathlib import Path

from scripts.production_promotion_readiness import production_promotion_readiness


def test_production_promotion_blocks_without_acknowledgement(monkeypatch, tmp_path) -> None:
    import scripts.production_promotion_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("prod_project\n", encoding="utf-8")
    evidence = tmp_path / "staging.json"
    evidence.write_text('{"commit": "abc123"}', encoding="utf-8")
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
    evidence.write_text('{"commit": "abc123"}', encoding="utf-8")
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
    evidence.write_text('{"commit": "abc123"}', encoding="utf-8")
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
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["status"] == "ready"
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
    evidence.write_text('{"commit": "abc123"}', encoding="utf-8")
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
        backup_reference="backup_123",
        acknowledge_production=True,
        run_linked_dry_run=True,
    )

    assert result["evidence"]["staging_evidence_exists"] is False
    assert result["status"] == "blocked"
