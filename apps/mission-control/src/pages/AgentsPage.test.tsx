import { render, screen, within } from "@testing-library/react";

import { AgentsPage } from "./AgentsPage";
import { missionControlFixtures } from "../lib/fixtures";

describe("AgentsPage", () => {
  it("renders the agent spotlight, adjacent operator views, and registry from fixture data", () => {
    render(
      <AgentsPage
        agents={missionControlFixtures.agents}
        workspaceLabel="Lead Machine"
        operatorViews={[
          {
            id: "dashboard",
            label: "Queue",
            metricLabel: "ready leads",
            metricValue: 7,
            description: "Review ready leads before the agent lane advances.",
          },
          {
            id: "inbox",
            label: "Replies",
            metricLabel: "open threads",
            metricValue: 8,
            description: "Keep human review adjacent to the active agents.",
          },
          {
            id: "approvals",
            label: "Approvals",
            metricLabel: "pending decisions",
            metricValue: 2,
            description: "Operator approvals stay visible beside release posture.",
          },
          {
            id: "runs",
            label: "Campaign State",
            metricLabel: "tracked runs",
            metricValue: 3,
            description: "Root and child automation runs stay attached to agents.",
          },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: "Agent platform cockpit" })).toBeInTheDocument();
    expect(screen.getByText("Fixture-backed / no Supabase wiring")).toBeInTheDocument();
    expect(screen.getByText("Agents are the product unit here. The rest is just scaffolding until live runtime wiring is turned on later.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Operator views around agents" })).toBeInTheDocument();
    expect(screen.getByText("Lead Machine operator workspace")).toBeInTheDocument();
    expect(screen.getByText("Queue")).toBeInTheDocument();
    expect(screen.getByText("7 ready leads")).toBeInTheDocument();
    expect(screen.getByText("Replies")).toBeInTheDocument();
    expect(screen.getByText("8 open threads")).toBeInTheDocument();
    expect(screen.getByText("Approvals")).toBeInTheDocument();
    expect(screen.getByText("2 pending decisions")).toBeInTheDocument();
    expect(screen.getByText("Campaign State")).toBeInTheDocument();
    expect(screen.getByText("3 tracked runs")).toBeInTheDocument();

    const publishedCard = screen.getByText("Published revisions").closest("article") ?? screen.getByRole("main");
    expect(within(publishedCard).getByText("Published revisions")).toBeInTheDocument();
    expect(within(publishedCard).getByText("1")).toBeInTheDocument();

    const environmentsCard = screen.getByText("Environments").closest("article") ?? screen.getByRole("main");
    expect(within(environmentsCard).getByText("Environments")).toBeInTheDocument();
    expect(within(environmentsCard).getByText("2")).toBeInTheDocument();

    const liveSessionsCard = screen.getAllByText("Live sessions")[0].closest("article") ?? screen.getByRole("main");
    expect(within(liveSessionsCard).getByText("Live sessions")).toBeInTheDocument();
    expect(within(liveSessionsCard).getByText("3")).toBeInTheDocument();

    const delegatedWorkCard = screen.getAllByText("Delegated work")[0].closest("article") ?? screen.getByRole("main");
    expect(within(delegatedWorkCard).getByText("Delegated work")).toBeInTheDocument();
    expect(within(delegatedWorkCard).getByText("6")).toBeInTheDocument();

    expect(screen.getByText(/featured agent: sierra inbox agent/i)).toBeInTheDocument();
    expect(screen.getByText("Agent registry")).toBeInTheDocument();
    expect(screen.getByText("2 tracked")).toBeInTheDocument();
  });
});
