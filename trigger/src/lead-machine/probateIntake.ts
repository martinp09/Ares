import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type ProbateIntakePayload, type ProbateIntakeResponse } from "./runtime";

export const probateIntake = task({
  id: "probate-intake",
  run: async (payload: ProbateIntakePayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<ProbateIntakeResponse, ProbateIntakePayload>("probateIntake", payload);
    }, { artifactType: "lead_machine_probate_intake" });
  },
});
