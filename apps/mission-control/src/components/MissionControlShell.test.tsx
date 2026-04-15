import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { MissionControlShell, type ShellNavSection } from "./MissionControlShell";

const navSections: ShellNavSection[] = [
  {
    title: "Operate",
    items: [
      { id: "dashboard", label: "Dashboard" },
      { id: "inbox", label: "Inbox", badge: 8 },
      { id: "approvals", label: "Approvals", badge: 4 },
      { id: "runs", label: "Runs", badge: 6 },
    ],
  },
  {
    title: "Govern",
    items: [
      { id: "agents", label: "Agents", badge: 3 },
      { id: "settings", label: "Settings" },
    ],
  },
];

describe("MissionControlShell", () => {
  it("renders nav sections, search entry, and the active workspace", () => {
    render(
      <MissionControlShell
        navSections={navSections}
        activeItemId="dashboard"
        onNavigate={vi.fn()}
        searchValue=""
        onSearchChange={vi.fn()}
        workspaceTitle="Dashboard"
        workspaceSubtitle="Live posture across inbox, approvals, runs, and agent health."
        statusBadge="Fixture mode"
        footerNote="Using local fixtures until the native read-model endpoints are wired."
        mainContent={<div>Dashboard workspace</div>}
        contextContent={<div>Context rail</div>}
      />,
    );

    expect(screen.getByRole("complementary", { name: /mission control/i })).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: /search mission control/i })).toBeInTheDocument();
    expect(screen.getByText("Operate")).toBeInTheDocument();
    expect(screen.getByText("Govern")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /dashboard/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /inbox/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Dashboard workspace")).toBeInTheDocument();
  });
});
