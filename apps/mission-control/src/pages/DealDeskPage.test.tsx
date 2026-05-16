import { render, screen } from "@testing-library/react";

import { DealDeskPage } from "./DealDeskPage";

const data = {
  deals: [
    {
      id: "deal_123",
      businessId: "limitless",
      environment: "prod",
      sourceLane: "probate",
      strategyLane: "curative_title",
      stage: "qualified",
      sourceLeadId: "lead_123",
      probateCaseNumber: "PR-2026-1",
      propertyAddress: "123 Skyview Dr",
      county: "harris",
      noSend: true,
      providerSendsEnabled: false,
      nextAction: "Verify seller authority",
      blockingReason: null,
      metadata: {},
      createdAt: "2026-05-15T10:00:00Z",
      updatedAt: "2026-05-15T10:00:00Z",
    },
    {
      id: "deal_456",
      businessId: "limitless",
      environment: "prod",
      sourceLane: "lease_option_inbound",
      strategyLane: "lease_option",
      stage: "offer_needed",
      sourceLeadId: "lead_456",
      probateCaseNumber: null,
      propertyAddress: "500 Pine Trace",
      county: "montgomery",
      noSend: true,
      providerSendsEnabled: false,
      nextAction: "Confirm PITI",
      blockingReason: null,
      metadata: {},
      createdAt: "2026-05-15T10:10:00Z",
      updatedAt: "2026-05-15T10:10:00Z",
    },
  ],
  fireList: [
    {
      dealId: "deal_123",
      itemType: "risk",
      severity: "high",
      reason: "Seller authority is not verified",
      recommendedAction: "Resolve before advancing",
      dueAt: null,
      actionEnabled: false,
      sourceId: "risk_123",
      metadata: {},
    },
  ],
};

describe("DealDeskPage", () => {
  it("renders deal desk metrics, deal rows, and no-send fire list", () => {
    render(<DealDeskPage data={data} dataSource="api" />);

    expect(screen.getByText("Deal Desk Spine")).toBeInTheDocument();
    expect(screen.getByText("Total deals")).toBeInTheDocument();
    expect(screen.getByText("No-send locks")).toBeInTheDocument();
    expect(screen.getByRole("article", { name: /123 Skyview Dr/i })).toHaveTextContent("curative title");
    expect(screen.getByRole("article", { name: /500 Pine Trace/i })).toHaveTextContent("lease option");
    expect(screen.getByLabelText("Deal fire list")).toHaveTextContent("Seller authority is not verified");
    expect(screen.getAllByText("No-send locked")).toHaveLength(2);
  });

  it("shows a clear empty state instead of fake provider actions", () => {
    render(<DealDeskPage data={{ deals: [], fireList: [] }} dataSource="fixture" />);

    expect(screen.getByText("No deals in this scope yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /send/i })).not.toBeInTheDocument();
  });
});
