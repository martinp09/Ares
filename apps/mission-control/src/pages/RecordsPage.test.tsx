import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { vi } from "vitest";

import { RecordsPage } from "./RecordsPage";
import { missionControlFixtures } from "../lib/fixtures";

describe("RecordsPage", () => {
  it("renders inventory KPIs and keeps promoted records linked to pipeline status", () => {
    render(<RecordsPage data={missionControlFixtures.records} />);

    expect(screen.getByText("Records")).toBeInTheDocument();
    expect(screen.getByText("128 inventory records")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Records SmartLists table" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Filter builder" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Manage fields" })).toBeInTheDocument();
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
    expect(within(promotedRecord).getByText("2 tasks")).toBeInTheDocument();

    const inventoryRecord = screen.getByLabelText("record-lead-1002");
    expect(within(inventoryRecord).getByText("Record actions call the CRM command API; promotion is gated until source identity is exposed to the row.")).toBeInTheDocument();
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

  it("enables promotion only for records with source identity", () => {
    const onRecordPromote = vi.fn();
    const records = {
      ...missionControlFixtures.records,
      records: missionControlFixtures.records.records.map((record) =>
        record.id === "lead-1002" ? { ...record, sourceLeadId: "lead_1002" } : record,
      ),
    };
    render(<RecordsPage data={records} onRecordPromote={onRecordPromote} />);

    const promotableRecord = screen.getByLabelText("record-lead-1002");
    fireEvent.click(within(promotableRecord).getByRole("button", { name: /^Promote$/i }));

    expect(onRecordPromote).toHaveBeenCalledWith(expect.objectContaining({ id: "lead-1002", sourceLeadId: "lead_1002" }));
  });

  it("fans out bulk status and suppress actions only across selected visible records", async () => {
    const onRecordStatusChange = vi.fn();
    const onRecordSuppress = vi.fn();
    render(
      <RecordsPage
        data={missionControlFixtures.records}
        onRecordStatusChange={onRecordStatusChange}
        onRecordSuppress={onRecordSuppress}
      />,
    );

    const selectAvery = within(screen.getByLabelText("record-lead-1001")).getByRole("checkbox", { name: /select Avery Stone/i });
    const selectBlake = within(screen.getByLabelText("record-lead-1002")).getByRole("checkbox", { name: /select Blake North/i });
    fireEvent.click(selectAvery);
    fireEvent.click(selectBlake);

    fireEvent.click(screen.getByRole("button", { name: /Needs skip trace selected/i }));
    await waitFor(() => expect(onRecordStatusChange).toHaveBeenCalledTimes(2));
    expect(onRecordStatusChange).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({ id: "lead-1001" }),
      "needs_skip_trace",
      "Operator bulk-marked selected visible records for skip trace from Mission Control",
    );
    expect(onRecordStatusChange).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({ id: "lead-1002" }),
      "needs_skip_trace",
      "Operator bulk-marked selected visible records for skip trace from Mission Control",
    );

    const savedViews = screen.getByLabelText("Saved record views");
    fireEvent.click(within(savedViews).getByRole("button", { name: /Needs skip trace 1/i }));
    fireEvent.click(screen.getByRole("button", { name: /Suppress selected/i }));

    await waitFor(() => expect(onRecordSuppress).toHaveBeenCalledTimes(1));
    expect(onRecordSuppress).toHaveBeenCalledWith(
      expect.objectContaining({ id: "lead-1002" }),
      "Bulk suppressed selected visible records from Mission Control Records workspace",
    );
  });

  it("disables bulk actions with no selected visible records or while a record action is running", () => {
    const onRecordStatusChange = vi.fn();
    const onRecordSuppress = vi.fn();
    const { rerender } = render(
      <RecordsPage
        data={missionControlFixtures.records}
        onRecordStatusChange={onRecordStatusChange}
        onRecordSuppress={onRecordSuppress}
      />,
    );

    expect(screen.getByRole("button", { name: /Mark marketable selected/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Needs skip trace selected/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Suppress selected/i })).toBeDisabled();

    fireEvent.click(within(screen.getByLabelText("record-lead-1001")).getByRole("checkbox", { name: /select Avery Stone/i }));
    expect(screen.getByRole("button", { name: /Mark marketable selected/i })).toBeEnabled();

    rerender(
      <RecordsPage
        data={missionControlFixtures.records}
        actionState={{ recordId: "lead-1001", status: "running", message: "Updating Avery Stone..." }}
        onRecordStatusChange={onRecordStatusChange}
        onRecordSuppress={onRecordSuppress}
      />,
    );

    expect(screen.getByRole("button", { name: /Mark marketable selected/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Needs skip trace selected/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /Suppress selected/i })).toBeDisabled();
  });
});
