from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import Settings
from app.models.slack_notifications import SlackNotificationRoute
from scripts.activation_readiness import build_activation_environment, _secret_status, _with_process_environ

ROUTE_CONFIG: dict[str, dict[str, Any]] = {
    SlackNotificationRoute.LEAD_RUNS.value: {
        "preferred_env_var": "SLACK_CHANNEL_LEAD_RUNS",
        "setting": "slack_channel_lead_runs",
        "fallback_env_vars": ["SLACK_CHANNEL_LEADS"],
        "fallback_settings": ["slack_channel_leads"],
    },
    SlackNotificationRoute.HOT_LEADS.value: {
        "preferred_env_var": "SLACK_CHANNEL_HOT_LEADS",
        "setting": "slack_channel_hot_leads",
        "fallback_env_vars": [],
        "fallback_settings": [],
    },
    SlackNotificationRoute.INSTANTLY_REPLIES.value: {
        "preferred_env_var": "SLACK_CHANNEL_INSTANTLY_REPLIES",
        "setting": "slack_channel_instantly_replies",
        "fallback_env_vars": [],
        "fallback_settings": [],
    },
    SlackNotificationRoute.LEASE_OPTION_INBOUND.value: {
        "preferred_env_var": "SLACK_CHANNEL_LEASE_OPTION_INBOUND",
        "setting": "slack_channel_lease_option_inbound",
        "fallback_env_vars": ["SLACK_CHANNEL_INTAKE"],
        "fallback_settings": ["slack_channel_intake"],
    },
    SlackNotificationRoute.SMS_CALLS.value: {
        "preferred_env_var": "SLACK_CHANNEL_SMS_CALLS",
        "setting": "slack_channel_sms_calls",
        "fallback_env_vars": [],
        "fallback_settings": [],
    },
    SlackNotificationRoute.ERRORS.value: {
        "preferred_env_var": "SLACK_CHANNEL_ERRORS",
        "setting": "slack_channel_errors",
        "fallback_env_vars": [],
        "fallback_settings": [],
    },
}
ACTIVATION_ROUTES = (
    SlackNotificationRoute.LEAD_RUNS.value,
    SlackNotificationRoute.HOT_LEADS.value,
    SlackNotificationRoute.INSTANTLY_REPLIES.value,
    SlackNotificationRoute.LEASE_OPTION_INBOUND.value,
    SlackNotificationRoute.SMS_CALLS.value,
)
LEGACY_CHANNELS = {
    "SLACK_CHANNEL_INTAKE": "slack_channel_intake",
    "SLACK_CHANNEL_LEADS": "slack_channel_leads",
}


def _present(value: str | None) -> bool:
    return bool(value and value.strip())


def _channel_id_shape(value: str | None) -> dict[str, Any]:
    if not _present(value):
        return {"valid_prefix": False, "length": 0, "looks_like_channel_id": False}
    channel = (value or "").strip()
    valid_prefix = channel[:1] in {"C", "G", "D"}
    return {
        "valid_prefix": valid_prefix,
        "length": len(channel),
        "looks_like_channel_id": valid_prefix and len(channel) >= 2 and channel.isalnum(),
    }


def _channel_status(value: str | None) -> dict[str, Any]:
    channel = value.strip() if _present(value) else None
    return {
        "present": channel is not None,
        "channel_id": channel,
        "shape": _channel_id_shape(channel),
    }


def _resolved_channel(settings: Settings, config: Mapping[str, Any]) -> str | None:
    preferred = getattr(settings, str(config["setting"]))
    if _present(preferred):
        return preferred
    for fallback_setting in config["fallback_settings"]:
        fallback = getattr(settings, fallback_setting)
        if _present(fallback):
            return fallback
    return None


def _route_status(settings: Settings, route: str) -> dict[str, Any]:
    config = ROUTE_CONFIG[route]
    preferred = getattr(settings, str(config["setting"]))
    resolved = _resolved_channel(settings, config)
    preferred_status = _channel_status(preferred)
    resolved_status = _channel_status(resolved)
    route_configured = bool(preferred_status["shape"]["looks_like_channel_id"])
    route_would_post = (
        settings.slack_notifications_enabled
        and _present(settings.slack_bot_token)
        and bool(resolved_status["shape"]["looks_like_channel_id"])
    )
    return {
        "route": route,
        "configured": route_configured,
        "would_post": route_would_post,
        "preferred_env_var": config["preferred_env_var"],
        "fallback_env_vars": list(config["fallback_env_vars"]),
        "channel_id": preferred_status,
        "resolved_channel_id": resolved_status,
    }


