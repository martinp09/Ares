from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

REQUIRED_VARS = (
    "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH",
    "LEAD_MACHINE_ARTIFACT_ROOT",
    "LEAD_MACHINE_BUSINESS_ID",
    "LEAD_MACHINE_ENVIRONMENT",
)

OUTBOUND_GATE_VARS = (
    "PROVIDER_LIVE_SENDS_ENABLED",
    "INSTANTLY_PROVIDER_LIVE_ENROLLMENT_ENABLED",
    "HUBSPOT_PROVIDER_LIVE_WRITES_ENABLED",
    "VAPI_PROVIDER_LIVE_SENDS_ENABLED",
)

LIVE_INTELLIGENCE_GATE_VARS = (
    "LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED",
    "LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED",
    "LEAD_MACHINE_LIVE_CAD_CALLS_ENABLED",
    "LEAD_MACHINE_LIVE_TAX_CALLS_ENABLED",
    "LEAD_MACHINE_LIVE_LAND_RECORD_CALLS_ENABLED",
    "LEAD_MACHINE_LIVE_CASE_DETAIL_CALLS_ENABLED",
    "LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED",
    "LEAD_MACHINE_SCHEDULED_LIVE_CASE_DETAIL_CALLS_ENABLED",
)

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


@dataclass(frozen=True)
class BoolCheck:
    name: str
    present: bool
    parsed: bool | None
    status: str
    message: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "present": self.present,
            "parsed": self.parsed,
            "status": self.status,
            "message": self.message,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the no-send Harris/Montgomery probate autopilot environment contract "
            "before deploying or enabling scheduled live read-only intelligence."
        )
    )
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        help="Optional .env-style file to layer over the current process environment. Can be passed more than once.",
    )
    parser.add_argument(
        "--require-scheduled-live",
        action="store_true",
        help="Treat disabled scheduled live source/case-detail/enrichment gates as blockers instead of warnings.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    env = merge_environment(os.environ, [Path(path) for path in args.env_file])
    report = validate_env_contract(env, require_scheduled_live=args.require_scheduled_live)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 2 if report["status"] == "blocked" else 0


def merge_environment(base: Mapping[str, str], env_files: list[Path]) -> dict[str, str]:
    merged = dict(base)
    for env_file in env_files:
        merged.update(load_env_file(env_file))
    return merged


def load_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"Env file not found: {path}")
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            raise SystemExit(f"Invalid env line {path}:{line_number}: expected KEY=VALUE")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            raise SystemExit(f"Invalid env line {path}:{line_number}: empty key")
        values[key] = _parse_env_value(raw_value)
    return values


def validate_env_contract(env: Mapping[str, str], *, require_scheduled_live: bool = False) -> dict[str, object]:
    blockers: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    required = [_required_check(name, env) for name in REQUIRED_VARS]
    for check in required:
        if check["status"] == "blocked":
            blockers.append(check)

    path_checks = _path_checks(env)
    for check in path_checks:
        if check["status"] == "blocked":
            blockers.append(check)
        elif check["status"] == "warning":
            warnings.append(check)

    outbound_gates = [_outbound_gate_check(name, env) for name in OUTBOUND_GATE_VARS]
    for check in outbound_gates:
        if check.status == "blocked":
            blockers.append(check.to_dict())

    live_intelligence_gates = [
        _live_intelligence_gate_check(name, env, require_scheduled_live=require_scheduled_live)
        for name in LIVE_INTELLIGENCE_GATE_VARS
    ]
    for check in live_intelligence_gates:
        if check.status == "blocked":
            blockers.append(check.to_dict())
        elif check.status == "warning":
            warnings.append(check.to_dict())

    status = "blocked" if blockers else "warning" if warnings else "healthy"
    return {
        "status": status,
        "no_send_ok": all(check.status == "healthy" and check.parsed is False for check in outbound_gates),
        "live_intelligence_ready": all(check.parsed is True for check in live_intelligence_gates),
        "required": required,
        "paths": path_checks,
        "outbound_gates": [check.to_dict() for check in outbound_gates],
        "live_intelligence_gates": [check.to_dict() for check in live_intelligence_gates],
        "blockers": blockers,
        "warnings": warnings,
        "side_effects": {
            "created_files_or_directories": False,
            "live_source_calls": False,
            "provider_mutations": False,
        },
    }


def _required_check(name: str, env: Mapping[str, str]) -> dict[str, object]:
    value = _clean(env.get(name))
    if value is None:
        return {
            "name": name,
            "present": False,
            "status": "blocked",
            "message": f"{name} must be configured before production no-send autopilot deployment.",
        }
    return {"name": name, "present": True, "status": "healthy", "message": "configured"}


