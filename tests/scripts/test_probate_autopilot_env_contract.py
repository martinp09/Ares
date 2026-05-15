from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.probate_autopilot_env_contract import validate_env_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "probate_autopilot_env_contract.py"


def _valid_env(tmp_path: Path) -> dict[str, str]:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    return {
        "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH": str(tmp_path / "source-runs.json"),
        "LEAD_MACHINE_ARTIFACT_ROOT": str(artifact_root),
        "LEAD_MACHINE_BUSINESS_ID": "limitless",
        "LEAD_MACHINE_ENVIRONMENT": "prod",
        "PROVIDER_LIVE_SENDS_ENABLED": "false",
        "INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED": "false",
        "HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED": "false",
        "VAPI_PROVIDER_LIVE_SENDS_ENABLED": "false",
        "LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED": "true",
        "LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED": "true",
        "LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED": "true",
        "LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED": "true",
        "LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED": "true",
        "LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED": "true",
    }


def test_env_contract_reports_healthy_no_send_preflight(tmp_path):
    report = validate_env_contract(_valid_env(tmp_path))

    assert report["status"] == "healthy"
    assert report["no_send_ok"] is True
    assert report["live_intelligence_ready"] is True
    assert report["blockers"] == []
    assert report["warnings"] == []
    assert report["side_effects"] == {
        "created_files_or_directories": False,
        "live_source_calls": False,
        "provider_mutations": False,
    }
    assert not (tmp_path / "source-runs.json").exists()


def test_env_contract_blocks_missing_durable_runtime_paths(tmp_path):
    env = _valid_env(tmp_path)
    env.pop("LEAD_MACHINE_SOURCE_RUNS_STATE_PATH")
    env.pop("LEAD_MACHINE_ARTIFACT_ROOT")

    report = validate_env_contract(env)

    assert report["status"] == "blocked"
    blocker_names = {blocker["name"] for blocker in report["blockers"]}
    assert "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH" in blocker_names
    assert "LEAD_MACHINE_ARTIFACT_ROOT" in blocker_names


def test_env_contract_blocks_outbound_provider_gates(tmp_path):
    env = _valid_env(tmp_path)
    env["PROVIDER_LIVE_SENDS_ENABLED"] = "true"
    env["HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED"] = "yes"

    report = validate_env_contract(env)

    assert report["status"] == "blocked"
    assert report["no_send_ok"] is False
    blocker_names = {blocker["name"] for blocker in report["blockers"]}
    assert "PROVIDER_LIVE_SENDS_ENABLED" in blocker_names
    assert "HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED" in blocker_names


def test_env_contract_blocks_invalid_boolean_values(tmp_path):
    env = _valid_env(tmp_path)
    env["LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED"] = "maybe"

    report = validate_env_contract(env)

    assert report["status"] == "blocked"
    assert any(blocker["name"] == "LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED" for blocker in report["blockers"])


def test_env_contract_marks_invalid_outbound_gate_not_no_send_ok(tmp_path):
    env = _valid_env(tmp_path)
    env["INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED"] = "maybe"

    report = validate_env_contract(env)

    assert report["status"] == "blocked"
    assert report["no_send_ok"] is False
    assert any(blocker["name"] == "INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED" for blocker in report["blockers"])


def test_env_contract_warns_when_live_intelligence_gates_are_not_explicit(tmp_path):
    env = _valid_env(tmp_path)
    env.pop("LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED")
    env.pop("LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED")

    report = validate_env_contract(env)

    assert report["status"] == "warning"
    assert report["live_intelligence_ready"] is False
    warning_names = {warning["name"] for warning in report["warnings"]}
    assert "LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED" in warning_names
    assert "LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED" in warning_names


def test_env_contract_can_block_disabled_scheduled_live_when_required(tmp_path):
    env = _valid_env(tmp_path)
    env["LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED"] = "false"

    report = validate_env_contract(env, require_scheduled_live=True)

    assert report["status"] == "blocked"
    assert any(blocker["name"] == "LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED" for blocker in report["blockers"])


def test_env_contract_blocks_nonexistent_path_targets(tmp_path):
    env = _valid_env(tmp_path)
    env["LEAD_MACHINE_SOURCE_RUNS_STATE_PATH"] = str(tmp_path / "missing" / "source-runs.json")
    env["LEAD_MACHINE_ARTIFACT_ROOT"] = str(tmp_path / "missing-artifacts")

    report = validate_env_contract(env)

    assert report["status"] == "blocked"
    messages = "\n".join(str(blocker["message"]) for blocker in report["blockers"])
    assert "parent directory does not exist" in messages
    assert "artifact root directory does not exist" in messages


def test_env_contract_cli_reads_env_file_without_printing_secret_values(tmp_path):
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                f"LEAD_MACHINE_SOURCE_RUNS_STATE_PATH={tmp_path / 'source-runs.json'}",
                f"LEAD_MACHINE_ARTIFACT_ROOT={artifact_root}",
                "LEAD_MACHINE_BUSINESS_ID=limitless",
                "LEAD_MACHINE_ENVIRONMENT=prod",
                "PROVIDER_LIVE_SENDS_ENABLED=false",
                "INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED=false",
                "HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED=false",
                "VAPI_PROVIDER_LIVE_SENDS_ENABLED=false",
                "LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true",
                "LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED=true",
                "LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED=true",
                "LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED=true",
                "LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED=true",
                "LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED=true",
                "HUBSPOT_ACCESS_TOKEN=super-secret-token",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--env-file", str(env_file), "--require-scheduled-live"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["status"] == "healthy"
    assert "super-secret-token" not in result.stdout
