import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { MissionControlShell, type ShellNavSection } from "./MissionControlShell";

const navSections: ShellNavSection[] = [
  {
    title: "Agents",
    items: [
      { id: "agents", label: "Agents", badge: 2 },
      { id: "dashboard", label: "Dashboard" },
    ],
  },
  {
    title: "Operator views",
    items: [
      { id: "inbox", label: "Inbox", badge: 8 },
      { id: "approvals", label: "Approvals", badge: 4 },
      { id: "runs", label: "Runs", badge: 6 },
      { id: "settings", label: "Settings" },
    ],
  },
];

describe("MissionControlShell", () => {
  it("renders nav sections, search entry, and the active workspace", () => {
    render(
      <MissionControlShell
        navSections={navSections}
        workspaces={[
          { id: "lead-machine", label: "Lead Machine" },
          { id: "marketing", label: "Marketing" },
          { id: "pipeline", label: "Pipeline" },
        ]}
        activeWorkspaceId="lead-machine"
        onSelectWorkspace={vi.fn()}
        activeItemId="agents"
        onNavigate={vi.fn()}
        searchValue=""
        onSearchChange={vi.fn()}
        workspaceTitle="Lead Machine / Agents"
        workspaceSubtitle="Agents are the product unit; the rest of Mission Control stays adjacent as operator views."
        statusBadge="Fixture mode"
        footerNote="Using local fixtures until the native read-model endpoints are wired."
        mainContent={<div>Agents workspace</div>}
        contextContent={<div>Context rail</div>}
      />,
    );

    expect(screen.getByRole("complementary", { name: /mission control/i })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: /search mission control/i })).toBeInTheDocument();
    expect(screen.getByText("Agents are the product unit.")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Agents" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Operator views" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /agents/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /inbox/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approvals/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Lead Machine" })).toHaveClass("workspace-switcher__item--active");
    expect(screen.getByRole("tab", { name: "Marketing" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Pipeline" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lead Machine / Agents" })).toBeInTheDocument();
    expect(screen.getByText("Agents workspace")).toBeInTheDocument();
  });
});
