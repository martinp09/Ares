from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
from datetime import UTC, datetime
from email.utils import parseaddr
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlparse, urlunparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import Settings

SENSITIVE_QUERY_KEYS = {"runtime_api_key", "api_key", "token", "key", "secret"}

REQUIRED_LANDING_ENV = (
    "BUSINESS_RUNTIME_MARKETING_LEADS_URL",
    "BUSINESS_RUNTIME_API_KEY",
    "BUSINESS_RUNTIME_BUSINESS_ID",
    "BUSINESS_RUNTIME_ENVIRONMENT",
)
OPTIONAL_LANDING_ENV = ("BUSINESS_RUNTIME_SITE_EVENTS_URL",)


def _present(value: str | None) -> bool:
    return bool(value and value.strip())


def _fingerprint(value: str | None) -> str | None:
    if not _present(value):
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]


def _secret_status(value: str | None) -> dict[str, Any]:
    return {
        "present": _present(value),
        "length": len(value or "") if _present(value) else 0,
        "fingerprint": _fingerprint(value),
    }


def _url_status(value: str | None) -> dict[str, Any]:
    if not _present(value):
        return {"present": False, "sanitized": None, "has_sensitive_query": False, "sensitive_query_keys": []}
    parsed = urlparse(value)
    sensitive_keys = sorted(
        {key for key, _ in parse_qsl(parsed.query, keep_blank_values=True) if key.lower() in SENSITIVE_QUERY_KEYS}
    )
    sanitized = urlunparse(parsed._replace(query="<redacted>" if parsed.query else "", fragment=""))
    return {
        "present": True,
        "sanitized": sanitized,
        "has_sensitive_query": bool(sensitive_keys),
        "sensitive_query_keys": sensitive_keys,
    }


def _looks_like_email_identity(value: str | None) -> bool:
    if not _present(value):
        return False
    _, parsed = parseaddr(value or "")
    return bool(parsed and "@" in parsed and "." in parsed.rsplit("@", 1)[-1])


def _plain_env_status(environ: Mapping[str, str], name: str) -> dict[str, Any]:
    value = environ.get(name)
    status: dict[str, Any] = {"present": _present(value)}
    if name.endswith("URL"):
        status.update(_url_status(value))
    elif name.endswith("KEY") or name.endswith("TOKEN") or name.endswith("SECRET"):
        status.update(_secret_status(value))
    else:
        status["length"] = len(value or "") if _present(value) else 0
    return status


def _gate(*, configured: bool, blockers: list[str], warnings: list[str] | None = None, **details: Any) -> dict[str, Any]:
    return {
        "configured": configured,
        "blockers": blockers,
        "warnings": warnings or [],
        **details,
    }


SLACK_ROUTE_CHANNELS = {
    "lead_runs": {
        "preferred_env_var": "SLACK_CHANNEL_LEAD_RUNS",
        "setting": "slack_channel_lead_runs",
        "fallback_env_vars": ["SLACK_CHANNEL_LEADS"],
    },
    "hot_leads": {
        "preferred_env_var": "SLACK_CHANNEL_HOT_LEADS",
        "setting": "slack_channel_hot_leads",
        "fallback_env_vars": [],
    },
    "instantly_replies": {
        "preferred_env_var": "SLACK_CHANNEL_INSTANTLY_REPLIES",
        "setting": "slack_channel_instantly_replies",
        "fallback_env_vars": [],
    },
    "lease_option_inbound": {
        "preferred_env_var": "SLACK_CHANNEL_LEASE_OPTION_INBOUND",
        "setting": "slack_channel_lease_option_inbound",
        "fallback_env_vars": ["SLACK_CHANNEL_INTAKE"],
    },
    "sms_calls": {
        "preferred_env_var": "SLACK_CHANNEL_SMS_CALLS",
        "setting": "slack_channel_sms_calls",
        "fallback_env_vars": [],
    },
}
SLACK_LEGACY_CHANNELS = {
    "SLACK_CHANNEL_INTAKE": "slack_channel_intake",
    "SLACK_CHANNEL_LEADS": "slack_channel_leads",
}


def _slack_route_channel_report(settings: Settings) -> dict[str, Any]:
    return {
        route: {
            "present": _present(getattr(settings, config["setting"])),
            "preferred": True,
            "preferred_env_var": config["preferred_env_var"],
            "fallback_env_vars": list(config["fallback_env_vars"]),
        }
        for route, config in SLACK_ROUTE_CHANNELS.items()
    }


