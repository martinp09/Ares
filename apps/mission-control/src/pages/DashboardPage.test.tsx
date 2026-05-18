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

function expectArticleValue(region: HTMLElement, label: string, value: string) {
  const labelElement = within(region).getByText(label);
  const card = labelElement.closest("article");

  expect(card).not.toBeNull();
  expect(within(card as HTMLElement).getByText(value)).toBeInTheDocument();
}

describe("DashboardPage", () => {
  it("renders a segmented analytics dashboard instead of an all-in-one action wall", () => {
    render(<DashboardPage data={dashboardFixture} />);

    expect(screen.getByText("Dashboard analytics")).toBeInTheDocument();
    expect(screen.getByText(/Segmented, chart-first view of Ares real-estate work/i)).toBeInTheDocument();
    expect(screen.getByText(/Admin\/backend controls stay out of this overview/i)).toBeInTheDocument();
    expect(screen.getByText("No-send locked")).toBeInTheDocument();

    expect(screen.queryByText("What should Martin work first?")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/daily action board/i)).not.toBeInTheDocument();

    const metricStrip = screen.getByLabelText(/dashboard kpi strip/i);
    expectArticleValue(metricStrip, "Ready leads", "13");
    expectArticleValue(metricStrip, "Replies", "14");
    expectArticleValue(metricStrip, "Approvals", "11");
    expectArticleValue(metricStrip, "Opportunities", "6");
  });

  it("surfaces graph-style analytics sections with real-estate labels", () => {
    render(<DashboardPage data={dashboardFixture} />);

    const charts = screen.getByLabelText(/dashboard charts/i);
    expect(within(charts).getByText("Lane performance")).toBeInTheDocument();
    expect(within(charts).getByText("Probate ready")).toBeInTheDocument();
    expect(within(charts).getByText("Lease-option pending")).toBeInTheDocument();
    expect(within(charts).getByText("Deal opportunities")).toBeInTheDocument();
    expect(within(charts).getByText("Contact mix")).toBeInTheDocument();
    expect(within(charts).getByText("38%"));

    const funnelAndBlockers = screen.getByLabelText(/funnel and blockers/i);
    expect(within(funnelAndBlockers).getByText("Acquisition funnel")).toBeInTheDocument();
    expect(within(funnelAndBlockers).getByText("Inventory")).toBeInTheDocument();
    expect(within(funnelAndBlockers).getByText("Ready")).toBeInTheDocument();
    expect(within(funnelAndBlockers).getByText("Deals")).toBeInTheDocument();
    expect(within(funnelAndBlockers).getByText("What is stopping movement?")).toBeInTheDocument();
    expect(within(funnelAndBlockers).getByText("Needs skiptrace")).toBeInTheDocument();
    expect(within(funnelAndBlockers).getByText("Open research")).toBeInTheDocument();
  });

  it("keeps the overview focused on operator analytics and not backend/admin controls", () => {
    render(<DashboardPage data={dashboardFixture} />);

    const segments = screen.getByLabelText(/segmented operating view/i);
    expect(within(segments).getByText("Acquisition lanes")).toBeInTheDocument();
    expectArticleValue(segments, "Probate active", "21");
    expectArticleValue(segments, "Lease pending", "5");
    expect(within(segments).getByText("Follow-up desk")).toBeInTheDocument();
    expectArticleValue(segments, "Manual calls", "4");
    expect(within(segments).getByText("Deal movement")).toBeInTheDocument();
    expectArticleValue(segments, "Promoted", "17");

    expect(screen.queryByText("Provider operations")).not.toBeInTheDocument();
    expect(screen.queryByText("HubSpot mirror preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Instantly enrollment preview")).not.toBeInTheDocument();
    expect(screen.queryByText("Vapi voice readiness")).not.toBeInTheDocument();
    expect(screen.queryByText("Active runs")).not.toBeInTheDocument();
    expect(screen.queryByText("Live agents")).not.toBeInTheDocument();
    expect(screen.queryByText("System status")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply|dispatch|send|enroll|call/i })).not.toBeInTheDocument();
  });
});
