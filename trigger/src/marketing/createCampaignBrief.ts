import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";
import {
  reportArtifactProduced,
  reportRunCompleted,
  reportRunFailed,
  reportRunStarted,
} from "../runtime/reportRunLifecycle";
import type { RunMarketResearchPayload } from "./runMarketResearch";

export type CreateCampaignBriefPayload = RunMarketResearchPayload & {
  campaignId: string;
  marketResearch?: unknown;
};

export const createCampaignBrief = task({
  id: "marketing-create-campaign-brief",
  run: async (payload: CreateCampaignBriefPayload) => {
    await reportRunStarted(payload);

    try {
      const marketResearch =
        payload.marketResearch ??
        (await invokeRuntimeApi<unknown, CreateCampaignBriefPayload>(
          "/marketing/market-research/run",
          payload
        ));

      const campaignBrief = await invokeRuntimeApi<unknown, CreateCampaignBriefPayload>(
        "/marketing/campaign-brief/create",
        {
          ...payload,
          marketResearch,
        }
      );

      await reportArtifactProduced({
        ...payload,
        artifactType: "campaign_brief",
        payload: { campaignBrief },
      });
      await reportRunCompleted(payload);

      return {
        campaignId: payload.campaignId,
        marketResearch,
        campaignBrief,
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
