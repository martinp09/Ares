import pytest

from app.services.ares_agent_registry_service import AresAgentRegistryService


def test_registry_stores_multiple_revisions_per_agent_and_tracks_active_revision() -> None:
    service = AresAgentRegistryService()

    service.register_revision(
        name="lead_triage",
        purpose="Rank incoming Ares opportunities",
        revision="r1",
        allowed_tools=["search"],
        risk_policy="read_only",
        output_contract="lead_triage_v1",
        set_active=True,
    )
    updated = service.register_revision(
        name="lead_triage",
        purpose="Rank incoming Ares opportunities",
        revision="r2",
        allowed_tools=["search", "summarize"],
        risk_policy="human_approval_required_for_sends",
        output_contract="lead_triage_v2",
        set_active=True,
    )

    assert [revision.revision for revision in updated.revisions] == ["r1", "r2"]
    assert updated.active_revision == "r2"
    assert updated.revisions[0].output_contract == "lead_triage_v1"


def test_registry_round_trips_through_snapshot_models() -> None:
    service = AresAgentRegistryService()
    service.register_revision(
        name="lead_triage",
        purpose="Rank incoming Ares opportunities",
        revision="r1",
        allowed_tools=["search", "fetch"],
        risk_policy="read_only",
        output_contract="lead_triage_v1",
        set_active=True,
    )

    snapshot = service.export_snapshot()
    reloaded = AresAgentRegistryService.from_snapshot(snapshot)
    restored = reloaded.get_agent("lead_triage")

    assert restored is not None
    assert restored.active_revision == "r1"
    assert list(restored.revisions[0].allowed_tools) == ["search", "fetch"]
    assert restored.model_dump(mode="json") == snapshot[0]


def test_registry_rejects_conflicting_duplicate_revision_registration() -> None:
    service = AresAgentRegistryService()
    service.register_revision(
        name="lead_triage",
        purpose="Rank incoming Ares opportunities",
        revision="r1",
        allowed_tools=["search"],
        risk_policy="read_only",
        output_contract="lead_triage_v1",
        set_active=True,
    )

    with pytest.raises(ValueError, match="immutable"):
        service.register_revision(
            name="lead_triage",
            purpose="Rank incoming Ares opportunities",
            revision="r1",
            allowed_tools=["search", "summarize"],
            risk_policy="read_only",
            output_contract="lead_triage_v2",
            set_active=True,
        )
