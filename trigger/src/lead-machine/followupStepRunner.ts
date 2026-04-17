import { task } from "@trigger.dev/sdk";

import { invokeRuntimeApi } from "../shared/runtimeApi";
import { LEAD_MACHINE_ENDPOINTS, type FollowupStepRunnerPayload, type FollowupStepRunnerResponse } from "./runtime";

export const followupStepRunner = task({
  id: "followup-step-runner",
  run: async (payload: FollowupStepRunnerPayload) => {
    return await invokeRuntimeApi<FollowupStepRunnerResponse, FollowupStepRunnerPayload>(
      LEAD_MACHINE_ENDPOINTS.followupStepRunner,
      payload
    );
  },
});
