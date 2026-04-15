from pathlib import Path

from app.domains.marketing.service import build_marketing_job_chain


def test_marketing_command_maps_to_expected_job_chain() -> None:
    chain = build_marketing_job_chain("run_market_research")
    assert chain == [
        "runMarketResearch",
        "createCampaignBrief",
        "draftCampaignAssets",
        "assembleLaunchProposal",
    ]


REPO_ROOT = Path(__file__).resolve().parents[3]
QUEUE_KEYS_FILE = REPO_ROOT / "trigger" / "src" / "runtime" / "queueKeys.ts"
RUNTIME_API_FILE = REPO_ROOT / "trigger" / "src" / "shared" / "runtimeApi.ts"


def test_marketing_queue_key_helpers_exist() -> None:
    source = QUEUE_KEYS_FILE.read_text(encoding="utf-8")

    assert "export function marketingQueueKey" in source
    assert "export function leadSequenceQueueKey" in source


def test_runtime_api_supports_runtime_env_fallbacks() -> None:
    source = RUNTIME_API_FILE.read_text(encoding="utf-8")

    assert "HERMES_RUNTIME_API_BASE_URL" in source
    assert "RUNTIME_API_BASE_URL" in source
    assert "HERMES_RUNTIME_API_KEY" in source
    assert "RUNTIME_API_KEY" in source
