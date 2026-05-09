from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_API = REPO_ROOT / "trigger" / "src" / "shared" / "runtimeApi.ts"
LEAD_MACHINE_RUNTIME = REPO_ROOT / "trigger" / "src" / "lead-machine" / "runtime.ts"
HARRIS_DAILY_IMPORT_TASK = REPO_ROOT / "trigger" / "src" / "lead-machine" / "harrisDailyImport.ts"
TRIGGER_PACKAGE = REPO_ROOT / "trigger" / "package.json"


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


def test_trigger_exposes_harris_daily_import_contract() -> None:
    runtime_source = LEAD_MACHINE_RUNTIME.read_text(encoding="utf-8")
    task_source = HARRIS_DAILY_IMPORT_TASK.read_text(encoding="utf-8")

    assert 'harrisDailyImport: "/lead-machine/harris/daily-import"' in runtime_source
    assert "export type HarrisDailyImportPayload" in runtime_source
    assert "export type HarrisDailyImportResponse" in runtime_source
    assert 'id: "harris-daily-import"' in task_source
    assert '"harrisDailyImport"' in task_source
    assert "lead_machine_harris_daily_import" in task_source
