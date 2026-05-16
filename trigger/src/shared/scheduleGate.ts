export type TriggerScheduleSkipResponse = {
  skipped: true;
  reason: "trigger_cloud_runtime_disabled";
  schedule_gate: "disabled";
  env_var: "ARES_TRIGGER_SCHEDULES_ENABLED";
  scope: string;
};

function envFlag(name: string, defaultValue = false): boolean {
  const raw = process.env[name];
  if (raw === undefined) {
    return defaultValue;
  }
  return ["1", "true", "yes", "on"].includes(raw.toLowerCase());
}

export function triggerSchedulesEnabled(): boolean {
  return envFlag("ARES_TRIGGER_SCHEDULES_ENABLED", false);
}

export function disabledScheduleResponse(scope: string): TriggerScheduleSkipResponse {
  return {
    skipped: true,
    reason: "trigger_cloud_runtime_disabled",
    schedule_gate: "disabled",
    env_var: "ARES_TRIGGER_SCHEDULES_ENABLED",
    scope,
  };
}
