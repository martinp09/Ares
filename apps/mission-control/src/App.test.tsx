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

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({ agents: [] });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /inbox/i }));

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

      if (url.includes("/mission-control/approvals")) {
        return jsonResponse({ approvals: [] });
      }

      if (url.includes("/mission-control/runs")) {
        return jsonResponse({ runs: [] });
      }

      if (url.includes("/mission-control/agents")) {
        return jsonResponse({ agents: [] });
      }

      if (url.includes("/mission-control/settings/assets")) {
        return jsonResponse({ assets: [] });
      }

      throw new Error(`Unexpected fetch URL: ${url}`);
    });

    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /inbox/i }));
    expect(await screen.findByText("Taylor detail from API")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /jordan patel/i }));

    expect(await screen.findByText("API + fixture fallback (inbox)")).toBeInTheDocument();
    expect(screen.queryByText("Taylor detail from API")).not.toBeInTheDocument();
    expect(screen.getByText("Using fixture fallback for: inbox.")).toBeInTheDocument();
  });
});
