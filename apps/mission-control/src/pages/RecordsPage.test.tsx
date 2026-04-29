import { fireEvent, render, screen, within } from "@testing-library/react";

import { RecordsPage } from "./RecordsPage";
import { missionControlFixtures } from "../lib/fixtures";

describe("RecordsPage", () => {
  it("renders inventory KPIs and keeps promoted records linked to pipeline status", () => {
    render(<RecordsPage data={missionControlFixtures.records} />);

    expect(screen.getByText("Records")).toBeInTheDocument();
    expect(screen.getByText("128 inventory records")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /All records/i })).toBeInTheDocument();
    expect(screen.getAllByText("Needs skip trace").length).toBeGreaterThan(0);
    expect(screen.getByText("Marketable / active")).toBeInTheDocument();
    expect(screen.getByText("No phone")).toBeInTheDocument();
    expect(screen.getAllByText("Promoted").length).toBeGreaterThan(0);

    const promotedRecord = screen.getByLabelText("record-lead-1001");
    expect(within(promotedRecord).getByText("Avery Stone")).toBeInTheDocument();
    expect(within(promotedRecord).getByText("Pipeline: Contract Sent")).toBeInTheDocument();
    expect(within(promotedRecord).getByText("Phone ready")).toBeInTheDocument();
    expect(within(promotedRecord).getByText("High quality")).toBeInTheDocument();

    const inventoryRecord = screen.getByLabelText("record-lead-1002");
    expect(within(inventoryRecord).getByText("Record actions now call the CRM command API; promotion stays gated until source identity is exposed to the row.")).toBeInTheDocument();
    expect(within(inventoryRecord).getByRole("button", { name: "Mark marketable" })).toBeDisabled();
    expect(within(inventoryRecord).getByRole("button", { name: "Promote gated" })).toBeDisabled();
    expect(within(inventoryRecord).getByText("Email only")).toBeInTheDocument();
    expect(within(inventoryRecord).getByText("Incomplete")).toBeInTheDocument();
  });

  it("filters records with saved views and operator tabs without adding fake write actions", () => {
    render(<RecordsPage data={missionControlFixtures.records} />);

    const savedViews = screen.getByLabelText("Saved record views");
    fireEvent.click(within(savedViews).getByRole("button", { name: /Needs skip trace 1/i }));

    expect(screen.queryByLabelText("record-lead-1001")).not.toBeInTheDocument();
    expect(screen.getByLabelText("record-lead-1002")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /All records/i }));
    fireEvent.click(screen.getAllByRole("button", { name: /Promoted/i })[0]);

    expect(screen.getByLabelText("record-lead-1001")).toBeInTheDocument();
    expect(screen.queryByLabelText("record-lead-1002")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Promote$/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Promote gated$/i })).toBeDisabled();
  });
});
