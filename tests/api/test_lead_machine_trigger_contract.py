from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
LEAD_MACHINE_DIR = REPO_ROOT / "trigger" / "src" / "lead-machine"


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_lead_machine_trigger_jobs_cover_the_todo_set() -> None:
    contracts = {
        "leadIntake.ts": (
            'id: "lead-intake"',
            "invokeLeadMachineRuntimeApi",
        ),
        "instantlyEnqueueLead.ts": (
            'id: "instantly-enqueue-lead"',
            "invokeLeadMachineRuntimeApi",
        ),
        "instantlyWebhookIngest.ts": (
            'id: "instantly-webhook-ingest"',
            "invokeLeadMachineRuntimeApi",
        ),
        "createManualCallTask.ts": (
            'id: "create-manual-call-task"',
            '"/marketing/internal/manual-call-task"',
        ),
        "followupStepRunner.ts": (
            'id: "followup-step-runner"',
            "invokeLeadMachineRuntimeApi",
        ),
        "suppressionSync.ts": (
            'id: "suppression-sync"',
            "invokeLeadMachineRuntimeApi",
        ),
        "taskReminderOrOverdue.ts": (
            'id: "task-reminder-or-overdue"',
            "invokeLeadMachineRuntimeApi",
        ),
    }

    for filename, (id_snippet, helper_snippet) in contracts.items():
        source = _source(LEAD_MACHINE_DIR / filename)
        assert id_snippet in source
        assert helper_snippet in source


def test_lead_machine_runtime_exports_all_todo_endpoints() -> None:
    source = _source(LEAD_MACHINE_DIR / "runtime.ts")

    for endpoint in (
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


def test_lead_machine_trigger_files_are_grouped_under_the_same_namespace() -> None:
    source = _source(LEAD_MACHINE_DIR / "followupStepRunner.ts")

    assert re.search(r'task\(\{\s*id:\s*"followup-step-runner"', source, re.S)
    assert 'invokeLeadMachineRuntimeApi' in source
