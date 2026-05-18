import { task } from "@trigger.dev/sdk";
import { runWithOptionalLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type ChiefOfStaffCheckInPayload, type ChiefOfStaffCheckInResponse } from "./runtime";

function envFlag(name: string, defaultValue = false): boolean {
  const raw = process.env[name];
  if (raw === undefined) {
    return defaultValue;
  }
  return ["1", "true", "yes", "on"].includes(raw.toLowerCase());
}

export function chiefOfStaffScheduledSlackEnabled(): boolean {
  return envFlag("ARES_CHIEF_OF_STAFF_SCHEDULED_SLACK_ENABLED", false);
}

export function chiefOfStaffSafePayload(payload: ChiefOfStaffCheckInPayload): ChiefOfStaffCheckInPayload {
  return {
    ...payload,
    no_send: true,
    provider_sends_enabled: false,
    live_source_calls: false,
    live_provider_writes: false,
    outreach_allowed: false,
    send_slack: payload.send_slack === true && chiefOfStaffScheduledSlackEnabled(),
    metadata: {
      ...(payload.metadata ?? {}),
      no_send: true,
      provider_sends_enabled: false,
      live_source_calls: false,
      live_provider_writes: false,
      outreach_allowed: false,
    },
  };
}

export const chiefOfStaffCheckIn = task({
  id: "chief-of-staff-check-in",
  run: async (payload: ChiefOfStaffCheckInPayload) => {
    const safePayload = chiefOfStaffSafePayload(payload);
    return await runWithOptionalLifecycle(safePayload, async () => {
      return await invokeLeadMachineRuntimeApi<ChiefOfStaffCheckInResponse, ChiefOfStaffCheckInPayload>(
        "chiefOfStaffCheckIn",
        safePayload
      );
    });
  },
});
