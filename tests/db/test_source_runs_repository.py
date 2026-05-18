from __future__ import annotations

from app.db.source_runs import SourceRunsRepository


def test_read_only_missing_state_does_not_create_lock_or_parent(tmp_path) -> None:
    state_path = tmp_path / "missing-state" / "source-runs.json"
    repository = SourceRunsRepository(state_path=state_path)

    assert repository.list_runs(business_id="limitless", environment="prod") == []
    assert repository.latest_brief(business_id="limitless", environment="prod") is None

    assert not state_path.exists()
    assert not state_path.with_suffix(".json.lock").exists()
    assert not state_path.parent.exists()
