import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { queryClient } from "./lib/queryClient";

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
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
        return jsonResponse({ agents: [] });
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
          selected_thread_id: "thread-1",
          selected_thread: {
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
          },
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
        return jsonResponse({ agents: [] });
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

  it("switches between lead machine, marketing, and pipeline workspaces", async () => {
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
        return jsonResponse({ agents: [] });
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
    expect(screen.getByRole("button", { name: /queue/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Marketing" }));
    expect(screen.getByRole("button", { name: /submissions/i })).toBeInTheDocument();
    expect(screen.getByText(/Lease-option submissions, booked vs pending/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Pipeline" }));
    expect(screen.getByRole("heading", { name: /pipeline board/i, level: 2 })).toBeInTheDocument();
    expect(screen.getByText("Qualified Opportunity")).toBeInTheDocument();
    expect(screen.getByText("Under Negotiation")).toBeInTheDocument();
  });

  it("renders governance data in the settings surface", async () => {
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
        return jsonResponse({ agents: [] });
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
              event_type: "secret_accessed",
              summary: "Operator viewed secret posture.",
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

    expect(await screen.findByRole("heading", { name: /governance overview/i, level: 3 })).toBeInTheDocument();
    expect(screen.getByText(/1\/2 configured/i)).toBeInTheDocument();
    expect(screen.getByText("Atlas Research Agent")).toBeInTheDocument();
    expect(screen.getByText(/Missing: provider_api_key/i)).toBeInTheDocument();
    expect(screen.getByText("Operator viewed secret posture.")).toBeInTheDocument();
    expect(screen.getByText(/tool_call: 3/i)).toBeInTheDocument();
  });
});

