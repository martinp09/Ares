from app.domains.marketing.commands import (
    APPROVAL_REQUIRED_MARKETING_COMMANDS,
    SAFE_AUTONOMOUS_MARKETING_COMMANDS,
)
from app.models.commands import CommandPolicy

POLICY_PRECEDENCE: dict[CommandPolicy, int] = {
    CommandPolicy.SAFE_AUTONOMOUS: 1,
    CommandPolicy.APPROVAL_REQUIRED: 2,
    CommandPolicy.FORBIDDEN: 3,
}


def apply_policy_precedence(*policies: CommandPolicy) -> CommandPolicy:
    if not policies:
        return CommandPolicy.SAFE_AUTONOMOUS
    return max(policies, key=lambda policy: POLICY_PRECEDENCE[policy])


def classify_command(command_type: str) -> CommandPolicy:
    if command_type in APPROVAL_REQUIRED_MARKETING_COMMANDS:
        return CommandPolicy.APPROVAL_REQUIRED
    if command_type in SAFE_AUTONOMOUS_MARKETING_COMMANDS:
        return CommandPolicy.SAFE_AUTONOMOUS
    return CommandPolicy.FORBIDDEN
