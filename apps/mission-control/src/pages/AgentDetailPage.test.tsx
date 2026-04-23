import { fireEvent, render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { missionControlAgentDetailFixtures, missionControlFixtures } from "../lib/fixtures";
import { AgentDetailPage } from "./AgentDetailPage";

describe("AgentDetailPage", () => {
  it("renders a read-only lifecycle page from typed detail data", () => {
    const onBack = vi.fn();

    render(
      <AgentDetailPage
        detail={missionControlAgentDetailFixtures["agt-1001"]}
        dataSource="fixture"
        onBack={onBack}
        selectedAgentHostAdapter={missionControlFixtures.agents[0].hostAdapter}
        selectedAgentSummary={missionControlFixtures.agents[0]}
      />,
    );

    expect(screen.getByRole("heading", { name: "Agent lifecycle" })).toBeInTheDocument();
    expect(screen.getByText(/read-only lifecycle view for the selected agent/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Current posture" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Revision history" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Secrets health" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Release history" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Usage" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent audit" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Recent turns" })).toBeInTheDocument();
    expect(screen.getByText("Sierra Inbox Agent · limitless · production")).toBeInTheDocument();
    expect(screen.getByText("Rollback clone restored the known-good prompt pack.")).toBeInTheDocument();
    expect(screen.getByText("Runtime owns publish and rollback. Mission Control is read-only in this slice.")).toBeInTheDocument();
    expect(screen.getByText("Trigger.dev enabled")).toBeInTheDocument();
    expect(screen.getByText("Adapter details: dispatch, status correlation, artifact reporting")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^publish$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^rollback$/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /back to agents/i }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("uses the selected agent summary for disabled host-adapter truth and compatibility warnings", () => {
    render(
      <AgentDetailPage
        detail={missionControlAgentDetailFixtures["agt-1002"]}
        dataSource="fixture"
        onBack={() => {}}
        selectedAgentHostAdapter={missionControlFixtures.agents[1].hostAdapter}
        selectedAgentSummary={missionControlFixtures.agents[1]}
      />,
    );

    expect(screen.getByText("Trigger.dev disabled")).toBeInTheDocument();
    expect(screen.getByText("Trigger.dev is disabled for staging dispatches.")).toBeInTheDocument();
    expect(screen.getByText("Compatibility warning: 1 required secret is missing for the active revision.")).toBeInTheDocument();
  });

  it("prefers the latest detail release when release history is available", () => {
    render(
      <AgentDetailPage
        detail={missionControlAgentDetailFixtures["agt-1001"]}
        dataSource="api"
        onBack={() => {}}
        selectedAgentHostAdapter={missionControlFixtures.agents[0].hostAdapter}
        selectedAgentSummary={{
          ...missionControlFixtures.agents[0],
          release: {
            ...missionControlFixtures.agents[0].release!,
            eventId: "rle-stale",
            targetRevisionId: "rev-stale",
            resultingActiveRevisionId: "rev-stale-live",
            createdAt: "2026-04-15T20:12:00+00:00",
          },
        }}
      />,
    );

    expect(screen.getByText("Channel dogfood · target rev-198 · active rev-201")).toBeInTheDocument();
    expect(screen.queryByText("Channel dogfood · target rev-stale · active rev-stale-live")).not.toBeInTheDocument();
  });

  it("renders deactivation release posture without inventing an active revision", () => {
    render(
      <AgentDetailPage
        detail={{
          ...missionControlAgentDetailFixtures["agt-1001"],
          agent: {
            ...missionControlAgentDetailFixtures["agt-1001"].agent,
            activeRevisionId: null,
            activeRevisionState: "archived",
            lifecycleStatus: "archived",
          },
          releaseHistory: [
            {
              ...missionControlAgentDetailFixtures["agt-1001"].releaseHistory[0],
              id: "rle-deactivate",
              eventType: "deactivate",
              targetRevisionId: "rev-201",
              resultingActiveRevisionId: null,
              createdAt: "2026-04-17T12:00:00+00:00",
            },
          ],
        }}
        dataSource="api"
        onBack={() => {}}
        selectedAgentHostAdapter={missionControlFixtures.agents[0].hostAdapter}
        selectedAgentSummary={{
          ...missionControlFixtures.agents[0],
          activeRevisionId: null,
          activeRevisionState: "archived",
          lifecycleStatus: "archived",
          release: {
            ...missionControlFixtures.agents[0].release!,
            eventType: "deactivate",
            targetRevisionId: "rev-201",
            resultingActiveRevisionId: null,
            createdAt: "2026-04-17T12:00:00+00:00",
          },
        }}
      />,
    );

    expect(screen.getByText("Channel dogfood · target rev-201 · active none")).toBeInTheDocument();
    expect(screen.getByText("Latest event rle-deactivate retired rev-201 from active service.")).toBeInTheDocument();
    expect(screen.getByText("inactive")).toBeInTheDocument();
  });
});
