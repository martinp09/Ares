import { render, screen, within } from "@testing-library/react";

import { missionControlFixtures } from "../lib/fixtures";
import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("renders a healthy pending-approvals badge when governance is empty", () => {
    render(
      <SettingsPage
        governance={{
          ...missionControlFixtures.governance,
          pendingApprovals: [],
        }}
        assets={missionControlFixtures.assets}
      />,
    );

    expect(screen.getByText(/governance stays org-scoped/i)).toBeInTheDocument();
    const pendingApprovalsCard = screen.getByText("Pending approvals").closest("article");
    expect(pendingApprovalsCard).not.toBeNull();
    const pendingApprovalsBadge = within(pendingApprovalsCard as HTMLElement).getByText("0");
    expect(pendingApprovalsBadge.className).toContain("risk-pill--healthy");
    expect(pendingApprovalsBadge.className).not.toContain("risk-pill--attention");
  });
});
