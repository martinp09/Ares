from app.db.client import InMemoryControlPlaneClient, InMemoryControlPlaneStore
from app.db.title_packets import TitlePacketsRepository
from app.models.title_packets import TitlePacketRecord, TitlePacketStatus


def test_title_packet_upsert_is_idempotent_by_external_key() -> None:
    repository = TitlePacketsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore()))
    packet = TitlePacketRecord(
        business_id="limitless",
        environment="dev",
        external_key="harris-hot18:0611340530007",
        lead_id="lead_123",
        status=TitlePacketStatus.NEEDS_REVIEW,
        owner_name="PLUMMER LETITIA W ESTATE OF",
        property_address="3324 S MACGREGOR WAY 77021",
        hctax_account="0611340530007",
        probate_case_number="500741",
        operator_lane="A — probate-first estate lead",
        facts={"tax_due": 63829.57},
    )

    created = repository.upsert(packet)
    updated = repository.upsert(packet.model_copy(update={"facts": {"tax_due": 64000.0}}))

    records = repository.list(business_id="limitless", environment="dev")
    assert created.id == updated.id
    assert len(records) == 1
    assert records[0].facts["tax_due"] == 64000.0
    assert repository.get_by_key(
        business_id="limitless",
        environment="dev",
        dedupe_key="title-packet:harris-hot18:0611340530007",
    ).id == created.id


def test_title_packet_list_filters_by_lead_and_status() -> None:
    repository = TitlePacketsRepository(InMemoryControlPlaneClient(InMemoryControlPlaneStore()))
    repository.upsert(
        TitlePacketRecord(
            business_id="limitless",
            environment="dev",
            external_key="harris-hot18:1",
            lead_id="lead_1",
            status=TitlePacketStatus.NEEDS_REVIEW,
        )
    )
    repository.upsert(
        TitlePacketRecord(
            business_id="limitless",
            environment="dev",
            external_key="harris-hot18:2",
            lead_id="lead_2",
            status=TitlePacketStatus.COMPLETED,
        )
    )

    records = repository.list(
        business_id="limitless",
        environment="dev",
        lead_id="lead_1",
        status=TitlePacketStatus.NEEDS_REVIEW,
    )

    assert [record.external_key for record in records] == ["harris-hot18:1"]
