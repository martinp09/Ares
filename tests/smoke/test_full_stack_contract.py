from scripts.smoke_full_stack_cohesion import run_full_stack_cohesion_smoke
from scripts.smoke_provider_readiness import provider_readiness


def test_full_stack_cohesion_smoke_contract() -> None:
    result = run_full_stack_cohesion_smoke(no_live_sends=True)

    assert result["health"] == {"status": "ok"}
    assert result["hermes"]["tool_count"] > 0
    assert result["trigger"]["completed_status"] == "completed"
    assert result["lead"]["booking_status"] == "booked"
    assert result["providers"] == {
        "calcom_status": "processed",
        "textgrid_status": "processed",
        "textgrid_action": "qualify",
        "live_sends": False,
    }
    assert result["mission_control"]["run_status"] == "completed"
    assert result["mission_control"]["run_count"] == 1
    assert result["mission_control"]["recent_completed_count"] >= 1
    assert result["mission_control"]["active_run_count"] == 0
    assert result["mission_control"]["opportunity_count"] >= 1
    assert result["state"]["message_count"] == 1
    assert result["state"]["task_count"] == 1
    assert result["state"]["booking_event_count"] == 1
    assert result["state"]["usage_by_kind"]["run"] >= 1
    assert result["state"]["audit_by_type"]["trigger_run_completed"] >= 1


def test_full_stack_cohesion_smoke_is_repeatable_with_live_env_present(monkeypatch) -> None:
    monkeypatch.setenv("TEXTGRID_ACCOUNT_SID", "acct_live_should_not_send")
    monkeypatch.setenv("TEXTGRID_AUTH_TOKEN", "token_live_should_not_send")
    monkeypatch.setenv("TEXTGRID_FROM_NUMBER", "+15550000000")
    monkeypatch.setenv("RESEND_API_KEY", "re_live_should_not_send")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "sender@example.com")
    monkeypatch.setenv("TRIGGER_SECRET_KEY", "tr_live_should_not_schedule")

    first = run_full_stack_cohesion_smoke(no_live_sends=True)
    second = run_full_stack_cohesion_smoke(no_live_sends=True)

    assert first["providers"]["live_sends"] is False
    assert second["providers"]["live_sends"] is False
    assert first["state"]["message_count"] == second["state"]["message_count"] == 1
    assert first["state"]["booking_event_count"] == second["state"]["booking_event_count"] == 1
    assert first["mission_control"]["run_count"] == second["mission_control"]["run_count"] == 1


def test_provider_readiness_is_shape_only_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ARES_SMOKE_SEND_SMS", raising=False)
    monkeypatch.delenv("ARES_SMOKE_SEND_EMAIL", raising=False)

    result = provider_readiness()

    assert result["live_sms_requested"] is False
    assert result["live_email_requested"] is False
    assert result["textgrid"]["payload_keys"] == ["Body", "From", "StatusCallback", "To"]
    assert result["resend"]["payload_keys"] == ["from", "subject", "text", "to"]
