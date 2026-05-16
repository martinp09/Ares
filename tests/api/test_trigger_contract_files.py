from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_API = REPO_ROOT / "trigger" / "src" / "shared" / "runtimeApi.ts"
LEAD_MACHINE_RUNTIME = REPO_ROOT / "trigger" / "src" / "lead-machine" / "runtime.ts"
HARRIS_DAILY_IMPORT_TASK = REPO_ROOT / "trigger" / "src" / "lead-machine" / "harrisDailyImport.ts"
APPOINTMENT_REMINDER_TASK = REPO_ROOT / "trigger" / "src" / "marketing" / "sendAppointmentReminder.ts"
SMS_REPLY_AGENT_PROCESSOR_TASK = REPO_ROOT / "trigger" / "src" / "marketing" / "smsReplyAgentProcessor.ts"
TRIGGER_PACKAGE = REPO_ROOT / "trigger" / "package.json"
PROBATE_AUTOPILOT_SCHEDULES = REPO_ROOT / "trigger" / "src" / "lead-machine" / "probateAutopilotSchedules.ts"


def test_trigger_runtime_api_uses_explicit_ares_env_contract() -> None:
    source = RUNTIME_API.read_text(encoding="utf-8")

    assert "HERMES_RUNTIME_API_BASE_URL" in source
    assert "RUNTIME_API_BASE_URL" in source
    assert "HERMES_RUNTIME_API_KEY" in source
    assert "RUNTIME_API_KEY" in source
    assert "Missing HERMES_RUNTIME_API_KEY (or RUNTIME_API_KEY)" in source
    assert 'headers.authorization = `Bearer ${apiKey}`' in source


def test_trigger_package_exposes_typecheck_contract() -> None:
    source = TRIGGER_PACKAGE.read_text(encoding="utf-8")

    assert '"typecheck": "tsc --noEmit -p tsconfig.json"' in source


def test_trigger_exposes_harris_daily_import_contract() -> None:
    runtime_source = LEAD_MACHINE_RUNTIME.read_text(encoding="utf-8")
    task_source = HARRIS_DAILY_IMPORT_TASK.read_text(encoding="utf-8")

    assert 'harrisDailyImport: "/lead-machine/harris/daily-import"' in runtime_source
    assert "export type HarrisDailyImportPayload" in runtime_source
    assert "export type HarrisDailyImportResponse" in runtime_source
    assert 'id: "harris-daily-import"' in task_source
    assert '"harrisDailyImport"' in task_source
    assert "lead_machine_harris_daily_import" in task_source


def test_trigger_exposes_appointment_reminder_contract() -> None:
    task_source = APPOINTMENT_REMINDER_TASK.read_text(encoding="utf-8")

    assert "export type SendAppointmentReminderPayload" in task_source
    assert 'id: "marketing-send-appointment-reminder"' in task_source
    assert '"/marketing/internal/appointment-reminder"' in task_source
    assert "smsProviderMessageId" in task_source
    assert "emailProviderMessageId" in task_source


def test_trigger_exposes_sms_reply_agent_processor_contract() -> None:
    task_source = SMS_REPLY_AGENT_PROCESSOR_TASK.read_text(encoding="utf-8")

    assert "schedules.task" in task_source
    assert 'id: "sms-agent-process-pending"' in task_source
    assert '"*/1 * * * *"' in task_source
    assert '"America/Chicago"' in task_source
    assert "SMS_AGENT_PROCESS_BATCH_SIZE" in task_source
    assert "triggerSchedulesEnabled" in task_source
    assert "disabledScheduleResponse" in task_source
    assert '"/sms-agent/internal/process-pending"' in task_source
    assert "processed_count" in task_source
    assert "sent_count" in task_source
    assert "blocked_count" in task_source
    assert "failed_count" in task_source


def test_probate_autopilot_schedules_are_no_send_and_ct_cadenced() -> None:
    source = PROBATE_AUTOPILOT_SCHEDULES.read_text(encoding="utf-8")

    assert 'timezone = "America/Chicago"' in source
    assert "10 7 * * *" in source
    assert "40 12 * * *" in source
    assert "40 17 * * *" in source
    assert "20 2 * * *" in source
    assert "15 3 * * 0" in source
    assert "harris_montgomery_probate" in source
    assert 'envFlag("LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED", true)' in source
    assert 'envFlag("LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED", true)' in source
    assert 'envFlag("LEAD_MACHINE_SCHEDULED_LIVE_CASE_DETAIL_CALLS_ENABLED", true)' in source
    assert "live_source_calls: liveSourceCalls" in source
    assert "source_provider_approval" in source
    assert "case_detail_enrichment" in source
    assert "live_case_detail_calls: true" in source
    assert "live_cad_calls: true" in source
    assert "live_tax_calls: true" in source
    assert "live_land_record_calls: true" in source
    assert "no_send: true" in source
    assert "provider_sends_enabled: false" in source
    assert "scheduledSourceWindow(slot, scheduledAt)" in source
    assert "triggerSchedulesEnabled" in source
    assert "disabledScheduleResponse" in source
    assert 'case "0710-ct":' in source
    assert "shiftDateKey(end, -1)" in source
    assert "shiftDateKey(end, -7)" in source
    assert "shiftDateKey(end, -30)" in source
    assert "...sourceWindow" in source
    assert "LEAD_MACHINE_BUSINESS_ID" in source
    assert "LEAD_MACHINE_ENVIRONMENT" in source
