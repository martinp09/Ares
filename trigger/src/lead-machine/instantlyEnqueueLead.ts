import { task } from "@trigger.dev/sdk";

import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type OutboundEnqueuePayload, type OutboundEnqueueResponse } from "./runtime";

export const instantlyEnqueueLead = task({
  id: "instantly-enqueue-lead",
  run: async (payload: OutboundEnqueuePayload) => {
    return await invokeLeadMachineRuntimeApi<OutboundEnqueueResponse, OutboundEnqueuePayload>(
      "outboundEnqueue",
      payload
    );
  },
});
