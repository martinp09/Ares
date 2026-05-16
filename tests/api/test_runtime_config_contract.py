from pathlib import Path

from app.core.config import Settings


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
VITE_CONFIG = REPO_ROOT / "apps" / "mission-control" / "vite.config.ts"


def test_runtime_config_defaults_are_local_safe(monkeypatch) -> None:
    monkeypatch.delenv("RUNTIME_API_KEY", raising=False)
    monkeypatch.delenv("RUNTIME_ACTOR_HEADER_OVERRIDES_ENABLED", raising=False)
    monkeypatch.delenv("PROVIDER_WEBHOOK_SIGNATURES_REQUIRED", raising=False)
    monkeypatch.delenv("PROVIDER_LIVE_SENDS_ENABLED", raising=False)
    settings = Settings(_env_file=None)

    assert settings.runtime_api_key is None
    assert settings.runtime_docs_enabled is False
    assert settings.runtime_actor_header_overrides_enabled is False
    assert settings.provider_webhook_signatures_required is True
    assert settings.provider_live_sends_enabled is False
    assert settings.control_plane_backend == "memory"
    assert settings.marketing_backend == "memory"
    assert settings.lead_machine_backend == "memory"
    assert settings.site_events_backend == "memory"
    assert settings.trigger_api_url == "https://api.trigger.dev"
    assert settings.trigger_non_booker_check_task_id == "marketing-check-submitted-lead-booking"


def test_slack_notification_route_settings_default_safe(monkeypatch) -> None:
    for name in (
        "SLACK_NOTIFICATIONS_ENABLED",
        "SLACK_CHANNEL_LEAD_RUNS",
        "SLACK_CHANNEL_INSTANTLY_REPLIES",
        "SLACK_CHANNEL_LEASE_OPTION_INBOUND",
        "SLACK_CHANNEL_SMS_CALLS",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.slack_notifications_enabled is False
    assert settings.slack_channel_lead_runs is None
    assert settings.slack_channel_instantly_replies is None
    assert settings.slack_channel_lease_option_inbound is None
    assert settings.slack_channel_sms_calls is None


def test_env_example_declares_full_stack_contract() -> None:
    source = ENV_EXAMPLE.read_text(encoding="utf-8")

    required = (
        "HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000",
        "HERMES_RUNTIME_API_KEY=<local-runtime-api-key>",
        "RUNTIME_API_BASE_URL=http://127.0.0.1:8000",
        "RUNTIME_API_KEY=<local-runtime-api-key>",
        "RUNTIME_DOCS_ENABLED=false",
        "RUNTIME_ACTOR_HEADER_OVERRIDES_ENABLED=false",
        "PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true",
        "PROVIDER_LIVE_SENDS_ENABLED=false",
        "CONTROL_PLANE_BACKEND=memory",
        "MARKETING_BACKEND=memory",
        "SITE_EVENTS_BACKEND=memory",
        "SUPABASE_URL=",
        "SUPABASE_SERVICE_ROLE_KEY=",
        "SUPABASE_DIRECT_CONNECTION_STRING=",
        "TRIGGER_SECRET_KEY=",
        "TRIGGER_API_URL=https://api.trigger.dev",
        "TRIGGER_NON_BOOKER_CHECK_TASK_ID=marketing-check-submitted-lead-booking",
        "CAL_API_KEY=",
        "CAL_BOOKING_URL=",
        "CAL_WEBHOOK_SECRET=",
        "TEXTGRID_ACCOUNT_SID=",
        "TEXTGRID_AUTH_TOKEN=",
        "TEXTGRID_FROM_NUMBER=",
        "TEXTGRID_SMS_URL=https://api.textgrid.com",
        "TEXTGRID_WEBHOOK_SECRET=",
        "RESEND_API_KEY=",
        "RESEND_FROM_EMAIL=",
        "RESEND_REPLY_TO_EMAIL=",
        "SLACK_NOTIFICATIONS_ENABLED=false",
        "SLACK_BOT_TOKEN=",
        "SLACK_CHANNEL_LEAD_RUNS=",
        "SLACK_CHANNEL_HOT_LEADS=",
        "SLACK_CHANNEL_INSTANTLY_REPLIES=",
        "SLACK_CHANNEL_LEASE_OPTION_INBOUND=",
        "SLACK_CHANNEL_SMS_CALLS=",
        "SLACK_CHANNEL_ERRORS=",
        "VITE_RUNTIME_API_BASE_URL=",
    )

    for expected in required:
        assert expected in source

    assert "VITE_RUNTIME_API_KEY" not in source


def test_mission_control_vite_proxy_injects_runtime_auth_server_side() -> None:
    source = VITE_CONFIG.read_text(encoding="utf-8")

    assert "RUNTIME_API_BASE_URL" in source
    assert "HERMES_RUNTIME_API_BASE_URL" in source
    assert "RUNTIME_API_KEY" in source
    assert "HERMES_RUNTIME_API_KEY" in source
    assert "options.headers = { Authorization: `Bearer ${runtimeApiKey}` }" in source
    assert '"/mission-control": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey)' in source
    assert '"/release-management": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey)' in source
    assert '"/usage": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey)' in source
