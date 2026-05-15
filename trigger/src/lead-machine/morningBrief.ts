import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type MorningBriefPayload, type MorningBriefResponse } from "./runtime";

export const morningBrief = task({
  id: "morning-brief",
  run: async (payload: MorningBriefPayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<MorningBriefResponse, MorningBriefPayload>("morningBrief", payload);
    }, { artifactType: "lead_machine_morning_brief" });
  },
});
