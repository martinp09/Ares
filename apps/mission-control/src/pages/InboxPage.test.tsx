import { render, screen, within } from "@testing-library/react";

import { InboxPage } from "./InboxPage";
import type { InboxData } from "../lib/api";
import { missionControlFixtures } from "../lib/fixtures";

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

    expect(screen.getByText("Inbox scopes")).toBeInTheDocument();
    expect(within(screen.getByLabelText("Conversation list")).getByText("0 threads")).toBeInTheDocument();
    expect(screen.getByLabelText("inbox-thread-placeholder")).toBeInTheDocument();
    expect(within(screen.getByLabelText("inbox-thread-placeholder")).getByText("Select a thread to inspect context.")).toBeInTheDocument();
  });

  it("renders the four-panel CRM conversation workspace with context actions", () => {
    render(
      <InboxPage
        data={missionControlFixtures.inbox}
        selectedConversationId={missionControlFixtures.inbox.selectedConversationId}
        {...handlers}
      />,
    );

    expect(screen.getByLabelText("Inbox scopes")).toHaveTextContent("My Inbox");
    expect(screen.getByLabelText("Conversation list")).toHaveTextContent("Taylor Brooks");
    expect(screen.getByLabelText("Conversation timeline")).toHaveTextContent("Can you send over the numbers for Oak Street?");
    expect(screen.getByLabelText("Conversation context")).toHaveTextContent("Linked opportunity");
    expect(screen.getByLabelText("Conversation context")).toHaveTextContent("Agent actions");
    const composerModes = screen.getByLabelText("Composer modes");
    expect(within(composerModes).getByText("SMS")).toBeInTheDocument();
    expect(within(composerModes).getByText("Email")).toBeInTheDocument();
    expect(within(composerModes).getByText("Note")).toBeInTheDocument();
    expect(within(composerModes).getByText("Task")).toBeInTheDocument();
  });
});
