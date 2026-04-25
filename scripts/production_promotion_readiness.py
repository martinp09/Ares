from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.rollout_evidence import validate_evidence

SUPABASE_PROJECT_REF = REPO_ROOT / "supabase" / ".temp" / "project-ref"
REQUIRED_PRODUCTION_ENV = (
    "RUNTIME_API_KEY",
    "CONTROL_PLANE_BACKEND",
    "MARKETING_BACKEND",
    "LEAD_MACHINE_BACKEND",
    "SITE_EVENTS_BACKEND",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "TRIGGER_SECRET_KEY",
    "TEXTGRID_ACCOUNT_SID",
    "TEXTGRID_AUTH_TOKEN",
    "TEXTGRID_FROM_NUMBER",
    "TEXTGRID_STATUS_CALLBACK_URL",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "CAL_BOOKING_URL",
)


def _read_project_ref() -> str | None:
    if not SUPABASE_PROJECT_REF.exists():
        return None
    value = SUPABASE_PROJECT_REF.read_text(encoding="utf-8").strip()
    return value or None


def _env_status(names: tuple[str, ...]) -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in names}


def _backend_env_ready() -> bool:
    return all(os.environ.get(name) == "supabase" for name in (
        "CONTROL_PLANE_BACKEND",
        "MARKETING_BACKEND",
        "LEAD_MACHINE_BACKEND",
        "SITE_EVENTS_BACKEND",
    ))


def _run_command(command: list[str], *, timeout_seconds: int = 120) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        return {
            "command": command,
            "returncode": 127,
            "stdout": "",
            "stderr": str(exc),
            "ok": False,
        }
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "ok": completed.returncode == 0,
    }


