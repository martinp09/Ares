from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SUPABASE_PROJECT_REF = REPO_ROOT / "supabase" / ".temp" / "project-ref"
REQUIRED_PREVIEW_ENV = (
    "RUNTIME_API_KEY",
    "CONTROL_PLANE_BACKEND",
    "MARKETING_BACKEND",
    "LEAD_MACHINE_BACKEND",
    "SITE_EVENTS_BACKEND",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
    "TRIGGER_SECRET_KEY",
)
REQUIRED_PROVIDER_SHAPE_ENV = (
    "TEXTGRID_ACCOUNT_SID",
    "TEXTGRID_AUTH_TOKEN",
    "TEXTGRID_FROM_NUMBER",
    "TEXTGRID_STATUS_CALLBACK_URL",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "CAL_BOOKING_URL",
)
SAFE_BACKEND_VALUE = "supabase"


def _read_project_ref() -> str | None:
    if not SUPABASE_PROJECT_REF.exists():
        return None
    value = SUPABASE_PROJECT_REF.read_text(encoding="utf-8").strip()
    return value or None


def _env_status(names: tuple[str, ...]) -> dict[str, bool]:
    return {name: bool(os.environ.get(name)) for name in names}


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


def _has_command(name: str, *local_paths: str) -> bool:
    if shutil.which(name):
        return True
    return any((REPO_ROOT / local_path).exists() for local_path in local_paths)


def _has_package_script(package_json: Path, script_name: str) -> bool:
    if not package_json.exists():
        return False
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return script_name in dict(package.get("scripts") or {})


def _backend_env_ready() -> bool:
    return all(os.environ.get(name) == SAFE_BACKEND_VALUE for name in (
        "CONTROL_PLANE_BACKEND",
        "MARKETING_BACKEND",
        "LEAD_MACHINE_BACKEND",
        "SITE_EVENTS_BACKEND",
    ))


def preview_rollout_readiness(
    *,
    expected_project_ref: str | None = None,
    run_linked_dry_run: bool = False,
) -> dict[str, Any]:
    project_ref = _read_project_ref()
    supabase_cli = _has_command("supabase")
    trigger_cli = _has_command(
        "trigger.dev",
        "trigger/node_modules/.bin/trigger.dev",
        "node_modules/.bin/trigger.dev",
    ) or _has_package_script(REPO_ROOT / "trigger" / "package.json", "dev")
    vercel_cli = _has_command("vercel")
    docker_cli = _has_command("docker")
    npm_cli = _has_command("npm")
    uv_cli = _has_command("uv")

    required_env = _env_status(REQUIRED_PREVIEW_ENV)
    provider_env = _env_status(REQUIRED_PROVIDER_SHAPE_ENV)
    project_ref_matches = expected_project_ref is not None and project_ref == expected_project_ref
    linked_target_verified = bool(project_ref and project_ref_matches)

    checks: dict[str, Any] = {
        "cli": {
            "supabase": bool(supabase_cli),
            "docker": bool(docker_cli),
            "npm": bool(npm_cli),
            "uv": bool(uv_cli),
            "trigger": bool(trigger_cli),
            "vercel": bool(vercel_cli),
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
            "required_preview": required_env,
            "provider_shape": provider_env,
            "all_required_preview_present": all(required_env.values()),
            "all_provider_shape_present": all(provider_env.values()),
            "backend_env_supabase": _backend_env_ready(),
        },
        "gates": {
            "can_apply_preview_migrations": False,
            "can_run_preview_smoke": False,
            "live_provider_smoke_requires_operator_approval": True,
        },
    }

    if run_linked_dry_run:
        if not supabase_cli:
            checks["supabase"]["dry_run_error"] = "supabase CLI is not installed."
        elif not linked_target_verified:
            checks["supabase"]["dry_run_error"] = "Linked Supabase target is not verified."
        else:
            checks["supabase"]["dry_run_executed"] = True
            checks["supabase"]["commands"] = [
                _run_command(["supabase", "migration", "list", "--linked"]),
                _run_command(["supabase", "db", "push", "--dry-run", "--linked"]),
            ]

    supabase_dry_run_ok = bool(
        checks["supabase"]["dry_run_executed"]
        and all(command["ok"] for command in checks["supabase"]["commands"])
    )
    checks["gates"]["can_apply_preview_migrations"] = bool(
        linked_target_verified
        and checks["env"]["all_required_preview_present"]
        and checks["env"]["backend_env_supabase"]
        and supabase_dry_run_ok
    )
    checks["gates"]["can_run_preview_smoke"] = bool(
        checks["gates"]["can_apply_preview_migrations"]
        and checks["cli"]["npm"]
        and checks["cli"]["uv"]
    )
    checks["status"] = "ready" if checks["gates"]["can_run_preview_smoke"] else "blocked"
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-project-ref")
    parser.add_argument("--run-linked-dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = preview_rollout_readiness(
        expected_project_ref=args.expected_project_ref,
        run_linked_dry_run=args.run_linked_dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
