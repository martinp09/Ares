from pydantic import ValidationError

from app.domains.ares.agent_registry import AresAgentRevisionSpec, AresVersionedAgentRecord


def test_agent_registry_model_carries_versioned_revision_contract() -> None:
    record = AresVersionedAgentRecord(
        name="lead_triage",
        purpose="Rank incoming Ares opportunities",
        revisions=[
            AresAgentRevisionSpec(
                revision="r1",
                allowed_tools=["search", "fetch"],
                risk_policy="read_only",
                output_contract="lead_triage_v1",
            ),
            AresAgentRevisionSpec(
                revision="r2",
                allowed_tools=["search", "fetch", "summarize"],
                risk_policy="human_approval_required_for_sends",
                output_contract="lead_triage_v2",
            ),
        ],
        active_revision="r2",
    )

    assert record.name == "lead_triage"
    assert record.purpose == "Rank incoming Ares opportunities"
    assert [revision.revision for revision in record.revisions] == ["r1", "r2"]
    assert list(record.revisions[1].allowed_tools) == ["search", "fetch", "summarize"]
    assert record.revisions[1].risk_policy == "human_approval_required_for_sends"
    assert record.revisions[1].output_contract == "lead_triage_v2"
    assert record.active_revision == "r2"


def test_agent_registry_model_rejects_unknown_active_revision() -> None:
    try:
        AresVersionedAgentRecord(
            name="lead_triage",
            purpose="Rank incoming Ares opportunities",
            revisions=[
                AresAgentRevisionSpec(
                    revision="r1",
                    allowed_tools=["search"],
                    risk_policy="read_only",
                    output_contract="lead_triage_v1",
                )
            ],
            active_revision="r2",
        )
    except ValidationError as exc:
        message = str(exc)
    else:
        raise AssertionError("expected validation error")

    assert "active_revision" in message
