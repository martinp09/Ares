import { useEffect, useMemo, useState } from "react";

import { ContextPanel } from "./components/ContextPanel";
import {
  MissionControlShell,
  type ShellNavSection,
} from "./components/MissionControlShell";
import { createMissionControlApi, type MissionControlSnapshot, type MissionControlView } from "./lib/api";
import { missionControlFixtures } from "./lib/fixtures";
import { queryClient } from "./lib/queryClient";
import { AgentsPage } from "./pages/AgentsPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { InboxPage } from "./pages/InboxPage";
import { IntakePage } from "./pages/IntakePage";
import { RunsPage } from "./pages/RunsPage";
import { TurnsPage } from "./pages/TurnsPage";
import { SettingsPage } from "./pages/SettingsPage";

const api = createMissionControlApi();
const missionControlScope = { businessId: "limitless", environment: "dev" };

function includesSearch(haystack: Array<string | number | null | undefined>, searchValue: string): boolean {
  if (!searchValue) {
    return true;
  }

  return haystack
    .filter((value): value is string | number => value !== null && value !== undefined)
    .join(" ")
    .toLowerCase()
    .includes(searchValue);
}

export default function App() {
  const [activeView, setActiveView] = useState<MissionControlView>("agents");
  const [searchValue, setSearchValue] = useState("");
  const [snapshot, setSnapshot] = useState<MissionControlSnapshot>(missionControlFixtures);
  const [selectedConversationId, setSelectedConversationId] = useState(
    missionControlFixtures.inbox.selectedConversationId,
  );
  const [dataSource, setDataSource] = useState<"api" | "fixture">("fixture");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoading(true);

      const [dashboard, inbox, approvals, runs, turns, agents, assets] = await Promise.all([
        queryClient.fetch("dashboard", api.getDashboard, missionControlFixtures.dashboard),
        queryClient.fetch(`inbox:${selectedConversationId}`, () => api.getInbox(selectedConversationId), missionControlFixtures.inbox),
        queryClient.fetch("approvals", api.getApprovals, missionControlFixtures.approvals),
        queryClient.fetch("runs", api.getRuns, missionControlFixtures.runs),
        queryClient.fetch("turns:limitless:dev", () => api.getTurns(missionControlScope), missionControlFixtures.turns),
        queryClient.fetch("agents", api.getAgents, missionControlFixtures.agents),
        queryClient.fetch("assets", api.getAssets, missionControlFixtures.assets),
      ]);

      if (!isMounted) {
        return;
      }

      setSnapshot({
        dashboard: dashboard.data,
        inbox: inbox.data,
        approvals: approvals.data,
        runs: runs.data,
        turns: turns.data,
        agents: agents.data,

        assets: assets.data,
      });
      setDataSource(
        [dashboard, inbox, approvals, runs, turns, agents, assets].some((result) => result.source === "fixture")
          ? "fixture"
          : "api",
      );
      setSelectedConversationId((currentId) =>
        inbox.data.conversations.some((conversation) => conversation.id === currentId)
          ? currentId
          : inbox.data.selectedConversationId,
      );
      setIsLoading(false);
    }

    void load();

    return () => {
      isMounted = false;
    };
  }, [selectedConversationId]);

  const normalizedSearchValue = searchValue.trim().toLowerCase();

  const filteredConversations = useMemo(
    () =>
      snapshot.inbox.conversations.filter((conversation) =>
        includesSearch(
          [
            conversation.leadName,
            conversation.channel,
            conversation.lastMessage,
            conversation.stage,
            conversation.sequenceState,
          ],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.inbox.conversations],
  );

  const visibleConversationId =
    filteredConversations.find((conversation) => conversation.id === selectedConversationId)?.id ??
    filteredConversations[0]?.id ??
    snapshot.inbox.selectedConversationId;

  const visibleThread =
    snapshot.inbox.threadsById[visibleConversationId] ??
    snapshot.inbox.threadsById[snapshot.inbox.selectedConversationId];

  const filteredApprovals = useMemo(
    () =>
      snapshot.approvals.filter((approval) =>
        includesSearch(
          [approval.title, approval.reason, approval.commandType, approval.payloadPreview],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.approvals],
  );

  const filteredRuns = useMemo(
    () =>
      snapshot.runs.filter((run) =>
        includesSearch(
          [run.commandType, run.status, run.businessId, run.environment, run.summary, run.parentRunId],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.runs],
  );

  const filteredTurns = useMemo(
    () =>
      snapshot.turns.filter((turn) =>
        includesSearch(
          [turn.id, turn.sessionId, turn.agentId, turn.agentRevisionId, turn.state, turn.retryCount],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.turns],
  );

  const filteredAgents = useMemo(
    () =>
      snapshot.agents.filter((agent) =>
        includesSearch(
          [agent.name, agent.activeRevisionId, agent.activeRevisionState, agent.environment],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.agents],
  );

  const filteredAssets = useMemo(
    () =>
      snapshot.assets.filter((asset) =>
        includesSearch([asset.name, asset.category, asset.status, asset.bindingTarget], normalizedSearchValue),
      ),
    [normalizedSearchValue, snapshot.assets],
  );

  const publishedAgentCount = filteredAgents.filter((agent) => agent.activeRevisionState === "published").length;
  const trackedEnvironmentCount = new Set(filteredAgents.map((agent) => agent.environment)).size;
  const liveSessionTotal = filteredAgents.reduce((total, agent) => total + agent.liveSessionCount, 0);
  const delegatedWorkTotal = filteredAgents.reduce((total, agent) => total + agent.delegatedWorkCount, 0);

  const navSections: ShellNavSection[] = [
    {
      title: "Primary surfaces",
      items: [
        { id: "agents", label: "Agents", badge: snapshot.dashboard.activeAgentCount },
        { id: "dashboard", label: "Dashboard" },
        { id: "intake", label: "Intake" },
      ],
    },
    {
      title: "Operations",
      items: [
        { id: "inbox", label: "Inbox", badge: snapshot.dashboard.unreadConversationCount },
        { id: "approvals", label: "Approvals", badge: snapshot.dashboard.approvalCount },
        { id: "runs", label: "Runs", badge: snapshot.dashboard.activeRunCount },
        { id: "turns", label: "Turns", badge: snapshot.turns.filter((turn) => turn.state !== "completed").length },
        { id: "settings", label: "Settings" },
      ],
    },
  ];

  const pageMap: Record<
    MissionControlView,
    {
      title: string;
      subtitle: string;
      mainContent: JSX.Element;
      contextContent: JSX.Element;
    }
  > = {
    intake: {
      title: "Intake",
      subtitle: "Submission-to-appointment happy path, fixture-backed on this machine.",
      mainContent: <IntakePage />,
      contextContent: (
        <ContextPanel
          eyebrow="Execution lane"
          title="No Supabase or provider wiring on this machine"
          items={[
            "Fixtures only here.",
            "Your local MacBook handles live persistence, provider writes, and database cutover.",
            "The operator still sees the entire happy path in Mission Control.",
          ]}
        />
      ),
    },
    dashboard: {
      title: "Dashboard",
      subtitle: "Live posture across inbox, approvals, runs, and agent health.",
      mainContent: <DashboardPage data={snapshot.dashboard} />,
      contextContent: (
        <ContextPanel
          eyebrow="Queue posture"
          title="Current operator priorities"
          items={[
            `${snapshot.dashboard.approvalCount} approvals waiting`,
            `${snapshot.dashboard.unreadConversationCount} unread conversations`,
            `${snapshot.dashboard.failedRunCount} failed automation flows`,
          ]}
        />
      ),
    },
    inbox: {
      title: "Inbox",
      subtitle: "Three-pane thread review with context kept on screen.",
      mainContent: (
        <InboxPage
          data={{ ...snapshot.inbox, conversations: filteredConversations }}
          selectedConversationId={visibleConversationId}
          onSelectConversation={setSelectedConversationId}
          onSendSmsTest={(payload) => api.sendTestSms(payload)}
          onSendEmailTest={(payload) => api.sendTestEmail(payload)}
        />
      ),
      contextContent: (
        <ContextPanel
          eyebrow="Selected thread"
          title={visibleThread.nextBestAction}
          items={[
            `Stage: ${visibleThread.stage}`,
            `Tags: ${visibleThread.tags.join(", ")}`,
            ...visibleThread.notes,
          ]}
        />
      ),
    },
    approvals: {
      title: "Approvals",
      subtitle: "Review risk-triggered actions without leaving the cockpit.",
      mainContent: <ApprovalsPage approvals={filteredApprovals} />,
      contextContent: (
        <ContextPanel
          eyebrow="Approval policy"
          title="Fast decisions, visible risk"
          items={[
            "Customer-facing replies should remain explicit approvals.",
            "Voice launch requests stay gated until live policy tuning is done.",
          ]}
        />
      ),
    },
    runs: {
      title: "Runs",
      subtitle: "Inspect active, failed, and child runs with visible lineage.",
      mainContent: <RunsPage runs={filteredRuns} />,
      contextContent: (
        <ContextPanel
          eyebrow="Run status"
          title="Lineage stays visible"
          items={[
            "Root and child runs stay on the same timeline.",
            "Failed jobs remain surfaced instead of disappearing into logs.",
          ]}
        />
      ),
    },
    turns: {
      title: "Turns",
      subtitle: "Review session turn state, retry counts, and runtime handoffs.",
      mainContent: <TurnsPage turns={filteredTurns} />,
      contextContent: (
        <ContextPanel
          eyebrow="Turn journal"
          title="Retries and state are visible here"
          items={[
            "Running and waiting turns stay visible instead of collapsing into a generic run row.",
            "Retry count is derived from the turn journal and metadata so operators can see why a turn was retried.",
          ]}
        />
      ),
    },
    agents: {
      title: "Agents",
      subtitle: "Registry-first cockpit for revisions, environments, live sessions, and delegated work.",
      mainContent: <AgentsPage agents={filteredAgents} />,
      contextContent: (
        <ContextPanel
          eyebrow="Fixture boundary"
          title="Agent control plane stays local-first here"
          items={[
            `${publishedAgentCount} published revisions across ${trackedEnvironmentCount} environments are visible in fixtures.`,
            `${liveSessionTotal} live sessions and ${delegatedWorkTotal} delegated work items are surfaced without live writes.`,
            "No Supabase persistence, provider routing, or publish/archive actions are wired from this machine.",
          ]}
        />
      ),
    },
    settings: {
      title: "Settings / Assets",
      subtitle: "Connect-later operational assets only. No page builder or CRM setup.",
      mainContent: <SettingsPage assets={filteredAssets} />,
      contextContent: (
        <ContextPanel
          eyebrow="Connect later"
          title="Asset binding is scaffold-only on this machine"
          items={[
            "Bindings are visible but not wired to live providers here.",
            "Supabase and provider cutover stay deferred.",
          ]}
        />
      ),
    },
  };

  const activePage = pageMap[activeView];
  const statusBadge = isLoading ? "Loading shell" : dataSource === "api" ? "Live API" : "Fixture mode";
  const footerNote =
    dataSource === "api"
      ? "Mission Control is reading Hermes runtime data."
      : "Using local fixtures until the native read-model endpoints are wired.";

  return (
    <MissionControlShell
      navSections={navSections}
      activeItemId={activeView}
      onNavigate={(itemId) => setActiveView(itemId as MissionControlView)}
      searchValue={searchValue}
      onSearchChange={setSearchValue}
      workspaceTitle={activePage.title}
      workspaceSubtitle={activePage.subtitle}
      statusBadge={statusBadge}
      footerNote={footerNote}
      mainContent={activePage.mainContent}
      contextContent={activePage.contextContent}
    />
  );
}
