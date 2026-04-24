import { task } from "@trigger.dev/sdk";

import { runWithOptionalLifecycle } from "../runtime/reportRunLifecycle";
import { invokeRuntimeApi } from "../shared/runtimeApi";

export type MarketingCreateManualCallTaskPayload = {
  leadId: string;
  businessId: string;
  environment: string;
  runId?: string;
  commandId?: string;
  idempotencyKey?: string;
  triggerRunId?: string;
  sequenceDay: number;
  reason: string;
};

type ManualCallTaskResponse = {
  taskId: string;
  status: "open" | "scheduled";
};

export const createManualCallTask = task({
  id: "marketing-create-manual-call-task",
  run: async (payload: MarketingCreateManualCallTaskPayload) => {
    return await runWithOptionalLifecycle(payload, async () => {
      const result = await invokeRuntimeApi<
        ManualCallTaskResponse,
        MarketingCreateManualCallTaskPayload
      >("/marketing/internal/manual-call-task", payload);

      return {
        leadId: payload.leadId,
        taskId: result.taskId,
        status: result.status,
      };
    });
  },
});
