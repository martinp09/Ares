import { task } from "@trigger.dev/sdk";

import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type ProbateIntakePayload, type ProbateIntakeResponse } from "./runtime";

export const leadIntake = task({
  id: "lead-intake",
  run: async (payload: ProbateIntakePayload) => {
    return await invokeLeadMachineRuntimeApi<ProbateIntakeResponse, ProbateIntakePayload>("probateIntake", payload);
  },
});
