import { task } from "@trigger.dev/sdk";

import { invokeRuntimeApi } from "../shared/runtimeApi";
import { LEAD_MACHINE_ENDPOINTS, type OutboundEnqueuePayload, type OutboundEnqueueResponse } from "./runtime";

export const instantlyEnqueueLead = task({
  id: "instantly-enqueue-lead",
  run: async (payload: OutboundEnqueuePayload) => {
    return await invokeRuntimeApi<OutboundEnqueueResponse, OutboundEnqueuePayload>(
      LEAD_MACHINE_ENDPOINTS.outboundEnqueue,
      payload
    );
  },
});
