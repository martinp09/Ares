from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.skills import SkillsRepository


def build_repository() -> SkillsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return SkillsRepository(client)


def test_registering_same_skill_name_updates_existing_record() -> None:
    repository = build_repository()

    first = repository.register(
        name="lead_triage",
        description="Route new lead payloads",
        input_schema={"type": "object", "properties": {"lead_id": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"queue": {"type": "string"}}},
        required_tools=[" route_lead "],
        permission_requirements=["crm.write"],
    )
    second = repository.register(
        name="lead_triage",
        description="Route and enrich new lead payloads",
        input_schema={"type": "object", "properties": {"lead_id": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"queue": {"type": "string"}, "score": {"type": "number"}}},
        required_tools=["route_lead", "enrich_lead", "route_lead"],
        permission_requirements=["crm.write", "lead.assign", "crm.write"],
    )

    assert second.id == first.id
    assert second.description == "Route and enrich new lead payloads"
    assert second.required_tools == ["route_lead", "enrich_lead"]
    assert second.permission_requirements == ["crm.write", "lead.assign"]
    assert second.output_schema == {
        "type": "object",
        "properties": {"queue": {"type": "string"}, "score": {"type": "number"}},
    }
    assert repository.get_by_name("lead_triage").id == first.id


def test_list_by_ids_preserves_requested_order() -> None:
    repository = build_repository()

    first = repository.register(name="qualify_seller")
    second = repository.register(name="schedule_follow_up")

    records = repository.list_by_ids([second.id, first.id])

    assert [record.id for record in records] == [second.id, first.id]


def test_repository_returns_defensive_copies_for_skill_metadata() -> None:
    repository = build_repository()

    created = repository.register(
        name="seller_enrichment",
        input_schema={
            "type": "object",
            "properties": {"company": {"type": "string"}},
        },
        required_tools=["lookup_firmographics"],
        permission_requirements=["crm.read"],
    )

    created.input_schema["properties"]["company"]["type"] = "integer"
    created.required_tools.append("mutated_tool")
    created.permission_requirements.append("mutated.permission")

    fetched = repository.get(created.id)

    assert fetched is not None
    assert fetched.input_schema == {
        "type": "object",
        "properties": {"company": {"type": "string"}},
    }
    assert fetched.required_tools == ["lookup_firmographics"]
    assert fetched.permission_requirements == ["crm.read"]
