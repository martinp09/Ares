import { render, screen, within } from "@testing-library/react";

import { ProbateAutopilotPage } from "./ProbateAutopilotPage";
import type { ProbateAutopilotHealthData } from "../lib/api";
import { probateAutopilotHealthFixture } from "../lib/fixtures";

function renderPage(overrides: Partial<ProbateAutopilotHealthData> = {}) {
  render(
    <ProbateAutopilotPage
      data={{ ...probateAutopilotHealthFixture, ...overrides }}
      dataSource="api"
    />,
  );
}

describe("ProbateAutopilotPage", () => {
  it("renders the read-only probate autopilot SLA and backlog", () => {
    renderPage();

    const panel = screen.getByLabelText(/probate autopilot health/i);
    expect(within(panel).getByText("Probate autopilot health")).toBeInTheDocument();
    expect(within(panel).getByText("API-backed")).toBeInTheDocument();
    expect(within(panel).getByText("SLA status")).toBeInTheDocument();
    expect(within(panel).getByText("Source quality")).toBeInTheDocument();
    expect(within(panel).getByText("Enrichment backlog")).toBeInTheDocument();
    expect(within(panel).getByText("Property match:")).toBeInTheDocument();
    expect(within(panel).getByText("Tax overlay:")).toBeInTheDocument();
    expect(within(panel).getByText("run property tax title enrichment", { exact: false })).toBeInTheDocument();
  });

  it("keeps source identifiers redacted from the operator panel", () => {
    renderPage({
      sourceQuality: {
        ...probateAutopilotHealthFixture.sourceQuality,
        duplicateCaseCount: 1,
        duplicateCaseCountByCounty: { harris: 1 },
      },
      anomalies: [
        {
          severity: "warning",
          type: "duplicate_case_numbers",
          message: "Duplicate probate rows were found in the source packet.",
          duplicateCaseCount: 1,
          duplicateCaseCountByCounty: { harris: 1 },
        },
      ],
    });

    expect(screen.getByText(/duplicate rows by county/i)).toBeInTheDocument();
    expect(screen.queryByText("543678")).not.toBeInTheDocument();
    expect(screen.queryByText(/tangie renee/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /scrape|sync|send|enroll|call|skiptrace/i })).not.toBeInTheDocument();
  });
});
