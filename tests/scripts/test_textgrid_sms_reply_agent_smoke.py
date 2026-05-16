import json
from urllib import request
from urllib.parse import parse_qs

from scripts.smoke import textgrid_sms_reply_agent_smoke as smoke


class FakeResponse:
    def __init__(self, payload: str, *, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self.payload = payload
        self.status = status
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload.encode("utf-8")

    def getcode(self) -> int:
        return self.status


def test_smoke_posts_signed_webhook_without_bearer_auth(monkeypatch, capsys) -> None:
    calls: list[request.Request] = []

    def fake_urlopen(req: request.Request, timeout: int):
        calls.append(req)
        assert timeout == 15
        assert req.full_url == "http://localhost:8000/sms-agent/webhooks/textgrid"
        assert req.get_header("Authorization") is None
        payload = {key: values[-1] for key, values in parse_qs(req.data.decode("utf-8")).items()}
        expected = smoke.build_twilio_signature(
            secret="whsec_123",
            request_url=req.full_url,
            payload=payload,
        )
        assert req.get_header("X-twilio-signature") == expected
        assert payload["From"] == "+15551234567"
        assert payload["To"] == "+13467725914"
        assert payload["Body"] == "Can you call me?"
        return FakeResponse(
            "<Response></Response>",
            headers={"Content-Type": "application/xml", "X-Ares-Sms-Agent-Status": "processed"},
        )

    monkeypatch.setattr(smoke.request, "urlopen", fake_urlopen)

    assert (
        smoke.main(
            [
                "--runtime-url",
                "http://localhost:8000",
                "--webhook-secret",
                "whsec_123",
                "--from",
                "+15551234567",
                "--to",
                "+13467725914",
                "--body",
                "Can you call me?",
                "--message-sid",
                "SMfixed",
            ]
        )
        == 0
    )

    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "passed"
    assert output["request"]["authorization_sent_to_webhook"] is False
    assert output["request"]["live_textgrid_send"] is False
    assert output["request"]["provider_dashboard_mutation"] is False
    assert output["request"]["from"] == "+1******4567"
    assert output["request"]["to"] == "+1******5914"
    assert "whsec_123" not in json.dumps(output)
    assert len(calls) == 1


def test_smoke_calls_process_pending_with_bearer_auth_when_runtime_key_is_provided(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str | None, str | None]] = []

    def fake_urlopen(req: request.Request, timeout: int):
        calls.append(
            (
                req.full_url,
                req.get_header("Authorization"),
                req.data.decode("utf-8") if req.data else None,
            )
        )
        if req.full_url.endswith("/sms-agent/webhooks/textgrid"):
            return FakeResponse("<Response></Response>")
        if req.full_url.endswith("/sms-agent/internal/process-pending"):
            return FakeResponse(
                json.dumps(
                    {
                        "processed_count": 1,
                        "sent_count": 0,
                        "blocked_count": 1,
                        "failed_count": 0,
                    }
                )
            )
        raise AssertionError(req.full_url)

    monkeypatch.setattr(smoke.request, "urlopen", fake_urlopen)

    assert (
        smoke.main(
            [
                "--runtime-url",
                "http://localhost:8000",
                "--webhook-secret",
                "whsec_123",
                "--from",
                "+15551234567",
                "--to",
                "+13467725914",
                "--body",
                "Can you call me?",
                "--runtime-api-key",
                "runtime-secret",
                "--process-limit",
                "3",
                "--message-sid",
                "SMfixed",
            ]
        )
        == 0
    )

    output = json.loads(capsys.readouterr().out)
    assert output["process_pending"]["response"]["processed_count"] == 1
    assert output["process_pending"]["response"]["sent_count"] == 0
    assert "runtime-secret" not in json.dumps(output)
    assert calls[0][1] is None
    assert calls[1] == (
        "http://localhost:8000/sms-agent/internal/process-pending",
        "Bearer runtime-secret",
        '{"limit":3}',
    )
