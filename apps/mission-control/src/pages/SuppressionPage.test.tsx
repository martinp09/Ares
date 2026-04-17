import { render, screen, within } from "@testing-library/react";

import { SuppressionPage } from "./SuppressionPage";
import type { DashboardSummaryData, InboxData, RunSummary, TasksData } from "../lib/api";

const dashboardFixture: DashboardSummaryData = {
  approvalCount: 1,
  activeRunCount: 2,
  failedRunCount: 1,
  activeAgentCount: 1,
  unreadConversationCount: 4,
  busyChannelCount: 2,
  recentCompletedCount: 8,
  repliesNeedingReviewCount: 3,
  systemStatus: "watch",
  updatedAt: "Updated moments ago",
};

const inboxFixture: InboxData = {
  selectedConversationId: "thread-1",
  conversations: [
    {
      id: "thread-1",
      leadName: "Taylor Brooks",
      channel: "sms",
      stage: "Warm lead",
      owner: "Sierra",
      unreadCount: 2,
      lastMessage: "Taylor reply needs review",
      lastActivityAt: "2m ago",
      sequenceState: "Manual review",
      replyNeedsReview: true,
    },
    {
      id: "thread-2",
      leadName: "Jordan Patel",
      channel: "email",
      stage: "Suppression watch",
      owner: "Atlas",
      unreadCount: 0,
      lastMessage: "Jordan unsubscribed yesterday",
      lastActivityAt: "18m ago",
      sequenceState: "Suppressed",
    },
  ],
  threadsById: {},
};

const runsFixture: RunSummary[] = [
  {
    id: "run-1",
    commandType: "run_market_research",
    status: "failed",
    businessId: "limitless",
    environment: "dev",
    updatedAt: "1m ago",
    parentRunId: null,
    triggerRunId: null,
    summary: "Provider timeout before the follow-up could continue.",
  },
];

const tasksFixture: TasksData = {
  dueCount: 1,
  tasks: [
    {
      threadId: "thread-1",
      leadName: "Taylor Brooks",
      channel: "sms",
      bookingStatus: "pending",
      sequenceStatus: "paused",
      nextSequenceStep: "manual_call_followup",
      manualCallDueAt: "2026-04-16T22:30:00+00:00",
      recentReplyPreview: "Taylor reply needs review",
      replyNeedsReview: true,
    },
  ],
};

describe("SuppressionPage", () => {
  it("renders suppression counts and exception queues", () => {
    render(
      <SuppressionPage dashboard={dashboardFixture} inbox={inboxFixture} runs={runsFixture} tasks={tasksFixture} />,
    );

    expect(screen.getByText("Suppression / Exceptions")).toBeInTheDocument();
    expect(screen.getByText("3 reviews")).toBeInTheDocument();
    expect(screen.getByText("Replies needing review")).toBeInTheDocument();
    expect(screen.getByText("Failed runs")).toBeInTheDocument();

    const reviewQueueHeading = screen.getByRole("heading", { name: "Review queue" });
    const reviewQueue = reviewQueueHeading.closest("section") ?? reviewQueueHeading.parentElement;
    expect(reviewQueue).toBeTruthy();
    expect(within(reviewQueue as HTMLElement).getByText("Taylor reply needs review")).toBeInTheDocument();
    expect(within(reviewQueue as HTMLElement).getByText("Jordan Patel")).toBeInTheDocument();

    const exceptionsHeading = screen.getByRole("heading", { name: "Exceptions" });
    const exceptions = exceptionsHeading.closest("section") ?? exceptionsHeading.parentElement;
    expect(exceptions).toBeTruthy();
    expect(within(exceptions as HTMLElement).getByText("Provider timeout before the follow-up could continue.")).toBeInTheDocument();
    expect(within(exceptions as HTMLElement).getByText("manual_call_followup")).toBeInTheDocument();
  });
});
