import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";
import type { CreateCampaignBriefPayload } from "./createCampaignBrief";

export type DraftCampaignAssetsPayload = CreateCampaignBriefPayload & {
  campaignBrief?: unknown;
};

export const draftCampaignAssets = task({
  id: "marketing-draft-campaign-assets",
  run: async (payload: DraftCampaignAssetsPayload) => {
    const campaignBrief =
      payload.campaignBrief ??
      (await invokeRuntimeApi<unknown, CreateCampaignBriefPayload>(
        "/marketing/campaign-brief/create",
        payload
      ));

    const campaignAssets = await invokeRuntimeApi<unknown, DraftCampaignAssetsPayload>(
      "/marketing/campaign-assets/draft",
      {
        ...payload,
        campaignBrief
      }
    );

    return {
      campaignId: payload.campaignId,
      campaignBrief,
      campaignAssets
    };
  }
});
