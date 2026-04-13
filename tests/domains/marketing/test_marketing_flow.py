from app.domains.marketing.service import build_marketing_job_chain


def test_marketing_command_maps_to_expected_job_chain() -> None:
    chain = build_marketing_job_chain("run_market_research")
    assert chain == [
        "runMarketResearch",
        "createCampaignBrief",
        "draftCampaignAssets",
        "assembleLaunchProposal",
    ]
