from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_API = REPO_ROOT / "trigger" / "src" / "shared" / "runtimeApi.ts"
TRIGGER_PACKAGE = REPO_ROOT / "trigger" / "package.json"
PROBATE_AUTOPILOT_SCHEDULES = REPO_ROOT / "trigger" / "src" / "lead-machine" / "probateAutopilotSchedules.ts"


def test_trigger_runtime_api_uses_explicit_ares_env_contract() -> None:
    source = RUNTIME_API.read_text(encoding="utf-8")

    assert "HERMES_RUNTIME_API_BASE_URL" in source
    assert "RUNTIME_API_BASE_URL" in source
    assert "HERMES_RUNTIME_API_KEY" in source
    assert "RUNTIME_API_KEY" in source
    assert 'headers.authorization = `Bearer ${apiKey}`' in source


def test_trigger_package_exposes_typecheck_contract() -> None:
    source = TRIGGER_PACKAGE.read_text(encoding="utf-8")

    assert '"typecheck": "tsc --noEmit -p tsconfig.json"' in source


def test_probate_autopilot_schedules_are_no_send_and_ct_cadenced() -> None:
    source = PROBATE_AUTOPILOT_SCHEDULES.read_text(encoding="utf-8")

    assert 'timezone = "America/Chicago"' in source
    assert "10 7 * * *" in source
    assert "40 12 * * *" in source
    assert "40 17 * * *" in source
    assert "20 2 * * *" in source
    assert "15 3 * * 0" in source
    assert "harris_montgomery_probate" in source
    assert "live_source_calls: false" in source
    assert "no_send: true" in source
    assert "provider_sends_enabled: false" in source
    assert "window_end: scheduledAt.toISOString()" in source
    assert "LEAD_MACHINE_BUSINESS_ID" in source
    assert "LEAD_MACHINE_ENVIRONMENT" in source
