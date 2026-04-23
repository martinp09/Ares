import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { missionControlAgentDetailFixtures } from "../lib/fixtures";
import { AgentDetailPage } from "./AgentDetailPage";

describe("AgentDetailPage", () => {
  it("renders a read-only lifecycle page from typed detail data", () => {
    const onBack = vi.fn();

    render(<AgentDetailPage detail={missionControlAgentDetailFixtures["agt-1001"]} dataSource="fixture" onBack={onBack} />);

    expect(screen.getByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText(/read-only lifecycle view for the selected agent/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Current posture" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Revision history" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Secrets health" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Release history" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Usage" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent audit" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent turns" })).toBeInTheDocument();
    expect(screen.getByText("Sierra Inbox Agent · limitless · production")).toBeInTheDocument();
    expect(screen.getByText("Rollback clone restored the known-good prompt pack.")).toBeInTheDocument();
    expect(screen.getByText(/No publish or rollback buttons are exposed/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^publish$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^rollback$/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back to agents/i }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
