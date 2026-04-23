import { render, screen } from "@testing-library/react";

import { missionControlFixtures } from "../lib/fixtures";
import { SecretsPage } from "./SecretsPage";

describe("SecretsPage", () => {
  it("renders the governance secret-health panel through the page wrapper", () => {
    const { secretsHealth } = missionControlFixtures.governance;

    render(<SecretsPage secretsHealth={secretsHealth} />);

    expect(screen.getByRole("heading", { name: "Secrets health" })).toBeInTheDocument();
    expect(screen.getByText("Active revisions")).toBeInTheDocument();
    expect(screen.getByText(secretsHealth.revisions[0].agentName)).toBeInTheDocument();
    expect(screen.getByText(secretsHealth.revisions[1].agentName)).toBeInTheDocument();
  });
});