def _load_staging_evidence(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _evidence_commit(evidence: dict[str, Any] | None) -> str | None:
    if evidence is None:
        return None
    for key in ("commit", "commit_sha", "staging_commit"):
        value = evidence.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    git_block = evidence.get("git")
    if isinstance(git_block, dict):
        for key in ("commit", "commit_sha", "current_commit"):
            value = git_block.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def production_promotion_readiness(
    *,
    expected_project_ref: str | None = None,
    expected_staging_project_ref: str | None = None,
    expected_staging_runtime_url: str | None = None,
    expected_staging_mission_control_url: str | None = None,
    staging_commit: str | None = None,
    current_commit: str | None = None,
    staging_evidence_path: Path | None = None,
    backup_reference: str | None = None,
    acknowledge_production: bool = False,
    allow_live_provider_smoke: bool = False,
    run_linked_dry_run: bool = False,
) -> dict[str, Any]:
    project_ref = _read_project_ref()
    linked_target_verified = bool(expected_project_ref and project_ref == expected_project_ref)
    effective_current_commit = current_commit or _run_command(["git", "rev-parse", "HEAD"], timeout_seconds=15)["stdout"]
    staging_evidence = _load_staging_evidence(staging_evidence_path)
    evidence_commit = _evidence_commit(staging_evidence)
    staging_evidence_validation = validate_evidence(staging_evidence) if staging_evidence is not None else None
    staging_evidence_complete = bool(
        staging_evidence_validation and staging_evidence_validation["status"] == "ready"
    )
    staging_environment = staging_evidence.get("environment") if staging_evidence else None
    staging_evidence_environment_ready = staging_environment in {"preview", "staging"}
    staging_project_ref = staging_evidence.get("supabase_project_ref") if staging_evidence else None
    staging_runtime_url = staging_evidence.get("ares_runtime_url") if staging_evidence else None
    staging_mission_control_url = staging_evidence.get("mission_control_url") if staging_evidence else None
    staging_project_ref_matches = bool(
        expected_staging_project_ref
        and staging_project_ref == expected_staging_project_ref
    )
    staging_runtime_url_matches = bool(
        expected_staging_runtime_url
        and staging_runtime_url == expected_staging_runtime_url
    )
    staging_mission_control_url_matches = (
        True
        if expected_staging_mission_control_url is None
        else staging_mission_control_url == expected_staging_mission_control_url
    )
    staging_evidence_targets_verified = bool(
        staging_evidence_environment_ready
        and staging_project_ref_matches
        and staging_runtime_url_matches
        and staging_mission_control_url_matches
    )
    same_commit_as_staging = bool(
        staging_commit
        and effective_current_commit == staging_commit
        and evidence_commit == staging_commit
    )
    staging_evidence_exists = staging_evidence is not None
    backup_ready = bool(backup_reference)
    production_ack_ready = acknowledge_production is True
    required_env = _env_status(REQUIRED_PRODUCTION_ENV)

    result: dict[str, Any] = {
        "status": "blocked",
        "git": {
            "current_commit": effective_current_commit,
            "staging_commit": staging_commit,
            "same_commit_as_staging": same_commit_as_staging,
        },
        "supabase": {
            "linked_project_ref": project_ref,
            "expected_project_ref": expected_project_ref,
            "linked_target_verified": linked_target_verified,
            "dry_run_requested": run_linked_dry_run,
            "dry_run_executed": False,
            "commands": [],
        },
        "env": {
            "required_production": required_env,
            "all_required_production_present": all(required_env.values()),
            "backend_env_supabase": _backend_env_ready(),
        },
        "evidence": {
            "staging_evidence_path": str(staging_evidence_path) if staging_evidence_path else None,
            "staging_evidence_exists": staging_evidence_exists,
            "staging_evidence_complete": staging_evidence_complete,
            "staging_evidence_missing_fields": staging_evidence_validation["missing_fields"]
            if staging_evidence_validation
            else [],
            "staging_evidence_todo_fields": staging_evidence_validation["todo_fields"]
            if staging_evidence_validation
            else [],
            "staging_evidence_commit": evidence_commit,
            "staging_evidence_commit_matches": bool(staging_commit and evidence_commit == staging_commit),
            "staging_evidence_environment": staging_environment,
            "staging_evidence_environment_ready": staging_evidence_environment_ready,
            "expected_staging_project_ref": expected_staging_project_ref,
            "staging_evidence_project_ref": staging_project_ref,
            "staging_evidence_project_ref_matches": staging_project_ref_matches,
            "expected_staging_runtime_url": expected_staging_runtime_url,
            "staging_evidence_runtime_url": staging_runtime_url,
            "staging_evidence_runtime_url_matches": staging_runtime_url_matches,
            "expected_staging_mission_control_url": expected_staging_mission_control_url,
            "staging_evidence_mission_control_url": staging_mission_control_url,
            "staging_evidence_mission_control_url_matches": staging_mission_control_url_matches,
            "staging_evidence_targets_verified": staging_evidence_targets_verified,
            "backup_reference": backup_reference,
            "backup_ready": backup_ready,
            "production_acknowledged": production_ack_ready,
        },
        "gates": {
            "can_apply_production_migrations": False,
            "can_deploy_production_runtime": False,
            "can_run_live_provider_smoke": False,
        },
    }

    if run_linked_dry_run:
        if not linked_target_verified:
            result["supabase"]["dry_run_error"] = "Linked production Supabase target is not verified."
        else:
            result["supabase"]["dry_run_executed"] = True
            result["supabase"]["commands"] = [
                _run_command(["supabase", "migration", "list", "--linked"]),
                _run_command(["supabase", "db", "push", "--dry-run", "--linked"]),
            ]

    dry_run_ok = bool(
        result["supabase"]["dry_run_executed"]
        and all(command["ok"] for command in result["supabase"]["commands"])
    )
    promotion_base_ready = bool(
        production_ack_ready
        and linked_target_verified
        and same_commit_as_staging
        and staging_evidence_exists
        and staging_evidence_complete
        and staging_evidence_targets_verified
        and backup_ready
        and result["env"]["all_required_production_present"]
        and result["env"]["backend_env_supabase"]
        and dry_run_ok
    )
    result["gates"]["can_apply_production_migrations"] = promotion_base_ready
    result["gates"]["can_deploy_production_runtime"] = promotion_base_ready
    result["gates"]["can_run_live_provider_smoke"] = bool(
        promotion_base_ready
        and allow_live_provider_smoke
        and os.environ.get("ARES_SMOKE_SEND_SMS") == "1"
        and bool(os.environ.get("ARES_SMOKE_TO_PHONE"))
        and os.environ.get("ARES_SMOKE_SEND_EMAIL") == "1"
        and bool(os.environ.get("ARES_SMOKE_TO_EMAIL"))
    )
    result["status"] = "ready" if promotion_base_ready else "blocked"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-project-ref", required=True)
    parser.add_argument("--expected-staging-project-ref", required=True)
    parser.add_argument("--expected-staging-runtime-url", required=True)
    parser.add_argument("--expected-staging-mission-control-url")
    parser.add_argument("--staging-commit", required=True)
    parser.add_argument("--staging-evidence-path", type=Path, required=True)
    parser.add_argument("--backup-reference", required=True)
    parser.add_argument("--acknowledge-production", action="store_true")
    parser.add_argument("--allow-live-provider-smoke", action="store_true")
    parser.add_argument("--run-linked-dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = production_promotion_readiness(
        expected_project_ref=args.expected_project_ref,
        expected_staging_project_ref=args.expected_staging_project_ref,
        expected_staging_runtime_url=args.expected_staging_runtime_url,
        expected_staging_mission_control_url=args.expected_staging_mission_control_url,
        staging_commit=args.staging_commit,
        staging_evidence_path=args.staging_evidence_path,
        backup_reference=args.backup_reference,
        acknowledge_production=args.acknowledge_production,
        allow_live_provider_smoke=args.allow_live_provider_smoke,
        run_linked_dry_run=args.run_linked_dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
