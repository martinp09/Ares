import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type SuppressionSyncPayload, type SuppressionSyncResponse } from "./runtime";

export const suppressionSync = task({
  id: "suppression-sync",
  run: async (payload: SuppressionSyncPayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<SuppressionSyncResponse, SuppressionSyncPayload>(
        "suppressionSync",
        payload
      );
    });
  },
});