def _slack_legacy_channel_report(settings: Settings) -> dict[str, Any]:
    return {
        env_var: {"present": _present(getattr(settings, setting)), "preferred": False}
        for env_var, setting in SLACK_LEGACY_CHANNELS.items()
    }


def _load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        name, raw_value = line.split("=", 1)
        name = name.strip()
        raw_value = raw_value.strip()
        if not name:
            continue
        try:
            parsed = shlex.split(raw_value, comments=False, posix=True)
            value = parsed[0] if parsed else ""
        except ValueError:
            value = raw_value.strip("'\"")
        values[name] = value
    return values


def _clean_runtime_url(runtime_url: str | None) -> str | None:
    if not _present(runtime_url):
        return None
    return (runtime_url or "").strip().rstrip("/")


def _first_present(environ: Mapping[str, str], *names: str) -> str | None:
    for name in names:
        value = environ.get(name)
        if _present(value):
            return value
    return None


def build_activation_environment(
    *,
    base_environ: Mapping[str, str] | None = None,
    env_files: Sequence[Path] = (),
    runtime_url: str | None = None,
    derive_local_defaults: bool = False,
) -> dict[str, str]:
    merged = dict(os.environ if base_environ is None else base_environ)
    for env_file in env_files:
        merged.update(_load_env_file(env_file))

    if not derive_local_defaults:
        return merged

    clean_runtime_url = _clean_runtime_url(runtime_url)
    if clean_runtime_url:
        merged.setdefault("TEXTGRID_STATUS_CALLBACK_URL", f"{clean_runtime_url}/marketing/webhooks/textgrid")
        merged.setdefault("BUSINESS_RUNTIME_MARKETING_LEADS_URL", f"{clean_runtime_url}/marketing/leads")
        merged.setdefault("BUSINESS_RUNTIME_SITE_EVENTS_URL", f"{clean_runtime_url}/site-events")

    if _present(merged.get("RUNTIME_API_KEY")):
        merged.setdefault("BUSINESS_RUNTIME_API_KEY", merged["RUNTIME_API_KEY"])

    merged.setdefault("BUSINESS_RUNTIME_BUSINESS_ID", "limitless")
    merged.setdefault("BUSINESS_RUNTIME_ENVIRONMENT", "prod")
    merged.setdefault("PROVIDER_LIVE_SENDS_ENABLED", "false")
    merged.setdefault("TRIGGER_API_URL", "https://api.trigger.dev")
    merged.setdefault("TRIGGER_NON_BOOKER_CHECK_TASK_ID", "marketing-check-submitted-lead-booking")
    merged.setdefault("TRIGGER_APPOINTMENT_REMINDER_TASK_ID", "marketing-send-appointment-reminder")
    merged.setdefault("MARKETING_APPOINTMENT_REMINDERS_ENABLED", "true")

    booking_url = _first_present(merged, "CAL_BOOKING_URL", "NEXT_PUBLIC_CAL_BOOKING_URL", "SCHEDULING_URL", "Scheduling_URL")
    if booking_url:
        merged.setdefault("CAL_BOOKING_URL", booking_url)

    return merged


def _with_process_environ(environ: Mapping[str, str]) -> Settings:
    previous = os.environ.copy()
    try:
        os.environ.clear()
        os.environ.update(environ)
        return Settings(_env_file=None)
    finally:
        os.environ.clear()
        os.environ.update(previous)