def _path_checks(env: Mapping[str, str]) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    state_value = _clean(env.get("LEAD_MACHINE_SOURCE_RUNS_STATE_PATH"))
    artifact_value = _clean(env.get("LEAD_MACHINE_ARTIFACT_ROOT"))
    if state_value is not None:
        checks.append(_state_path_check(Path(state_value).expanduser()))
    if artifact_value is not None:
        checks.append(_artifact_root_check(Path(artifact_value).expanduser()))
    return checks


def _state_path_check(path: Path) -> dict[str, object]:
    parent = path.parent
    if path.exists() and path.is_dir():
        return {
            "name": "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH",
            "path": str(path),
            "status": "blocked",
            "message": "state path points to a directory; it must point to a JSON file path.",
        }
    if not parent.exists():
        return {
            "name": "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH",
            "path": str(path),
            "status": "blocked",
            "message": "state path parent directory does not exist; preflight does not create directories.",
        }
    if not parent.is_dir():
        return {
            "name": "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH",
            "path": str(path),
            "status": "blocked",
            "message": "state path parent is not a directory.",
        }
    if not os.access(parent, os.W_OK):
        return {
            "name": "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH",
            "path": str(path),
            "status": "blocked",
            "message": "state path parent directory is not writable by the current process.",
        }
    return {
        "name": "LEAD_MACHINE_SOURCE_RUNS_STATE_PATH",
        "path": str(path),
        "status": "healthy",
        "message": "state file path parent exists and is writable; no file was created.",
    }


def _artifact_root_check(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "name": "LEAD_MACHINE_ARTIFACT_ROOT",
            "path": str(path),
            "status": "blocked",
            "message": "artifact root directory does not exist; preflight does not create directories.",
        }
    if not path.is_dir():
        return {
            "name": "LEAD_MACHINE_ARTIFACT_ROOT",
            "path": str(path),
            "status": "blocked",
            "message": "artifact root exists but is not a directory.",
        }
    if not os.access(path, os.W_OK):
        return {
            "name": "LEAD_MACHINE_ARTIFACT_ROOT",
            "path": str(path),
            "status": "blocked",
            "message": "artifact root directory is not writable by the current process.",
        }
    return {
        "name": "LEAD_MACHINE_ARTIFACT_ROOT",
        "path": str(path),
        "status": "healthy",
        "message": "artifact root exists and is writable; no artifact was created.",
    }


def _outbound_gate_check(name: str, env: Mapping[str, str]) -> BoolCheck:
    parsed = _optional_bool(env.get(name))
    if parsed == "invalid":
        return BoolCheck(name, True, None, "blocked", f"{name} must be true/false when set.")
    if parsed is True:
        return BoolCheck(name, True, True, "blocked", f"{name}=true would allow provider mutation; keep it false for no-send autopilot.")
    if parsed is False:
        return BoolCheck(name, True, False, "healthy", "explicitly disabled")
    return BoolCheck(name, False, False, "healthy", "unset; safe default is disabled")


def _live_intelligence_gate_check(
    name: str,
    env: Mapping[str, str],
    *,
    require_scheduled_live: bool,
) -> BoolCheck:
    parsed = _optional_bool(env.get(name))
    if parsed == "invalid":
        return BoolCheck(name, True, None, "blocked", f"{name} must be true/false when set.")
    if parsed is None:
        return BoolCheck(
            name,
            False,
            None,
            "warning",
            f"{name} is not explicit; code defaults may apply, but deployment env should declare this gate.",
        )
    if require_scheduled_live and name.startswith("LEAD_MACHINE_SCHEDULED_") and parsed is False:
        return BoolCheck(
            name,
            True,
            False,
            "blocked",
            f"{name}=false blocks scheduled live no-send intelligence while --require-scheduled-live is set.",
        )
    if parsed is False:
        return BoolCheck(name, True, False, "warning", "disabled; live no-send intelligence for this lane will not run")
    return BoolCheck(name, True, True, "healthy", "enabled for live read-only intelligence")


def _optional_bool(value: str | None) -> bool | None | str:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    lowered = cleaned.lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return "invalid"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_env_value(raw_value: str) -> str:
    stripped = raw_value.strip()
    if not stripped:
        return ""
    try:
        parsed = shlex.split(stripped, comments=True, posix=True)
    except ValueError as exc:
        raise SystemExit(f"Invalid env value syntax: {exc}") from exc
    if not parsed:
        return ""
    return parsed[0]


if __name__ == "__main__":
    raise SystemExit(main())
