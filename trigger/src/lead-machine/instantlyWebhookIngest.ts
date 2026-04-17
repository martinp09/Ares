import { task } from "@trigger.dev/sdk";

import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type InstantlyWebhookPayload, type InstantlyWebhookResponse } from "./runtime";

export const instantlyWebhookIngest = task({
  id: "instantly-webhook-ingest",
  run: async (payload: InstantlyWebhookPayload) => {
    return await invokeLeadMachineRuntimeApi<InstantlyWebhookResponse, InstantlyWebhookPayload>(
      "instantlyWebhookIngest",
      payload
    );
  },
});
