import json

from scripts.rollout_evidence import (
    TODO_STATUS,
    build_evidence_skeleton,
    validate_evidence,
    write_evidence_skeleton,
)


def test_build_preview_evidence_skeleton_uses_non_secret_todos() -> None:
    skeleton = build_evidence_skeleton(
        environment="preview",
        commit="abc123",
        generated_at="2026-04-24T18:00:00Z",
    )

    assert skeleton["commit"] == "abc123"
    assert skeleton["environment"] == "preview"
    assert skeleton["operator_inputs_required"] == [
        "supabase_project_ref",
        "ares_runtime_url",
        "mission_control_url",
        "trigger_project_ref",
        "runtime_api_key_present",
        "supabase_service_role_key_present",
        "trigger_secret_key_present",
        "textgrid_status_callback_url",
        "provider_webhook_urls",
        "operator_owned_phone",
        "operator_owned_email",
    ]
    assert skeleton["runtime_api_key_present"] == TODO_STATUS
    assert skeleton["supabase_service_role_key_present"] == TODO_STATUS
    assert skeleton["trigger_secret_key_present"] == TODO_STATUS
    assert "SUPABASE_SERVICE_ROLE_KEY" not in json.dumps(skeleton)


def test_validate_evidence_reports_todo_fields() -> None:
    skeleton = build_evidence_skeleton(
        environment="preview",
        commit="abc123",
        generated_at="2026-04-24T18:00:00Z",
    )

    result = validate_evidence(skeleton)

    assert result["status"] == "blocked"
    assert "supabase_project_ref" in result["todo_fields"]
    assert "runtime_health" in result["todo_fields"]
    assert "notes" not in result["missing_fields"]


def test_validate_evidence_accepts_completed_required_preview_fields() -> None:
    skeleton = build_evidence_skeleton(
        environment="preview",
        commit="abc123",
        generated_at="2026-04-24T18:00:00Z",
    )
    for key in skeleton:
        if key == "notes":
            continue
        if skeleton[key] == TODO_STATUS:
            skeleton[key] = "present" if key.endswith("_present") else "passed"
    skeleton.update(
        {
            "supabase_project_ref": "preview_project",
            "ares_runtime_url": "https://preview-ares.example.com",
            "mission_control_url": "https://preview-mc.example.com",
            "trigger_project_ref": "trigger_preview",
            "runtime_api_key_present": "yes",
            "supabase_service_role_key_present": "yes",
            "trigger_secret_key_present": "yes",
            "textgrid_status_callback_url": "https://preview-ares.example.com/marketing/webhooks/textgrid",
            "provider_webhook_urls": {
                "textgrid": "https://preview-ares.example.com/marketing/webhooks/textgrid",
                "calcom": "https://preview-ares.example.com/marketing/webhooks/calcom",
                "instantly": "https://preview-ares.example.com/lead-machine/webhooks/instantly",
            },
            "operator_owned_phone": "provided",
            "operator_owned_email": "provided",
            "notes": [],
        }
    )

    result = validate_evidence(skeleton)

    assert result["status"] == "ready"
    assert result["todo_fields"] == []
    assert result["missing_fields"] == []


def test_write_evidence_skeleton_refuses_to_overwrite_by_default(tmp_path) -> None:
    target = tmp_path / "preview.json"
    target.write_text("{}", encoding="utf-8")

    result = write_evidence_skeleton(
        path=target,
        environment="preview",
        commit="abc123",
        generated_at="2026-04-24T18:00:00Z",
    )

    assert result["status"] == "blocked"
    assert result["error"] == "Evidence file already exists."
    assert target.read_text(encoding="utf-8") == "{}"
