from pathlib import Path

import pytest

from app.domains.ares import AresCounty
from app.services.ares_memory_service import AresMemoryService


def _storage_path(tmp_path: Path) -> Path:
    return tmp_path / "runtime" / "ares-memory.json"


def test_load_returns_empty_state_when_storage_file_is_missing(tmp_path: Path) -> None:
    service = AresMemoryService(_storage_path(tmp_path))

    snapshot = service.load()

    assert snapshot.market_preferences == {}
    assert snapshot.county_defaults == {}
    assert snapshot.lead_history == []
    assert snapshot.outreach_history == []
    assert snapshot.operator_decisions == []
    assert snapshot.outcomes == []
    assert snapshot.exceptions == []


def test_memory_state_persists_across_save_and_reload(tmp_path: Path) -> None:
    storage_path = _storage_path(tmp_path)
    writer = AresMemoryService(storage_path)

    writer.set_market_preferences(
        {
            "preferred_counties": ["harris", "dallas"],
            "max_daily_outreach": 25,
        }
    )
    writer.set_county_defaults(
        AresCounty.HARRIS,
        {
            "timezone": "America/Chicago",
            "touch_window": "09:00-18:00",
        },
    )
    writer.record_lead_history(
        {
            "lead_id": "lead-1",
            "status": "new",
            "source": "probate",
        }
    )
    writer.record_outreach_history(
        {
            "lead_id": "lead-1",
            "channel": "email",
            "result": "drafted",
        }
    )
    writer.record_operator_decision(
        {
            "decision_id": "decision-1",
            "decision": "hold",
            "reason": "missing phone number",
        }
    )
    writer.record_outcome(
        {
            "lead_id": "lead-1",
            "outcome": "follow_up",
        }
    )
    writer.record_exception(
        {
            "code": "missing_contact",
            "message": "No phone number available",
        }
    )
    writer.save()

    reader = AresMemoryService(storage_path)
    snapshot = reader.load()

    assert storage_path.exists()
    assert snapshot.market_preferences["max_daily_outreach"] == 25
    assert snapshot.county_defaults[AresCounty.HARRIS]["timezone"] == "America/Chicago"
    assert snapshot.lead_history[0]["lead_id"] == "lead-1"
    assert snapshot.outreach_history[0]["channel"] == "email"
    assert snapshot.operator_decisions[0]["decision"] == "hold"
    assert snapshot.outcomes[0]["outcome"] == "follow_up"
    assert snapshot.exceptions[0]["code"] == "missing_contact"


def test_first_memory_event_is_preserved_without_explicit_load(tmp_path: Path) -> None:
    service = AresMemoryService(_storage_path(tmp_path))

    service.record_lead_history({"lead_id": "lead-1", "status": "new"})

    snapshot = service.snapshot()
    assert snapshot.lead_history == [{"lead_id": "lead-1", "status": "new"}]


def test_concurrent_memory_writers_merge_history_instead_of_clobbering(tmp_path: Path) -> None:
    storage_path = _storage_path(tmp_path)
    writer_a = AresMemoryService(storage_path)
    writer_b = AresMemoryService(storage_path)

    writer_a.load()
    writer_b.load()

    writer_a.record_lead_history({"lead_id": "lead-a", "status": "new"})
    writer_a.save()

    writer_b.record_lead_history({"lead_id": "lead-b", "status": "new"})
    writer_b.save()

    snapshot = AresMemoryService(storage_path).load()

    assert [entry["lead_id"] for entry in snapshot.lead_history] == ["lead-a", "lead-b"]


def test_memory_load_raises_predictable_error_for_corrupt_json(tmp_path: Path) -> None:
    storage_path = _storage_path(tmp_path)
    storage_path.parent.mkdir(parents=True, exist_ok=True)
    storage_path.write_text("{ definitely-not-valid-json", encoding="utf-8")

    service = AresMemoryService(storage_path)

    with pytest.raises(ValueError, match="Corrupted Ares memory state"):
        service.load()
