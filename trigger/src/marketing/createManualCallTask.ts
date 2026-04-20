import { task } from "@trigger.dev/sdk";

import { invokeRuntimeApi } from "../shared/runtimeApi";

export type MarketingCreateManualCallTaskPayload = {
  leadId: string;
  businessId: string;
  environment: string;
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
    const result = await invokeRuntimeApi<
      ManualCallTaskResponse,
      MarketingCreateManualCallTaskPayload
    >("/marketing/internal/manual-call-task", payload);

    return {
      leadId: payload.leadId,
      taskId: result.taskId,
      status: result.status,
    };
  },
});
