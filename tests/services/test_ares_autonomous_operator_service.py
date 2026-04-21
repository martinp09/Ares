from app.services.ares_agent_registry_service import AresAgentRegistryService
from app.services.ares_autonomous_operator_service import AresAutonomousOperatorService


def test_initialize_surface_is_idempotent_and_does_not_duplicate_agent_revisions() -> None:
    registry = AresAgentRegistryService()
    service = AresAutonomousOperatorService(agent_registry_service=registry)

    service.initialize_surface()
    service.initialize_surface()

    record = registry.get_agent("ares_guarded_operator")

    assert record is not None
    assert record.active_revision == "v1"
    assert [revision.revision for revision in record.revisions] == ["v1"]
