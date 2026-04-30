import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { PipelinePage } from "./PipelinePage";

const stages = [
  { sourceLane: "probate", stage: "qualified_opportunity", count: 2 },
  { sourceLane: "probate", stage: "offer_path_selected", count: 1 },
  { sourceLane: "lease_option_inbound", stage: "qualified_opportunity", count: 3 },
];

describe("PipelinePage", () => {
  it("renders stage movement controls and submits the selected stage", () => {
    const onMoveStage = vi.fn();
    render(<PipelinePage stages={stages} totalCount={6} onMoveStage={onMoveStage} actionState={null} />);

    fireEvent.change(screen.getByLabelText("Opportunity ID"), { target: { value: "opp_123" } });
    fireEvent.change(screen.getByLabelText("Target stage"), { target: { value: "offer_path_selected" } });
    fireEvent.change(screen.getByLabelText("Move reason"), { target: { value: "seller ready for offer path" } });
    fireEvent.click(screen.getByRole("button", { name: "Move stage" }));

    expect(onMoveStage).toHaveBeenCalledWith("opp_123", {
      stage: "offer_path_selected",
      reason: "seller ready for offer path",
      metadata: { surface: "mission-control-pipeline" },
    });
  });

  it("keeps stage movement disabled until an opportunity id is present", () => {
    render(<PipelinePage stages={stages} totalCount={6} onMoveStage={vi.fn()} actionState={null} />);

    expect(screen.getByRole("button", { name: "Move stage" })).toBeDisabled();
  });
});
