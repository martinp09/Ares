from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_API = REPO_ROOT / "trigger" / "src" / "shared" / "runtimeApi.ts"
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
