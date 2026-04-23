import { describe, expect, it, vi } from "vitest";

import { createMissionControlApi } from "./api";
import { missionControlFixtures, missionControlTasksFixture } from "./fixtures";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function parseUrl(input: RequestInfo | URL): URL {
  return new URL(input.toString(), "https://example.test");
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

  it("adds org headers, preserves mission-control filters, and keeps governance org-scoped", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = parseUrl(input);

      if (url.pathname === "/organizations") {
        return jsonResponse({
          organizations: [
            {
              id: "org_alpha",
              name: "Alpha Org",
              slug: "alpha-org",
              metadata: { tier: "enterprise" },
              is_internal: false,
              created_at: "2026-04-22T00:00:00+00:00",
              updated_at: "2026-04-22T00:00:00+00:00",
            },
          ],
        });
      }
      if (url.pathname === "/mission-control/dashboard") {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-22T00:00:00+00:00",
        });
      }
      if (url.pathname === "/mission-control/inbox") {
        return jsonResponse({
          threads: [],
          selected_thread_id: null,
          selected_thread: null,
        });
      }
      if (url.pathname === "/agents/agt-1") {
        return jsonResponse({
          agent: {
            id: "agt-1",
            name: "Scoped Agent",
            slug: "scoped-agent",
            business_id: "limitless",
            environment: "dev",
            lifecycle_status: "active",
            active_revision_id: "rev-1",
            active_revision_state: "published",
          },
          revisions: [],
        });
      }
      if (url.pathname === "/release-management/agents/agt-1/events") {
        return jsonResponse({ events: [] });
      }
      if (url.pathname === "/mission-control/audit") {
        return jsonResponse({ events: [] });
      }
      if (url.pathname === "/usage") {
        return jsonResponse({
          summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-22T00:00:00+00:00" },
          events: [],
        });
      }
      if (url.pathname === "/mission-control/turns") {
        return jsonResponse({ turns: [] });
      }
      if (url.pathname === "/mission-control/settings/secrets/revisions/rev-1") {
        return jsonResponse({ bindings: [] });
      }
      if (url.pathname === "/mission-control/settings/governance") {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: { revisions: [] },
          recent_audit: [],
          usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-22T00:00:00+00:00" },
          recent_usage: [],
        });
      }

      throw new Error(`Unexpected URL ${url.toString()}`);
    });

    const api = createMissionControlApi({
      fetchImpl: fetchMock as typeof fetch,
      orgId: "org_alpha",
      businessId: "limitless",
      environment: "dev",
    });

    const [organizations, governance] = await Promise.all([
      api.getOrganizations(),
      api.getGovernance(),
      api.getDashboard(),
      api.getInbox("thread-42"),
      api.getAgentDetail("agt-1"),
    ]);

    expect(organizations).toEqual([
      {
        id: "org_alpha",
        name: "Alpha Org",
        slug: "alpha-org",
        metadata: { tier: "enterprise" },
        isInternal: false,
        createdAt: "2026-04-22T00:00:00+00:00",
        updatedAt: "2026-04-22T00:00:00+00:00",
      },
    ]);
    expect(governance.orgId).toBe("org_alpha");

    const requests = fetchMock.mock.calls.map((call) => {
      const input = call[0] as RequestInfo | URL;
      const init = (call as unknown as Array<RequestInfo | URL | RequestInit | undefined>)[1] as RequestInit | undefined;
      return {
        url: parseUrl(input),
        headers: init?.headers as Record<string, string> | undefined,
      };
    });

    expect(requests.every(({ headers }) => headers?.["X-Ares-Org-Id"] === "org_alpha")).toBe(true);

    expect(
      requests.find(({ url }) => url.pathname === "/organizations")?.url.searchParams.toString(),
    ).toBe("");
    expect(
      requests.find(({ url }) => url.pathname === "/mission-control/dashboard")?.url.searchParams.toString(),
    ).toBe("business_id=limitless&environment=dev");
    expect(
      requests.find(({ url }) => url.pathname === "/mission-control/inbox")?.url.searchParams.toString(),
    ).toBe("selected_thread_id=thread-42&business_id=limitless&environment=dev");
    expect(
      requests.find(({ url }) => url.pathname === "/mission-control/audit")?.url.searchParams.toString(),
    ).toBe("agent_id=agt-1&limit=8&business_id=limitless&environment=dev");
    expect(
      requests.find(({ url }) => url.pathname === "/mission-control/turns")?.url.searchParams.toString(),
    ).toBe("business_id=limitless&environment=dev");
    expect(
      requests.find(({ url }) => url.pathname === "/mission-control/settings/secrets/revisions/rev-1")?.url.searchParams.toString(),
    ).toBe("business_id=limitless&environment=dev");
    expect(
      requests.find(({ url }) => url.pathname === "/mission-control/settings/governance")?.url.searchParams.toString(),
    ).toBe("");
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
              business_id: "limitless",
              description: "Primary rollback-managed agent",
              name: "Release Agent",
              environment: "dev",
              active_revision_id: "rev-3",
              active_revision_state: "published",
              host_adapter: {
                kind: "trigger_dev",
                enabled: false,
                display_name: "Trigger.dev",
                adapter_details_label: "Adapter details",
                capabilities: {
                  dispatch: false,
                  status_correlation: false,
                  artifact_reporting: false,
                  cancellation: false,
                },
                disabled_reason: "Trigger.dev is disabled for this environment.",
              },
              created_at: "2026-04-16T21:55:00+00:00",
              updated_at: "2026-04-16T22:00:00+00:00",
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
    expect(agents[0].hostAdapter).toEqual({
      kind: "trigger_dev",
      enabled: false,
      displayName: "Trigger.dev",
      adapterDetailsLabel: "Adapter details",
      capabilities: {
        dispatch: false,
        statusCorrelation: false,
        artifactReporting: false,
        cancellation: false,
      },
      disabledReason: "Trigger.dev is disabled for this environment.",
    });
    expect(agents[0]).toMatchObject({
      businessId: "limitless",
      description: "Primary rollback-managed agent",
      createdAt: "2026-04-16T21:55:00+00:00",
      updatedAt: "2026-04-16T22:00:00+00:00",
    });
  });

  it("aggregates a read-only agent lifecycle detail view from existing typed endpoints", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/agents/agt-1")) {
        return jsonResponse({
          agent: {
            id: "agt-1",
            name: "Lifecycle Agent",
            slug: "lifecycle-agent",
            description: "Read-only detail agent",
            business_id: "limitless",
            environment: "production",
            lifecycle_status: "active",
            active_revision_id: "rev-2",
            active_revision_state: "published",
          },
          revisions: [
            {
              id: "rev-1",
              agent_id: "agt-1",
              revision_number: 1,
              state: "published",
              host_adapter_kind: "trigger_dev",
              provider_kind: "anthropic",
              provider_capabilities: ["chat"],
              skill_ids: ["skill.one"],
              compatibility_metadata: { requires_secrets: ["textgrid_auth_token"] },
              release_channel: "dogfood",
              created_at: "2026-04-16T20:00:00+00:00",
              updated_at: "2026-04-16T20:01:00+00:00",
              published_at: "2026-04-16T20:02:00+00:00",
            },
            {
              id: "rev-2",
              agent_id: "agt-1",
              revision_number: 2,
              state: "published",
              host_adapter_kind: "trigger_dev",
              provider_kind: "anthropic",
              provider_capabilities: ["chat", "tool_calling"],
              skill_ids: ["skill.one", "skill.two"],
              compatibility_metadata: { requires_secrets: ["textgrid_auth_token", "resend_api_key"] },
              release_channel: "dogfood",
              release_notes: "Known-good rollback clone.",
              created_at: "2026-04-16T21:00:00+00:00",
              updated_at: "2026-04-16T21:01:00+00:00",
              published_at: "2026-04-16T21:02:00+00:00",
              cloned_from_revision_id: "rev-1",
            },
          ],
        });
      }
      if (url.endsWith("/release-management/agents/agt-1/events")) {
        return jsonResponse({
          events: [
            {
              id: "rle-1",
              event_type: "rollback",
              actor_id: "ops-42",
              actor_type: "user",
              previous_active_revision_id: "rev-3",
              target_revision_id: "rev-1",
              resulting_active_revision_id: "rev-2",
              release_channel: "dogfood",
              notes: "Rollback to the last known-good revision.",
              created_at: "2026-04-16T21:03:00+00:00",
              evaluation_summary: {
                outcome_id: "out-1",
                outcome_name: "rollback_assessment",
                status: "failed",
                satisfied: false,
                evaluator_result: "Regression confirmed.",
                failure_details: ["reply quality regressed"],
                rubric_criteria: ["known good revision exists"],
                require_passing_evaluation: false,
                blocked_promotion: false,
                rollback_reason: "Operator reported a regression",
              },
            },
          ],
        });
      }
      if (url.includes("/mission-control/audit?agent_id=agt-1")) {
        return jsonResponse({
          events: [
            {
              id: "audit-1",
              event_type: "release_rolled_back",
              summary: "Lifecycle agent was rolled back.",
              resource_type: "agent_release",
              resource_id: "rle-1",
              created_at: "2026-04-16T21:03:00+00:00",
            },
          ],
        });
      }
      if (url.includes("/usage?agent_id=agt-1")) {
        return jsonResponse({
          summary: {
            total_count: 5,
            by_kind: { tool_call: 3, host_dispatch: 2 },
            by_source_kind: [{ key: "hermes", label: "hermes", count: 3, last_used_at: "2026-04-16T21:04:00+00:00" }],
            by_agent: [{ key: "agt-1", label: "Lifecycle Agent", count: 5, last_used_at: "2026-04-16T21:04:00+00:00" }],
            updated_at: "2026-04-16T21:04:00+00:00",
          },
          events: [
            {
              id: "usage-1",
              kind: "tool_call",
              count: 3,
              source_kind: "hermes",
              created_at: "2026-04-16T21:04:00+00:00",
            },
          ],
        });
      }
      if (url.endsWith("/mission-control/turns")) {
        return jsonResponse({
          turns: [
            {
              id: "turn-1",
              session_id: "session-1",
              business_id: "limitless",
              environment: "production",
              agent_id: "agt-1",
              agent_revision_id: "rev-2",
              turn_number: 1,
              state: "completed",
              retry_count: 0,
              updated_at: "2026-04-16T21:05:00+00:00",
            },
            {
              id: "turn-2",
              session_id: "session-2",
              business_id: "limitless",
              environment: "production",
              agent_id: "agt-other",
              agent_revision_id: "rev-9",
              turn_number: 2,
              state: "completed",
              retry_count: 0,
              updated_at: "2026-04-16T21:06:00+00:00",
            },
          ],
        });
      }
      if (url.endsWith("/mission-control/settings/secrets/revisions/rev-2")) {
        return jsonResponse({
          bindings: [{ binding_name: "textgrid_auth_token" }],
        });
      }
      throw new Error(`Unexpected URL ${url}`);
    });

    const api = createMissionControlApi({ fetchImpl: fetchMock as typeof fetch });
    const detail = await api.getAgentDetail("agt-1");

    expect(detail.agent).toMatchObject({
      id: "agt-1",
      activeRevisionId: "rev-2",
      activeRevisionState: "published",
    });
    expect(detail.revisions[1]).toMatchObject({
      id: "rev-2",
      skillIds: ["skill.one", "skill.two"],
      requiredSecrets: ["textgrid_auth_token", "resend_api_key"],
    });
    expect(detail.secretsHealth).toMatchObject({
      revisionId: "rev-2",
      configuredSecrets: ["textgrid_auth_token"],
      missingSecrets: ["resend_api_key"],
      status: "attention",
    });
    expect(detail.releaseHistory).toHaveLength(1);
    expect(detail.releaseHistory[0]).toMatchObject({
      eventType: "rollback",
      targetRevisionId: "rev-1",
      evaluation: { rollbackReason: "Operator reported a regression" },
    });
    expect(detail.recentTurns).toHaveLength(1);
    expect(detail.usageSummary.totalCount).toBe(5);
    expect(detail.recentAudit[0].eventType).toBe("release_rolled_back");
  });

  it("keeps live agent detail when auxiliary detail endpoints fail", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.endsWith("/agents/agt-1")) {
        return jsonResponse({
          agent: {
            id: "agt-1",
            name: "Lifecycle Agent",
            slug: "lifecycle-agent",
            business_id: "limitless",
            environment: "production",
            lifecycle_status: "active",
            active_revision_id: "rev-2",
            active_revision_state: "published",
          },
          revisions: [
            {
              id: "rev-2",
              agent_id: "agt-1",
              revision_number: 2,
              state: "published",
              host_adapter_kind: "trigger_dev",
              provider_kind: "anthropic",
              provider_capabilities: ["chat"],
              skill_ids: ["skill.one"],
              compatibility_metadata: { requires_secrets: ["textgrid_auth_token"] },
              release_channel: "dogfood",
              created_at: "2026-04-16T21:00:00+00:00",
              updated_at: "2026-04-16T21:01:00+00:00",
            },
          ],
        });
      }
      if (url.endsWith("/release-management/agents/agt-1/events") || url.includes("/mission-control/audit?agent_id=agt-1") || url.includes("/usage?agent_id=agt-1")) {
        throw new Error("transient detail dependency failure");
      }
      if (url.endsWith("/mission-control/turns")) {
        return jsonResponse({ turns: [] });
      }
      if (url.includes("/mission-control/settings/secrets/revisions/rev-2")) {
        throw new Error("bindings temporarily unavailable");
      }
      throw new Error(`Unexpected URL ${url}`);
    });

    const api = createMissionControlApi({ fetchImpl: fetchMock as typeof fetch });
    const detail = await api.getAgentDetail("agt-1");

    expect(detail.agent).toMatchObject({
      id: "agt-1",
      name: "Lifecycle Agent",
      activeRevisionId: "rev-2",
    });
    expect(detail.revisions).toHaveLength(1);
    expect(detail.releaseHistory).toEqual([]);
    expect(detail.recentAudit).toEqual([]);
    expect(detail.recentUsage).toEqual([]);
    expect(detail.usageSummary.totalCount).toBe(0);
    expect(detail.secretsHealth).toBeNull();
    expect(detail.degradedSections).toEqual(
      expect.arrayContaining(["releaseHistory", "recentAudit", "usage", "secretsHealth"]),
    );
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

  it("maps catalog entries and installs through the new catalog APIs", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const headers = new Headers(init?.headers);

      if (url.endsWith("/catalog")) {
        expect(headers.get("X-Ares-Org-Id")).toBe("org_alpha");
        return jsonResponse({
          entries: [
            {
              id: "cat-1",
              org_id: "org_alpha",
              agent_id: "agt-source-1",
              agent_revision_id: "rev-source-1",
              slug: "seller-ops",
              name: "Seller Ops",
              summary: "Installable seller ops agent",
              description: "Operator package for seller follow-up.",
              visibility: "marketplace_candidate",
              marketplace_publication_enabled: false,
              host_adapter_kind: "trigger_dev",
              provider_kind: "anthropic",
              provider_capabilities: ["tool_calls"],
              required_skill_ids: ["skl_triage"],
              required_secret_names: ["resend_api_key"],
              release_channel: "dogfood",
              metadata: { category: "operations" },
              created_at: "2026-04-23T03:00:00+00:00",
              updated_at: "2026-04-23T03:00:00+00:00",
            },
          ],
        });
      }

      if (url.endsWith("/agent-installs") && init?.method === "POST") {
        expect(headers.get("X-Ares-Org-Id")).toBe("org_alpha");
        expect(init?.body).toBe(
          JSON.stringify({
            catalog_entry_id: "cat-1",
            business_id: "limitless",
            environment: "prod",
            name: "Installed Seller Ops",
          }),
        );
        return jsonResponse({
          install: {
            id: "ins-1",
            org_id: "org_alpha",
            catalog_entry_id: "cat-1",
            source_agent_id: "agt-source-1",
            source_agent_revision_id: "rev-source-1",
            installed_agent_id: "agt-installed-1",
            installed_agent_revision_id: "rev-installed-1",
            business_id: "limitless",
            environment: "prod",
            created_at: "2026-04-23T03:05:00+00:00",
            updated_at: "2026-04-23T03:05:00+00:00",
          },
          agent: {
            id: "agt-installed-1",
            org_id: "org_alpha",
            business_id: "limitless",
            environment: "prod",
            name: "Installed Seller Ops",
            slug: "installed-seller-ops",
            description: "Operator package for seller follow-up.",
            visibility: "private_catalog",
            lifecycle_status: "draft",
            packaging_metadata: {
              catalog_entry_id: "cat-1",
              source_agent_id: "agt-source-1",
              source_agent_revision_id: "rev-source-1",
            },
            active_revision_id: null,
            created_at: "2026-04-23T03:05:00+00:00",
            updated_at: "2026-04-23T03:05:00+00:00",
          },
          revisions: [
            {
              id: "rev-installed-1",
              agent_id: "agt-installed-1",
              revision_number: 1,
              state: "draft",
              host_adapter_kind: "trigger_dev",
              host_adapter_config: {},
              provider_kind: "anthropic",
              provider_config: {},
              provider_capabilities: ["tool_calls"],
              skill_ids: ["skl_triage"],
              input_schema: {},
              output_schema: {},
              release_notes: null,
              compatibility_metadata: { requires_secrets: ["resend_api_key"] },
              release_channel: "dogfood",
              created_at: "2026-04-23T03:05:00+00:00",
              updated_at: "2026-04-23T03:05:00+00:00",
              published_at: null,
              archived_at: null,
              cloned_from_revision_id: null,
            },
          ],
        });
      }

      throw new Error(`Unexpected URL ${url}`);
    });

    const api = createMissionControlApi({
      fetchImpl: fetchMock as typeof fetch,
      orgId: "org_alpha",
    });

    const entries = await api.getCatalogEntries();
    const install = await api.installCatalogEntry({
      catalogEntryId: "cat-1",
      businessId: "limitless",
      environment: "prod",
      name: "Installed Seller Ops",
    });

    expect(entries[0]).toMatchObject({
      id: "cat-1",
      slug: "seller-ops",
      visibility: "marketplace_candidate",
      marketplacePublicationEnabled: false,
      requiredSecretNames: ["resend_api_key"],
      requiredSkillIds: ["skl_triage"],
    });
    expect(install.install).toMatchObject({
      id: "ins-1",
      catalogEntryId: "cat-1",
      installedAgentId: "agt-installed-1",
      environment: "prod",
    });
    expect(install.agent).toMatchObject({
      id: "agt-installed-1",
      businessId: "limitless",
      packagingMetadata: {
        catalogEntryId: "cat-1",
        sourceAgentId: "agt-source-1",
        sourceAgentRevisionId: "rev-source-1",
      },
    });
  });
});
