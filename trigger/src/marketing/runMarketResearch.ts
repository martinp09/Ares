import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";
import {
  reportArtifactProduced,
  reportRunCompleted,
  reportRunFailed,
  reportRunStarted,
} from "../runtime/reportRunLifecycle";

export type RunMarketResearchPayload = {
  runId: string;
  commandId: string;
  businessId: string;
  environment: string;
  idempotencyKey: string;
  campaignId: string;
  market?: string;
  objective?: string;
  context?: Record<string, unknown>;
};

export const runMarketResearch = task({
  id: "marketing-run-market-research",
  run: async (payload: RunMarketResearchPayload) => {
    await reportRunStarted(payload);

    try {
      const marketResearch = await invokeRuntimeApi<unknown, RunMarketResearchPayload>(
        "/marketing/market-research/run",
        payload
      );

      await reportArtifactProduced({
        ...payload,
        artifactType: "market_research",
        payload: { marketResearch },
      });
      await reportRunCompleted(payload);

      return {
        campaignId: payload.campaignId,
        marketResearch,
      };
    } catch (error) {
      await reportRunFailed({
        ...payload,
        error_classification: "task_error",
        error_message: error instanceof Error ? error.message : String(error),
      });
      throw error;
    }
  },
});
