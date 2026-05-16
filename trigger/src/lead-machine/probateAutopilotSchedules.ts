import { schedules } from "@trigger.dev/sdk";

import { disabledScheduleResponse, triggerSchedulesEnabled, type TriggerScheduleSkipResponse } from "../shared/scheduleGate";
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

type ProbateAutopilotCadence = "daily";

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

function shiftDateKey(dateKey: string, days: number): string {
  const date = new Date(`${dateKey}T12:00:00.000Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function scheduledSourceWindow(slot: string, scheduledAt: Date): { window_start: string; window_end: string } {
  const end = ctDateKey(scheduledAt);
  switch (slot) {
    case "0710-ct":
      return { window_start: shiftDateKey(end, -1), window_end: end };
    default:
      return { window_start: end, window_end: end };
  }
}

function envFlag(name: string, defaultValue = false): boolean {
  const raw = process.env[name];
  if (raw === undefined) {
    return defaultValue;
  }
  return ["1", "true", "yes", "on"].includes(raw.toLowerCase());
}

export function buildProbateAutopilotScheduledPayload(
  schedule: ScheduleContext,
  slot: string,
  cadence: ProbateAutopilotCadence
): NightlySourcePullPayload {
  const scheduledAt = scheduledDate(schedule);
  const scheduleTimezone = schedule.timezone ?? timezone;
  const scheduleId = schedule.scheduleId ?? schedule.id ?? slot;
  const sourceWindow = scheduledSourceWindow(slot, scheduledAt);
  const liveSourceCalls = envFlag("LEAD_MACHINE_SCHEDULED_LIVE_SOURCE_CALLS_ENABLED", true);
  const liveEnrichmentCalls = envFlag("LEAD_MACHINE_SCHEDULED_LIVE_ENRICHMENT_CALLS_ENABLED", true);
  const liveCaseDetailCalls = envFlag("LEAD_MACHINE_SCHEDULED_LIVE_CASE_DETAIL_CALLS_ENABLED", true);
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
  const caseDetailApproval = liveCaseDetailCalls
    ? {
        approved: true,
        approved_by: "trigger-schedule-env-gate",
        scope: "harris_montgomery_probate_public_case_detail_pages",
        no_send: true,
        provider_sends_enabled: false,
      }
    : undefined;
  const enrichmentApproval = liveEnrichmentCalls
    ? {
        approved: true,
        approved_by: "trigger-schedule-env-gate",
        scope: "harris_montgomery_probate_public_cad_tax_land_records",
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
      source_run_scope: "autonomous",
      run_kind: slotToRunKind(slot),
      slot,
      cadence,
      scheduled_at: scheduledAt.toISOString(),
      ...sourceWindow,
      schedule_id: scheduleId,
      schedule_timezone: scheduleTimezone,
      schedule_type: schedule.type ?? "cron",
      ...(sourceProviderBridge ? { source_provider_bridge: sourceProviderBridge } : {}),
      ...(sourceProviderApproval ? { source_provider_approval: sourceProviderApproval } : {}),
      ...(caseDetailApproval
        ? {
            case_detail_enrichment: {
              live_case_detail_calls: true,
              case_detail_approval: caseDetailApproval,
            },
          }
        : {}),
      ...(enrichmentApproval
        ? {
            property_tax_title_enrichment: {
              live_cad_calls: true,
              live_tax_calls: true,
              live_land_record_calls: true,
              enrichment_approval: enrichmentApproval,
            },
          }
        : {}),
    },
  };
}

async function runProbateAutopilotNoSendSourcePull(
  schedule: ScheduleContext,
  slot: string,
  cadence: ProbateAutopilotCadence
): Promise<NightlySourcePullResponse | TriggerScheduleSkipResponse> {
  if (!triggerSchedulesEnabled()) {
    return disabledScheduleResponse(`harris-montgomery-probate:${slot}`);
  }

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
