import { schedules } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";

export type SmsReplyAgentProcessResponse = {
  processed_count: number;
  sent_count: number;
  blocked_count: number;
  failed_count: number;
};

export const smsReplyAgentProcessor = schedules.task({
  id: "sms-agent-process-pending",
  cron: {
    pattern: "*/1 * * * *",
    timezone: "America/Chicago",
  },
  run: async () => {
    const limit = Number(process.env.SMS_AGENT_PROCESS_BATCH_SIZE ?? "25");

    return await invokeRuntimeApi<SmsReplyAgentProcessResponse, { limit: number }>(
      "/sms-agent/internal/process-pending",
      { limit }
    );
  },
});
