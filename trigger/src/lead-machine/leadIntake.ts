import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type LeadIntakePayload, type LeadIntakeResponse } from "./runtime";

export const leadIntake = task({
  id: "lead-intake",
  run: async (payload: LeadIntakePayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<LeadIntakeResponse, LeadIntakePayload>("leadIntake", payload);
    }, { artifactType: "lead_machine_intake" });
  },
});
