import { render, screen, within } from "@testing-library/react";

import { AgentsPage } from "./AgentsPage";
import { missionControlFixtures } from "../lib/fixtures";

describe("AgentsPage", () => {
  it("renders the agent spotlight and registry from fixture data", () => {
    render(<AgentsPage agents={missionControlFixtures.agents} />);

    expect(screen.getByRole("heading", { name: "Agent platform cockpit" })).toBeInTheDocument();
    expect(screen.getByText("Fixture-backed / no Supabase wiring")).toBeInTheDocument();
    expect(screen.getByText("Agents are the product unit here. The rest is just scaffolding until live runtime wiring is turned on later.")).toBeInTheDocument();

    const summary = screen.getByText("Published revisions").closest("section") ?? screen.getByRole("main");
    expect(within(summary).getByText("Published revisions")).toBeInTheDocument();
    expect(within(summary).getByText("1")).toBeInTheDocument();
    expect(within(summary).getByText("Environments")).toBeInTheDocument();
    expect(within(summary).getByText("2")).toBeInTheDocument();
    expect(within(summary).getByText("Live sessions")).toBeInTheDocument();
    expect(within(summary).getByText("3")).toBeInTheDocument();
    expect(within(summary).getByText("Delegated work")).toBeInTheDocument();
    expect(within(summary).getByText("6")).toBeInTheDocument();

    expect(screen.getByText(/featured agent: sierra inbox agent/i)).toBeInTheDocument();
    expect(screen.getByText("Agent registry")).toBeInTheDocument();
    expect(screen.getByText("2 tracked")).toBeInTheDocument();
  });
});
