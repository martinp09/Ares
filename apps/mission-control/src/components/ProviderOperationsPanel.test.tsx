import { render, screen } from "@testing-library/react";

import { ProviderOperationsPanel } from "./ProviderOperationsPanel";
import { providerOperationsFixture } from "../lib/fixtures";

describe("ProviderOperationsPanel", () => {
  it("renders provider preview/read status with no-live labels", () => {
    render(<ProviderOperationsPanel data={providerOperationsFixture} />);

    expect(screen.getByLabelText(/provider operations preview/i)).toBeInTheDocument();
    expect(screen.getByText("HubSpot mirror preview")).toBeInTheDocument();
    expect(screen.getByText("Instantly enrollment preview")).toBeInTheDocument();
    expect(screen.getByText("Vapi voice readiness")).toBeInTheDocument();
    expect(screen.getByText("Nightly brief / source runs")).toBeInTheDocument();
    expect(screen.getByText(/No-live read\/preview status only/i)).toBeInTheDocument();
    expect(screen.getAllByText(/would-call-provider/i)).toHaveLength(2);
    expect(screen.getAllByText("false").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("dry-run only")).toBeInTheDocument();
    expect(screen.getByText("read-only ledger")).toBeInTheDocument();
  });

  it("does not expose live action buttons", () => {
    render(<ProviderOperationsPanel data={providerOperationsFixture} />);

    const buttons = screen.queryAllByRole("button");
    expect(buttons).toEqual([]);
    expect(screen.queryByRole("button", { name: /apply|dispatch|send|enroll|call/i })).not.toBeInTheDocument();
  });
});
