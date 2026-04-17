import { task } from "@trigger.dev/sdk";

import { invokeRuntimeApi } from "../shared/runtimeApi";
import { LEAD_MACHINE_ENDPOINTS, type InstantlyWebhookPayload, type InstantlyWebhookResponse } from "./runtime";

export const instantlyWebhookIngest = task({
  id: "instantly-webhook-ingest",
  run: async (payload: InstantlyWebhookPayload) => {
    return await invokeRuntimeApi<InstantlyWebhookResponse, InstantlyWebhookPayload>(
      LEAD_MACHINE_ENDPOINTS.instantlyWebhookIngest,
      payload
    );
  },
});
