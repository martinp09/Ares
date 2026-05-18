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


def test_sms_agent_settings_default_to_draft_safe_mode(monkeypatch) -> None:
    for env_var in (
        "sms_agent_mode",
        "SMS_AGENT_MODE",
        "sms_agent_auto_replies_enabled",
        "SMS_AGENT_AUTO_REPLIES_ENABLED",
        "sms_agent_allowed_from_numbers",
        "SMS_AGENT_ALLOWED_FROM_NUMBERS",
        "sms_agent_process_batch_size",
        "SMS_AGENT_PROCESS_BATCH_SIZE",
        "sms_agent_max_attempts",
        "SMS_AGENT_MAX_ATTEMPTS",
        "sms_agent_lock_seconds",
        "SMS_AGENT_LOCK_SECONDS",
        "sms_agent_retention_days",
        "SMS_AGENT_RETENTION_DAYS",
        "sms_agent_archive_enabled",
        "SMS_AGENT_ARCHIVE_ENABLED",
        "sms_agent_obsidian_archive_root",
        "SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT",
        "sms_agent_prompt_version",
        "SMS_AGENT_PROMPT_VERSION",
        "sms_agent_llm_replies_enabled",
        "SMS_AGENT_LLM_REPLIES_ENABLED",
        "sms_agent_llm_provider",
        "SMS_AGENT_LLM_PROVIDER",
        "sms_agent_llm_model",
        "SMS_AGENT_LLM_MODEL",
        "sms_agent_llm_temperature",
        "SMS_AGENT_LLM_TEMPERATURE",
        "sms_agent_llm_timeout_seconds",
        "SMS_AGENT_LLM_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(env_var, raising=False)
    settings = Settings(_env_file=None)

    assert settings.sms_agent_mode == "draft_only"
    assert settings.sms_agent_auto_replies_enabled is False
    assert settings.sms_agent_process_batch_size == 25
    assert settings.sms_agent_max_attempts == 5
    assert settings.sms_agent_archive_enabled is False
    assert settings.sms_agent_llm_replies_enabled is False
    assert settings.sms_agent_llm_provider == "openai_compat"
    assert settings.sms_agent_llm_model == "gpt-4o-mini"


def test_slack_notification_route_settings_default_safe(monkeypatch) -> None:
    for name in (
        "SLACK_NOTIFICATIONS_ENABLED",
        "SLACK_CHANNEL_LEAD_RUNS",
        "SLACK_CHANNEL_HOT_LEADS",
        "SLACK_CHANNEL_CHIEF_OF_STAFF",
        "SLACK_CHANNEL_INSTANTLY_REPLIES",
        "SLACK_CHANNEL_LEASE_OPTION_INBOUND",
        "SLACK_CHANNEL_SMS_CALLS",
        "ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.slack_notifications_enabled is False
    assert settings.slack_channel_lead_runs is None
    assert settings.slack_channel_hot_leads is None
    assert settings.slack_channel_chief_of_staff is None
    assert settings.slack_channel_instantly_replies is None
    assert settings.slack_channel_lease_option_inbound is None
    assert settings.slack_channel_sms_calls is None
    assert settings.ares_chief_of_staff_scheduled_slack_enabled is False


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
        "SMS_AGENT_MODE=draft_only",
        "SMS_AGENT_AUTO_REPLIES_ENABLED=false",
        "SMS_AGENT_ALLOWED_FROM_NUMBERS=",
        "SMS_AGENT_PROCESS_BATCH_SIZE=25",
        "SMS_AGENT_MAX_ATTEMPTS=5",
        "SMS_AGENT_LOCK_SECONDS=120",
        "SMS_AGENT_RETENTION_DAYS=90",
        "SMS_AGENT_ARCHIVE_ENABLED=false",
        "SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT=",
        "SMS_AGENT_PROMPT_VERSION=sms_reply_agent_v1",
        "SMS_AGENT_LLM_REPLIES_ENABLED=false",
        "SMS_AGENT_LLM_PROVIDER=openai_compat",
        "SMS_AGENT_LLM_MODEL=gpt-4o-mini",
        "SMS_AGENT_LLM_TEMPERATURE=0.4",
        "SMS_AGENT_LLM_TIMEOUT_SECONDS=8.0",
        "RESEND_API_KEY=",
        "RESEND_FROM_EMAIL=",
        "RESEND_REPLY_TO_EMAIL=",
        "SLACK_NOTIFICATIONS_ENABLED=false",
        "SLACK_BOT_TOKEN=",
        "SLACK_CHANNEL_LEAD_RUNS=",
        "SLACK_CHANNEL_HOT_LEADS=",
        "SLACK_CHANNEL_CHIEF_OF_STAFF=",
        "SLACK_CHANNEL_INSTANTLY_REPLIES=",
        "SLACK_CHANNEL_LEASE_OPTION_INBOUND=",
        "SLACK_CHANNEL_SMS_CALLS=",
        "SLACK_CHANNEL_ERRORS=",
        "ARES_CHIEF_OF_STAFF_ARTIFACT_ROOT=",
        "ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED=false",
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
