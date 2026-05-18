import { schedules } from "@trigger.dev/sdk";

import { disabledScheduleResponse, triggerSchedulesEnabled, type TriggerScheduleSkipResponse } from "../shared/scheduleGate";
import { chiefOfStaffScheduledSlackEnabled } from "./chiefOfStaffCheckIn";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type ChiefOfStaffCheckInPayload, type ChiefOfStaffCheckInResponse } from "./runtime";

export const timezone = "America/Chicago";

type ScheduleContext = {
  timestamp?: Date | string;
  scheduledTime?: Date | string;
  scheduleId?: string;
  id?: string;
  timezone?: string;
  type?: string;
};

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing ${name} for Chief of Staff employee check-in schedule.`);
  }
  return value;
}

function scheduledDate(schedule: ScheduleContext): Date {
  const value = schedule.timestamp ?? schedule.scheduledTime ?? new Date();
  return value instanceof Date ? value : new Date(value);
}

function ctDateKey(date: Date): string {
  return date.toLocaleDateString("en-CA", { timeZone: timezone });
}

export function buildChiefOfStaffScheduledPayload(schedule: ScheduleContext, slot = "0815-ct"): ChiefOfStaffCheckInPayload {
  const scheduledAt = scheduledDate(schedule);
  const scheduleTimezone = schedule.timezone ?? timezone;
  const scheduleId = schedule.scheduleId ?? schedule.id ?? slot;

  return {
    business_id: requiredEnv("LEAD_MACHINE_BUSINESS_ID"),
    environment: requiredEnv("LEAD_MACHINE_ENVIRONMENT"),
    limit: Number(process.env.ARES_CHIEF_OF_STAFF_SCHEDULED_LIMIT ?? "10"),
    write_artifacts: true,
    send_slack: chiefOfStaffScheduledSlackEnabled(),
    no_send: true,
    provider_sends_enabled: false,
    live_source_calls: false,
    live_provider_writes: false,
    outreach_allowed: false,
    idempotency_key: `chief-of-staff:${slot}:${ctDateKey(scheduledAt)}`,
    metadata: {
      source: "trigger-schedule",
      employee: "ares_chief_of_staff",
      check_in_type: "scheduled_employee_check_in",
      no_send: true,
      provider_sends_enabled: false,
      live_source_calls: false,
      live_provider_writes: false,
      outreach_allowed: false,
      scheduled_at: scheduledAt.toISOString(),
      slot,
      schedule_id: scheduleId,
      schedule_timezone: scheduleTimezone,
      schedule_type: schedule.type ?? "cron",
    },
  };
}

async function runScheduledChiefOfStaffCheckIn(
  schedule: ScheduleContext,
  slot = "0815-ct"
): Promise<ChiefOfStaffCheckInResponse | TriggerScheduleSkipResponse> {
  if (!triggerSchedulesEnabled()) {
    return disabledScheduleResponse(`chief-of-staff-check-in:${slot}`);
  }

  return await invokeLeadMachineRuntimeApi<ChiefOfStaffCheckInResponse, ChiefOfStaffCheckInPayload>(
    "chiefOfStaffCheckIn",
    buildChiefOfStaffScheduledPayload(schedule, slot)
  );
}

export const chiefOfStaffCheckIn0815Ct = schedules.task({
  id: "chief-of-staff-check-in-0815-ct",
  cron: { pattern: "15 8 * * *", timezone },
  run: async (schedule: ScheduleContext) => runScheduledChiefOfStaffCheckIn(schedule, "0815-ct"),
});
