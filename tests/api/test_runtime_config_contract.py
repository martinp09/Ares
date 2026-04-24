from pathlib import Path

from app.core.config import Settings


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
VITE_CONFIG = REPO_ROOT / "apps" / "mission-control" / "vite.config.ts"


def test_runtime_config_defaults_are_local_safe() -> None:
    settings = Settings(_env_file=None)

    assert settings.runtime_api_key == "dev-runtime-key"
    assert settings.control_plane_backend == "memory"
    assert settings.marketing_backend == "memory"
    assert settings.lead_machine_backend == "memory"
    assert settings.site_events_backend == "memory"
    assert settings.trigger_api_url == "https://api.trigger.dev"
    assert settings.trigger_non_booker_check_task_id == "marketing-check-submitted-lead-booking"


def test_env_example_declares_full_stack_contract() -> None:
    source = ENV_EXAMPLE.read_text(encoding="utf-8")

    required = (
        "HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000",
        "HERMES_RUNTIME_API_KEY=dev-runtime-key",
        "RUNTIME_API_BASE_URL=http://127.0.0.1:8000",
        "RUNTIME_API_KEY=dev-runtime-key",
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
    assert 'proxyReq.setHeader("Authorization", `Bearer ${runtimeApiKey}`)' in source
    assert '"/mission-control": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey)' in source
    assert '"/release-management": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey)' in source
    assert '"/usage": runtimeProxy(runtimeApiBaseUrl, runtimeApiKey)' in source
