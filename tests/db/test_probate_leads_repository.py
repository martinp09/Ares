from app.db.probate_leads import ProbateLeadsRepository


def test_record_from_supabase_ignores_tenant_and_timestamp_columns() -> None:
    record = ProbateLeadsRepository._record_from_supabase(
        {
            "id": 42,
            "business_id": 1,
            "environment": "dev",
            "case_number": "2026-12345",
            "filing_type": "INDEPENDENT ADMINISTRATION",
            "created_at": "2026-04-16T00:00:00+00:00",
            "updated_at": "2026-04-16T00:00:00+00:00",
            "raw_payload": {},
        }
    )

    assert record.id == "prob_42"
    assert record.case_number == "2026-12345"
    assert record.filing_type == "INDEPENDENT ADMINISTRATION"

