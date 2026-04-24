import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type InstantlyWebhookPayload, type InstantlyWebhookResponse } from "./runtime";

export const instantlyWebhookIngest = task({
  id: "instantly-webhook-ingest",
  run: async (payload: InstantlyWebhookPayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<InstantlyWebhookResponse, InstantlyWebhookPayload>(
        "instantlyWebhookIngest",
        payload
      );
    });
  },
});
