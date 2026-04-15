from app.core.config import Settings
from app.providers.resend import build_send_email_request


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
