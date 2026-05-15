import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type NightlySourcePullPayload, type NightlySourcePullResponse } from "./runtime";

export const nightlySourcePull = task({
  id: "nightly-source-pull",
  run: async (payload: NightlySourcePullPayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<NightlySourcePullResponse, NightlySourcePullPayload>(
        "nightlySourcePull",
        payload
      );
    });
  },
});
