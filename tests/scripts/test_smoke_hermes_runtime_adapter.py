import json
from urllib import request

from scripts import smoke_hermes_runtime_adapter as smoke


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_smoke_polls_safe_run_and_reads_mission_control(monkeypatch, capsys) -> None:
    calls: list[tuple[str, str, str | None]] = []

    def fake_urlopen(req: request.Request, timeout: int):
        body = req.data.decode("utf-8") if req.data else None
        calls.append((req.get_method(), req.full_url, body))
        if req.full_url.endswith("/health"):
            return FakeResponse({"status": "ok"})
        if req.full_url.endswith("/hermes/tools"):
            return FakeResponse({"tools": [{"name": "run_market_research"}]})
        if req.full_url.endswith("/hermes/tools/run_market_research/invoke"):
            return FakeResponse({"id": "cmd_safe", "run_id": "run_safe", "deduped": False})
        if req.full_url.endswith("/runs/run_safe"):
            return FakeResponse({"id": "run_safe", "status": "queued", "trigger_run_id": None})
        if req.full_url.endswith("/mission-control/dashboard?business_id=limitless&environment=dev"):
            return FakeResponse({"active_run_count": 1, "recent_completed_count": 0})
        if req.full_url.endswith("/mission-control/runs?business_id=limitless&environment=dev"):
            return FakeResponse({"runs": [{"id": "run_safe", "status": "queued"}]})
        if req.full_url.endswith("/mission-control/approvals?business_id=limitless&environment=dev"):
            return FakeResponse({"approvals": []})
        raise AssertionError(req.full_url)

    monkeypatch.setattr(smoke.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("HERMES_RUNTIME_API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("HERMES_RUNTIME_API_KEY", "super-secret-runtime-key")
    monkeypatch.delenv("ARES_SMOKE_APPROVAL_PATH", raising=False)

    assert smoke.main() == 0

    output = json.loads(capsys.readouterr().out)
    assert output["run"]["id"] == "run_safe"
    assert output["mission_control"]["safe_run_readback"] is True
    assert "super-secret-runtime-key" not in json.dumps(output)
    assert [method for method, _, _ in calls] == ["GET", "GET", "POST", "GET", "GET", "GET", "GET"]


def test_smoke_can_exercise_approval_path_when_enabled(monkeypatch, capsys) -> None:
    seen_urls: list[str] = []

    def fake_urlopen(req: request.Request, timeout: int):
        seen_urls.append(req.full_url)
        if req.full_url.endswith("/health"):
            return FakeResponse({"status": "ok"})
        if req.full_url.endswith("/hermes/tools"):
            return FakeResponse({"tools": [{"name": "run_market_research"}, {"name": "publish_campaign"}]})
        if req.full_url.endswith("/hermes/tools/run_market_research/invoke"):
            return FakeResponse({"id": "cmd_safe", "run_id": "run_safe", "deduped": False})
        if req.full_url.endswith("/runs/run_safe"):
            return FakeResponse({"id": "run_safe", "status": "queued"})
        if req.full_url.endswith("/hermes/tools/publish_campaign/invoke"):
            return FakeResponse({"id": "cmd_approval", "approval_id": "apr_1", "run_id": None})
        if req.full_url.endswith("/approvals/apr_1/approve"):
            return FakeResponse({"approval_id": "apr_1", "run_id": "run_approved", "status": "approved"})
        if req.full_url.endswith("/runs/run_approved"):
            return FakeResponse({"id": "run_approved", "status": "queued"})
        if req.full_url.endswith("/mission-control/dashboard?business_id=limitless&environment=dev"):
            return FakeResponse({"active_run_count": 2})
        if req.full_url.endswith("/mission-control/runs?business_id=limitless&environment=dev"):
            return FakeResponse({"runs": [{"id": "run_safe"}, {"id": "run_approved"}]})
        if req.full_url.endswith("/mission-control/approvals?business_id=limitless&environment=dev"):
            return FakeResponse({"approvals": [{"id": "apr_1", "status": "approved"}]})
        raise AssertionError(req.full_url)

    monkeypatch.setattr(smoke.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("HERMES_RUNTIME_API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("HERMES_RUNTIME_API_KEY", "super-secret-runtime-key")
    monkeypatch.setenv("ARES_SMOKE_APPROVAL_PATH", "1")

    assert smoke.main() == 0

    output = json.loads(capsys.readouterr().out)
    assert output["approval"]["approval_id"] == "apr_1"
    assert output["approval"]["run_id"] == "run_approved"
    assert output["mission_control"]["approval_run_readback"] is True
    assert any(url.endswith("/approvals/apr_1/approve") for url in seen_urls)


def test_smoke_fails_when_required_tool_is_missing(monkeypatch) -> None:
    def fake_urlopen(req: request.Request, timeout: int):
        if req.full_url.endswith("/health"):
            return FakeResponse({"status": "ok"})
        if req.full_url.endswith("/hermes/tools"):
            return FakeResponse({"tools": []})
        if req.full_url.endswith("/hermes/tools/run_market_research/invoke"):
            return FakeResponse({"id": "cmd_safe", "run_id": "run_safe", "deduped": False})
        if req.full_url.endswith("/runs/run_safe"):
            return FakeResponse({"id": "run_safe", "status": "queued"})
        if req.full_url.endswith("/mission-control/dashboard?business_id=limitless&environment=dev"):
            return FakeResponse({"active_run_count": 1, "recent_completed_count": 0})
        if req.full_url.endswith("/mission-control/runs?business_id=limitless&environment=dev"):
            return FakeResponse({"runs": [{"id": "run_safe", "status": "queued"}]})
        if req.full_url.endswith("/mission-control/approvals?business_id=limitless&environment=dev"):
            return FakeResponse({"approvals": []})
        raise AssertionError(req.full_url)

    monkeypatch.setattr(smoke.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("HERMES_RUNTIME_API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("HERMES_RUNTIME_API_KEY", "super-secret-runtime-key")
    monkeypatch.delenv("ARES_SMOKE_APPROVAL_PATH", raising=False)

    try:
        smoke.main()
    except SystemExit as exc:
        assert "run_market_research" in str(exc)
    else:
        raise AssertionError("smoke.main() should fail closed")


def test_smoke_fails_when_safe_run_is_not_read_back(monkeypatch) -> None:
    def fake_urlopen(req: request.Request, timeout: int):
        if req.full_url.endswith("/health"):
            return FakeResponse({"status": "ok"})
        if req.full_url.endswith("/hermes/tools"):
            return FakeResponse({"tools": [{"name": "run_market_research"}]})
        if req.full_url.endswith("/hermes/tools/run_market_research/invoke"):
            return FakeResponse({"id": "cmd_safe", "run_id": "run_safe", "deduped": False})
        if req.full_url.endswith("/runs/run_safe"):
            return FakeResponse({"id": "run_safe", "status": "queued"})
        if req.full_url.endswith("/mission-control/dashboard?business_id=limitless&environment=dev"):
            return FakeResponse({"active_run_count": 0, "recent_completed_count": 0})
        if req.full_url.endswith("/mission-control/runs?business_id=limitless&environment=dev"):
            return FakeResponse({"runs": []})
        if req.full_url.endswith("/mission-control/approvals?business_id=limitless&environment=dev"):
            return FakeResponse({"approvals": []})
        raise AssertionError(req.full_url)

    monkeypatch.setattr(smoke.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("HERMES_RUNTIME_API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("HERMES_RUNTIME_API_KEY", "super-secret-runtime-key")
    monkeypatch.delenv("ARES_SMOKE_APPROVAL_PATH", raising=False)

    try:
        smoke.main()
    except SystemExit as exc:
        assert "safe run readback" in str(exc)
    else:
        raise AssertionError("smoke.main() should fail closed")
