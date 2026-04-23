import { render, screen, within } from "@testing-library/react";

import { UsagePanel } from "./UsagePanel";

describe("UsagePanel", () => {
  it("renders usage summary and recent usage entries", () => {
    render(
      <UsagePanel
        usageSummary={{
          totalCount: 5,
          byKind: {
            tool_call: 3,
            approval: 2,
          },
          bySourceKind: [],
          byAgent: [],
          updatedAt: "2026-04-22T10:00:00Z",
        }}
        recentUsage={[
          {
            id: "usage-1",
            kind: "tool_call",
            count: 3,
            sourceKind: "runtime",
            createdAt: "2026-04-22T10:00:00Z",
          },
          {
            id: "usage-2",
            kind: "approval",
            count: 2,
            sourceKind: null,
            createdAt: "2026-04-22T11:00:00Z",
          },
        ]}
      />,
    );

    const summary = screen.getByRole("region", { name: "Usage summary" });
    expect(within(summary).getByText("Usage summary")).toBeInTheDocument();
    expect(within(summary).getByText("5 events")).toBeInTheDocument();
    expect(within(summary).getByText("tool_call: 3 • approval: 2")).toBeInTheDocument();

    const recentUsage = screen.getByRole("region", { name: "Recent usage" });
    expect(within(recentUsage).getByRole("heading", { name: "Recent usage" })).toBeInTheDocument();
    expect(within(recentUsage).getByText("2 entries")).toBeInTheDocument();
    expect(within(recentUsage).getByText("tool_call")).toBeInTheDocument();
    expect(within(recentUsage).getByText("runtime • 2026-04-22T10:00:00Z")).toBeInTheDocument();
    expect(within(recentUsage).getByText("approval")).toBeInTheDocument();
    expect(within(recentUsage).getByText("2026-04-22T11:00:00Z")).toBeInTheDocument();
  });

  it("renders empty states when no usage is recorded", () => {
    render(
      <UsagePanel
        usageSummary={{
          totalCount: 0,
          byKind: {},
          bySourceKind: [],
          byAgent: [],
          updatedAt: "Unknown",
        }}
        recentUsage={[]}
      />,
    );

    const summary = screen.getByRole("region", { name: "Usage summary" });
    expect(within(summary).getByText("0 events")).toBeInTheDocument();
    expect(within(summary).getByText("No usage recorded.")).toBeInTheDocument();

    const recentUsage = screen.getByRole("region", { name: "Recent usage" });
    expect(within(recentUsage).getAllByText("0 entries")).toHaveLength(2);
    expect(within(recentUsage).getByText("No recent usage")).toBeInTheDocument();
    expect(within(recentUsage).getByText("No usage recorded.")).toBeInTheDocument();
  });
});
