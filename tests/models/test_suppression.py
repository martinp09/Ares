from app.models.suppression import SuppressionRecord, SuppressionScope, SuppressionSource


def test_global_suppression_uses_identity_scope_key() -> None:
    record = SuppressionRecord(
        business_id="limitless",
        environment="dev",
        email="Owner@Example.com",
        reason="opt_out",
        source=SuppressionSource.WEBHOOK,
    )

    assert record.scope_key() == "global:owner@example.com"
    assert record.scope == SuppressionScope.GLOBAL


def test_campaign_suppression_requires_campaign_and_preserves_active_state() -> None:
    record = SuppressionRecord(
        business_id="limitless",
        environment="dev",
        lead_id="lead_123",
        campaign_id="camp_123",
        scope=SuppressionScope.CAMPAIGN,
        reason="reply_received",
        source=SuppressionSource.AUTOMATION,
        active=False,
    )

    assert record.scope_key() == "campaign:camp_123:lead_123"
    assert record.active is False
