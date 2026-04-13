from app.domains.marketing.commands import MarketingCommandType

MARKETING_JOB_CHAINS: dict[str, list[str]] = {
    "run_market_research": [
        "runMarketResearch",
        "createCampaignBrief",
        "draftCampaignAssets",
        "assembleLaunchProposal",
    ],
    "create_campaign_brief": [
        "createCampaignBrief",
        "draftCampaignAssets",
        "assembleLaunchProposal",
    ],
    "draft_campaign_assets": [
        "draftCampaignAssets",
        "assembleLaunchProposal",
    ],
    "propose_launch": ["assembleLaunchProposal"],
}


def build_marketing_job_chain(command_type: MarketingCommandType) -> list[str]:
    try:
        return MARKETING_JOB_CHAINS[command_type]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"unsupported marketing command: {command_type}") from exc
