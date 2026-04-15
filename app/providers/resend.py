from typing import Any


def build_send_email_request(
    *,
    api_key: str,
    from_email: str,
    to_email: str,
    subject: str,
    text_body: str,
) -> dict[str, Any]:
    return {
        "endpoint": "https://api.resend.com/emails",
        "headers": {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        "payload": {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "text": text_body,
        },
    }
