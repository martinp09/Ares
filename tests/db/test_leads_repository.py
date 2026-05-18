from __future__ import annotations

import pytest

from app.core.config import Settings
from app.db.lead_machine_supabase import LeadMachineTenant
from app.db.leads import LeadsRepository


def _supabase_settings() -> Settings:
    return Settings(
        _env_file=None,
        lead_machine_backend="supabase",
        supabase_url="https://example.supabase.co",
        supabase_service_role_key="service-role",
    )


def test_supabase_list_resolves_slug_business_before_fetching_leads(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "app.db.leads.resolve_tenant",
        lambda business_id, environment, settings=None: LeadMachineTenant(business_pk=101, environment="prod"),
    )

    def fake_fetch_rows(table: str, *, params: dict[str, str], settings=None):
        captured["table"] = table
        captured["params"] = dict(params)
        return [{"id": 7, "business_id": 101, "environment": "prod", "source": "manual"}]

    monkeypatch.setattr("app.db.leads.fetch_rows", fake_fetch_rows)

    records = LeadsRepository(settings=_supabase_settings()).list(business_id="limitless", environment="prod")

    assert [record.id for record in records] == ["lead_7"]
    assert captured == {
        "table": "leads",
        "params": {
            "select": "*",
            "order": "created_at.asc",
            "business_id": "eq.101",
            "environment": "eq.prod",
        },
    }


def test_supabase_list_requires_environment_for_slug_business() -> None:
    with pytest.raises(ValueError, match="environment is required"):
        LeadsRepository(settings=_supabase_settings()).list(business_id="limitless")
