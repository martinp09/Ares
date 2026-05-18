import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { MissionControlShell, type ShellNavSection } from "./MissionControlShell";

const navSections: ShellNavSection[] = [
  {
    title: "Work today",
    items: [
      { id: "dashboard", label: "Today Desk", badge: 12 },
      { id: "inbox", label: "Replies", badge: 8 },
      { id: "approvals", label: "Approvals", badge: 4 },
      { id: "tasks", label: "To-Do", badge: 6 },
    ],
  },
  {
    title: "Reference",
    items: [
      { id: "probate-autopilot", label: "Source Health", badge: 1 },
    ],
  },
  {
    title: "Backstage",
    items: [
      { id: "agents", label: "Agents", badge: 2 },
      { id: "catalog", label: "Catalog", badge: 1 },
      { id: "settings", label: "Settings", badge: 0 },
    ],
  },
];

describe("MissionControlShell", () => {
  it("renders a Mission Control-style operator cockpit with command search and real-estate workspaces", () => {
    const { container } = render(
      <MissionControlShell
        navSections={navSections}
        workspaces={[
          { id: "lead-machine", label: "Lead Machine" },
          { id: "marketing", label: "Marketing" },
          { id: "pipeline", label: "Pipeline" },
        ]}
        activeWorkspaceId="lead-machine"
        onSelectWorkspace={vi.fn()}
        activeItemId="dashboard"
        onNavigate={vi.fn()}
        searchValue=""
        onSearchChange={vi.fn()}
        workspaceTitle="Lead Machine / Today Desk"
        workspaceSubtitle="Hot leads, replies, approvals, and blocked records without backend clutter."
        headerSlot={<div>Org-aware scope controls</div>}
        statusBadge="Fixture mode"
        footerNote="Using local fixtures until the native read-model endpoints are wired."
        mainContent={<div>Today desk</div>}
        contextContent={<div>Manager brief</div>}
      />,
    );

    expect(screen.getByRole("complementary", { name: /mission control/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/real estate workspaces/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/operator queues/i)).toBeInTheDocument();
    expect(screen.getByRole("searchbox", { name: /search mission control/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Find a lead, reply, approval, deal, or daily action/i)).toBeInTheDocument();
    expect(screen.getByText("Lead desk, approvals, and deal flow only.")).toBeInTheDocument();
    expect(screen.getByText("No-send locked")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /lead machine/i })).toHaveClass("workspace-rail__item--active");
    expect(screen.getByRole("button", { name: /today desk queue/i })).toHaveClass("nav-item--active");
    expect(screen.getByRole("heading", { name: "Work today" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Reference" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Backstage" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /settings/i })).not.toBeInTheDocument();
    expect(screen.getByText("Org-aware scope controls")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lead Machine / Today Desk" })).toBeInTheDocument();
    expect(screen.getByText("Today desk")).toBeInTheDocument();
    expect(screen.getByText("Manager brief")).toBeInTheDocument();
    expect(container.querySelector(".shell")).toHaveClass("shell--operator");
    expect(container.querySelector(".shell")).not.toHaveClass("shell--crm");
  });

  it("can still render the legacy CRM shell surface if a bounded page explicitly asks for it", () => {
    const { container } = render(
      <MissionControlShell
        navSections={navSections}
        workspaces={[
          { id: "lead-machine", label: "Lead Machine" },
          { id: "pipeline", label: "Pipeline" },
        ]}
        activeWorkspaceId="pipeline"
        onSelectWorkspace={vi.fn()}
        activeItemId="pipeline"
        onNavigate={vi.fn()}
        searchValue=""
        onSearchChange={vi.fn()}
        workspaceTitle="Pipeline Board"
        workspaceSubtitle="Opportunity board"
        statusBadge="Live API"
        footerNote="Live data"
        mainContent={<div>CRM cockpit</div>}
        contextContent={<div>Context rail</div>}
        surface="crm"
      />,
    );

    expect(container.querySelector(".shell")).toHaveClass("shell--operator");
    expect(container.querySelector(".shell")).toHaveClass("shell--crm");
    expect(screen.getByText("CRM cockpit")).toBeInTheDocument();
  });
});
