import { render, screen, within } from "@testing-library/react";

import { missionControlFixtures } from "../lib/fixtures";
import { UsagePage } from "./UsagePage";

describe("UsagePage", () => {
  it("renders the governance usage panels through the page wrapper", () => {
    const { usageSummary, recentUsage: recentUsageEvents } = missionControlFixtures.governance;

    render(
      <UsagePage
        usageSummary={usageSummary}
        recentUsage={recentUsageEvents}
      />,
    );

    const summary = screen.getByRole("region", { name: "Usage summary" });
    const recentUsage = screen.getByRole("region", { name: "Recent usage" });

    expect(within(summary).getByText("Usage summary")).toBeInTheDocument();
    expect(within(summary).getByText(`${usageSummary.totalCount} events`)).toBeInTheDocument();
    expect(within(recentUsage).getByRole("heading", { name: "Recent usage" })).toBeInTheDocument();
    expect(within(recentUsage).getByText(`${recentUsageEvents.length} entries`)).toBeInTheDocument();
    expect(within(recentUsage).getByText(recentUsageEvents[0].kind)).toBeInTheDocument();
    expect(within(recentUsage).getByText(recentUsageEvents[1].kind)).toBeInTheDocument();
  });
});
