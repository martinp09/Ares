import { render, screen } from "@testing-library/react";

import { InboxPage } from "./InboxPage";
import type { InboxData } from "../lib/api";

const handlers = {
  onSelectConversation: () => undefined,
  onSendSmsTest: async () => ({ status: "sent", providerMessageId: "sms-1", errorMessage: null }),
  onSendEmailTest: async () => ({ status: "sent", providerMessageId: "email-1", errorMessage: null }),
};

describe("InboxPage", () => {
  it("renders a neutral placeholder when no thread is available", () => {
    const data: InboxData = {
      selectedConversationId: "",
      conversations: [],
      threadsById: {},
    };

    render(<InboxPage data={data} selectedConversationId="" {...handlers} />);

    expect(screen.getByText("Conversation Desk")).toBeInTheDocument();
    expect(screen.getByText("0 threads")).toBeInTheDocument();
    expect(screen.getByLabelText("inbox-thread-placeholder")).toBeInTheDocument();
    expect(screen.getByText("Select a thread to inspect context.")).toBeInTheDocument();
  });

  it("renders SMS-agent decision review details with disabled placeholder actions", () => {
    const data: InboxData = {
      selectedConversationId: "thread-sms-agent-1",
      conversations: [
        {
          id: "thread-sms-agent-1",
          leadName: "Interested Owner",
          channel: "sms",
          stage: "Review",
          owner: "TextGrid",
          unreadCount: 1,
          lastMessage: "Yes, I am interested.",
          lastActivityAt: "2026-05-16T10:01:00Z",
          sequenceState: "active",
        },
      ],
      threadsById: {
        "thread-sms-agent-1": {
          conversationId: "thread-sms-agent-1",
          leadName: "Interested Owner",
          company: "+15550001000",
          phone: "+15550001000",
          stage: "Review",
          nextBestAction: "Review SMS-agent draft.",
          tags: ["sms", "open"],
          notes: [],
          smsAgent: {
            intent: "interested",
            sourceLane: "outbound_probate",
            action: "draft_only",
            suggestedBody: "Thanks. I will have a human review and follow up.",
          },
          messages: [
            {
              id: "message-1",
              author: "Interested Owner",
              direction: "inbound",
              body: "Yes, I am interested.",
              timestamp: "2026-05-16T10:01:00Z",
              status: "message",
            },
          ],
        },
      },
    };

    render(<InboxPage data={data} selectedConversationId="thread-sms-agent-1" {...handlers} />);

    expect(screen.getByText("interested")).toBeInTheDocument();
    expect(screen.getByText("outbound_probate")).toBeInTheDocument();
    expect(screen.getByText(/human review and follow up/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Appointment Setter" })).toBeInTheDocument();
    expect(screen.getByText("Qualification score")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Take over thread" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Approve reply" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Request slots" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send to nurture" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Disqualify" })).toBeDisabled();
  });
});
