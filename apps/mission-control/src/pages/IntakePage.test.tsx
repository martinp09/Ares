import { render, screen, within } from "@testing-library/react";

import { IntakePage } from "./IntakePage";

describe("IntakePage", () => {
  it("renders the fixture-backed happy path checkpoints", () => {
    render(<IntakePage />);

    expect(screen.getByRole("heading", { name: "Submission to appointment, with the ugly parts still visible." })).toBeInTheDocument();
    expect(screen.getByText("Fixture-backed on this machine. The real backend cutover stays on the MacBook. No white surfaces, no fake product marketing nonsense.")).toBeInTheDocument();

    const summary = screen.getByRole("table");
    expect(within(summary).getByText("Form submission arrives")).toBeInTheDocument();
    expect(within(summary).getByText("Confirmation SMS goes out")).toBeInTheDocument();
    expect(within(summary).getByText("Status and failures stay visible")).toBeInTheDocument();
    expect(screen.getByText("Duplicate submissions must stay obvious.")).toBeInTheDocument();
    expect(screen.getByText("Execution metrics")).toBeInTheDocument();
  });
});
