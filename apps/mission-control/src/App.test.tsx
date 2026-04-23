import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { queryClient } from "./lib/queryClient";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

function createDeferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, resolve, reject };
}

describe("App", () => {
  beforeEach(() => {
    queryClient.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("refetches inbox detail when the operator selects a different conversation", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 2,
          busy_channel_count: 2,
          recent_completed_count: 3,
          system_status: "watch",
          updated_at: "2026-04-13T20:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        const selectedThreadId = new URL(url, "http://localhost").searchParams.get("selected_thread_id");
        const selectedThread =
          selectedThreadId === "thread-2"
            ? {
                thread_id: "thread-2",
                channel: "email",
                status: "open",
                unread_count: 1,
                requires_approval: false,
                related_run_id: null,
                related_approval_id: null,
                contact: { display_name: "Jordan Patel", email: "jordan@example.com" },
                messages: [
                  {
                    id: "msg-2",
                    direction: "inbound",
                    channel: "email",
                    body: "Jordan detail from API",
                    created_at: "2026-04-13T20:05:00+00:00",
                    message_type: "received",
                  },
                ],
                context: { stage: "Follow-up", next_best_action: "Send contract packet." },
              }
            : {
                thread_id: "thread-1",
                channel: "sms",
                status: "open",
                unread_count: 1,
                requires_approval: true,
                related_run_id: null,
                related_approval_id: null,
                contact: { display_name: "Taylor Brooks", phone: "+15551230001" },
                messages: [
                  {
                    id: "msg-1",
                    direction: "inbound",
                    channel: "sms",
                    body: "Taylor detail from API",
                    created_at: "2026-04-13T20:01:00+00:00",
                    message_type: "received",
                  },
                ],
                context: { stage: "Qualified", next_best_action: "Approve the draft." },
              };

        return jsonResponse({
          summary: { thread_count: 2, unread_count: 2, approval_required_count: 1 },
          threads: [
            {
              thread_id: "thread-1",
              channel: "sms",
              status: "open",
              unread_count: 1,
              last_message_preview: "Taylor preview",
              last_message_at: "2026-04-13T20:01:00+00:00",
              requires_approval: true,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Taylor Brooks", phone: "+15551230001" },
            },
            {
              thread_id: "thread-2",
              channel: "email",
              status: "open",
              unread_count: 1,
              last_message_preview: "Jordan preview",
              last_message_at: "2026-04-13T20:05:00+00:00",
              requires_approval: false,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Jordan Patel", email: "jordan@example.com" },
            },
          ],
          selected_thread_id: selectedThread.thread_id,
          selected_thread: selectedThread,
        });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-13T20:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /replies/i }));

    expect(await screen.findByText("Taylor detail from API")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /jordan patel/i }));

    expect(await screen.findByText("Jordan detail from API")).toBeInTheDocument();
    expect(screen.queryByText("Taylor detail from API")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/mission-control/inbox?selected_thread_id=thread-2"),
        expect.any(Object),
      );
    });
  });

  it("opens the read-only agent lifecycle page from the agents-first workspace", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 1,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-1",
              business_id: "limitless",
              description: "Primary rollback-managed agent",
              name: "Lifecycle Agent",
              environment: "production",
              active_revision_id: "rev-2",
              active_revision_state: "published",
              live_session_count: 2,
              delegated_work_count: 3,
              host_adapter: {
                kind: "trigger_dev",
                enabled: true,
                display_name: "Trigger.dev",
                adapter_details_label: "Adapter details",
                capabilities: {
                  dispatch: true,
                  status_correlation: true,
                  artifact_reporting: true,
                  cancellation: false,
                },
                disabled_reason: null,
              },
              release: {
                event_id: "rle-1",
                event_type: "rollback",
                release_channel: "dogfood",
                created_at: "2026-04-16T21:03:00+00:00",
                previous_active_revision_id: "rev-3",
                target_revision_id: "rev-1",
                resulting_active_revision_id: "rev-2",
                rollback_source_revision_id: "rev-1",
              },
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 1,
            healthy_revision_count: 1,
            attention_revision_count: 0,
            required_secret_count: 1,
            configured_secret_count: 1,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

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
              provider_capabilities: ["chat", "tool_calling"],
              skill_ids: ["skill.one", "skill.two"],
              compatibility_metadata: { requires_secrets: ["textgrid_auth_token"] },
              release_channel: "dogfood",
              release_notes: "Known-good rollback clone.",
              created_at: "2026-04-16T21:00:00+00:00",
              updated_at: "2026-04-16T21:01:00+00:00",
              published_at: "2026-04-16T21:02:00+00:00",
            },
          ],
        });
      }

      if (url.endsWith("/release-management/agents/agt-1/events")) {
        return jsonResponse({
          events: [
            {
              id: "rle-0",
              event_type: "publish",
              actor_id: "ops-21",
              actor_type: "user",
              previous_active_revision_id: null,
              target_revision_id: "rev-1",
              resulting_active_revision_id: "rev-1",
              release_channel: "dogfood",
              notes: "First publish.",
              created_at: "2026-04-16T20:00:00+00:00",
            },
            {
              id: "rle-1",
              event_type: "rollback",
              actor_id: "ops-42",
              actor_type: "user",
              previous_active_revision_id: "rev-3",
              target_revision_id: "rev-1",
              resulting_active_revision_id: "rev-2",
              release_channel: "dogfood",
              notes: "Rollback to known-good.",
              created_at: "2026-04-16T21:03:00+00:00",
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
            total_count: 2,
            by_kind: { tool_call: 2 },
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:04:00+00:00",
          },
          events: [
            {
              id: "usage-1",
              kind: "tool_call",
              count: 2,
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
          ],
        });
      }

      if (url.endsWith("/mission-control/settings/secrets/revisions/rev-2")) {
        return jsonResponse({ bindings: [{ binding_name: "textgrid_auth_token" }] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for lifecycle agent/i }));

    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText(/read-only lifecycle view for the selected agent/i)).toBeInTheDocument();
    expect(screen.getByText("Lifecycle Agent · limitless · production")).toBeInTheDocument();
    expect(screen.getByText(/Latest event rle-1 moved rev-1 to rev-2/i)).toBeInTheDocument();
    expect(screen.getByText("Adapter details: dispatch, status correlation, artifact reporting")).toBeInTheDocument();
    expect(screen.getByText("Lifecycle agent was rolled back.")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back to agents/i }));

    expect(await screen.findByRole("heading", { name: /lead machine \/ agents/i, level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /view lifecycle for lifecycle agent/i })).toBeInTheDocument();
  });

  it("keeps host-adapter truth unavailable when agents are fixture-backed but detail loads live", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 1,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        throw new Error("agents unavailable");
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 1,
            healthy_revision_count: 1,
            attention_revision_count: 0,
            required_secret_count: 1,
            configured_secret_count: 1,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      if (url.endsWith("/agents/agt-1001")) {
        return jsonResponse({
          agent: {
            id: "agt-1001",
            name: "Sierra Inbox Agent",
            slug: "sierra-inbox-agent",
            business_id: "limitless",
            environment: "production",
            lifecycle_status: "active",
            active_revision_id: "rev-201",
            active_revision_state: "published",
          },
          revisions: [
            {
              id: "rev-201",
              agent_id: "agt-1001",
              revision_number: 3,
              state: "published",
              host_adapter_kind: "trigger_dev",
              provider_kind: "anthropic",
              provider_capabilities: ["chat", "tool_calling"],
              skill_ids: ["inbox.reply-review"],
              compatibility_metadata: { requires_secrets: [] },
              release_channel: "dogfood",
              release_notes: "Live detail revision.",
              created_at: "2026-04-16T21:57:00+00:00",
              updated_at: "2026-04-16T22:02:00+00:00",
              published_at: "2026-04-16T22:03:00+00:00",
            },
          ],
        });
      }

      if (url.endsWith("/release-management/agents/agt-1001/events")) {
        throw new Error("release history unavailable");
      }

      if (url.includes("/mission-control/audit?agent_id=agt-1001")) {
        return jsonResponse({ events: [] });
      }

      if (url.includes("/usage?agent_id=agt-1001")) {
        return jsonResponse({
          summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          events: [],
        });
      }

      if (url.endsWith("/mission-control/turns")) {
        return jsonResponse({ turns: [] });
      }

      if (url.endsWith("/mission-control/settings/secrets/revisions/rev-201")) {
        return jsonResponse({ bindings: [{ binding_name: "textgrid_auth_token" }] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for sierra inbox agent/i }));

    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText(/status unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText("Trigger.dev enabled")).not.toBeInTheDocument();
    expect(screen.getByText("Channel dogfood · revision rev-201 · state published")).toBeInTheDocument();
    expect(screen.queryByText("Channel dogfood · target rev-198 · active rev-201")).not.toBeInTheDocument();
  });

  it("keeps summary release and host-adapter truth unavailable when the live agents revision no longer matches detail", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 1,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-1001",
              business_id: "limitless",
              description: "Live agents summary is stale.",
              name: "Sierra Inbox Agent",
              environment: "production",
              active_revision_id: "rev-stale",
              active_revision_state: "published",
              host_adapter: {
                kind: "trigger_dev",
                enabled: false,
                display_name: "Trigger.dev",
                disabled_reason: "Trigger.dev is disabled in the stale summary.",
              },
              release: {
                event_id: "rle-stale",
                event_type: "rollback",
                release_channel: "dogfood",
                created_at: "2026-04-16T20:30:00+00:00",
                previous_active_revision_id: "rev-older",
                target_revision_id: "rev-stale",
                resulting_active_revision_id: "rev-stale",
              },
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 1,
            healthy_revision_count: 1,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      if (url.endsWith("/agents/agt-1001")) {
        return jsonResponse({
          agent: {
            id: "agt-1001",
            name: "Sierra Inbox Agent",
            slug: "sierra-inbox-agent",
            business_id: "limitless",
            environment: "production",
            lifecycle_status: "active",
            active_revision_id: "rev-201",
            active_revision_state: "published",
          },
          revisions: [
            {
              id: "rev-201",
              agent_id: "agt-1001",
              revision_number: 3,
              state: "published",
              host_adapter_kind: "trigger_dev",
              provider_kind: "anthropic",
              provider_capabilities: ["chat", "tool_calling"],
              skill_ids: ["inbox.reply-review"],
              compatibility_metadata: { requires_secrets: [] },
              release_channel: "dogfood",
              release_notes: "Live detail revision.",
              created_at: "2026-04-16T21:57:00+00:00",
              updated_at: "2026-04-16T22:02:00+00:00",
              published_at: "2026-04-16T22:03:00+00:00",
            },
          ],
        });
      }

      if (url.endsWith("/release-management/agents/agt-1001/events")) {
        throw new Error("release history unavailable");
      }

      if (url.includes("/mission-control/audit?agent_id=agt-1001")) {
        return jsonResponse({ events: [] });
      }

      if (url.includes("/usage?agent_id=agt-1001")) {
        return jsonResponse({
          summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          events: [],
        });
      }

      if (url.endsWith("/mission-control/turns")) {
        return jsonResponse({ turns: [] });
      }

      if (url.endsWith("/mission-control/settings/secrets/revisions/rev-201")) {
        return jsonResponse({ bindings: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for sierra inbox agent/i }));

    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText(/status unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText("Trigger.dev disabled")).not.toBeInTheDocument();
    expect(screen.queryByText("Trigger.dev is disabled in the stale summary.")).not.toBeInTheDocument();
    expect(screen.getByText("Channel dogfood · revision rev-201 · state published")).toBeInTheDocument();
    expect(screen.queryByText("Channel dogfood · target rev-stale · active rev-stale")).not.toBeInTheDocument();
  });

  it("keeps summary release and host-adapter truth unavailable when the live agents state no longer matches detail", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 1,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-1001",
              business_id: "limitless",
              description: "Live agents summary has a newer state.",
              name: "Sierra Inbox Agent",
              environment: "production",
              active_revision_id: "rev-201",
              active_revision_state: "draft",
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
                disabled_reason: "Trigger.dev is disabled in the stale state summary.",
              },
              release: {
                event_id: "rle-stale-state",
                event_type: "publish",
                release_channel: "dogfood",
                created_at: "2026-04-16T20:30:00+00:00",
                previous_active_revision_id: "rev-200",
                target_revision_id: "rev-201",
                resulting_active_revision_id: "rev-201",
              },
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 1,
            healthy_revision_count: 1,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      if (url.endsWith("/agents/agt-1001")) {
        return jsonResponse({
          agent: {
            id: "agt-1001",
            name: "Sierra Inbox Agent",
            slug: "sierra-inbox-agent",
            business_id: "limitless",
            environment: "production",
            lifecycle_status: "active",
            active_revision_id: "rev-201",
            active_revision_state: "published",
          },
          revisions: [
            {
              id: "rev-201",
              agent_id: "agt-1001",
              revision_number: 3,
              state: "published",
              host_adapter_kind: "trigger_dev",
              provider_kind: "anthropic",
              provider_capabilities: ["chat", "tool_calling"],
              skill_ids: ["inbox.reply-review"],
              compatibility_metadata: { requires_secrets: [] },
              release_channel: "dogfood",
              release_notes: "Live detail revision.",
              created_at: "2026-04-16T21:57:00+00:00",
              updated_at: "2026-04-16T22:02:00+00:00",
              published_at: "2026-04-16T22:03:00+00:00",
            },
          ],
        });
      }

      if (url.endsWith("/release-management/agents/agt-1001/events")) {
        throw new Error("release history unavailable");
      }

      if (url.includes("/mission-control/audit?agent_id=agt-1001")) {
        return jsonResponse({ events: [] });
      }

      if (url.includes("/usage?agent_id=agt-1001")) {
        return jsonResponse({
          summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          events: [],
        });
      }

      if (url.endsWith("/mission-control/turns")) {
        return jsonResponse({ turns: [] });
      }

      if (url.endsWith("/mission-control/settings/secrets/revisions/rev-201")) {
        return jsonResponse({ bindings: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for sierra inbox agent/i }));

    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.queryByText("Trigger.dev disabled")).not.toBeInTheDocument();
    expect(screen.queryByText("Trigger.dev is disabled in the stale state summary.")).not.toBeInTheDocument();
    expect(screen.getByText("Channel dogfood · revision rev-201 · state published")).toBeInTheDocument();
    expect(screen.queryByText("Channel dogfood · target rev-201 · active rev-201")).not.toBeInTheDocument();
  });

  it("keeps summary host-adapter truth unavailable when agents recover after fixture detail fallback", async () => {
    let agentsRequestCount = 0;

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 1,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        agentsRequestCount += 1;
        if (agentsRequestCount < 3) {
          throw new Error("agents unavailable");
        }
        return jsonResponse({
          agents: [
            {
              id: "agt-1001",
              business_id: "limitless",
              description: "Recovered live agent.",
              name: "Sierra Inbox Agent",
              environment: "production",
              active_revision_id: "rev-201",
              active_revision_state: "published",
              host_adapter: {
                kind: "trigger_dev",
                enabled: true,
                display_name: "Trigger.dev",
                adapter_details_label: "Adapter details",
                capabilities: {
                  dispatch: true,
                  status_correlation: true,
                  artifact_reporting: true,
                  cancellation: false,
                },
                disabled_reason: null,
              },
            },
          ],
        });
      }

      if (url.includes("/catalog")) {
        return jsonResponse({ entries: [] });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T21:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      if (url.endsWith("/agents/agt-1001")) {
        throw new Error("detail unavailable");
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for sierra inbox agent/i }));

    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText("Fixture fallback")).toBeInTheDocument();
    expect(screen.getByText(/status unavailable/i)).toBeInTheDocument();
    expect(screen.queryByText("Trigger.dev enabled")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /queue/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /agents/i })[0]);

    expect(await screen.findByText("Live API")).toBeInTheDocument();
    const reopenedLifecycleButton = screen.queryByRole("button", { name: /view lifecycle for sierra inbox agent/i });
    if (reopenedLifecycleButton) {
      fireEvent.click(reopenedLifecycleButton);
    }
    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.queryByText("Trigger.dev enabled")).not.toBeInTheDocument();
    expect(screen.queryByText("Adapter details: dispatch, status correlation, artifact reporting")).not.toBeInTheDocument();
  });

  it("clears stale selected agent detail when search excludes the agent", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 2,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }
      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }
      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }
      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }
      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }
      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-1",
              name: "Lifecycle Agent",
              environment: "production",
              active_revision_id: "rev-2",
              active_revision_state: "published",
              live_session_count: 1,
              delegated_work_count: 1,
            },
            {
              id: "agt-2",
              name: "Other Agent",
              environment: "staging",
              active_revision_id: "rev-9",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }
      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-16T21:00:00+00:00" },
          recent_usage: [],
        });
      }
      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }
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
          revisions: [],
        });
      }
      if (url.endsWith("/release-management/agents/agt-1/events")) {
        return jsonResponse({ events: [] });
      }
      if (url.includes("/mission-control/audit?agent_id=agt-1")) {
        return jsonResponse({ events: [] });
      }
      if (url.includes("/usage?agent_id=agt-1")) {
        return jsonResponse({ summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-16T21:00:00+00:00" }, events: [] });
      }
      if (url.endsWith("/mission-control/turns")) {
        return jsonResponse({ turns: [] });
      }
      if (url.includes("/mission-control/settings/secrets/revisions/rev-2")) {
        return jsonResponse({ bindings: [] });
      }
      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for lifecycle agent/i }));
    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();

    fireEvent.change(screen.getByRole("searchbox", { name: /search mission control/i }), { target: { value: "other agent" } });

    await waitFor(() => {
      expect(screen.queryByRole("heading", { name: "Agent lifecycle" })).not.toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /view lifecycle for other agent/i })).toBeInTheDocument();
  });

  it("keeps the side context panel neutral while a different agent detail is still loading", async () => {
    let resolveFirstAgentDetail: ((value: Response) => void) | null = null;
    let resolveSecondAgentDetail: ((value: Response) => void) | null = null;

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return Promise.resolve(
          jsonResponse({
            approval_count: 0,
            active_run_count: 0,
            failed_run_count: 0,
            active_agent_count: 2,
            unread_conversation_count: 0,
            busy_channel_count: 0,
            recent_completed_count: 0,
            system_status: "healthy",
            updated_at: "2026-04-16T21:00:00+00:00",
          }),
        );
      }
      if (url.includes("/mission-control/inbox")) {
        return Promise.resolve(
          jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null }),
        );
      }
      if (url.includes("/mission-control/tasks")) {
        return Promise.resolve(jsonResponse({ due_count: 0, tasks: [] }));
      }
      if (url.includes("/mission-control/approvals")) {
        return Promise.resolve(jsonResponse({ approvals: [] }));
      }
      if (url.includes("/mission-control/runs")) {
        return Promise.resolve(jsonResponse({ runs: [] }));
      }
      if (url.includes("/mission-control/agents")) {
        return Promise.resolve(
          jsonResponse({
            agents: [
              {
                id: "agt-1",
                business_id: "limitless",
                description: "First live agent",
                name: "First Agent",
                environment: "production",
                active_revision_id: "rev-1",
                active_revision_state: "published",
              },
              {
                id: "agt-2",
                business_id: "limitless",
                description: "Second live agent",
                name: "Second Agent",
                environment: "production",
                active_revision_id: "rev-2",
                active_revision_state: "published",
              },
            ],
          }),
        );
      }
      if (url.includes("/mission-control/settings/governance")) {
        return Promise.resolve(
          jsonResponse({
            org_id: "org_alpha",
            pending_approvals: [],
            secrets_health: {
              active_revision_count: 0,
              healthy_revision_count: 0,
              attention_revision_count: 0,
              required_secret_count: 0,
              configured_secret_count: 0,
              missing_secret_count: 0,
              revisions: [],
            },
            recent_audit: [],
            usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-16T21:00:00+00:00" },
            recent_usage: [],
          }),
        );
      }
      if (url.includes("/mission-control/settings/assets")) {
        return Promise.resolve(jsonResponse({ assets: [] }));
      }
      if (url.endsWith("/agents/agt-1")) {
        return new Promise((resolve) => {
          resolveFirstAgentDetail = resolve;
        });
      }
      if (url.endsWith("/agents/agt-2")) {
        return new Promise((resolve) => {
          resolveSecondAgentDetail = resolve;
        });
      }
      if (url.endsWith("/release-management/agents/agt-1/events") || url.endsWith("/release-management/agents/agt-2/events")) {
        return Promise.resolve(jsonResponse({ events: [] }));
      }
      if (url.includes("/mission-control/audit?agent_id=agt-1") || url.includes("/mission-control/audit?agent_id=agt-2")) {
        return Promise.resolve(jsonResponse({ events: [] }));
      }
      if (url.includes("/usage?agent_id=agt-1") || url.includes("/usage?agent_id=agt-2")) {
        return Promise.resolve(
          jsonResponse({ summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-16T21:00:00+00:00" }, events: [] }),
        );
      }
      if (url.endsWith("/mission-control/turns")) {
        return Promise.resolve(jsonResponse({ turns: [] }));
      }
      if (url.includes("/mission-control/settings/secrets/revisions/rev-1") || url.includes("/mission-control/settings/secrets/revisions/rev-2")) {
        return Promise.resolve(jsonResponse({ bindings: [] }));
      }

      return Promise.reject(new Error(`Unexpected fetch URL: ${url}`));
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for first agent/i }));

    if (!resolveFirstAgentDetail) {
      throw new Error("First agent detail request was not issued");
    }

    (resolveFirstAgentDetail as (value: Response) => void)(
      jsonResponse({
        agent: {
          id: "agt-1",
          name: "First Agent",
          slug: "first-agent",
          business_id: "limitless",
          environment: "production",
          lifecycle_status: "active",
          active_revision_id: "rev-1",
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
            compatibility_metadata: { requires_secrets: [] },
            release_channel: "dogfood",
            created_at: "2026-04-16T21:00:00+00:00",
            updated_at: "2026-04-16T21:01:00+00:00",
          },
        ],
      }),
    );

    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText("1 revisions are tracked for this agent")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back to agents/i }));
    expect(await screen.findByRole("button", { name: /view lifecycle for second agent/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /view lifecycle for second agent/i }));

    expect(await screen.findByRole("heading", { name: "Loading agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Second Agent" })).toBeInTheDocument();
    expect(screen.getByText("Fetching runtime lifecycle context for the selected agent.")).toBeInTheDocument();
    expect(screen.queryByText("1 revisions are tracked for this agent")).not.toBeInTheDocument();

    if (!resolveSecondAgentDetail) {
      throw new Error("Second agent detail request was not issued");
    }

    (resolveSecondAgentDetail as (value: Response) => void)(
      jsonResponse({
        agent: {
          id: "agt-2",
          name: "Second Agent",
          slug: "second-agent",
          business_id: "limitless",
          environment: "production",
          lifecycle_status: "active",
          active_revision_id: "rev-2",
          active_revision_state: "published",
        },
        revisions: [],
      }),
    );

    expect(await screen.findByText("0 revisions are tracked for this agent")).toBeInTheDocument();
  });

  it("loads fixtures when the API is unavailable", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("API unavailable");
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Agent platform cockpit" })).toBeInTheDocument();
    expect(screen.getByText("Fixture mode")).toBeInTheDocument();
  });

  it("reconciles shell fallback labels after the agents surface recovers from fixture mode", async () => {
    let agentsRequestCount = 0;

    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }
      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }
      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }
      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }
      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }
      if (url.includes("/mission-control/agents")) {
        agentsRequestCount += 1;
        if (agentsRequestCount < 3) {
          throw new Error("agents temporarily unavailable");
        }
        return jsonResponse({
          agents: [
            {
              id: "agt-1",
              business_id: "limitless",
              description: "Recovered agent",
              name: "Recovered Agent",
              environment: "production",
              active_revision_id: "rev-2",
              active_revision_state: "published",
            },
          ],
        });
      }
      if (url.includes("/catalog")) {
        return jsonResponse({ entries: [] });
      }
      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-16T21:00:00+00:00" },
          recent_usage: [],
        });
      }
      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("API + fixture fallback (agents)")).toBeInTheDocument();
    expect(screen.getByText("Fixture fallback / no Supabase wiring")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /queue/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /agents/i })[0]);

    await screen.findByText("Live API / no Supabase wiring");
    await screen.findByText("Live API");

    expect(screen.getByText("Mission Control is reading Hermes runtime data.")).toBeInTheDocument();
    expect(screen.queryByText("API + fixture fallback (agents)")).not.toBeInTheDocument();
    expect(screen.queryByText("Using fixture fallback for: agents.")).not.toBeInTheDocument();
  });

  it("preserves summary business truth when agent detail falls back to degraded mode", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-16T21:00:00+00:00",
        });
      }
      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }
      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }
      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }
      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }
      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-1",
              business_id: "limitless",
              description: "Primary rollback-managed agent",
              name: "Lifecycle Agent",
              environment: "production",
              active_revision_id: "rev-2",
              active_revision_state: "published",
              release: {
                event_id: "rle-1",
                event_type: "rollback",
                release_channel: "dogfood",
                created_at: "2026-04-16T21:03:00+00:00",
                previous_active_revision_id: "rev-3",
                target_revision_id: "rev-1",
                resulting_active_revision_id: "rev-2",
                rollback_source_revision_id: "rev-1",
              },
            },
          ],
        });
      }
      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-16T21:00:00+00:00" },
          recent_usage: [],
        });
      }
      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }
      if (url.endsWith("/agents/agt-1")) {
        throw new Error("detail endpoint unavailable");
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for lifecycle agent/i }));

    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText("Lifecycle Agent · limitless · production")).toBeInTheDocument();
    expect(screen.getByText("Live detail unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Lifecycle Agent · unavailable · production")).not.toBeInTheDocument();
    const lifecycleBadgeRow = screen.getByRole("button", { name: /back to agents/i }).parentElement;
    if (!lifecycleBadgeRow) {
      throw new Error("Lifecycle badge row is missing");
    }
    expect(within(lifecycleBadgeRow).getByText("published")).toBeInTheDocument();
    expect(within(lifecycleBadgeRow).getByText("unavailable")).toBeInTheDocument();
  });

  it("falls back safely when the second-thread inbox detail fetch fails mid-session", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 2,
          busy_channel_count: 2,
          recent_completed_count: 3,
          system_status: "watch",
          updated_at: "2026-04-13T20:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        const selectedThreadId = new URL(url, "http://localhost").searchParams.get("selected_thread_id");

        if (selectedThreadId && selectedThreadId !== "thread-1") {
          throw new Error("Inbox detail unavailable");
        }

        return jsonResponse({
          summary: { thread_count: 2, unread_count: 2, approval_required_count: 1 },
          threads: [
            {
              thread_id: "thread-1",
              channel: "sms",
              status: "open",
              unread_count: 1,
              last_message_preview: "Taylor preview",
              last_message_at: "2026-04-13T20:01:00+00:00",
              requires_approval: true,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Taylor Brooks", phone: "+155****0001" },
            },
            {
              thread_id: "thread-2",
              channel: "email",
              status: "open",
              unread_count: 1,
              last_message_preview: "Jordan preview",
              last_message_at: "2026-04-13T20:05:00+00:00",
              requires_approval: false,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Jordan Patel", email: "jordan@example.com" },
            },
          ],
          selected_thread_id: "thread-1",
          selected_thread: {
            thread_id: "thread-1",
            channel: "sms",
            status: "open",
            unread_count: 1,
            requires_approval: true,
            related_run_id: null,
            related_approval_id: null,
            contact: { display_name: "Taylor Brooks", phone: "+155****0001" },
            messages: [
              {
                id: "msg-1",
                direction: "inbound",
                channel: "sms",
                body: "Taylor detail from API",
                created_at: "2026-04-13T20:01:00+00:00",
                message_type: "received",
              },
            ],
            context: { stage: "Qualified", next_best_action: "Approve the draft." },
          },
        });
      }

      if (url.includes("/catalog")) {
        return jsonResponse({ entries: [] });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-13T20:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /replies/i }));
    expect(await screen.findByText("Taylor detail from API")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /jordan patel/i }));

    expect(await screen.findByText("API + fixture fallback (inbox)")).toBeInTheDocument();
    expect(screen.queryByText("Taylor detail from API")).not.toBeInTheDocument();
    expect(screen.getByText("Using fixture fallback for: inbox.")).toBeInTheDocument();
  });

  it("defaults to agents-first navigation and keeps operator views around each workspace", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 2,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 3,
          busy_channel_count: 2,
          recent_completed_count: 5,
          pending_lead_count: 6,
          booked_lead_count: 2,
          active_non_booker_enrollment_count: 4,
          due_manual_call_count: 1,
          replies_needing_review_count: 2,
          opportunity_count: 3,
          opportunity_stage_summaries: [
            { stage: "qualified_opportunity", count: 2 },
            { stage: "under_negotiation", count: 1 },
          ],
          outbound_probate_summary: {
            ready_lead_count: 6,
            active_campaign_count: 3,
            open_task_count: 2,
          },
          inbound_lease_option_summary: {
            pending_lead_count: 4,
            booked_lead_count: 2,
            active_non_booker_enrollment_count: 3,
            due_manual_call_count: 1,
            replies_needing_review_count: 1,
          },
          system_status: "healthy",
          updated_at: "2026-04-16T22:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({
          summary: { thread_count: 1, unread_count: 1, approval_required_count: 0 },
          threads: [
            {
              thread_id: "thread-1",
              channel: "sms",
              status: "open",
              unread_count: 1,
              last_message_preview: "Jordan preview",
              last_message_at: "2026-04-16T22:05:00+00:00",
              requires_approval: false,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Jordan Patel", phone: "+155****0001" },
            },
          ],
          selected_thread_id: "thread-1",
          selected_thread: {
            thread_id: "thread-1",
            channel: "sms",
            status: "open",
            unread_count: 1,
            requires_approval: false,
            related_run_id: null,
            related_approval_id: null,
            contact: { display_name: "Jordan Patel", phone: "+155****0001" },
            messages: [],
            context: { stage: "Qualified", next_best_action: "Review the thread." },
          },
        });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({
          due_count: 1,
          tasks: [
            {
              thread_id: "thread-1",
              lead_name: "Jordan Patel",
              channel: "sms",
              booking_status: "pending",
              sequence_status: "active",
              next_sequence_step: "manual_call_day_3",
              manual_call_due_at: "2026-04-16T22:30:00+00:00",
              recent_reply_preview: "Can we talk tonight?",
              reply_needs_review: true,
            },
          ],
        });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-13T20:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByRole("tab", { name: "Lead Machine" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /agents/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /lead machine \/ agents/i, level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /queue/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approvals/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /campaign state/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /approvals/i }));
    expect(screen.getByRole("heading", { name: /approvals queue/i, level: 3 })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Marketing" }));
    expect(screen.getByRole("heading", { name: /marketing \/ agents/i, level: 2 })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submissions/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approvals/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /runs/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /submissions/i }));
    expect(screen.getByText(/Work new lease-option submissions/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Pipeline" }));
    expect(screen.getByRole("heading", { name: /pipeline board/i, level: 2 })).toBeInTheDocument();
    expect(screen.getByText("Qualified Opportunity")).toBeInTheDocument();
    expect(screen.getByText("Under Negotiation")).toBeInTheDocument();
  });

  it("renders the settings workspace and governance surface through App", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 1,
          busy_channel_count: 1,
          recent_completed_count: 1,
          system_status: "watch",
          updated_at: "2026-04-16T22:00:00+00:00",
        });
      }

      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({
          summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 },
          threads: [],
          selected_thread_id: null,
          selected_thread: null,
        });
      }

      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [
            {
              id: "apr-1",
              command_type: "publish_campaign",
              status: "pending",
              created_at: "2026-04-16T22:00:00+00:00",
              payload_snapshot: { campaign_id: "camp-1" },
            },
          ],
          secrets_health: {
            active_revision_count: 2,
            healthy_revision_count: 1,
            attention_revision_count: 1,
            required_secret_count: 2,
            configured_secret_count: 1,
            missing_secret_count: 1,
            revisions: [
              {
                agent_id: "agt-1",
                agent_name: "Sierra Inbox Agent",
                agent_revision_id: "rev-1",
                business_id: "limitless",
                environment: "dev",
                status: "healthy",
                required_secret_count: 1,
                configured_secret_count: 1,
                missing_secret_count: 0,
                required_secrets: ["textgrid_auth_token"],
                configured_secrets: ["textgrid_auth_token"],
                missing_secrets: [],
              },
              {
                agent_id: "agt-2",
                agent_name: "Atlas Research Agent",
                agent_revision_id: "rev-2",
                business_id: "limitless",
                environment: "dev",
                status: "attention",
                required_secret_count: 1,
                configured_secret_count: 0,
                missing_secret_count: 1,
                required_secrets: ["provider_api_key"],
                configured_secrets: [],
                missing_secrets: ["provider_api_key"],
              },
            ],
          },
          recent_audit: [
            {
              id: "audit-1",
              event_type: "approval_granted",
              summary: "Governance review approved the current release posture.",
              created_at: "2026-04-16T22:05:00+00:00",
            },
          ],
          usage_summary: {
            total_count: 3,
            by_kind: { tool_call: 3 },
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T22:06:00+00:00",
          },
          recent_usage: [
            {
              id: "usage-1",
              kind: "tool_call",
              count: 3,
              source_kind: "hermes",
              created_at: "2026-04-16T22:06:00+00:00",
            },
          ],
        });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({
          assets: [
            {
              id: "asset-1",
              label: "SMTP relay",
              asset_type: "email",
              status: "attention",
              binding_reference: "staging",
              updated_at: "2026-04-16T22:01:00+00:00",
            },
          ],
        });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /settings/i }));

    expect(await screen.findByRole("heading", { name: "Settings / Governance", level: 2 })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /governance overview/i, level: 3 })).toBeInTheDocument();
    expect(screen.getByText("Operator trust surface")).toBeInTheDocument();
    expect(screen.getByText(/1\/2 configured/i)).toBeInTheDocument();
    expect(screen.getByText("Atlas Research Agent")).toBeInTheDocument();
    expect(screen.getByText(/Missing: provider_api_key/i)).toBeInTheDocument();
    expect(screen.getByText("Governance review approved the current release posture.")).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Usage summary" })).getByText(/tool_call: 3/i)).toBeInTheDocument();
  });

  it("keeps governance org-scoped when secondary business filters change in settings", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({
          approval_count: 1,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 1,
          busy_channel_count: 1,
          recent_completed_count: 1,
          system_status: "watch",
          updated_at: "2026-04-16T22:00:00+00:00",
        });
      }
      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({
          summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 },
          threads: [],
          selected_thread_id: null,
          selected_thread: null,
        });
      }
      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }
      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }
      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }
      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }
      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 2,
            healthy_revision_count: 1,
            attention_revision_count: 1,
            required_secret_count: 2,
            configured_secret_count: 1,
            missing_secret_count: 1,
            revisions: [
              {
                agent_id: "agt-1",
                agent_name: "Sierra Inbox Agent",
                agent_revision_id: "rev-1",
                business_id: "limitless",
                environment: "dev",
                status: "healthy",
                required_secret_count: 1,
                configured_secret_count: 1,
                missing_secret_count: 0,
                required_secrets: ["textgrid_auth_token"],
                configured_secrets: ["textgrid_auth_token"],
                missing_secrets: [],
              },
              {
                agent_id: "agt-2",
                agent_name: "Atlas Research Agent",
                agent_revision_id: "rev-2",
                business_id: "limitless",
                environment: "dev",
                status: "attention",
                required_secret_count: 1,
                configured_secret_count: 0,
                missing_secret_count: 1,
                required_secrets: ["provider_api_key"],
                configured_secrets: [],
                missing_secrets: ["provider_api_key"],
              },
            ],
          },
          recent_audit: [
            {
              id: "audit-1",
              event_type: "approval_granted",
              summary: "Governance review approved the current release posture.",
              created_at: "2026-04-16T22:05:00+00:00",
            },
          ],
          usage_summary: {
            total_count: 3,
            by_kind: { tool_call: 3 },
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-16T22:06:00+00:00",
          },
          recent_usage: [
            {
              id: "usage-1",
              kind: "tool_call",
              count: 3,
              source_kind: "hermes",
              created_at: "2026-04-16T22:06:00+00:00",
            },
          ],
        });
      }
      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /settings/i }));
    await screen.findByRole("heading", { name: "Settings / Governance", level: 2 });

    fireEvent.click(within(screen.getByRole("group", { name: "Business filter" })).getByRole("button", { name: "default" }));

    expect(await screen.findByText("Atlas Research Agent")).toBeInTheDocument();
    expect(screen.getByText(/governance stays org-scoped/i)).toBeInTheDocument();
    expect(within(screen.getByRole("region", { name: "Usage summary" })).getByText(/tool_call: 3/i)).toBeInTheDocument();
  });

  it("applies org scope first, keeps business and environment as secondary filters, and clears stale selections on scope changes", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const parsedUrl = new URL(url, "http://localhost");
      const headers = init?.headers as Record<string, string> | undefined;
      const orgId = headers?.["X-Ares-Org-Id"] ?? "org_internal";
      const businessId = parsedUrl.searchParams.get("business_id");
      const environment = parsedUrl.searchParams.get("environment");

      if (parsedUrl.pathname === "/organizations") {
        return jsonResponse({
          organizations: [
            { id: "org_alpha", name: "Alpha Org", slug: "alpha-org" },
            { id: "org_beta", name: "Beta Org", slug: "beta-org" },
          ],
        });
      }

      if (parsedUrl.pathname === "/mission-control/dashboard") {
        return jsonResponse({
          approval_count: orgId === "org_beta" ? 2 : orgId === "org_alpha" ? 1 : 0,
          active_run_count: 1,
          failed_run_count: 0,
          active_agent_count: 1,
          unread_conversation_count: 1,
          busy_channel_count: 1,
          recent_completed_count: 1,
          system_status: "healthy",
          updated_at: "2026-04-22T12:00:00+00:00",
        });
      }

      if (parsedUrl.pathname === "/mission-control/inbox") {
        if (orgId === "org_alpha") {
          return jsonResponse({
            summary: { thread_count: 1, unread_count: 1, approval_required_count: 0 },
            threads: [
              {
                thread_id: "thread-alpha",
                channel: "sms",
                status: "open",
                unread_count: 1,
                last_message_preview: "Alpha preview",
                last_message_at: "2026-04-22T12:01:00+00:00",
                requires_approval: false,
                related_run_id: null,
                related_approval_id: null,
                contact: { display_name: "Alpha Lead", phone: "+15551230001" },
                context: { org_id: "org_alpha" },
              },
            ],
            selected_thread_id: "thread-alpha",
            selected_thread: {
              thread_id: "thread-alpha",
              channel: "sms",
              status: "open",
              unread_count: 1,
              requires_approval: false,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Alpha Lead", phone: "+15551230001" },
              messages: [
                {
                  id: "msg-alpha",
                  direction: "inbound",
                  channel: "sms",
                  body: "Alpha detail from API",
                  created_at: "2026-04-22T12:01:00+00:00",
                  message_type: "received",
                },
              ],
              context: { stage: "Qualified", next_best_action: "Call alpha lead." },
            },
          });
        }

        if (orgId === "org_internal") {
          return jsonResponse({
            summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 },
            threads: [],
            selected_thread_id: null,
            selected_thread: null,
          });
        }

        return jsonResponse({
          summary: { thread_count: 1, unread_count: 1, approval_required_count: 0 },
          threads: [
            {
              thread_id: "thread-beta",
              channel: "email",
              status: "open",
              unread_count: 1,
              last_message_preview: "Beta preview",
              last_message_at: "2026-04-22T12:02:00+00:00",
              requires_approval: false,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Beta Lead", email: "beta@example.com" },
              context: { org_id: "org_beta" },
            },
          ],
          selected_thread_id: "thread-beta",
          selected_thread: {
            thread_id: "thread-beta",
            channel: "email",
            status: "open",
            unread_count: 1,
            requires_approval: false,
            related_run_id: null,
            related_approval_id: null,
            contact: { display_name: "Beta Lead", email: "beta@example.com" },
            messages: [
              {
                id: "msg-beta",
                direction: "inbound",
                channel: "email",
                body: "Beta detail from API",
                created_at: "2026-04-22T12:02:00+00:00",
                message_type: "received",
              },
            ],
            context: { stage: "New", next_best_action: "Review beta lead." },
          },
        });
      }

      if (parsedUrl.pathname === "/mission-control/tasks") {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (parsedUrl.pathname === "/mission-control/approvals") {
        return jsonResponse({ approvals: [] });
      }

      if (parsedUrl.pathname === "/mission-control/runs") {
        return jsonResponse({ runs: [] });
      }

      if (parsedUrl.pathname === "/mission-control/agents") {
        if (orgId === "org_alpha") {
          return jsonResponse({
            agents: [
              {
                id: "agt-alpha",
                business_id: "limitless",
                description: "Alpha scoped agent",
                name: "Alpha Agent",
                environment: "dev",
                active_revision_id: "rev-alpha",
                active_revision_state: "published",
                live_session_count: 1,
                delegated_work_count: 1,
              },
            ],
          });
        }

        if (orgId === "org_internal") {
          return jsonResponse({ agents: [] });
        }

        return jsonResponse({
          agents: [
            {
              id: "agt-beta",
              business_id: "otherco",
              description: "Beta scoped agent",
              name: "Beta Agent",
              environment: "prod",
              active_revision_id: "rev-beta",
              active_revision_state: "published",
              live_session_count: 1,
              delegated_work_count: 1,
            },
          ],
        });
      }

      if (parsedUrl.pathname === "/mission-control/settings/governance") {
        expect(parsedUrl.searchParams.get("business_id")).toBeNull();
        expect(parsedUrl.searchParams.get("environment")).toBeNull();
        return jsonResponse({
          org_id: orgId ?? "org_alpha",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-22T12:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (parsedUrl.pathname === "/mission-control/settings/assets") {
        expect(parsedUrl.searchParams.get("business_id")).toBeNull();
        expect(parsedUrl.searchParams.get("environment")).toBeNull();
        return jsonResponse({ assets: [] });
      }

      if (parsedUrl.pathname === "/agents/agt-alpha") {
        return jsonResponse({
          agent: {
            id: "agt-alpha",
            name: "Alpha Agent",
            slug: "alpha-agent",
            business_id: "limitless",
            environment: "dev",
            lifecycle_status: "active",
            active_revision_id: "rev-alpha",
            active_revision_state: "published",
          },
          revisions: [],
        });
      }

      if (parsedUrl.pathname === "/agents/agt-beta") {
        return jsonResponse({
          agent: {
            id: "agt-beta",
            name: "Beta Agent",
            slug: "beta-agent",
            business_id: "otherco",
            environment: "prod",
            lifecycle_status: "active",
            active_revision_id: "rev-beta",
            active_revision_state: "published",
          },
          revisions: [],
        });
      }

      if (parsedUrl.pathname === "/mission-control/turns") {
        return jsonResponse({ turns: [] });
      }

      if (parsedUrl.pathname.startsWith("/release-management/agents/")) {
        return jsonResponse({ events: [] });
      }

      if (parsedUrl.pathname === "/mission-control/audit" || parsedUrl.pathname === "/usage") {
        return jsonResponse({
          events: [],
          summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-22T12:00:00+00:00",
          },
        });
      }

      if (parsedUrl.pathname.startsWith("/mission-control/settings/secrets/revisions/")) {
        return jsonResponse({ bindings: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    await screen.findByRole("tab", { name: "Alpha Org" });
    await screen.findByRole("button", { name: /view lifecycle for alpha agent/i });
    fireEvent.click(within(screen.getByRole("group", { name: "Business filter" })).getByRole("button", { name: "limitless" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Environment filter" })).getByRole("button", { name: "dev" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/mission-control/agents?business_id=limitless&environment=dev"),
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-Ares-Org-Id": "org_alpha",
          }),
        }),
      );
    });

    fireEvent.click(await screen.findByRole("button", { name: /view lifecycle for alpha agent/i }));
    expect(await screen.findByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /replies/i }));
    expect(await screen.findByText("Alpha detail from API")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Beta Org" }));

    expect(await screen.findByText("Beta detail from API")).toBeInTheDocument();
    expect(screen.queryByText("Alpha detail from API")).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: /agents/i })[0]);
    expect(await screen.findByRole("button", { name: /view lifecycle for beta agent/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Agent lifecycle" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));
    expect(await screen.findByText("org_beta")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/mission-control/settings/governance"),
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-Ares-Org-Id": "org_beta",
          }),
        }),
      );
    });
  });

  it("hides prior-scope inbox detail while the next org reload is still in flight", async () => {
    const betaInbox = createDeferred<unknown>();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const parsedUrl = new URL(url, "http://localhost");
      const headers = init?.headers as Record<string, string> | undefined;
      const orgId = headers?.["X-Ares-Org-Id"] ?? "org_internal";

      if (parsedUrl.pathname === "/organizations") {
        return jsonResponse({
          organizations: [
            { id: "org_alpha", name: "Alpha Org", slug: "alpha-org" },
            { id: "org_beta", name: "Beta Org", slug: "beta-org" },
          ],
        });
      }

      if (parsedUrl.pathname === "/mission-control/dashboard") {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 0,
          unread_conversation_count: 1,
          busy_channel_count: 0,
          recent_completed_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-22T12:00:00+00:00",
        });
      }

      if (parsedUrl.pathname === "/mission-control/inbox") {
        if (orgId === "org_alpha") {
          return jsonResponse({
            summary: { thread_count: 1, unread_count: 1, approval_required_count: 0 },
            threads: [
              {
                thread_id: "thread-alpha",
                channel: "sms",
                status: "open",
                unread_count: 1,
                last_message_preview: "Alpha preview",
                last_message_at: "2026-04-22T12:01:00+00:00",
                requires_approval: false,
                related_run_id: null,
                related_approval_id: null,
                contact: { display_name: "Alpha Lead", phone: "+15551230001" },
              },
            ],
            selected_thread_id: "thread-alpha",
            selected_thread: {
              thread_id: "thread-alpha",
              channel: "sms",
              status: "open",
              unread_count: 1,
              requires_approval: false,
              related_run_id: null,
              related_approval_id: null,
              contact: { display_name: "Alpha Lead", phone: "+15551230001" },
              messages: [
                {
                  id: "msg-alpha",
                  direction: "inbound",
                  channel: "sms",
                  body: "Alpha detail from API",
                  created_at: "2026-04-22T12:01:00+00:00",
                  message_type: "received",
                },
              ],
              context: { stage: "Qualified", next_best_action: "Call alpha lead." },
            },
          });
        }

        if (orgId === "org_beta") {
          return betaInbox.promise.then((payload) => jsonResponse(payload));
        }

        return jsonResponse({
          summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 },
          threads: [],
          selected_thread_id: null,
          selected_thread: null,
        });
      }

      if (parsedUrl.pathname === "/mission-control/tasks") {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (parsedUrl.pathname === "/mission-control/approvals") {
        return jsonResponse({ approvals: [] });
      }

      if (parsedUrl.pathname === "/mission-control/runs") {
        return jsonResponse({ runs: [] });
      }

      if (parsedUrl.pathname === "/mission-control/agents") {
        return jsonResponse({ agents: [] });
      }

      if (parsedUrl.pathname === "/mission-control/settings/governance") {
        return jsonResponse({
          org_id: orgId,
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-22T12:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (parsedUrl.pathname === "/mission-control/settings/assets") {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /replies/i }));
    expect(await screen.findByText("Alpha detail from API")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Beta Org" }));

    expect(screen.queryByText("Alpha detail from API")).not.toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Loading conversations" })).toBeInTheDocument();
    expect(screen.getByText(/prior-scope inbox content stays hidden until the reload settles/i)).toBeInTheDocument();

    betaInbox.resolve({
        summary: { thread_count: 1, unread_count: 1, approval_required_count: 0 },
        threads: [
          {
            thread_id: "thread-beta",
            channel: "email",
            status: "open",
            unread_count: 1,
            last_message_preview: "Beta preview",
            last_message_at: "2026-04-22T12:02:00+00:00",
            requires_approval: false,
            related_run_id: null,
            related_approval_id: null,
            contact: { display_name: "Beta Lead", email: "beta@example.com" },
          },
        ],
        selected_thread_id: "thread-beta",
        selected_thread: {
          thread_id: "thread-beta",
          channel: "email",
          status: "open",
          unread_count: 1,
          requires_approval: false,
          related_run_id: null,
          related_approval_id: null,
          contact: { display_name: "Beta Lead", email: "beta@example.com" },
          messages: [
            {
              id: "msg-beta",
              direction: "inbound",
              channel: "email",
              body: "Beta detail from API",
              created_at: "2026-04-22T12:02:00+00:00",
              message_type: "received",
            },
          ],
          context: { stage: "New", next_best_action: "Review beta lead." },
        },
      });

    expect(await screen.findByText("Beta detail from API")).toBeInTheDocument();
  });

  it("keeps fallback agents scoped to the selected business and environment", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const parsedUrl = new URL(url, "http://localhost");

      if (parsedUrl.pathname === "/organizations") {
        return jsonResponse({
          organizations: [{ id: "org_internal", name: "Internal Org", slug: "internal-org" }],
        });
      }

      if (parsedUrl.pathname === "/mission-control/dashboard") {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 0,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-22T12:00:00+00:00",
        });
      }

      if (parsedUrl.pathname === "/mission-control/inbox") {
        return jsonResponse({
          summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 },
          threads: [],
          selected_thread_id: null,
          selected_thread: null,
        });
      }

      if (parsedUrl.pathname === "/mission-control/tasks") {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (parsedUrl.pathname === "/mission-control/approvals") {
        return jsonResponse({ approvals: [] });
      }

      if (parsedUrl.pathname === "/mission-control/runs") {
        return jsonResponse({ runs: [] });
      }

      if (parsedUrl.pathname === "/mission-control/agents") {
        throw new Error("agents unavailable");
      }

      if (parsedUrl.pathname === "/mission-control/settings/governance") {
        expect(parsedUrl.searchParams.get("business_id")).toBeNull();
        expect(parsedUrl.searchParams.get("environment")).toBeNull();
        return jsonResponse({
          org_id: (init?.headers as Record<string, string> | undefined)?.["X-Ares-Org-Id"] ?? "org_internal",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-22T12:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (parsedUrl.pathname === "/mission-control/settings/assets") {
        expect(parsedUrl.searchParams.get("business_id")).toBeNull();
        expect(parsedUrl.searchParams.get("environment")).toBeNull();
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("Fixture fallback / no Supabase wiring")).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole("group", { name: "Business filter" })).getByRole("button", { name: "limitless" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Environment filter" })).getByRole("button", { name: "production" }));

    await waitFor(() => {
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("/mission-control/agents?business_id=limitless&environment=production"),
          expect.objectContaining({
            headers: expect.objectContaining({
              "X-Ares-Org-Id": "org_internal",
            }),
          }),
        );
    });

    expect((await screen.findAllByText("Sierra Inbox Agent")).length).toBeGreaterThan(0);
    expect(screen.queryByText("Atlas Research Agent")).not.toBeInTheDocument();
    expect(screen.getByText("1 agents in scope")).toBeInTheDocument();
  });

  it("neutralizes org-only fixture fallback instead of relabeling internal fixtures under another org", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const parsedUrl = new URL(url, "http://localhost");
      const headers = init?.headers as Record<string, string> | undefined;
      const orgId = headers?.["X-Ares-Org-Id"] ?? "org_internal";

      if (parsedUrl.pathname === "/organizations") {
        return jsonResponse({
          organizations: [
            { id: "org_internal", name: "Internal Org", slug: "internal-org" },
            { id: "org_beta", name: "Beta Org", slug: "beta-org" },
          ],
        });
      }

      if (
        orgId === "org_beta" &&
        [
          "/mission-control/dashboard",
          "/mission-control/inbox",
          "/mission-control/tasks",
          "/mission-control/approvals",
          "/mission-control/runs",
          "/mission-control/settings/governance",
          "/mission-control/settings/assets",
        ].includes(parsedUrl.pathname)
      ) {
        throw new Error("beta fallback");
      }

      if (parsedUrl.pathname === "/mission-control/dashboard") {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 0,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-22T12:00:00+00:00",
        });
      }

      if (parsedUrl.pathname === "/mission-control/inbox") {
        return jsonResponse({
          summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 },
          threads: [],
          selected_thread_id: null,
          selected_thread: null,
        });
      }

      if (parsedUrl.pathname === "/mission-control/tasks") {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (parsedUrl.pathname === "/mission-control/approvals") {
        return jsonResponse({ approvals: [] });
      }

      if (parsedUrl.pathname === "/mission-control/runs") {
        return jsonResponse({ runs: [] });
      }

      if (parsedUrl.pathname === "/mission-control/agents") {
        throw new Error("agents unavailable");
      }

      if (parsedUrl.pathname === "/mission-control/settings/governance") {
        return jsonResponse({
          org_id: orgId,
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-22T12:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (parsedUrl.pathname === "/mission-control/settings/assets") {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("tab", { name: "Beta Org" }));

    expect(await screen.findByText("0 agents in scope")).toBeInTheDocument();
    expect(screen.queryByText("Sierra Inbox Agent")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /replies/i }));

    expect(await screen.findByRole("heading", { name: "No conversations in scope" })).toBeInTheDocument();
    expect(screen.getByText("org_beta")).toBeInTheDocument();
    expect(screen.queryByText("Taylor Brooks")).not.toBeInTheDocument();
    expect(screen.queryByText("Taylor detail from API")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /settings/i }));

    expect(await screen.findByText("0 bindings")).toBeInTheDocument();
    expect(screen.getByText("org_beta")).toBeInTheDocument();
    expect(screen.queryByText("Twilio voice line")).not.toBeInTheDocument();
  });

  it("refetches settings assets when business and environment filters change inside the same org", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const parsedUrl = new URL(url, "http://localhost");
      const headers = init?.headers as Record<string, string> | undefined;
      const orgId = headers?.["X-Ares-Org-Id"] ?? "org_internal";

      if (parsedUrl.pathname === "/organizations") {
        return jsonResponse({
          organizations: [{ id: "org_internal", name: "Internal Org", slug: "internal-org" }],
        });
      }

      if (parsedUrl.pathname === "/mission-control/dashboard") {
        return jsonResponse({
          approval_count: 0,
          active_run_count: 0,
          failed_run_count: 0,
          active_agent_count: 2,
          unread_conversation_count: 0,
          busy_channel_count: 0,
          recent_completed_count: 0,
          system_status: "healthy",
          updated_at: "2026-04-22T12:00:00+00:00",
        });
      }

      if (parsedUrl.pathname === "/mission-control/inbox") {
        return jsonResponse({
          summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 },
          threads: [],
          selected_thread_id: null,
          selected_thread: null,
        });
      }

      if (parsedUrl.pathname === "/mission-control/tasks") {
        return jsonResponse({ due_count: 0, tasks: [] });
      }

      if (parsedUrl.pathname === "/mission-control/approvals") {
        return jsonResponse({ approvals: [] });
      }

      if (parsedUrl.pathname === "/mission-control/runs") {
        return jsonResponse({ runs: [] });
      }

      if (parsedUrl.pathname === "/mission-control/agents") {
        return jsonResponse({
          agents: [
            {
              id: "agt-prod",
              name: "Prod Agent",
              slug: "prod-agent",
              description: "Production agent",
              business_id: "limitless",
              environment: "production",
              lifecycle_status: "active",
              active_revision_id: "rev-prod",
              active_revision_state: "published",
              live_session_count: 1,
              delegated_work_count: 0,
            },
            {
              id: "agt-dev",
              name: "Dev Agent",
              slug: "dev-agent",
              description: "Development agent",
              business_id: "limitless",
              environment: "dev",
              lifecycle_status: "active",
              active_revision_id: "rev-dev",
              active_revision_state: "published",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }

      if (parsedUrl.pathname === "/mission-control/settings/governance") {
        expect(parsedUrl.searchParams.get("business_id")).toBeNull();
        expect(parsedUrl.searchParams.get("environment")).toBeNull();
        return jsonResponse({
          org_id: orgId,
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: {
            total_count: 0,
            by_kind: {},
            by_source_kind: [],
            by_agent: [],
            updated_at: "2026-04-22T12:00:00+00:00",
          },
          recent_usage: [],
        });
      }

      if (parsedUrl.pathname === "/mission-control/settings/assets") {
        const businessId = parsedUrl.searchParams.get("business_id");
        const environment = parsedUrl.searchParams.get("environment");
        const name =
          businessId === "limitless" && environment === "production"
            ? "Limitless production asset"
            : businessId === "limitless" && environment === "dev"
              ? "Limitless dev asset"
              : "Shared asset";

        return jsonResponse({
          assets: [
            {
              id: `${businessId ?? "all"}-${environment ?? "all"}`,
              name,
              category: "integration",
              binding_target: "settings",
              status: "healthy",
              updated_at: "2026-04-22T12:00:00+00:00",
            },
          ],
        });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /settings/i }));

    expect(await screen.findByText("Shared asset")).toBeInTheDocument();

    fireEvent.click(within(screen.getByRole("group", { name: "Business filter" })).getByRole("button", { name: "limitless" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Environment filter" })).getByRole("button", { name: "production" }));

    expect(await screen.findByText("Limitless production asset")).toBeInTheDocument();
    expect(screen.queryByText("Shared asset")).not.toBeInTheDocument();

    fireEvent.click(within(screen.getByRole("group", { name: "Environment filter" })).getByRole("button", { name: "dev" }));

    expect(await screen.findByText("Limitless dev asset")).toBeInTheDocument();
    expect(screen.queryByText("Limitless production asset")).not.toBeInTheDocument();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/mission-control/settings/assets?business_id=limitless&environment=dev"),
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-Ares-Org-Id": "org_internal",
          }),
        }),
      );
    });
  });

  it("neutralizes fixture-backed catalog entries when the operator switches away from the internal org", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.endsWith("/organizations")) {
        return jsonResponse({
          organizations: [
            { id: "org_internal", name: "Internal", is_internal: true, created_at: "2026-04-23T00:00:00+00:00", updated_at: "2026-04-23T00:00:00+00:00" },
            { id: "org_alpha", name: "Acme Alpha", is_internal: false, created_at: "2026-04-23T00:00:00+00:00", updated_at: "2026-04-23T00:00:00+00:00" },
          ],
        });
      }
      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({ approval_count: 0, active_run_count: 0, failed_run_count: 0, active_agent_count: 0, unread_conversation_count: 0, busy_channel_count: 0, recent_completed_count: 0, system_status: "healthy", updated_at: "2026-04-23T00:00:00+00:00" });
      }
      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }
      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }
      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }
      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }
      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_internal",
          pending_approvals: [],
          secrets_health: {
            active_revision_count: 0,
            healthy_revision_count: 0,
            attention_revision_count: 0,
            required_secret_count: 0,
            configured_secret_count: 0,
            missing_secret_count: 0,
            revisions: [],
          },
          recent_audit: [],
          usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-23T00:00:00+00:00" },
          recent_usage: [],
        });
      }
      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }
      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }
      if (url.includes("/catalog")) {
        throw new Error("catalog unavailable");
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /catalog/i }));

    expect(await screen.findByText("Sierra Inbox Agent")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /install sierra inbox agent/i })).toBeDisabled();

    fireEvent.click(screen.getByRole("tab", { name: /acme alpha/i }));
    expect(await screen.findByText(/no catalog entries are available for the current org scope/i)).toBeInTheDocument();
    expect(screen.queryByText("Sierra Inbox Agent")).not.toBeInTheDocument();
  });

  it("renders the catalog UI and installs a catalog entry through the Mission Control shell", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.endsWith("/organizations")) {
        return jsonResponse({ organizations: [{ id: "org_internal", name: "Internal", slug: "internal", is_internal: true }] });
      }
      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({ approval_count: 0, active_run_count: 0, failed_run_count: 0, active_agent_count: 0, unread_conversation_count: 0, busy_channel_count: 0, recent_completed_count: 0, system_status: "healthy", updated_at: "2026-04-23T03:00:00+00:00" });
      }
      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }
      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }
      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }
      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }
      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }
      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_internal",
          pending_approvals: [],
          secrets_health: { active_revision_count: 0, healthy_revision_count: 0, attention_revision_count: 0, required_secret_count: 0, configured_secret_count: 0, missing_secret_count: 0, revisions: [] },
          recent_audit: [],
          usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-23T03:00:00+00:00" },
          recent_usage: [],
        });
      }
      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }
      if (url.includes("/catalog")) {
        return jsonResponse({
          entries: [{
            id: "cat-1",
            org_id: "org_internal",
            agent_id: "agt-source-1",
            agent_revision_id: "rev-source-1",
            slug: "seller-ops",
            name: "Seller Ops",
            summary: "Installable seller ops agent",
            description: "Operator package for seller follow-up.",
            visibility: "private_catalog",
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
          }],
        });
      }
      if (url.endsWith("/agent-installs") && init?.method === "POST") {
        return jsonResponse({
          install: {
            id: "ins-1",
            org_id: "org_internal",
            catalog_entry_id: "cat-1",
            source_agent_id: "agt-source-1",
            source_agent_revision_id: "rev-source-1",
            installed_agent_id: "agt-installed-1",
            installed_agent_revision_id: "rev-installed-1",
            business_id: "default",
            environment: "dev",
            created_at: "2026-04-23T03:05:00+00:00",
            updated_at: "2026-04-23T03:05:00+00:00",
          },
          agent: {
            id: "agt-installed-1",
            org_id: "org_internal",
            business_id: "default",
            environment: "dev",
            name: "Seller Ops",
            slug: "seller-ops",
            description: "Operator package for seller follow-up.",
            visibility: "private_catalog",
            lifecycle_status: "draft",
            packaging_metadata: { catalog_entry_id: "cat-1", source_agent_id: "agt-source-1", source_agent_revision_id: "rev-source-1" },
            active_revision_id: null,
            created_at: "2026-04-23T03:05:00+00:00",
            updated_at: "2026-04-23T03:05:00+00:00",
          },
          revisions: [{
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
          }],
        });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /catalog/i }));
    expect(screen.getAllByRole("heading", { name: /internal catalog/i }).length).toBeGreaterThan(0);
    expect(screen.getByText(/resend_api_key/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /install seller ops/i }));
    expect(await screen.findByText(/installed seller ops as seller-ops in default\/dev\./i)).toBeInTheDocument();
  });

  it("reports when a catalog install succeeds outside the currently viewed filters", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;

      if (url.endsWith("/organizations")) {
        return jsonResponse({ organizations: [{ id: "org_internal", name: "Internal", slug: "internal", is_internal: true }] });
      }
      if (url.includes("/mission-control/dashboard")) {
        return jsonResponse({ approval_count: 0, active_run_count: 0, failed_run_count: 0, active_agent_count: 0, unread_conversation_count: 0, busy_channel_count: 0, recent_completed_count: 0, system_status: "healthy", updated_at: "2026-04-23T03:00:00+00:00" });
      }
      if (url.includes("/mission-control/inbox")) {
        return jsonResponse({ summary: { thread_count: 0, unread_count: 0, approval_required_count: 0 }, threads: [], selected_thread_id: null });
      }
      if (url.includes("/mission-control/tasks")) {
        return jsonResponse({ due_count: 0, tasks: [] });
      }
      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }
      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }
      if (url.includes("/mission-control/agents")) {
        return jsonResponse({
          agents: [
            {
              id: "agt-filtered-1",
              name: "Filtered Agent",
              business_id: "default",
              environment: "dev",
              active_revision_id: "rev-filtered-1",
              active_revision_state: "draft",
              live_session_count: 0,
              delegated_work_count: 0,
            },
          ],
        });
      }
      if (url.includes("/mission-control/settings/governance")) {
        return jsonResponse({
          org_id: "org_internal",
          pending_approvals: [],
          secrets_health: { active_revision_count: 0, healthy_revision_count: 0, attention_revision_count: 0, required_secret_count: 0, configured_secret_count: 0, missing_secret_count: 0, revisions: [] },
          recent_audit: [],
          usage_summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "2026-04-23T03:00:00+00:00" },
          recent_usage: [],
        });
      }
      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }
      if (url.includes("/catalog")) {
        return jsonResponse({
          entries: [{
            id: "cat-1",
            org_id: "org_internal",
            agent_id: "agt-source-1",
            agent_revision_id: "rev-source-1",
            slug: "seller-ops",
            name: "Seller Ops",
            summary: "Installable seller ops agent",
            description: "Operator package for seller follow-up.",
            visibility: "private_catalog",
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
          }],
        });
      }
      if (url.endsWith("/agent-installs") && init?.method === "POST") {
        return jsonResponse({
          install: {
            id: "ins-2",
            org_id: "org_internal",
            catalog_entry_id: "cat-1",
            source_agent_id: "agt-source-1",
            source_agent_revision_id: "rev-source-1",
            installed_agent_id: "agt-installed-2",
            installed_agent_revision_id: "rev-installed-2",
            business_id: "otherbiz",
            environment: "stage",
            created_at: "2026-04-23T03:06:00+00:00",
            updated_at: "2026-04-23T03:06:00+00:00",
          },
          agent: {
            id: "agt-installed-2",
            org_id: "org_internal",
            business_id: "otherbiz",
            environment: "stage",
            name: "Seller Ops",
            slug: "seller-ops",
            description: "Operator package for seller follow-up.",
            visibility: "private_catalog",
            lifecycle_status: "draft",
            packaging_metadata: { catalog_entry_id: "cat-1", source_agent_id: "agt-source-1", source_agent_revision_id: "rev-source-1" },
            active_revision_id: null,
            created_at: "2026-04-23T03:06:00+00:00",
            updated_at: "2026-04-23T03:06:00+00:00",
          },
          revisions: [],
        });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /catalog/i }));
    fireEvent.click(within(screen.getByRole("group", { name: "Business filter" })).getByRole("button", { name: "default" }));
    fireEvent.click(within(screen.getByRole("group", { name: "Environment filter" })).getByRole("button", { name: "dev" }));
    expect(await screen.findByText("Seller Ops")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/target business id/i), { target: { value: "otherbiz" } });
    fireEvent.change(screen.getByLabelText(/target environment/i), { target: { value: "stage" } });
    fireEvent.click(screen.getByRole("button", { name: /install seller ops/i }));

    expect(await screen.findByText(/installed seller ops as seller-ops in otherbiz\/stage\./i)).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/outside the current filtered view/i);
  });
});
