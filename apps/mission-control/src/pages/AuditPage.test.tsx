import { render, screen } from "@testing-library/react";

import { missionControlFixtures } from "../lib/fixtures";
import { AuditPage } from "./AuditPage";

describe("AuditPage", () => {
  it("renders the governance audit timeline through the page wrapper", () => {
    const { recentAudit } = missionControlFixtures.governance;

    render(<AuditPage events={recentAudit} />);

    expect(screen.getByRole("heading", { name: "Recent audit" })).toBeInTheDocument();
    expect(screen.getByText(`${recentAudit.length} events`)).toBeInTheDocument();
    expect(screen.getByText(recentAudit[0].summary)).toBeInTheDocument();
    expect(screen.getByText(recentAudit[1].eventType)).toBeInTheDocument();
  });
});