def activation_readiness(
    *,
    settings: Settings | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    active_settings = settings or Settings()
    active_env = environ or os.environ

    blockers: list[str] = []
    warnings: list[str] = []

    runtime_blockers: list[str] = []
    if not _present(active_settings.runtime_api_key):
        runtime_blockers.append("RUNTIME_API_KEY is missing")
    runtime_gate = _gate(
        configured=not runtime_blockers,
        blockers=runtime_blockers,
        runtime_api_key=_secret_status(active_settings.runtime_api_key),
        docs_enabled=active_settings.runtime_docs_enabled,
        actor_header_overrides_enabled=active_settings.runtime_actor_header_overrides_enabled,
        provider_webhook_signatures_required=active_settings.provider_webhook_signatures_required,
    )

    live_gate_blockers: list[str] = []
    if not active_settings.provider_live_sends_enabled:
        live_gate_blockers.append("PROVIDER_LIVE_SENDS_ENABLED is false; safe default blocks live provider delivery")
    live_send_gate = _gate(
        configured=active_settings.provider_live_sends_enabled,
        blockers=live_gate_blockers,
        provider_live_sends_enabled=active_settings.provider_live_sends_enabled,
    )

    textgrid_callback = _url_status(active_settings.textgrid_status_callback_url)
    textgrid_blockers = [
        name
        for name, value in (
            ("TEXTGRID_ACCOUNT_SID", active_settings.textgrid_account_sid),
            ("TEXTGRID_AUTH_TOKEN", active_settings.textgrid_auth_token),
            ("TEXTGRID_FROM_NUMBER", active_settings.textgrid_from_number),
            ("TEXTGRID_WEBHOOK_SECRET", active_settings.textgrid_webhook_secret),
            ("TEXTGRID_STATUS_CALLBACK_URL", active_settings.textgrid_status_callback_url),
        )
        if not _present(value)
    ]
    textgrid_warnings: list[str] = []
    if textgrid_callback["has_sensitive_query"]:
        textgrid_warnings.append("TEXTGRID_STATUS_CALLBACK_URL includes sensitive query keys")
    textgrid_gate = _gate(
        configured=not textgrid_blockers and not textgrid_callback["has_sensitive_query"],
        blockers=[f"{name} is missing" for name in textgrid_blockers],
        warnings=textgrid_warnings,
        account_sid=_secret_status(active_settings.textgrid_account_sid),
        auth_token=_secret_status(active_settings.textgrid_auth_token),
        from_number_present=_present(active_settings.textgrid_from_number),
        webhook_secret=_secret_status(active_settings.textgrid_webhook_secret),
        status_callback_url=textgrid_callback,
    )

    resend_sender_valid = _looks_like_email_identity(active_settings.resend_from_email)
    resend_blockers = [
        f"{name} is missing"
        for name, value in (
            ("RESEND_API_KEY", active_settings.resend_api_key),
            ("RESEND_FROM_EMAIL", active_settings.resend_from_email),
        )
        if not _present(value)
    ]
    if _present(active_settings.resend_from_email) and not resend_sender_valid:
        resend_blockers.append("RESEND_FROM_EMAIL must be an email address or Name <email@example.com>")
    resend_gate = _gate(
        configured=not resend_blockers,
        blockers=resend_blockers,
        api_key=_secret_status(active_settings.resend_api_key),
        from_email_present=_present(active_settings.resend_from_email),
        from_email_valid=resend_sender_valid,
        reply_to_present=_present(active_settings.resend_reply_to_email),
    )

    slack_route_channels = _slack_route_channel_report(active_settings)
    slack_legacy_channels = _slack_legacy_channel_report(active_settings)
    slack_blockers = []
    if not active_settings.slack_notifications_enabled:
        slack_blockers.append("SLACK_NOTIFICATIONS_ENABLED=true is required")
    if not _present(active_settings.slack_bot_token):
        slack_blockers.append("SLACK_BOT_TOKEN is missing")
    for route_report in slack_route_channels.values():
        if not route_report["present"]:
            slack_blockers.append(f"{route_report['preferred_env_var']} is missing")
    slack_gate = _gate(
        configured=not slack_blockers,
        blockers=slack_blockers,
        slack_notifications_enabled=active_settings.slack_notifications_enabled,
        bot_token=_secret_status(active_settings.slack_bot_token),
        route_channels=slack_route_channels,
        legacy_channels=slack_legacy_channels,
        intake_channel_present=_present(active_settings.slack_channel_intake),
        leads_channel_present=_present(active_settings.slack_channel_leads),
        errors_channel_present=_present(active_settings.slack_channel_errors),
    )

    cal_blockers = [
        name
        for name, value in (
            ("CAL_BOOKING_URL", active_settings.cal_booking_url),
            ("CAL_WEBHOOK_SECRET", active_settings.cal_webhook_secret),
        )
        if not _present(value)
    ]
    cal_booking_url = _url_status(active_settings.cal_booking_url)
    cal_warnings = ["CAL_BOOKING_URL includes sensitive query keys"] if cal_booking_url["has_sensitive_query"] else []
    cal_gate = _gate(
        configured=not cal_blockers and not cal_booking_url["has_sensitive_query"],
        blockers=[f"{name} is missing" for name in cal_blockers],
        warnings=cal_warnings,
        booking_url=cal_booking_url,
        webhook_secret=_secret_status(active_settings.cal_webhook_secret),
    )

    trigger_blockers = [
        f"{name} is missing"
        for name, value in (
            ("TRIGGER_SECRET_KEY", active_settings.trigger_secret_key),
            ("TRIGGER_NON_BOOKER_CHECK_TASK_ID", active_settings.trigger_non_booker_check_task_id),
            ("TRIGGER_APPOINTMENT_REMINDER_TASK_ID", active_settings.trigger_appointment_reminder_task_id),
        )
        if not _present(value)
    ]
    if not active_settings.marketing_appointment_reminders_enabled:
        trigger_blockers.append("MARKETING_APPOINTMENT_REMINDERS_ENABLED is false")
    trigger_gate = _gate(
        configured=not trigger_blockers,
        blockers=trigger_blockers,
        secret_key=_secret_status(active_settings.trigger_secret_key),
        api_url=_url_status(active_settings.trigger_api_url),
        non_booker_task_id=active_settings.trigger_non_booker_check_task_id,
        appointment_reminder_task_id=active_settings.trigger_appointment_reminder_task_id,
        marketing_appointment_reminders_enabled=active_settings.marketing_appointment_reminders_enabled,
    )

    landing_env = {name: _plain_env_status(active_env, name) for name in REQUIRED_LANDING_ENV + OPTIONAL_LANDING_ENV}
    landing_blockers = [f"{name} is missing" for name in REQUIRED_LANDING_ENV if not landing_env[name]["present"]]
    landing_warnings = [
        f"{name} includes sensitive query keys"
        for name in ("BUSINESS_RUNTIME_MARKETING_LEADS_URL", "BUSINESS_RUNTIME_SITE_EVENTS_URL")
        if landing_env[name].get("has_sensitive_query")
    ]
    landing_gate = _gate(
        configured=not landing_blockers and not landing_warnings,
        blockers=landing_blockers,
        warnings=landing_warnings,
        env=landing_env,
    )

    gates = {
        "runtime_auth": runtime_gate,
        "live_send_gate": live_send_gate,
        "textgrid": textgrid_gate,
        "resend": resend_gate,
        "slack": slack_gate,
        "calcom": cal_gate,
        "trigger": trigger_gate,
        "landing": landing_gate,
    }

    for gate_name, gate in gates.items():
        blockers.extend(f"{gate_name}: {blocker}" for blocker in gate["blockers"])
        warnings.extend(f"{gate_name}: {warning}" for warning in gate["warnings"])

    provider_ready = all(gates[name]["configured"] for name in ("textgrid", "resend", "slack", "calcom", "trigger"))
    live_ready = provider_ready and runtime_gate["configured"] and live_send_gate["configured"] and landing_gate["configured"]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "verdict": "ready_for_live_smoke" if live_ready else "blocked",
        "safe_to_deploy_without_live_sends": runtime_gate["configured"] and not active_settings.provider_live_sends_enabled,
        "gates": gates,
        "blockers": blockers,
        "warnings": warnings,
        "next_commands": [
            "python scripts/activation_readiness.py --json",
            "python scripts/smoke_provider_readiness.py",
            "PROVIDER_LIVE_SENDS_ENABLED=true python scripts/activation_readiness.py --json",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report Ares activation readiness without printing raw secrets.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output. This is the default for automation.")
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        type=Path,
        help="Load additional dotenv-style env file(s) before reporting. Values are never printed raw.",
    )
    parser.add_argument(
        "--runtime-url",
        help="Runtime base URL used with --derive-local-defaults to fill callback and landing endpoint URLs.",
    )
    parser.add_argument(
        "--derive-local-defaults",
        action="store_true",
        help="Derive safe local activation defaults from loaded envs without copying secrets into a new file.",
    )
    args = parser.parse_args(argv)
    base_environ = {} if args.env_file else os.environ
    environ = build_activation_environment(
        base_environ=base_environ,
        env_files=tuple(args.env_file),
        runtime_url=args.runtime_url,
        derive_local_defaults=args.derive_local_defaults,
    )
    settings = _with_process_environ(environ)
    report = activation_readiness(settings=settings, environ=environ)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "ready_for_live_smoke" else 2


if __name__ == "__main__":
    raise SystemExit(main())
