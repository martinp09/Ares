import { task } from "@trigger.dev/sdk";

import { runWithLifecycle } from "../runtime/reportRunLifecycle";
import { invokeLeadMachineRuntimeApi } from "./runtimeClient";
import {
  type ProbatePropertyTaxTitleEnrichmentPayload,
  type ProbatePropertyTaxTitleEnrichmentResponse,
} from "./runtime";

export const probatePropertyTaxTitleEnrichment = task({
  id: "probate-property-tax-title-enrichment",
  run: async (payload: ProbatePropertyTaxTitleEnrichmentPayload) => {
    return await runWithLifecycle(payload, async () => {
      return await invokeLeadMachineRuntimeApi<
        ProbatePropertyTaxTitleEnrichmentResponse,
        ProbatePropertyTaxTitleEnrichmentPayload
      >("probatePropertyTaxTitleEnrichment", payload);
    });
  },
});
