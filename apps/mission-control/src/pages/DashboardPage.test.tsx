import { render, screen, within } from "@testing-library/react";

import { DashboardPage } from "./DashboardPage";
import type { DashboardSummaryData } from "../lib/api";

const dashboardFixture: DashboardSummaryData = {
  approvalCount: 11,
  activeRunCount: 7,
  failedRunCount: 2,
  activeAgentCount: 5,
  unreadConversationCount: 14,
  busyChannelCount: 3,
  recentCompletedCount: 19,
  outboundProbateSummary: {
    activeCampaignCount: 2,
    readyLeadCount: 8,
    activeLeadCount: 21,
    interestedLeadCount: 4,
    suppressedLeadCount: 3,
    openTaskCount: 6,
  },
  inboundLeaseOptionSummary: {
    pendingLeadCount: 5,
    bookedLeadCount: 2,
    activeNonBookerEnrollmentCount: 7,
    dueManualCallCount: 4,
    repliesNeedingReviewCount: 9,
  },
  opportunityPipelineSummary: {
    totalOpportunityCount: 6,
    laneStageSummaries: [],
  },
  recordInventorySummary: {
    totalCount: 128,
    activeCount: 84,
    suppressedCount: 11,
    needsSkipTraceCount: 19,
    noPhoneCount: 19,
    promotedCount: 17,
    openTaskCount: 14,
  },
  systemStatus: "watch",
  updatedAt: "Updated moments ago",
};

function expectCardValue(region: HTMLElement, label: string, value: string) {
  const labelElement = within(region).getByText(label);
  const card = labelElement.closest("article");

  expect(card).not.toBeNull();
  expect(within(card as HTMLElement).getByText(value)).toBeInTheDocument();
}

describe("DashboardPage", () => {
  it("renders a human-readable real-estate action desk instead of backend counters", () => {
    render(<DashboardPage data={dashboardFixture} />);

    expect(screen.getByText("What should Martin work first?")).toBeInTheDocument();
    expect(screen.getByText(/Backend plumbing stays out of the primary dashboard/i)).toBeInTheDocument();
    expect(screen.getByText("No-send locked")).toBeInTheDocument();

    const actionDesk = screen.getByLabelText(/real estate action desk/i);
    expectCardValue(actionDesk, "Hit list today", "13");
    expectCardValue(actionDesk, "Replies to review", "14");
    expectCardValue(actionDesk, "Needs approval", "11");
    expectCardValue(actionDesk, "Research / skiptrace", "33");
    expectCardValue(actionDesk, "Deals in motion", "6");
    expectCardValue(actionDesk, "Blocked / suppressions", "13");

    expect(screen.queryByText("Active runs")).not.toBeInTheDocument();
    expect(screen.queryByText("Live agents")).not.toBeInTheDocument();
    expect(screen.queryByText("Provider failures")).not.toBeInTheDocument();
    expect(screen.queryByText("System status")).not.toBeInTheDocument();
  });

  it("surfaces daily actions and real-estate lanes from API-provided values", () => {
    render(<DashboardPage data={dashboardFixture} />);

    const actionBoard = screen.getByLabelText(/daily action board/i);
    expectCardValue(actionBoard, "Contact-ready lead desk", "13");
    expectCardValue(actionBoard, "Messages needing Martin", "14");
    expectCardValue(actionBoard, "Approval queue", "11");
    expectCardValue(actionBoard, "Research / skiptrace bench", "23");
    expectCardValue(actionBoard, "Blocked or dead", "13");

    const lanes = screen.getByLabelText(/real estate lane overview/i);
    expect(within(lanes).getByText("Probate / tax title lane")).toBeInTheDocument();
    expectCardValue(lanes, "Ready", "8");
    expectCardValue(lanes, "Interested", "4");
    expect(within(lanes).getByText("Lease-option lane")).toBeInTheDocument();
    expectCardValue(lanes, "Pending", "5");
    expectCardValue(lanes, "Booked", "2");
    expect(within(lanes).getByText("Deal desk")).toBeInTheDocument();
    expectCardValue(lanes, "Opportunities", "6");
    expectCardValue(lanes, "Skiptrace", "19");
  });

  it("does not render provider operations or live action controls on the primary dashboard", () => {
    render(<DashboardPage data={dashboardFixture} />);

    expect(screen.queryByText("Provider operations")).not.toBeInTheDocument();
    expect(screen.queryByText("HubSpot mirror preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Instantly enrollment preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Vapi voice readiness")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply|dispatch|send|enroll|call/i })).not.toBeInTheDocument();
  });
});
