import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import { type HarrisDailyImportPayload, type HarrisDailyImportResponse } from "./runtime";

export const harrisDailyImport = task({
  id: "harris-daily-import",
  run: async (payload: HarrisDailyImportPayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<HarrisDailyImportResponse, HarrisDailyImportPayload>(
        "harrisDailyImport",
        payload
      );
    }, { artifactType: "lead_machine_harris_daily_import" });
  },
});
