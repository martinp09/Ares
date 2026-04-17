import { task } from "@trigger.dev/sdk";

import { invokeRuntimeApi } from "../shared/runtimeApi";
import { LEAD_MACHINE_ENDPOINTS, type ProbateIntakePayload, type ProbateIntakeResponse } from "./runtime";

export const leadIntake = task({
  id: "lead-intake",
  run: async (payload: ProbateIntakePayload) => {
    return await invokeRuntimeApi<ProbateIntakeResponse, ProbateIntakePayload>(
      LEAD_MACHINE_ENDPOINTS.probateIntake,
      payload
    );
  },
});
