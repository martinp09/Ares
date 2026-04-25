from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

TODO_STATUS = "TODO"
VALID_ENVIRONMENTS = ("preview", "staging", "production")
REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FIELDS = (
    "commit",
    "environment",
    "generated_at",
    "supabase_project_ref",
    "ares_runtime_url",
    "mission_control_url",
    "trigger_project_ref",
    "runtime_api_key_present",
    "supabase_service_role_key_present",
    "trigger_secret_key_present",
    "textgrid_status_callback_url",
    "provider_webhook_urls",
    "migration_dry_run",
    "migration_apply",
    "runtime_health",
    "runtime_auth",
    "trigger_runtime_callbacks",
    "mission_control_api_source",
    "provider_webhooks_configured",
    "provider_request_shape_smoke",
    "no_live_smoke",
    "live_provider_smoke",
    "live_provider_smoke_recipients",
    "operator_owned_phone",
    "operator_owned_email",
    "rollback_reference",
    "notes",
)

OPERATOR_INPUT_FIELDS = (
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
)

SECRET_FIELD_NAMES = (
    "RUNTIME_API_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "TRIGGER_SECRET_KEY",
    "TEXTGRID_AUTH_TOKEN",
    "RESEND_API_KEY",
)


def _current_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return completed.stdout.strip() if completed.returncode == 0 else TODO_STATUS


def build_evidence_skeleton(
    *,
    environment: str,
    commit: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if environment not in VALID_ENVIRONMENTS:
        raise ValueError(f"environment must be one of: {', '.join(VALID_ENVIRONMENTS)}")

    rollback_reference = TODO_STATUS if environment == "production" else "not-required-for-preview"
    return {
        "commit": commit or _current_commit(),
        "environment": environment,
        "generated_at": generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "supabase_project_ref": TODO_STATUS,
        "ares_runtime_url": TODO_STATUS,
        "mission_control_url": TODO_STATUS,
        "trigger_project_ref": TODO_STATUS,
        "runtime_api_key_present": TODO_STATUS,
        "supabase_service_role_key_present": TODO_STATUS,
        "trigger_secret_key_present": TODO_STATUS,
        "textgrid_status_callback_url": TODO_STATUS,
        "provider_webhook_urls": {
            "textgrid": TODO_STATUS,
            "calcom": TODO_STATUS,
            "instantly": TODO_STATUS,
        },
        "migration_dry_run": TODO_STATUS,
        "migration_apply": TODO_STATUS,
        "runtime_health": TODO_STATUS,
        "runtime_auth": TODO_STATUS,
        "trigger_runtime_callbacks": TODO_STATUS,
        "mission_control_api_source": TODO_STATUS,
        "provider_webhooks_configured": TODO_STATUS,
        "provider_request_shape_smoke": TODO_STATUS,
        "no_live_smoke": TODO_STATUS,
        "live_provider_smoke": TODO_STATUS,
        "live_provider_smoke_recipients": TODO_STATUS,
        "operator_owned_phone": TODO_STATUS,
        "operator_owned_email": TODO_STATUS,
        "rollback_reference": rollback_reference,
        "operator_inputs_required": list(OPERATOR_INPUT_FIELDS),
        "notes": [],
    }


def _find_todo_fields(value: Any, *, prefix: str = "") -> list[str]:
    if value == TODO_STATUS:
        return [prefix]
    if isinstance(value, dict):
        fields: list[str] = []
        for key, item in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            fields.extend(_find_todo_fields(item, prefix=child_prefix))
        return fields
    if isinstance(value, list):
        fields = []
        for index, item in enumerate(value):
            fields.extend(_find_todo_fields(item, prefix=f"{prefix}[{index}]"))
        return fields
    return []


def validate_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    missing_fields = [field for field in REQUIRED_FIELDS if field not in evidence]
    todo_fields = _find_todo_fields(evidence)
    serialized = json.dumps(evidence, sort_keys=True)
    secret_name_leaks = [name for name in SECRET_FIELD_NAMES if name in serialized]
    status = "ready" if not missing_fields and not todo_fields and not secret_name_leaks else "blocked"
    return {
        "status": status,
        "missing_fields": missing_fields,
        "todo_fields": todo_fields,
        "secret_name_leaks": secret_name_leaks,
    }


def load_and_validate_evidence(path: Path) -> dict[str, Any]:
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return {
            "status": "blocked",
            "missing_fields": list(REQUIRED_FIELDS),
            "todo_fields": [],
            "secret_name_leaks": [],
            "error": str(exc),
        }
    if not isinstance(evidence, dict):
        return {
            "status": "blocked",
            "missing_fields": list(REQUIRED_FIELDS),
            "todo_fields": [],
            "secret_name_leaks": [],
            "error": "Evidence JSON must be an object.",
        }
    return validate_evidence(evidence)


def write_evidence_skeleton(
    *,
    path: Path,
    environment: str,
    commit: str | None = None,
    generated_at: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    if path.exists() and not overwrite:
        return {"status": "blocked", "error": "Evidence file already exists.", "path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    skeleton = build_evidence_skeleton(
        environment=environment,
        commit=commit,
        generated_at=generated_at,
    )
    path.write_text(json.dumps(skeleton, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = validate_evidence(skeleton)
    return {"status": "written", "path": str(path), "validation": validation}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("path", type=Path)
    init_parser.add_argument("--environment", choices=VALID_ENVIRONMENTS, required=True)
    init_parser.add_argument("--commit")
    init_parser.add_argument("--overwrite", action="store_true")

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    if args.command == "init":
        result = write_evidence_skeleton(
            path=args.path,
            environment=args.environment,
            commit=args.commit,
            overwrite=args.overwrite,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "written" else 2

    result = load_and_validate_evidence(args.path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
