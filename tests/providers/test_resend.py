from app.core.config import Settings
from app.providers.resend import build_send_email_request
from app.services.providers.resend import get_resend_status, send_test_email


def test_resend_request_shape() -> None:
    request = build_send_email_request(
        api_key="re_123",
        from_email="Hermes <team@example.com>",
        to_email="lead@example.com",
        subject="Thanks for your lease-option inquiry",
        text_body="We got your message.",
    )

    assert request["endpoint"] == "https://api.resend.com/emails"
    assert request["headers"] == {
        "Authorization": "Bearer re_123",
        "Content-Type": "application/json",
    }
    assert request["payload"] == {
        "from": "Hermes <team@example.com>",
        "to": ["lead@example.com"],
        "subject": "Thanks for your lease-option inquiry",
        "text": "We got your message.",
    }


def test_settings_exposes_resend_provider_fields() -> None:
    settings = Settings(
        resend_api_key="re_abc",
        resend_from_email="hello@example.com",
    )
    assert settings.resend_api_key == "re_abc"
    assert settings.resend_from_email == "hello@example.com"


def test_resend_status_flags_invalid_sender_identity() -> None:
    status = get_resend_status(
        Settings(
            _env_file=None,
            resend_api_key="re_abc",
            resend_from_email="marketing",
        )
    )

    assert status["configured"] is False
    assert status["can_send"] is False
    assert status["details"] == "Invalid RESEND_FROM_EMAIL format"


def test_resend_test_send_rejects_invalid_sender_identity() -> None:
    try:
        send_test_email(
            Settings(
                _env_file=None,
                resend_api_key="re_abc",
                resend_from_email="marketing",
            ),
            to="lead@example.com",
            subject="Smoke",
            text="Test",
        )
    except RuntimeError as exc:
        assert str(exc) == "RESEND_FROM_EMAIL must be an email address or Name <email@example.com>"
    else:
        raise AssertionError("Expected invalid Resend sender identity to fail before provider call")
