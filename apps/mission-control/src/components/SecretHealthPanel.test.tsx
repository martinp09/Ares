import { render, screen, within } from "@testing-library/react";

import { SecretHealthPanel } from "./SecretHealthPanel";
import type { GovernanceData } from "../lib/api";

const baseSecretsHealth: GovernanceData["secretsHealth"] = {
  activeRevisionCount: 2,
  healthyRevisionCount: 1,
  attentionRevisionCount: 1,
  requiredSecretCount: 3,
  configuredSecretCount: 2,
  missingSecretCount: 1,
  revisions: [
    {
      agentRevisionId: "rev-101",
      agentId: "agt-1",
      agentName: "Atlas Research Agent",
      businessId: "limitless-home-solutions",
      environment: "production",
      status: "attention",
      requiredSecretCount: 2,
      configuredSecretCount: 1,
      missingSecretCount: 1,
      requiredSecrets: ["provider_api_key", "resend_api_key"],
      configuredSecrets: ["provider_api_key"],
      missingSecrets: ["resend_api_key"],
    },
    {
      agentRevisionId: "rev-102",
      agentId: "agt-2",
      agentName: "Offer Intake Agent",
      businessId: "limitless-home-solutions",
      environment: "staging",
      status: "healthy",
      requiredSecretCount: 1,
      configuredSecretCount: 1,
      missingSecretCount: 0,
      requiredSecrets: ["textgrid_auth_token"],
      configuredSecrets: ["textgrid_auth_token"],
      missingSecrets: [],
    },
  ],
};

describe("SecretHealthPanel", () => {
  it("renders attention posture with business, environment, and missing-secret truth", () => {
    render(<SecretHealthPanel secretsHealth={baseSecretsHealth} />);

    expect(screen.getByText("Secrets health")).toBeInTheDocument();
    expect(screen.getByText("2/3 configured")).toBeInTheDocument();
    expect(screen.getByText("1 active revisions need secret attention.")).toBeInTheDocument();

    const attentionRevision = screen.getByText("Atlas Research Agent").closest("article");
    expect(attentionRevision).not.toBeNull();
    expect(within(attentionRevision as HTMLElement).getByText("attention")).toBeInTheDocument();
    expect(within(attentionRevision as HTMLElement).getByText("limitless-home-solutions / production")).toBeInTheDocument();
    expect(within(attentionRevision as HTMLElement).getByText("1/2 configured")).toBeInTheDocument();
    expect(within(attentionRevision as HTMLElement).getByText("Missing: resend_api_key")).toBeInTheDocument();
  });

  it("renders healthy revisions with configured-secret truth", () => {
    render(<SecretHealthPanel secretsHealth={baseSecretsHealth} />);

    const healthyRevision = screen.getByText("Offer Intake Agent").closest("article");
    expect(healthyRevision).not.toBeNull();
    expect(within(healthyRevision as HTMLElement).getByText("healthy")).toBeInTheDocument();
    expect(within(healthyRevision as HTMLElement).getByText("limitless-home-solutions / staging")).toBeInTheDocument();
    expect(within(healthyRevision as HTMLElement).getByText("1/1 configured")).toBeInTheDocument();
    expect(within(healthyRevision as HTMLElement).getByText("Configured: textgrid_auth_token")).toBeInTheDocument();
  });

  it("renders an empty state when no revisions report secrets posture", () => {
    render(
      <SecretHealthPanel
        secretsHealth={{
          ...baseSecretsHealth,
          activeRevisionCount: 0,
          healthyRevisionCount: 0,
          attentionRevisionCount: 0,
          requiredSecretCount: 0,
          configuredSecretCount: 0,
          missingSecretCount: 0,
          revisions: [],
        }}
      />,
    );

    expect(screen.getByText("0/0 configured")).toBeInTheDocument();
    expect(screen.getByText("No active revisions have reported secret requirements yet.")).toBeInTheDocument();
    const emptyBadge = screen.getByText("empty");
    expect(emptyBadge.className).not.toContain("risk-pill--attention");
    expect(emptyBadge.className).not.toContain("risk-pill--healthy");
    expect(screen.queryByText("Atlas Research Agent")).not.toBeInTheDocument();
  });
});
