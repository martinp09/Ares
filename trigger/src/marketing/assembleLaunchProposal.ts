import { task } from "@trigger.dev/sdk";
import { invokeRuntimeApi } from "../shared/runtimeApi";
import {
  reportArtifactProduced,
  reportRunCompleted,
  reportRunFailed,
  reportRunStarted,
} from "../runtime/reportRunLifecycle";
import type { DraftCampaignAssetsPayload } from "./draftCampaignAssets";

export type AssembleLaunchProposalPayload = DraftCampaignAssetsPayload & {
  campaignId: string;
  campaignAssets?: unknown;
};

export const assembleLaunchProposal = task({
  id: "marketing-assemble-launch-proposal",
  run: async (payload: AssembleLaunchProposalPayload) => {
    await reportRunStarted(payload);

    try {
      const campaignAssets =
        payload.campaignAssets ??
        (await invokeRuntimeApi<unknown, AssembleLaunchProposalPayload>(
          "/marketing/campaign-assets/draft",
          payload
        ));

      const launchProposal = await invokeRuntimeApi<unknown, AssembleLaunchProposalPayload>(
        "/marketing/launch-proposal/assemble",
        {
          ...payload,
          campaignAssets,
        }
      );

      await reportArtifactProduced({
        ...payload,
        artifactType: "launch_proposal",
        payload: { launchProposal },
      });
      await reportRunCompleted(payload);

      return {
        campaignId: payload.campaignId,
        campaignAssets,
        launchProposal,
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
