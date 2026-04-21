import { task } from "@trigger.dev/sdk";

import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type FollowupStepRunnerPayload, type FollowupStepRunnerResponse } from "./runtime";

export const followupStepRunner = task({
  id: "followup-step-runner",
  run: async (payload: FollowupStepRunnerPayload) => {
    return await invokeLeadMachineRuntimeApi<FollowupStepRunnerResponse, FollowupStepRunnerPayload>(
      "followupStepRunner",
      payload
    );
  },
});
