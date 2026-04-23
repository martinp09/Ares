import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { CatalogEntrySummary } from "../lib/api";
import { CatalogPage } from "./CatalogPage";

const entries: CatalogEntrySummary[] = [
  {
    id: "cat-1",
    orgId: "org_internal",
    agentId: "agt-source-1",
    agentRevisionId: "rev-source-1",
    slug: "seller-ops",
    name: "Seller Ops",
    summary: "Installable seller ops agent",
    description: "Operator package for seller follow-up.",
    visibility: "marketplace_candidate",
    marketplacePublicationEnabled: false,
    hostAdapterKind: "trigger_dev",
    providerKind: "anthropic",
    providerCapabilities: ["tool_calls", "json_schema"],
    requiredSkillIds: ["skl_triage", "skl_followup"],
    requiredSecretNames: ["resend_api_key", "textgrid_api_key"],
    releaseChannel: "dogfood",
    metadata: { category: "operations" },
    createdAt: "2026-04-23T03:00:00+00:00",
    updatedAt: "2026-04-23T03:00:00+00:00",
  },
];

describe("CatalogPage", () => {
  it("renders catalog entries with compatibility requirements and install controls", () => {
    const onInstall = vi.fn();

    render(
      <CatalogPage
        entries={entries}
        hasActiveSearch={false}
        installEnabled={true}
        installStates={{}}
        onInstall={onInstall}
        selectedBusinessId="limitless"
        selectedEnvironment="prod"
      />,
    );

    expect(screen.getByRole("heading", { name: /internal catalog/i })).toBeInTheDocument();
    expect(screen.getByText(/install proven agent revisions into a selected target scope/i)).toBeInTheDocument();
    expect(screen.getByText("Seller Ops")).toBeInTheDocument();
    expect(screen.getByText("Installable seller ops agent")).toBeInTheDocument();
    expect(screen.getByText(/marketplace candidate/i)).toBeInTheDocument();
    expect(screen.getByText(/public launch disabled/i)).toBeInTheDocument();
    expect(screen.getByText(/trigger_dev/i)).toBeInTheDocument();
    expect(screen.getByText(/anthropic/i)).toBeInTheDocument();
    expect(screen.getByText(/resend_api_key/i)).toBeInTheDocument();
    expect(screen.getByText(/skl_triage/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("limitless")).toBeInTheDocument();
    expect(screen.getByDisplayValue("prod")).toBeInTheDocument();
    expect(screen.getByText(/changing them installs outside the current filtered view/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /install seller ops/i }));

    expect(onInstall).toHaveBeenCalledWith("cat-1", {
      businessId: "limitless",
      environment: "prod",
      name: "Seller Ops",
    });
  });

  it("shows install failure reasons before runtime and preserves the form for retry", () => {
    render(
      <CatalogPage
        entries={entries}
        hasActiveSearch={false}
        installEnabled={true}
        installStates={{
          "cat-1": {
            status: "failed",
            message: "Catalog entry is missing required secret bindings.",
          },
        }}
        onInstall={vi.fn()}
        selectedBusinessId="limitless"
        selectedEnvironment="prod"
      />,
    );

    expect(screen.getByText(/missing required secret bindings/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /install seller ops/i })).toBeEnabled();
  });

  it("disables installs when the catalog is fixture-backed", () => {
    render(
      <CatalogPage
        entries={entries}
        hasActiveSearch={false}
        installEnabled={false}
        installDisabledReason="Install is unavailable while the catalog is running on fixture fallback."
        installStates={{}}
        onInstall={vi.fn()}
        selectedBusinessId="limitless"
        selectedEnvironment="prod"
      />,
    );

    expect(screen.getByText(/fixture fallback/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /install seller ops/i })).toBeDisabled();
  });
});
