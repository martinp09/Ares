import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";
import type { RunMarketResearchPayload } from "./runMarketResearch";

export type CreateCampaignBriefPayload = RunMarketResearchPayload & {
  marketResearch?: unknown;
};

export const createCampaignBrief = task({
  id: "marketing-create-campaign-brief",
  run: async (payload: CreateCampaignBriefPayload) => {
    const marketResearch =
      payload.marketResearch ??
      (await invokeRuntimeApi<unknown, RunMarketResearchPayload>(
        "/marketing/market-research/run",
        payload
      ));

    const campaignBrief = await invokeRuntimeApi<unknown, CreateCampaignBriefPayload>(
      "/marketing/campaign-brief/create",
      {
        ...payload,
        marketResearch
      }
    );

    return {
      campaignId: payload.campaignId,
      marketResearch,
      campaignBrief
    };
  }
});
