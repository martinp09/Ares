import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type OutboundEnqueuePayload, type OutboundEnqueueResponse } from "./runtime";

export const instantlyEnqueueLead = task({
  id: "instantly-enqueue-lead",
  run: async (payload: OutboundEnqueuePayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<OutboundEnqueueResponse, OutboundEnqueuePayload>(
        "outboundEnqueue",
        payload
      );
    }, { artifactType: "lead_machine_outbound_enqueue" });
  },
});
