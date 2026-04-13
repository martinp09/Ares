from app.domains.marketing.commands import (
    APPROVAL_REQUIRED_MARKETING_COMMANDS,
    SAFE_AUTONOMOUS_MARKETING_COMMANDS,
)
from app.models.commands import PolicyResult

POLICY_PRECEDENCE: dict[PolicyResult, int] = {
    "safe_autonomous": 1,
    "approval_required": 2,
    "forbidden": 3,
}


def apply_policy_precedence(*policies: PolicyResult) -> PolicyResult:
    if not policies:
        return "safe_autonomous"
    return max(policies, key=lambda policy: POLICY_PRECEDENCE[policy])


def classify_command(command_type: str) -> PolicyResult:
    if command_type in APPROVAL_REQUIRED_MARKETING_COMMANDS:
        return "approval_required"
    if command_type in SAFE_AUTONOMOUS_MARKETING_COMMANDS:
        return "safe_autonomous"
    return "safe_autonomous"
