import { schedules } from "@trigger.dev/sdk";

import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type NightlySourcePullPayload, type NightlySourcePullResponse } from "./runtime";

export const timezone = "America/Chicago";

type ScheduleContext = {
  timestamp?: Date | string;
  scheduledTime?: Date | string;
  scheduleId?: string;
  id?: string;
  timezone?: string;
  type?: string;
};

type ProbateAutopilotCadence = "daily" | "weekly";

function requiredEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing ${name} for Harris/Montgomery probate autopilot schedule.`);
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

function envFlag(name: string): boolean {
  return ["1", "true", "yes", "on"].includes((process.env[name] ?? "").toLowerCase());
}

export function buildProbateAutopilotScheduledPayload(
  schedule: ScheduleContext,
  slot: string,
  cadence: ProbateAutopilotCadence
): NightlySourcePullPayload {
  const scheduledAt = scheduledDate(schedule);
  const scheduleTimezone = schedule.timezone ?? timezone;
  const scheduleId = schedule.scheduleId ?? schedule.id ?? slot;
  const liveSourceCalls = envFlag("LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED");
  const sourceProviderBridge = liveSourceCalls
    ? {
        mode: "live_source_adapters",
        expected_counties: ["harris", "montgomery"],
      }
    : undefined;
  const sourceProviderApproval = liveSourceCalls
    ? {
        approved: true,
        approved_by: "trigger-schedule-env-gate",
        scope: "harris_montgomery_probate_public_sources",
        no_send: true,
        provider_sends_enabled: false,
      }
    : undefined;

  return {
    business_id: requiredEnv("LEAD_MACHINE_BUSINESS_ID"),
    environment: requiredEnv("LEAD_MACHINE_ENVIRONMENT"),
    live_source_calls: liveSourceCalls,
    idempotency_key: `harris-montgomery-probate:${cadence}:${slot}:${ctDateKey(scheduledAt)}`,
    metadata: {
      source: "trigger-schedule",
      autopilot: "harris_montgomery_probate",
      county_scope: ["harris", "montgomery"],
      no_send: true,
      provider_sends_enabled: false,
      run_kind: slotToRunKind(slot),
      slot,
      cadence,
      scheduled_at: scheduledAt.toISOString(),
      window_end: scheduledAt.toISOString(),
      schedule_id: scheduleId,
      schedule_timezone: scheduleTimezone,
      schedule_type: schedule.type ?? "cron",
      ...(sourceProviderBridge ? { source_provider_bridge: sourceProviderBridge } : {}),
      ...(sourceProviderApproval ? { source_provider_approval: sourceProviderApproval } : {}),
    },
  };
}

async function runProbateAutopilotNoSendSourcePull(
  schedule: ScheduleContext,
  slot: string,
  cadence: ProbateAutopilotCadence
): Promise<NightlySourcePullResponse> {
  return await invokeLeadMachineRuntimeApi<NightlySourcePullResponse, NightlySourcePullPayload>(
    "nightlySourcePull",
    buildProbateAutopilotScheduledPayload(schedule, slot, cadence)
  );
}

function slotToRunKind(slot: string): string {
  switch (slot) {
    case "0710-ct":
      return "morning_catchup";
    case "1240-ct":
      return "midday";
    case "1740-ct":
      return "end_of_day";
    case "0220-ct":
      return "daily_reconciliation";
    case "sunday-0315-ct":
      return "weekly_reconciliation";
    default:
      return "manual";
  }
}

export const harrisMontgomeryProbate0710Ct = schedules.task({
  id: "harris-montgomery-probate-0710-ct",
  cron: { pattern: "10 7 * * *", timezone },
  run: async (schedule: ScheduleContext) => runProbateAutopilotNoSendSourcePull(schedule, "0710-ct", "daily"),
});

export const harrisMontgomeryProbate1240Ct = schedules.task({
  id: "harris-montgomery-probate-1240-ct",
  cron: { pattern: "40 12 * * *", timezone },
  run: async (schedule: ScheduleContext) => runProbateAutopilotNoSendSourcePull(schedule, "1240-ct", "daily"),
});

export const harrisMontgomeryProbate1740Ct = schedules.task({
  id: "harris-montgomery-probate-1740-ct",
  cron: { pattern: "40 17 * * *", timezone },
  run: async (schedule: ScheduleContext) => runProbateAutopilotNoSendSourcePull(schedule, "1740-ct", "daily"),
});

export const harrisMontgomeryProbate0220Ct = schedules.task({
  id: "harris-montgomery-probate-0220-ct",
  cron: { pattern: "20 2 * * *", timezone },
  run: async (schedule: ScheduleContext) => runProbateAutopilotNoSendSourcePull(schedule, "0220-ct", "daily"),
});

export const harrisMontgomeryProbateWeeklySunday0315Ct = schedules.task({
  id: "harris-montgomery-probate-weekly-sunday-0315-ct",
  cron: { pattern: "15 3 * * 0", timezone },
  run: async (schedule: ScheduleContext) => runProbateAutopilotNoSendSourcePull(schedule, "sunday-0315-ct", "weekly"),
});
