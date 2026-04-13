import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";

export type RunMarketResearchPayload = {
  campaignId: string;
  market?: string;
  objective?: string;
  context?: Record<string, unknown>;
};

export const runMarketResearch = task({
  id: "marketing-run-market-research",
  run: async (payload: RunMarketResearchPayload) => {
    const marketResearch = await invokeRuntimeApi<unknown, RunMarketResearchPayload>(
      "/marketing/market-research/run",
      payload
    );

    return {
      campaignId: payload.campaignId,
      marketResearch
    };
  }
});
