from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
TRIGGER_SRC = REPO_ROOT / "trigger" / "src"
LEAD_MACHINE_DIR = TRIGGER_SRC / "lead-machine"
MARKETING_DIR = TRIGGER_SRC / "marketing"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase_four_trigger_jobs_cover_the_expected_id_set() -> None:
    contracts = {
        MARKETING_DIR / "checkSubmittedLeadBooking.ts": (
            'id: "marketing-check-submitted-lead-booking"',
            "invokeRuntimeApi",
        ),
        MARKETING_DIR / "runLeaseOptionSequenceStep.ts": (
            'id: "marketing-run-lease-option-sequence-step"',
            "leadSequenceQueueKey",
        ),
        MARKETING_DIR / "createManualCallTask.ts": (
            'id: "marketing-create-manual-call-task"',
            '"/marketing/internal/manual-call-task"',
        ),
        LEAD_MACHINE_DIR / "leadIntake.ts": (
            'id: "lead-intake"',
            "invokeLeadMachineRuntimeApi",
        ),
        LEAD_MACHINE_DIR / "probateIntake.ts": (
            'id: "probate-intake"',
            "invokeLeadMachineRuntimeApi",
        ),
        LEAD_MACHINE_DIR / "instantlyEnqueueLead.ts": (
            'id: "instantly-enqueue-lead"',
            "invokeLeadMachineRuntimeApi",
        ),
        LEAD_MACHINE_DIR / "instantlyWebhookIngest.ts": (
            'id: "instantly-webhook-ingest"',
            "invokeLeadMachineRuntimeApi",
        ),
        LEAD_MACHINE_DIR / "followupStepRunner.ts": (
            'id: "followup-step-runner"',
            "invokeLeadMachineRuntimeApi",
        ),
        LEAD_MACHINE_DIR / "suppressionSync.ts": (
            'id: "suppression-sync"',
            "invokeLeadMachineRuntimeApi",
        ),
        LEAD_MACHINE_DIR / "taskReminderOrOverdue.ts": (
            'id: "task-reminder-or-overdue"',
            "invokeLeadMachineRuntimeApi",
        ),
    }

    for path, (id_snippet, helper_snippet) in contracts.items():
        source = _source(path)
        assert id_snippet in source
        assert helper_snippet in source

    trigger_source = "\n".join(_source(path) for path in TRIGGER_SRC.glob("**/*.ts"))
    ids = set(re.findall(r'id:\s*"([^"]+)"', trigger_source))
    assert {
        "marketing-check-submitted-lead-booking",
        "marketing-run-lease-option-sequence-step",
        "marketing-create-manual-call-task",
        "lead-intake",
        "probate-intake",
        "instantly-enqueue-lead",
        "instantly-webhook-ingest",
        "followup-step-runner",
        "suppression-sync",
        "task-reminder-or-overdue",
    }.issubset(ids)
    assert "create-manual-call-task" not in ids


def test_lead_machine_runtime_exports_all_todo_endpoints() -> None:
    source = _source(LEAD_MACHINE_DIR / "runtime.ts")

    for endpoint in (
        'leadIntake: "/lead-machine/intake"',
        'probateIntake: "/lead-machine/probate/intake"',
        'outboundEnqueue: "/lead-machine/outbound/enqueue"',
        'instantlyWebhookIngest: "/lead-machine/webhooks/instantly"',
        'followupStepRunner: "/lead-machine/internal/followup-step-runner"',
        'suppressionSync: "/lead-machine/internal/suppression-sync"',
        'taskReminderOrOverdue: "/lead-machine/internal/task-reminder-or-overdue"',
    ):
        assert endpoint in source


def test_lead_machine_runtime_client_centralizes_runtime_invocation() -> None:
    source = _source(LEAD_MACHINE_DIR / "runtimeClient.ts")

    assert 'invokeLeadMachineRuntimeApi' in source
    assert 'LEAD_MACHINE_ENDPOINTS[endpoint]' in source


def test_trigger_jobs_require_lifecycle_reporting_for_run_mapped_payloads() -> None:
    runtime_source = _source(TRIGGER_SRC / "runtime" / "reportRunLifecycle.ts")
    assert "runWithLifecycle" in runtime_source
    assert "runWithOptionalLifecycle" in runtime_source
    assert "Missing run lifecycle fields" in runtime_source
    assert "command_id:" in runtime_source
    assert "business_id:" in runtime_source
    assert "idempotency_key:" in runtime_source
    assert "reportRunStarted" in runtime_source
    assert "reportRunCompleted" in runtime_source
    assert "reportRunFailed" in runtime_source

    for path in (
        LEAD_MACHINE_DIR / "leadIntake.ts",
        LEAD_MACHINE_DIR / "probateIntake.ts",
        LEAD_MACHINE_DIR / "instantlyEnqueueLead.ts",
        LEAD_MACHINE_DIR / "instantlyWebhookIngest.ts",
        LEAD_MACHINE_DIR / "followupStepRunner.ts",
        LEAD_MACHINE_DIR / "suppressionSync.ts",
        LEAD_MACHINE_DIR / "taskReminderOrOverdue.ts",
    ):
        assert "runWithLifecycle" in _source(path)


def test_marketing_sequence_jobs_do_not_reuse_parent_run_context_for_child_jobs() -> None:
    check_booking_source = _source(MARKETING_DIR / "checkSubmittedLeadBooking.ts")
    sequence_source = _source(MARKETING_DIR / "runLeaseOptionSequenceStep.ts")

    assert "runWithOptionalLifecycle" in check_booking_source
    assert "runWithOptionalLifecycle" in sequence_source
    assert "runId: payload.runId" not in check_booking_source
    assert "commandId: payload.commandId" not in check_booking_source
    assert "idempotencyKey: payload.idempotencyKey" not in check_booking_source
    assert "runId: payload.runId" not in sequence_source
    assert "commandId: payload.commandId" not in sequence_source
    assert "idempotencyKey: payload.idempotencyKey" not in sequence_source


def test_lead_machine_trigger_files_are_grouped_under_the_same_namespace() -> None:
    source = _source(LEAD_MACHINE_DIR / "followupStepRunner.ts")

    assert re.search(r'task\(\{\s*id:\s*"followup-step-runner"', source, re.S)
    assert 'invokeLeadMachineRuntimeApi' in source


def test_lead_intake_trigger_job_targets_canonical_intake_endpoint() -> None:
    source = _source(LEAD_MACHINE_DIR / "leadIntake.ts")

    assert 'LeadIntakePayload' in source
    assert '"leadIntake"' in source
    assert '"probateIntake"' not in source


def test_probate_intake_trigger_job_preserves_probate_endpoint() -> None:
    source = _source(LEAD_MACHINE_DIR / "probateIntake.ts")

    assert 'ProbateIntakePayload' in source
    assert '"probateIntake"' in source
    assert 'id: "probate-intake"' in source
