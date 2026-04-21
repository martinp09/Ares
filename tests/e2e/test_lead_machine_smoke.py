from scripts.smoke.lead_machine_smoke import run_lead_machine_smoke


def test_lead_machine_smoke_harness_covers_duplicate_submission_replay_and_manual_task_dedupe() -> None:
    result = run_lead_machine_smoke()

    assert result["duplicate_submission"]["second_status"] == "duplicate"
    assert result["replay_safety"]["requires_approval"] is False
    assert result["replay_safety"]["child_run_id"] is not None
    assert result["manual_call_task"]["first_status"] == "reminded"
    assert result["manual_call_task"]["second_status"] == "deduped"
