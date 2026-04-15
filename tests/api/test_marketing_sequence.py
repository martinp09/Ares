from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK_BOOKING_TASK = (
    REPO_ROOT / "trigger" / "src" / "marketing" / "checkSubmittedLeadBooking.ts"
)
SEQUENCE_STEP_TASK = (
    REPO_ROOT / "trigger" / "src" / "marketing" / "runLeaseOptionSequenceStep.ts"
)
MANUAL_CALL_TASK = (
    REPO_ROOT / "trigger" / "src" / "marketing" / "createManualCallTask.ts"
)


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_check_submitted_lead_booking_contract() -> None:
    source = _source(CHECK_BOOKING_TASK)

    assert 'id: "marketing-check-submitted-lead-booking"' in source
    assert '"/marketing/internal/non-booker-check"' in source
    assert 'tasks.trigger("marketing-run-lease-option-sequence-step"' in source


def test_lease_option_sequence_is_hardcoded_for_mvp() -> None:
    source = _source(SEQUENCE_STEP_TASK)

    assert "LEASE_OPTION_SEQUENCE_STEPS" in source
    for day in (0, 1, 2, 4, 6, 8, 10):
        assert re.search(rf"day:\s*{day}\b", source)
    assert 'tasks.trigger("marketing-create-manual-call-task"' in source


def test_lease_option_sequence_stops_for_booking_and_opt_out() -> None:
    source = _source(SEQUENCE_STEP_TASK)

    assert '"/marketing/internal/lease-option-sequence/guard"' in source
    assert "bookingStatus" in source
    assert "sequenceStatus" in source
    assert "optedOut" in source
    assert "delay:" in source


def test_manual_call_task_contract() -> None:
    source = _source(MANUAL_CALL_TASK)

    assert 'id: "marketing-create-manual-call-task"' in source
    assert '"/marketing/internal/manual-call-task"' in source
