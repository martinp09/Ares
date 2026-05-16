from collections import defaultdict
from typing import cast

from app.core.config import Settings
from app.db.client import SupabaseControlPlaneClient
from app.models.deals import (
    Deal,
    DealDocumentRequirement,
    DealParty,
    DealRiskFlag,
    DealSourceLane,
    DealStage,
    DealStrategyLane,
    DealTask,
    DealTaskType,
)


def build_settings() -> Settings:
    return Settings(
        _env_file=None,
        control_plane_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def test_supabase_control_plane_persists_and_hydrates_deal_spine(monkeypatch) -> None:
    rows_by_table: dict[str, dict[str, dict]] = defaultdict(dict)

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        return list(rows_by_table.get(table, {}).values())

    def fake_insert_rows(table: str, rows: list[dict], *, select=None, prefer="return=representation", settings=None):
        for row in rows:
            rows_by_table[table][str(row["id"])] = dict(row)
        return [{"id": row["id"]} for row in rows]

    def fake_patch_rows(table: str, *, params: dict[str, str], row: dict, select=None, settings=None):
        rows_by_table[table][str(row["id"])] = dict(row)
        return [{"id": row["id"]}]

    monkeypatch.setattr("app.db.control_plane_store_supabase.fetch_rows", fake_fetch_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.insert_rows", fake_insert_rows)
    monkeypatch.setattr("app.db.control_plane_store_supabase.patch_rows", fake_patch_rows)

    client = SupabaseControlPlaneClient(build_settings())
    with client.transaction() as store:
        deal = Deal(
            id="deal_1",
            business_id="limitless",
            environment="prod",
            source_lane=DealSourceLane.HARRIS_PROBATE,
            strategy_lane=DealStrategyLane.CURATIVE_TITLE,
            stage=DealStage.QUALIFIED,
            source_record_id="lead_1",
            source_lead_id="lead_1",
            property_address="123 Skyview Dr",
            metadata={"dedupe_key": "lead:harris_probate:lead_1"},
        )
        assert deal.id is not None
        store.deals[deal.id] = deal
        store.deal_keys[(deal.business_id, deal.environment, "lead:harris_probate:lead_1")] = deal.id
        party = DealParty(
            id="party_1",
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            name="Jane Applicant",
        )
        task = DealTask(
            id="task_1",
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            task_type=DealTaskType.VERIFY_AUTHORITY,
            title="Verify authority",
        )
        doc = DealDocumentRequirement(
            id="doc_1",
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            document_type="letters_testamentary_or_administration",
            required_stage=DealStage.CONTACT_READY,
        )
        risk = DealRiskFlag(
            id="risk_1",
            business_id=deal.business_id,
            environment=deal.environment,
            deal_id=deal.id,
            code="authority_unverified",
            label="Seller authority is not verified",
        )
        store.deal_parties[party.id] = party
        store.deal_tasks[task.id] = task
        store.deal_document_requirements[doc.id] = doc
        store.deal_risk_flags[risk.id] = risk

    assert "deal_records_runtime" in rows_by_table
    assert "deal_parties_runtime" in rows_by_table
    assert "deal_tasks_runtime" in rows_by_table
    assert "deal_document_requirements_runtime" in rows_by_table
    assert "deal_risk_flags_runtime" in rows_by_table

    with client.transaction() as store:
        assert store.deals["deal_1"].property_address == "123 Skyview Dr"
        assert store.deal_keys[("limitless", "prod", "lead:harris_probate:lead_1")] == "deal_1"
        assert store.deal_parties["party_1"].name == "Jane Applicant"
        assert store.deal_tasks["task_1"].title == "Verify authority"
        assert store.deal_document_requirements["doc_1"].required_stage == DealStage.CONTACT_READY
        assert store.deal_risk_flags["risk_1"].code == "authority_unverified"