def _legacy_channel_status(settings: Settings) -> dict[str, Any]:
    return {
        env_var: {
            "present": _present(getattr(settings, setting)),
            "preferred": False,
            "channel_id": _channel_status(getattr(settings, setting)),
        }
        for env_var, setting in LEGACY_CHANNELS.items()
    }


def _sample_for(route: str) -> dict[str, Any]:
    context = f"Ares | prod | {route} | sample:readiness"
    samples = {
        SlackNotificationRoute.LEAD_RUNS.value: (
            "Ares lead run completed: 42 records, 5 warnings, 3 hot leads.",
            "Lead run completed for Harris probate + CAD enrichment.",
        ),
        SlackNotificationRoute.HOT_LEADS.value: (
            "Ares hot lead: 91 score, Harris probate, 123 Main St.",
            "Hot enriched probate lead ready for operator review.",
        ),
        SlackNotificationRoute.INSTANTLY_REPLIES.value: (
            "Instantly reply: lead@example.com said they are available today.",
            "Reply received from Probate Wave campaign.",
        ),
        SlackNotificationRoute.LEASE_OPTION_INBOUND.value: (
            "Lease-option inbound: Seller submitted 123 Main St with phone consent.",
            "Website lead accepted by Ares intake.",
        ),
        SlackNotificationRoute.SMS_CALLS.value: (
            "Inbound SMS: matched lead asked for a call back.",
            "TextGrid inbound message resolved to an existing lead.",
        ),
        SlackNotificationRoute.ERRORS.value: (
            "Slack delivery issue: operator notification failed safely.",
            "Delivery failure captured without blocking runtime ingestion.",
        ),
    }
    text, summary = samples[route]
    return {
        "route": route,
        "text": text,
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*{summary}*"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": context}]},
        ],
    }


def slack_notification_readiness(
    *,
    settings: Settings | None = None,
    route: str | None = None,
    render_sample: bool = False,
) -> dict[str, Any]:
    active_settings = settings or Settings()
    selected_route = SlackNotificationRoute(route).value if route else None
    required_routes = (selected_route,) if selected_route else ACTIVATION_ROUTES
    routes = {name: _route_status(active_settings, name) for name in ROUTE_CONFIG}

    missing: list[str] = []
    if not active_settings.slack_notifications_enabled:
        missing.append("SLACK_NOTIFICATIONS_ENABLED=true")
    if not _present(active_settings.slack_bot_token):
        missing.append("SLACK_BOT_TOKEN")
    for route_name in required_routes:
        route_report = routes[route_name]
        if not route_report["configured"]:
            if route_report["channel_id"]["present"]:
                missing.append(f"{route_report['preferred_env_var']} must be a Slack channel ID")
            else:
                missing.append(route_report["preferred_env_var"])

    configured = not missing
    would_post = (
        routes[selected_route]["would_post"]
        if selected_route
        else configured
    )
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "configured": configured,
        "would_post": would_post,
        "selected_route": selected_route,
        "missing": missing,
        "bot_token": _secret_status(active_settings.slack_bot_token),
        "routes": routes,
        "legacy_channels": _legacy_channel_status(active_settings),
    }
    if render_sample:
        sample_route = selected_route or SlackNotificationRoute.HOT_LEADS.value
        report["sample"] = _sample_for(sample_route)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report Slack notification readiness without posting or leaking secrets."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON output. This is the default for automation.")
    parser.add_argument("--route", choices=tuple(ROUTE_CONFIG), help="Limit readiness to one Slack notification route.")
    parser.add_argument(
        "--render-sample",
        action="store_true",
        help="Render a safe sample Slack payload without posting.",
    )
    parser.add_argument(
        "--env-file",
        action="append",
        default=[],
        type=Path,
        help="Load dotenv-style env file(s) before reporting. Values are never printed raw.",
    )
    parser.add_argument("--runtime-url", help="Runtime base URL used with --derive-local-defaults.")
    parser.add_argument(
        "--derive-local-defaults",
        action="store_true",
        help="Derive safe local activation defaults from loaded envs.",
    )
    args = parser.parse_args(argv)
    environ = build_activation_environment(
        base_environ={"PATH": os.environ.get("PATH", "")} if args.env_file else os.environ,
        env_files=tuple(args.env_file),
        runtime_url=args.runtime_url,
        derive_local_defaults=args.derive_local_defaults,
    )
    settings = _with_process_environ(environ)
    report = slack_notification_readiness(settings=settings, route=args.route, render_sample=args.render_sample)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["configured"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
