import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";
import {
  reportArtifactProduced,
  reportRunCompleted,
  reportRunFailed,
  reportRunStarted,
} from "../runtime/reportRunLifecycle";
import type { CreateCampaignBriefPayload } from "./createCampaignBrief";

export type DraftCampaignAssetsPayload = CreateCampaignBriefPayload & {
  campaignId: string;
  campaignBrief?: unknown;
};

export const draftCampaignAssets = task({
  id: "marketing-draft-campaign-assets",
  run: async (payload: DraftCampaignAssetsPayload) => {
    await reportRunStarted(payload);

    try {
      const campaignBrief =
        payload.campaignBrief ??
        (await invokeRuntimeApi<unknown, DraftCampaignAssetsPayload>(
          "/marketing/campaign-brief/create",
          payload
        ));

      const campaignAssets = await invokeRuntimeApi<unknown, DraftCampaignAssetsPayload>(
        "/marketing/campaign-assets/draft",
        {
          ...payload,
          campaignBrief,
        }
      );

      await reportArtifactProduced({
        ...payload,
        artifactType: "campaign_assets",
        payload: { campaignAssets },
      });
      await reportRunCompleted(payload);

      return {
        campaignId: payload.campaignId,
        campaignBrief,
        campaignAssets,
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
