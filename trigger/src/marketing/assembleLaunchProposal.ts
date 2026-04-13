import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";
import type { DraftCampaignAssetsPayload } from "./draftCampaignAssets";

export type AssembleLaunchProposalPayload = DraftCampaignAssetsPayload & {
  campaignAssets?: unknown;
};

export const assembleLaunchProposal = task({
  id: "marketing-assemble-launch-proposal",
  run: async (payload: AssembleLaunchProposalPayload) => {
    const campaignAssets =
      payload.campaignAssets ??
      (await invokeRuntimeApi<unknown, DraftCampaignAssetsPayload>(
        "/marketing/campaign-assets/draft",
        payload
      ));

    const launchProposal = await invokeRuntimeApi<unknown, AssembleLaunchProposalPayload>(
      "/marketing/launch-proposal/assemble",
      {
        ...payload,
        campaignAssets
      }
    );

    return {
      campaignId: payload.campaignId,
      campaignAssets,
      launchProposal
    };
  }
});
