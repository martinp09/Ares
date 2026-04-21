import { describe, expect, it, vi } from "vitest";

import { createMissionControlApi } from "./api";
import { missionControlFixtures, missionControlTasksFixture } from "./fixtures";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("Mission Control API client", () => {
  it("maps additive pipeline summaries from the dashboard payload", async () => {
    const fetchMock = vi.fn(async () =>
      jsonResponse({
        approval_count: 1,
        active_run_count: 2,
        failed_run_count: 0,
        active_agent_count: 3,
        unread_conversation_count: 4,
        busy_channel_count: 2,
        recent_completed_count: 6,
        pending_lead_count: 5,
        booked_lead_count: 2,
        active_non_booker_enrollment_count: 3,
        due_manual_call_count: 1,
        replies_needing_review_count: 2,
        opportunity_count: 4,
        opportunity_stage_summaries: [
          { source_lane: "probate", stage: "contract_sent", count: 1 },
          { source_lane: "lease_option_inbound", stage: "qualified_opportunity", count: 3 },
        ],
        outbound_probate_summary: {
          active_campaign_count: 2,
          ready_lead_count: 7,
          active_lead_count: 5,
          interested_lead_count: 3,
          suppressed_lead_count: 1,
        },
        inbound_lease_option_summary: {
          pending_lead_count: 5,
          booked_lead_count: 2,
          active_non_booker_enrollment_count: 3,
          due_manual_call_count: 1,
          replies_needing_review_count: 2,
        },
        opportunity_pipeline_summary: {
          total_opportunity_count: 4,
          lane_stage_summaries: [
            { source_lane: "probate", stage: "contract_sent", count: 1 },
            { source_lane: "lease_option_inbound", stage: "qualified_opportunity", count: 3 },
          ],
        },
        system_status: "watch",
        updated_at: "2026-04-16T22:00:00+00:00",
      }),
    );
    const api = createMissionControlApi({ fetchImpl: fetchMock as typeof fetch });

    const dashboard = await api.getDashboard();

    expect(dashboard.opportunityCount).toBe(4);
    expect(dashboard.opportunityStageSummaries).toEqual([
      { sourceLane: "probate", stage: "contract_sent", count: 1 },
      { sourceLane: "lease_option_inbound", stage: "qualified_opportunity", count: 3 },
    ]);
    expect(dashboard.outboundProbateSummary?.readyLeadCount).toBe(7);
    expect(dashboard.inboundLeaseOptionSummary?.pendingLeadCount).toBe(5);
    expect(dashboard.opportunityPipelineSummary?.laneStageSummaries).toEqual([
      { sourceLane: "probate", stage: "contract_sent", count: 1 },
      { sourceLane: "lease_option_inbound", stage: "qualified_opportunity", count: 3 },
    ]);
  });

  it("exposes compact fixture data for the marketing manual-call lane", () => {
    expect(missionControlFixtures.dashboard.opportunityCount).toBeGreaterThan(0);
    expect(missionControlFixtures.dashboard.opportunityStageSummaries).toEqual(
      expect.arrayContaining([{ sourceLane: expect.any(String), stage: expect.any(String), count: expect.any(Number) }]),
    );
    expect(missionControlTasksFixture.dueCount).toBeGreaterThan(0);
    expect(missionControlTasksFixture.tasks[0]).toMatchObject({
      threadId: expect.any(String),
      leadName: expect.any(String),
      bookingStatus: expect.any(String),
      sequenceStatus: expect.any(String),
    });
  });
});
