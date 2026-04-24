from scripts.preview_rollout_readiness import preview_rollout_readiness


def test_preview_rollout_readiness_blocks_unverified_supabase_target(monkeypatch, tmp_path) -> None:
    import scripts.preview_rollout_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)

    result = preview_rollout_readiness(expected_project_ref="preview_project")

    assert result["status"] == "blocked"
    assert result["supabase"]["linked_project_ref"] is None
    assert result["supabase"]["linked_target_verified"] is False
    assert result["gates"]["can_apply_preview_migrations"] is False
    assert result["gates"]["live_provider_smoke_requires_operator_approval"] is True


def test_preview_rollout_readiness_requires_expected_project_ref_for_dry_run(monkeypatch, tmp_path) -> None:
    import scripts.preview_rollout_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("preview_project\n", encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(readiness, "_run_command", lambda command: {"command": command, "ok": True})

    result = preview_rollout_readiness(run_linked_dry_run=True)

    assert result["status"] == "blocked"
    assert result["supabase"]["linked_project_ref"] == "preview_project"
    assert result["supabase"]["linked_target_verified"] is False
    assert result["supabase"]["dry_run_executed"] is False
    assert result["supabase"]["commands"] == []


def test_preview_rollout_readiness_requires_supabase_backend_env(monkeypatch, tmp_path) -> None:
    import scripts.preview_rollout_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("preview_project\n", encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    for name in readiness.REQUIRED_PREVIEW_ENV:
        monkeypatch.setenv(name, "present")
    monkeypatch.setenv("CONTROL_PLANE_BACKEND", "memory")
    monkeypatch.setenv("MARKETING_BACKEND", "supabase")
    monkeypatch.setenv("LEAD_MACHINE_BACKEND", "supabase")
    monkeypatch.setenv("SITE_EVENTS_BACKEND", "supabase")

    result = preview_rollout_readiness(expected_project_ref="preview_project")

    assert result["supabase"]["linked_target_verified"] is True
    assert result["env"]["all_required_preview_present"] is True
    assert result["env"]["backend_env_supabase"] is False
    assert result["gates"]["can_apply_preview_migrations"] is False


def test_preview_rollout_readiness_requires_successful_linked_dry_run(monkeypatch, tmp_path) -> None:
    import scripts.preview_rollout_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("preview_project\n", encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(readiness.shutil, "which", lambda command: f"/bin/{command}")
    for name in readiness.REQUIRED_PREVIEW_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = preview_rollout_readiness(expected_project_ref="preview_project")

    assert result["status"] == "blocked"
    assert result["supabase"]["linked_target_verified"] is True
    assert result["supabase"]["dry_run_executed"] is False
    assert result["gates"]["can_apply_preview_migrations"] is False


def test_preview_rollout_readiness_can_reach_ready_after_linked_dry_run(monkeypatch, tmp_path) -> None:
    import scripts.preview_rollout_readiness as readiness

    project_ref = tmp_path / "supabase" / ".temp" / "project-ref"
    project_ref.parent.mkdir(parents=True)
    project_ref.write_text("preview_project\n", encoding="utf-8")
    monkeypatch.setattr(readiness, "SUPABASE_PROJECT_REF", project_ref)
    monkeypatch.setattr(readiness.shutil, "which", lambda command: f"/bin/{command}")
    monkeypatch.setattr(
        readiness,
        "_run_command",
        lambda command: {
            "command": command,
            "returncode": 0,
            "stdout": "ok",
            "stderr": "",
            "ok": True,
        },
    )
    for name in readiness.REQUIRED_PREVIEW_ENV:
        monkeypatch.setenv(name, "present")
    for name in ("CONTROL_PLANE_BACKEND", "MARKETING_BACKEND", "LEAD_MACHINE_BACKEND", "SITE_EVENTS_BACKEND"):
        monkeypatch.setenv(name, "supabase")

    result = preview_rollout_readiness(
        expected_project_ref="preview_project",
        run_linked_dry_run=True,
    )

    assert result["status"] == "ready"
    assert result["supabase"]["dry_run_executed"] is True
    assert len(result["supabase"]["commands"]) == 2
    assert result["gates"]["can_apply_preview_migrations"] is True
    assert result["gates"]["can_run_preview_smoke"] is True
    assert result["gates"]["live_provider_smoke_requires_operator_approval"] is True
