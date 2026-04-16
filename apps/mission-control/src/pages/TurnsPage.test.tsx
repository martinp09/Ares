import { render, screen } from "@testing-library/react";

import { TurnsPage } from "./TurnsPage";
import { missionControlFixtures } from "../lib/fixtures";

describe("TurnsPage", () => {
  it("renders the turn journal with state and retry counts", () => {
    render(<TurnsPage turns={missionControlFixtures.turns} />);

    expect(screen.getByRole("heading", { name: "Turn state and retries" })).toBeInTheDocument();
    expect(screen.getByText("trn-1001")).toBeInTheDocument();
    expect(screen.getByText("trn-1002")).toBeInTheDocument();
    expect(screen.getByText("2 visible")).toBeInTheDocument();
    expect(screen.getByText("waiting_for_tool")).toBeInTheDocument();
    expect(screen.getAllByText("limitless / dev")).toHaveLength(2);
  });
});
