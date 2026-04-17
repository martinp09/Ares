import { useEffect, useMemo, useState } from "react";

import { ContextPanel } from "./components/ContextPanel";
import {
  MissionControlShell,
  type ShellNavSection,
  type ShellWorkspace,
} from "./components/MissionControlShell";
import { createMissionControlApi, type MissionControlSnapshot, type MissionControlView } from "./lib/api";
import { missionControlFixtures } from "./lib/fixtures";
import { queryClient } from "./lib/queryClient";
import { DashboardPage } from "./pages/DashboardPage";
import { InboxPage } from "./pages/InboxPage";
import { PipelinePage } from "./pages/PipelinePage";
import { RunsPage } from "./pages/RunsPage";
import { TasksPage } from "./pages/TasksPage";

const api = createMissionControlApi();

type WorkspaceId = "lead-machine" | "marketing" | "pipeline";

interface WorkspacePage {
  title: string;
  subtitle: string;
  mainContent: JSX.Element;
  contextContent: JSX.Element;
}

interface WorkspaceDefinition {
  label: string;
  defaultView: MissionControlView;
  navSections: ShellNavSection[];
  pages: Partial<Record<MissionControlView, WorkspacePage>>;
}

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
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceId>("lead-machine");
  const [activeView, setActiveView] = useState<MissionControlView>("dashboard");
  const [searchValue, setSearchValue] = useState("");
  const [snapshot, setSnapshot] = useState<MissionControlSnapshot>(missionControlFixtures);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [dataSource, setDataSource] = useState<"api" | "fixture">("fixture");
  const [fallbackViews, setFallbackViews] = useState<MissionControlView[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoading(true);

      const [dashboard, inbox, tasks, approvals, runs, agents, assets] = await Promise.all([
        queryClient.fetch("dashboard", api.getDashboard, missionControlFixtures.dashboard),
        queryClient.fetch(
          `inbox:${selectedConversationId || "default"}`,
          () => api.getInbox(selectedConversationId || undefined),
          missionControlFixtures.inbox,
        ),
        queryClient.fetch("tasks", api.getTasks, missionControlFixtures.tasks),
        queryClient.fetch("approvals", api.getApprovals, missionControlFixtures.approvals),
        queryClient.fetch("runs", api.getRuns, missionControlFixtures.runs),
        queryClient.fetch("agents", api.getAgents, missionControlFixtures.agents),
        queryClient.fetch("assets", api.getAssets, missionControlFixtures.assets),
      ]);

      if (!isMounted) {
        return;
      }

      setSnapshot({
        dashboard: dashboard.data,
        inbox: inbox.data,
        tasks: tasks.data,
        approvals: approvals.data,
        runs: runs.data,
        agents: agents.data,
        assets: assets.data,
      });
      setDataSource(
        [dashboard, inbox, tasks, approvals, runs, agents, assets].some((result) => result.source === "fixture")
          ? "fixture"
          : "api",
      );
      setFallbackViews(
        (
          [
            ["dashboard", dashboard.source],
            ["inbox", inbox.source],
            ["tasks", tasks.source],
            ["approvals", approvals.source],
            ["runs", runs.source],
            ["agents", agents.source],
            ["settings", assets.source],
          ] as const
        )
          .filter(([, source]) => source === "fixture")
          .map(([viewId]) => viewId),
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

  const filteredTasks = useMemo(
    () =>
      snapshot.tasks.tasks.filter((task) =>
        includesSearch(
          [
            task.leadName,
            task.channel,
            task.bookingStatus,
            task.sequenceStatus,
            task.nextSequenceStep,
            task.recentReplyPreview,
          ],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.tasks.tasks],
  );

  const visibleConversationId =
    filteredConversations.find((conversation) => conversation.id === selectedConversationId)?.id ??
    filteredConversations[0]?.id ??
    snapshot.inbox.selectedConversationId;

  const visibleThread =
    snapshot.inbox.threadsById[visibleConversationId] ??
    snapshot.inbox.threadsById[snapshot.inbox.selectedConversationId];
  const contextThread = visibleThread ?? {
    nextBestAction: "Select a thread to inspect context.",
    stage: "No thread selected",
    tags: [] as string[],
    notes: ["No conversation detail is currently available."],
  };

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

  const filteredOpportunityStages = useMemo(
    () =>
      (snapshot.dashboard.opportunityStageSummaries ?? []).filter((stage) =>
        includesSearch([stage.stage, stage.count], normalizedSearchValue),
      ),
    [normalizedSearchValue, snapshot.dashboard.opportunityStageSummaries],
  );

  const workspaces: ShellWorkspace[] = [
    { id: "lead-machine", label: "Lead Machine" },
    { id: "marketing", label: "Marketing" },
    { id: "pipeline", label: "Pipeline" },
  ];

  const workspaceDefinitions: Record<WorkspaceId, WorkspaceDefinition> = {
    "lead-machine": {
      label: "Lead Machine",
      defaultView: "dashboard",
      navSections: [
        {
          title: "Lead Machine",
          items: [
            { id: "dashboard", label: "Queue", badge: snapshot.dashboard.pendingLeadCount ?? 0 },
            { id: "inbox", label: "Replies", badge: snapshot.dashboard.unreadConversationCount },
            { id: "runs", label: "Campaign State", badge: snapshot.dashboard.activeRunCount },
            { id: "tasks", label: "Tasks", badge: snapshot.dashboard.dueManualCallCount ?? 0 },
          ],
        },
      ],
      pages: {
        dashboard: {
          title: "Lead Machine / Queue",
          subtitle: "Outbound probate queue, campaign posture, and operator attention in one lane.",
          mainContent: <DashboardPage data={snapshot.dashboard} />,
          contextContent: (
            <ContextPanel
              eyebrow="Probate lane"
              title="Outbound machine posture"
              items={[
                `${snapshot.dashboard.pendingLeadCount ?? 0} probate leads ready for operator review`,
                `${snapshot.dashboard.activeRunCount} active campaign flows`,
                `${snapshot.dashboard.dueManualCallCount ?? 0} follow-ups waiting on a human`,
              ]}
            />
          ),
        },
        inbox: {
          title: "Lead Machine / Replies",
          subtitle: "Review probate reply context, suppression signals, and next actions without leaving the lane.",
          mainContent: (
            <InboxPage
              data={{ ...snapshot.inbox, conversations: filteredConversations }}
              selectedConversationId={visibleConversationId}
              onSelectConversation={setSelectedConversationId}
            />
          ),
          contextContent: (
            <ContextPanel
              eyebrow="Selected reply"
              title={contextThread.nextBestAction}
              items={[
                `Stage: ${contextThread.stage}`,
                `Tags: ${contextThread.tags.join(", ") || "none"}`,
                ...contextThread.notes,
              ]}
            />
          ),
        },
        runs: {
          title: "Lead Machine / Campaign State",
          subtitle: "Inspect outbound automation runs and keep campaign lineage visible.",
          mainContent: <RunsPage runs={filteredRuns} />,
          contextContent: (
            <ContextPanel
              eyebrow="Campaign state"
              title="Automation posture"
              items={[
                "Root and child runs stay surfaced together.",
                "Provider and suppression failures stay visible to operators.",
              ]}
            />
          ),
        },
        tasks: {
          title: "Lead Machine / Tasks",
          subtitle: "Manual call checkpoints and reply review tasks for the outbound lane.",
          mainContent: <TasksPage data={{ dueCount: filteredTasks.length, tasks: filteredTasks }} />,
          contextContent: (
            <ContextPanel
              eyebrow="Operator tasks"
              title="Human follow-up remains explicit"
              items={[
                `${filteredTasks.length} tasks are visible in the queue`,
                "Manual reviews stay separate from automated campaign state.",
              ]}
            />
          ),
        },
      },
    },
    marketing: {
      label: "Marketing",
      defaultView: "dashboard",
      navSections: [
        {
          title: "Marketing",
          items: [
            { id: "dashboard", label: "Overview", badge: snapshot.dashboard.pendingLeadCount ?? 0 },
            { id: "inbox", label: "Submissions", badge: snapshot.dashboard.unreadConversationCount },
            { id: "tasks", label: "Tasks", badge: snapshot.dashboard.dueManualCallCount ?? 0 },
          ],
        },
      ],
      pages: {
        dashboard: {
          title: "Marketing / Overview",
          subtitle: "Lease-option submissions, booked vs pending, and non-booker follow-up health.",
          mainContent: <DashboardPage data={snapshot.dashboard} />,
          contextContent: (
            <ContextPanel
              eyebrow="Lease-option lane"
              title="Inbound marketing posture"
              items={[
                `${snapshot.dashboard.pendingLeadCount ?? 0} pending lease-option leads`,
                `${snapshot.dashboard.bookedLeadCount ?? 0} booked consultations`,
                `${snapshot.dashboard.activeNonBookerEnrollmentCount ?? 0} active non-booker sequences`,
              ]}
            />
          ),
        },
        inbox: {
          title: "Marketing / Submissions",
          subtitle: "Work new lease-option submissions and inbound replies in a dedicated operator workspace.",
          mainContent: (
            <InboxPage
              data={{ ...snapshot.inbox, conversations: filteredConversations }}
              selectedConversationId={visibleConversationId}
              onSelectConversation={setSelectedConversationId}
            />
          ),
          contextContent: (
            <ContextPanel
              eyebrow="Submission context"
              title={contextThread.nextBestAction}
              items={[
                `Stage: ${contextThread.stage}`,
                `Tags: ${contextThread.tags.join(", ") || "none"}`,
                ...contextThread.notes,
              ]}
            />
          ),
        },
        tasks: {
          title: "Marketing / Tasks",
          subtitle: "Surface booked vs pending follow-up work and replies that need an operator decision.",
          mainContent: <TasksPage data={{ dueCount: filteredTasks.length, tasks: filteredTasks }} />,
          contextContent: (
            <ContextPanel
              eyebrow="Sequence posture"
              title="Non-booker follow-up stays visible"
              items={[
                `${snapshot.dashboard.repliesNeedingReviewCount ?? 0} replies need review`,
                `${filteredTasks.length} manual call checkpoints remain active`,
              ]}
            />
          ),
        },
      },
    },
    pipeline: {
      label: "Pipeline",
      defaultView: "pipeline",
      navSections: [
        {
          title: "Pipeline",
          items: [{ id: "pipeline", label: "Board", badge: snapshot.dashboard.opportunityCount ?? 0 }],
        },
      ],
      pages: {
        pipeline: {
          title: "Pipeline Board",
          subtitle: "Minimal downstream opportunity stages without collapsing lane boundaries.",
          mainContent: (
            <PipelinePage
              stages={filteredOpportunityStages}
              totalCount={snapshot.dashboard.opportunityCount ?? filteredOpportunityStages.length}
            />
          ),
          contextContent: (
            <ContextPanel
              eyebrow="Downstream seam"
              title="Thin contract-to-close skeleton"
              items={[
                "Opportunities stay visible without pretending title or dispo are finished.",
                "Lead Machine and Marketing can both hand off into the same minimal board.",
              ]}
            />
          ),
        },
      },
    },
  };

  const activeWorkspaceDefinition = workspaceDefinitions[activeWorkspace];
  const activePage =
    activeWorkspaceDefinition.pages[activeView] ?? activeWorkspaceDefinition.pages[activeWorkspaceDefinition.defaultView];

  if (!activePage) {
    throw new Error(`Missing page definition for ${activeWorkspace}:${activeView}`);
  }

  const fallbackLabel = fallbackViews.length > 0 ? ` (${fallbackViews.join(", ")})` : "";
  const statusBadge = isLoading
    ? "Loading shell"
    : dataSource === "api"
      ? "Live API"
      : fallbackViews.length === 7
        ? "Fixture mode"
        : `API + fixture fallback${fallbackLabel}`;
  const footerNote =
    dataSource === "api"
      ? "Mission Control is reading Hermes runtime data."
      : fallbackViews.length === 7
        ? "Using local fixtures until the native read-model endpoints are wired."
        : `Using fixture fallback for: ${fallbackViews.join(", ")}.`;

  return (
    <MissionControlShell
      navSections={activeWorkspaceDefinition.navSections}
      workspaces={workspaces}
      activeWorkspaceId={activeWorkspace}
      onSelectWorkspace={(workspaceId) => {
        const nextWorkspace = workspaceId as WorkspaceId;
        setActiveWorkspace(nextWorkspace);
        setActiveView(workspaceDefinitions[nextWorkspace].defaultView);
      }}
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
