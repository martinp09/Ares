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
  systemStatus: "watch",
  updatedAt: "Updated moments ago",
};

function expectSummaryCardValue(label: string, value: string) {
  const labelElement = screen.getByText(label);
  const card = labelElement.closest("article, div");

  expect(card).not.toBeNull();
  expect(within(card as HTMLElement).getByText(value)).toBeInTheDocument();
}

describe("DashboardPage", () => {
  it("renders the counts it is given from the backend fixture", () => {
    render(<DashboardPage data={dashboardFixture} />);

    const summary = screen.getByLabelText(/dashboard summary/i);

    expect(within(summary).getByText("Approval queue")).toBeInTheDocument();
    expect(within(summary).getByText("11")).toBeInTheDocument();
    expect(within(summary).getByText("Active runs")).toBeInTheDocument();
    expect(within(summary).getByText("7")).toBeInTheDocument();
    expect(within(summary).getByText("Failed runs")).toBeInTheDocument();
    expect(within(summary).getByText("2")).toBeInTheDocument();
    expect(within(summary).getByText("Live agents")).toBeInTheDocument();
    expect(within(summary).getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Recent completions")).toBeInTheDocument();
    expect(screen.getByText("19")).toBeInTheDocument();
    expect(screen.getByText("watch")).toBeInTheDocument();
  });

  it("renders secondary dashboard fields from API-provided values", () => {
    render(
      <DashboardPage
        data={{
          ...dashboardFixture,
          unreadConversationCount: 28,
          busyChannelCount: 9,
          recentCompletedCount: 77,
          recordInventorySummary: {
            totalCount: 128,
            activeCount: 84,
            suppressedCount: 11,
            needsSkipTraceCount: 19,
            noPhoneCount: 19,
            promotedCount: 6,
            openTaskCount: 14,
          },
          providerFailureTaskCount: 3,
          systemStatus: "degraded",
          updatedAt: "2026-04-13T20:09:00+00:00",
        }}
      />,
    );

    const summary = screen.getByLabelText(/dashboard summary/i);

    expect(within(summary).getByText("Unread conversations")).toBeInTheDocument();
    expect(within(summary).getByText("28")).toBeInTheDocument();
    expect(within(summary).getByText("Busy channels")).toBeInTheDocument();
    expect(within(summary).getByText("9")).toBeInTheDocument();
    expectSummaryCardValue("Recent completions", "77");
    expectSummaryCardValue("Inventory records", "128");
    expectSummaryCardValue("Needs skip trace", "19");
    expectSummaryCardValue("Provider failures", "3");
    expectSummaryCardValue("System status", "degraded");
    expect(screen.getByText("2026-04-13T20:09:00+00:00")).toBeInTheDocument();
  });

  it("renders fixture-backed provider operations without live action controls", () => {
    render(<DashboardPage data={dashboardFixture} />);

    expect(screen.getByText("Provider operations")).toBeInTheDocument();
    expect(screen.getByText("HubSpot mirror preview")).toBeInTheDocument();
    expect(screen.getByText("Instantly enrollment preview")).toBeInTheDocument();
    expect(screen.getByText("Vapi voice readiness")).toBeInTheDocument();
    expect(screen.getByText("Nightly brief / source runs")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply|dispatch|send|enroll|call/i })).not.toBeInTheDocument();
  });
});
