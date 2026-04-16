from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.leads import LeadsRepository
from app.models.leads import LeadRecord, LeadSource


def build_repository() -> LeadsRepository:
    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
    return LeadsRepository(client)


def test_upsert_reuses_deterministic_id_for_same_lead_identity() -> None:
    repository = build_repository()

    first = repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            source=LeadSource.PROBATE_INTAKE,
            email="owner@example.com",
            first_name="Ava",
        )
    )
    second = repository.upsert(
        LeadRecord(
            business_id="limitless",
            environment="dev",
            email="OWNER@example.com",
            first_name="Updated",
        )
    )

    assert first.id == second.id
    assert second.first_name == "Updated"


def test_upsert_does_not_collide_across_environments() -> None:
    repository = build_repository()

    first = repository.upsert(LeadRecord(business_id="limitless", environment="dev", email="owner@example.com"))
    second = repository.upsert(LeadRecord(business_id="limitless", environment="prod", email="owner@example.com"))

    assert first.id != second.id
