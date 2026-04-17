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
          { stage: "contract_sent", count: 1 },
          { stage: "qualified_opportunity", count: 3 },
        ],
        system_status: "watch",
        updated_at: "2026-04-16T22:00:00+00:00",
      }),
    );
    const api = createMissionControlApi({ fetchImpl: fetchMock as typeof fetch });

    const dashboard = await api.getDashboard();

    expect(dashboard.opportunityCount).toBe(4);
    expect(dashboard.opportunityStageSummaries).toEqual([
      { stage: "contract_sent", count: 1 },
      { stage: "qualified_opportunity", count: 3 },
    ]);
  });

  it("exposes compact fixture data for the marketing manual-call lane", () => {
    expect(missionControlFixtures.dashboard.opportunityCount).toBeGreaterThan(0);
    expect(missionControlFixtures.dashboard.opportunityStageSummaries).toEqual(
      expect.arrayContaining([{ stage: expect.any(String), count: expect.any(Number) }]),
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
