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

    expect(screen.getByText("Inbox queue")).toBeInTheDocument();
    expect(screen.getByText("0 threads")).toBeInTheDocument();
    expect(screen.getByLabelText("inbox-thread-placeholder")).toBeInTheDocument();
    expect(screen.getByText("Select a thread to inspect context.")).toBeInTheDocument();
  });
});
