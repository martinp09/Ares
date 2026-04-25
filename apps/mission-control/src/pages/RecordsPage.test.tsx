import { render, screen, within } from "@testing-library/react";

import { RecordsPage } from "./RecordsPage";
import { missionControlFixtures } from "../lib/fixtures";

describe("RecordsPage", () => {
  it("renders inventory KPIs and keeps promoted records linked to pipeline status", () => {
    render(<RecordsPage data={missionControlFixtures.records} />);

    expect(screen.getByText("Records")).toBeInTheDocument();
    expect(screen.getByText("128 inventory records")).toBeInTheDocument();
    expect(screen.getByText("Needs skip trace")).toBeInTheDocument();
    expect(screen.getByText("Promoted")).toBeInTheDocument();

    const promotedRecord = screen.getByLabelText("record-lead-1001");
    expect(within(promotedRecord).getByText("Avery Stone")).toBeInTheDocument();
    expect(within(promotedRecord).getByText("Pipeline: Contract Sent")).toBeInTheDocument();

    const inventoryRecord = screen.getByLabelText("record-lead-1002");
    expect(within(inventoryRecord).getByText("Record inventory only")).toBeInTheDocument();
  });
});
