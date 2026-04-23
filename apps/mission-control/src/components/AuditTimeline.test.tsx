import { render, screen } from "@testing-library/react";

import { AuditTimeline } from "./AuditTimeline";

describe("AuditTimeline", () => {
  it("renders the recent audit heading, count, and events", () => {
    render(
      <AuditTimeline
        events={[
          {
            id: "audit-1",
            eventType: "approval_granted",
            summary: "Approved runtime access for lead machine.",
            resourceType: "agent_revision",
            resourceId: "rev-1",
            createdAt: "2026-04-22T10:15:00Z",
          },
          {
            id: "audit-2",
            eventType: "policy_updated",
            summary: "Updated governance review policy for enterprise pack rollout.",
            resourceType: "policy",
            resourceId: "policy-9",
            createdAt: "2026-04-22T11:30:00Z",
          },
        ]}
      />,
    );

    expect(screen.getByRole("heading", { name: "Recent audit" })).toBeInTheDocument();
    expect(screen.getByText("2 events")).toBeInTheDocument();
    expect(screen.getByText("Approved runtime access for lead machine.")).toBeInTheDocument();
    expect(screen.getByText("approval_granted")).toBeInTheDocument();
    expect(screen.getByText("Updated governance review policy for enterprise pack rollout.")).toBeInTheDocument();
    expect(screen.getByText("policy_updated")).toBeInTheDocument();
  });

  it("renders the empty state when no audit events are available", () => {
    render(<AuditTimeline events={[]} />);

    expect(screen.getByText("0 events")).toBeInTheDocument();
    expect(screen.getByText("No audit events are currently available.")).toBeInTheDocument();
  });
});
