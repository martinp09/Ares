from fastapi.testclient import TestClient

from app.main import app


def test_marketing_runtime_endpoints_match_trigger_worker_contract() -> None:
    client = TestClient(app)

    market_research = client.post(
        "/marketing/market-research/run",
        json={"campaignId": "camp-1", "market": "houston"},
    )
    assert market_research.status_code == 200
    assert market_research.json()["artifact_type"] == "market_research"

    campaign_brief = client.post(
        "/marketing/campaign-brief/create",
        json={"campaignId": "camp-1", "marketResearch": {"artifact_type": "market_research"}},
    )
    assert campaign_brief.status_code == 200
    assert campaign_brief.json()["artifact_type"] == "campaign_brief"

    campaign_assets = client.post(
        "/marketing/campaign-assets/draft",
        json={"campaignId": "camp-1", "campaignBrief": {"artifact_type": "campaign_brief"}},
    )
    assert campaign_assets.status_code == 200
    assert campaign_assets.json()["artifact_type"] == "campaign_assets"

    launch_proposal = client.post(
        "/marketing/launch-proposal/assemble",
        json={"campaignId": "camp-1", "campaignAssets": {"artifact_type": "campaign_assets"}},
    )
    assert launch_proposal.status_code == 200
    assert launch_proposal.json()["artifact_type"] == "launch_proposal"
