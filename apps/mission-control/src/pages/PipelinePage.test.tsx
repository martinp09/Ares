import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { PipelinePage } from "./PipelinePage";

const stages = [
  { sourceLane: "probate", stage: "qualified_opportunity", count: 2 },
  { sourceLane: "probate", stage: "offer_path_selected", count: 1 },
  { sourceLane: "lease_option_inbound", stage: "qualified_opportunity", count: 3 },
];

const opportunities = [
  {
    id: "opp_123",
    businessId: "1",
    environment: "prod",
    sourceLane: "probate",
    strategyLane: "cash_offer",
    stage: "qualified_opportunity",
    leadId: "lead_123",
    contactId: null,
    titleStatus: "not_open",
    tcStatus: "not_started",
    dispoStatus: "not_ready",
    metadata: { estimated_value: 210000, next_action: "Select offer path" },
    createdAt: "2026-04-29T12:00:00Z",
    updatedAt: "2026-04-29T12:00:00Z",
  },
  {
    id: "opp_456",
    businessId: "1",
    environment: "prod",
    sourceLane: "probate",
    strategyLane: "creative_finance",
    stage: "offer_path_selected",
    leadId: "lead_456",
    contactId: null,
    titleStatus: "open",
    tcStatus: "active",
    dispoStatus: "ready",
    metadata: { estimated_value: 315000, next_action: "Send contract" },
    createdAt: "2026-04-29T12:05:00Z",
    updatedAt: "2026-04-29T12:05:00Z",
  },
];

const records = [
  {
    id: "lead_123",
    recordType: "lead",
    displayName: "Estate of Avery Stone",
    ownerName: "Avery Stone Estate",
    propertyAddress: "123 Skyview Dr",
    mailingAddress: null,
    source: "probate_intake",
    lifecycleStatus: "ready",
    recordStatus: "needs_skip_trace",
    promotionStatus: "promoted",
    opportunityId: "opp_123",
    pipelineStage: "qualified_opportunity",
    sourceLeadId: "lead_123",
    sourceContactId: null,
    assignedTo: "Sierra",
    phone: null,
    email: "avery@example.com",
    hasPhone: false,
    hasEmail: true,
    openTaskCount: 2,
    lastActivityAt: "2026-04-29T12:00:00Z",
    dataQualityScore: 62,
  },
];

describe("PipelinePage", () => {
  it("renders enterprise board metrics, stage columns, and selected opportunity detail", () => {
    render(
      <PipelinePage
        stages={stages}
        opportunities={opportunities}
        records={records}
        totalCount={2}
        onMoveStage={vi.fn()}
        actionState={null}
      />,
    );

    expect(screen.getByText("Total pipeline")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Board" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Forecast" })).toBeInTheDocument();
    expect(screen.getByText("Pipeline: Probate / Curative Title")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Card layout" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Estate of Avery Stone/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Estate of Avery Stone/i })).toHaveTextContent("C 1");
    expect(screen.getByRole("button", { name: /Estate of Avery Stone/i })).toHaveTextContent("T 2");
    expect(screen.getByLabelText("Opportunity detail")).toHaveTextContent("Estate of Avery Stone");
    expect(screen.getByLabelText("Opportunity detail")).toHaveTextContent("$210,000");
    expect(screen.getByLabelText("Opportunity detail")).toHaveTextContent("Agent workbench");
  });

  it("moves the selected opportunity through the real stage callback", () => {
    const onMoveStage = vi.fn();
    render(
      <PipelinePage
        stages={stages}
        opportunities={opportunities}
        records={records}
        totalCount={2}
        onMoveStage={onMoveStage}
        actionState={null}
      />,
    );

    fireEvent.change(screen.getByLabelText("Target stage"), { target: { value: "offer_path_selected" } });
    fireEvent.change(screen.getByLabelText("Move reason"), { target: { value: "seller ready for offer path" } });
    fireEvent.click(screen.getByRole("button", { name: "Move selected opportunity" }));

    expect(onMoveStage).toHaveBeenCalledWith("opp_123", {
      stage: "offer_path_selected",
      reason: "seller ready for offer path",
      metadata: { surface: "mission-control-pipeline-board" },
    });
  });

  it("keeps stage movement disabled until the target stage changes", () => {
    render(
      <PipelinePage
        stages={stages}
        opportunities={opportunities}
        records={records}
        totalCount={2}
        onMoveStage={vi.fn()}
        actionState={null}
      />,
    );

    expect(screen.getByRole("button", { name: "Move selected opportunity" })).toBeDisabled();
  });
});
