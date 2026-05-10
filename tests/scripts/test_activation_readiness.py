import json

import pytest

from app.core.config import Settings
from scripts.activation_readiness import activation_readiness, main


def _ready_settings(**overrides):
    values = {
        "_env_file": None,
        "runtime_api_key": "runtime-secret",
        "provider_live_sends_enabled": True,
        "textgrid_account_sid": "acct_123",
        "textgrid_auth_token": "token_123",
        "textgrid_from_number": "+13467725914",
        "textgrid_webhook_secret": "textgrid-webhook-secret",
        "textgrid_status_callback_url": "https://ares.example.com/marketing/webhooks/textgrid",
        "resend_api_key": "re_123",
        "resend_from_email": "Martin <ops@example.com>",
        "slack_bot_token": "xoxb-test-token",
        "slack_channel_intake": "CINTAKE",
        "cal_booking_url": "https://cal.com/limitless/review",
        "cal_webhook_secret": "cal-webhook-secret",
        "trigger_secret_key": "tr_secret",
        "trigger_non_booker_check_task_id": "marketing-check-submitted-lead-booking",
        "trigger_appointment_reminder_task_id": "marketing-send-appointment-reminder",
        "marketing_appointment_reminders_enabled": True,
    }
    values.update(overrides)
    return Settings(**values)


def _ready_landing_env(**overrides):
    values = {
        "BUSINESS_RUNTIME_MARKETING_LEADS_URL": "https://ares.example.com/marketing/leads",
        "BUSINESS_RUNTIME_API_KEY": "runtime-secret",
        "BUSINESS_RUNTIME_BUSINESS_ID": "limitless",
        "BUSINESS_RUNTIME_ENVIRONMENT": "prod",
        "BUSINESS_RUNTIME_SITE_EVENTS_URL": "https://ares.example.com/site-events",
    }
    values.update(overrides)
    return values


def test_activation_readiness_reports_ready_without_leaking_secrets() -> None:
    report = activation_readiness(settings=_ready_settings(), environ=_ready_landing_env())

    assert report["verdict"] == "ready_for_live_smoke"
    assert report["blockers"] == []
    rendered = json.dumps(report)
    assert "runtime-secret" not in rendered
    assert "xoxb-test-token" not in rendered
    assert "tr_secret" not in rendered
    assert "cal-webhook-secret" not in rendered
    assert report["gates"]["runtime_auth"]["runtime_api_key"]["fingerprint"]


def test_activation_readiness_blocks_live_when_global_send_gate_is_disabled() -> None:
    report = activation_readiness(
        settings=_ready_settings(provider_live_sends_enabled=False),
        environ=_ready_landing_env(),
    )

    assert report["verdict"] == "blocked"
    assert report["safe_to_deploy_without_live_sends"] is True
    assert any("PROVIDER_LIVE_SENDS_ENABLED is false" in blocker for blocker in report["blockers"])


def test_activation_readiness_flags_invalid_resend_sender_and_sensitive_callback_query() -> None:
    report = activation_readiness(
        settings=_ready_settings(
            resend_from_email="Martin at Limitless",
            textgrid_status_callback_url="https://ares.example.com/marketing/webhooks/textgrid?runtime_api_key=secret",
        ),
        environ=_ready_landing_env(),
    )

    assert report["verdict"] == "blocked"
    assert "RESEND_FROM_EMAIL must be an email address" in "\n".join(report["blockers"])
    assert any("TEXTGRID_STATUS_CALLBACK_URL includes sensitive query keys" in warning for warning in report["warnings"])
    rendered = json.dumps(report)
    assert "runtime_api_key=secret" not in rendered
    assert "query=\"<redacted>\"" not in rendered
    assert "<redacted>" in rendered


def test_activation_readiness_requires_landing_runtime_env() -> None:
    report = activation_readiness(settings=_ready_settings(), environ={})

    assert report["verdict"] == "blocked"
    assert "landing: BUSINESS_RUNTIME_MARKETING_LEADS_URL is missing" in report["blockers"]
    assert "landing: BUSINESS_RUNTIME_API_KEY is missing" in report["blockers"]


def test_activation_readiness_cli_exits_nonzero_until_live_ready(monkeypatch, capsys) -> None:
    monkeypatch.setenv("RUNTIME_API_KEY", "runtime-secret")
    monkeypatch.setenv("PROVIDER_LIVE_SENDS_ENABLED", "false")

    with pytest.raises(SystemExit) as exc:
        raise SystemExit(main(["--json"]))

    assert exc.value.code == 2
    output = json.loads(capsys.readouterr().out)
    assert output["verdict"] == "blocked"
    assert "runtime-secret" not in json.dumps(output)


def test_activation_readiness_cli_can_load_env_file_and_derive_local_defaults(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("RUNTIME_API_KEY", raising=False)
    monkeypatch.delenv("BUSINESS_RUNTIME_API_KEY", raising=False)
    env_file = tmp_path / "ares.env"
    env_file.write_text(
        "\n".join(
            [
                "RUNTIME_API_KEY=runtime-secret",
                "TEXTGRID_ACCOUNT_SID=acct_123",
                "TEXTGRID_AUTH_TOKEN=token_123",
                "TEXTGRID_FROM_NUMBER=3467725914",
                "TEXTGRID_WEBHOOK_SECRET=textgrid-webhook-secret",
                "RESEND_API_KEY=re_123",
                "RESEND_FROM_EMAIL=bad-sender",
                "SCHEDULING_URL=https://cal.com/limitless/review",
                "TRIGGER_SECRET_KEY=tr_secret",
            ]
        )
    )

    code = main(
        [
            "--json",
            "--env-file",
            str(env_file),
            "--runtime-url",
            "https://ares.example.com",
            "--derive-local-defaults",
        ]
    )

    assert code == 2
    output = json.loads(capsys.readouterr().out)
    rendered = json.dumps(output)
    assert "runtime-secret" not in rendered
    assert "token_123" not in rendered
    assert "textgrid-webhook-secret" not in rendered
    assert "tr_secret" not in rendered
    assert output["gates"]["runtime_auth"]["configured"] is True
    assert output["gates"]["textgrid"]["configured"] is True
    assert output["gates"]["trigger"]["configured"] is True
    assert output["gates"]["landing"]["configured"] is True
    assert output["gates"]["calcom"]["booking_url"]["sanitized"] == "https://cal.com/limitless/review"
    assert output["gates"]["textgrid"]["status_callback_url"]["sanitized"] == (
        "https://ares.example.com/marketing/webhooks/textgrid"
    )
    assert output["gates"]["landing"]["env"]["BUSINESS_RUNTIME_MARKETING_LEADS_URL"]["sanitized"] == (
        "https://ares.example.com/marketing/leads"
    )
    assert "RESEND_FROM_EMAIL must be an email address" in "\n".join(output["blockers"])
