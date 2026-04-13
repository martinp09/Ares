from typing import Literal

MarketingCommandType = Literal[
    "run_market_research",
    "create_campaign_brief",
    "draft_campaign_assets",
    "propose_launch",
    "publish_campaign",
]

SAFE_AUTONOMOUS_MARKETING_COMMANDS: set[str] = {
    "run_market_research",
    "create_campaign_brief",
    "draft_campaign_assets",
}

APPROVAL_REQUIRED_MARKETING_COMMANDS: set[str] = {
    "propose_launch",
    "publish_campaign",
}

SUPPORTED_MARKETING_COMMANDS: set[str] = (
    SAFE_AUTONOMOUS_MARKETING_COMMANDS | APPROVAL_REQUIRED_MARKETING_COMMANDS
)
