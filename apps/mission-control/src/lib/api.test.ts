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

  it("maps release and replay read-model fields for agents and runs", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/mission-control/runs")) {
        return jsonResponse({
          runs: [
            {
              id: "run-1",
              command_type: "run_market_research",
              status: "completed",
              business_id: "limitless",
              environment: "dev",
              updated_at: "2026-04-16T22:10:00+00:00",
              trigger_run_id: "trg-1",
              replay: {
                role: "parent",
                requested_at: "2026-04-16T22:00:00+00:00",
                resolved_at: "2026-04-16T22:00:00+00:00",
                replay_reason: "rerun after rollback",
                requires_approval: false,
                child_run_id: "run-2",
                triggering_actor: {
                  org_id: "org_internal",
                  actor_id: "ops-42",
                  actor_type: "user",
                },
                source: {
                  agent_id: "agt-1",
                  agent_revision_id: "rev-1",
                  active_revision_id: "rev-1",
                  revision_state: "published",
                  release_channel: "dogfood",
                  release_event_id: "rle-1",
                  release_event_type: "publish",
                },
                replay: {
                  agent_id: "agt-1",
                  agent_revision_id: "rev-1",
                  active_revision_id: "rev-3",
                  revision_state: "published",
                  release_channel: "dogfood",
                  release_event_id: "rle-3",
                  release_event_type: "rollback",
                },
              },
            },
          ],
        });
      }
      if (url.endsWith("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-1",
              name: "Release Agent",
              environment: "dev",
              active_revision_id: "rev-3",
              active_revision_state: "published",
              release: {
                event_id: "rle-3",
                event_type: "rollback",
                release_channel: "dogfood",
                created_at: "2026-04-16T22:00:00+00:00",
                previous_active_revision_id: "rev-2",
                target_revision_id: "rev-1",
                resulting_active_revision_id: "rev-3",
                rollback_source_revision_id: "rev-1",
                evaluation: {
                  outcome_id: "out-1",
                  outcome_name: "rollback_assessment",
                  status: "failed",
                  satisfied: false,
                  evaluator_result: "Regression reproduced.",
                  failure_details: ["voice workflow regressed"],
                  rubric_criteria: ["known good revision exists"],
                  require_passing_evaluation: false,
                  blocked_promotion: false,
                  rollback_reason: "Operator reported a production regression",
                },
              },
            },
          ],
        });
      }
      throw new Error(`Unexpected URL ${url}`);
    });

    const api = createMissionControlApi({ fetchImpl: fetchMock as typeof fetch });
    const [runs, agents] = await Promise.all([api.getRuns(), api.getAgents()]);

    expect(runs[0].replay).toMatchObject({
      role: "parent",
      replayReason: "rerun after rollback",
      childRunId: "run-2",
      source: { releaseEventType: "publish", releaseChannel: "dogfood" },
      replay: { releaseEventType: "rollback", activeRevisionId: "rev-3" },
    });
    expect(runs[0].summary).toContain("Replay launched child run run-2");
    expect(agents[0].release).toMatchObject({
      eventType: "rollback",
      rollbackSourceRevisionId: "rev-1",
      evaluation: {
        status: "failed",
        rollbackReason: "Operator reported a production regression",
      },
    });
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
    expect(missionControlFixtures.agents[0].release?.eventType).toBe("rollback");
    expect(missionControlFixtures.runs[0].replay?.replay?.releaseEventType).toBe("rollback");
  });
});
