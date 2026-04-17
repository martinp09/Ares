import { task } from "@trigger.dev/sdk";

import { invokeRuntimeApi } from "../shared/runtimeApi";
import { LEAD_MACHINE_ENDPOINTS, type SuppressionSyncPayload, type SuppressionSyncResponse } from "./runtime";

export const suppressionSync = task({
  id: "suppression-sync",
  run: async (payload: SuppressionSyncPayload) => {
    return await invokeRuntimeApi<SuppressionSyncResponse, SuppressionSyncPayload>(
      LEAD_MACHINE_ENDPOINTS.suppressionSync,
      payload
    );
  },
});
