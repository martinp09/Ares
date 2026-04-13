from app.policies.classifier import apply_policy_precedence, classify_command


def test_marketing_research_is_safe_autonomous() -> None:
    result = classify_command("run_market_research")
    assert result == "safe_autonomous"


def test_publish_campaign_requires_approval() -> None:
    result = classify_command("publish_campaign")
    assert result == "approval_required"


def test_policy_precedence_forbidden_beats_approval_required() -> None:
    result = apply_policy_precedence("approval_required", "forbidden")
    assert result == "forbidden"


def test_policy_precedence_does_not_downgrade_approval_required() -> None:
    result = apply_policy_precedence("approval_required", "safe_autonomous")
    assert result == "approval_required"
