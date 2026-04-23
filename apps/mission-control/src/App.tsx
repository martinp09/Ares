import { useEffect, useMemo, useState } from "react";

import { ContextPanel } from "./components/ContextPanel";
import {
  MissionControlShell,
  type ShellNavSection,
  type ShellWorkspace,
} from "./components/MissionControlShell";
import {
  createMissionControlApi,
  type AgentDetailData,
  type MissionControlDataSource,
  type MissionControlSnapshot,
  type MissionControlView,
  type OutboundSendResponse,
} from "./lib/api";
import { missionControlAgentDetailFixtures, missionControlFixtures } from "./lib/fixtures";
import { queryClient } from "./lib/queryClient";
import { AgentDetailPage } from "./pages/AgentDetailPage";
import { AgentsPage, type AgentsPageOperatorView } from "./pages/AgentsPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { InboxPage } from "./pages/InboxPage";
import { PipelinePage } from "./pages/PipelinePage";
import { RunsPage } from "./pages/RunsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SuppressionPage } from "./pages/SuppressionPage";
import { TasksPage } from "./pages/TasksPage";

const api = createMissionControlApi();

async function unsupportedSend(): Promise<OutboundSendResponse> {
  return {
    status: "unsupported",
    providerMessageId: null,
    errorMessage: "Provider test actions are not wired in this Mission Control build.",
  };
}

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

function fallbackAgentDetailForSnapshot(
  snapshot: MissionControlSnapshot,
  agentId: string,
  preferFixture = false,
): AgentDetailData {
  const summaryAgent = snapshot.agents.find((agent) => agent.id === agentId);
  const fallbackFixture = missionControlAgentDetailFixtures[agentId];

  if (preferFixture && fallbackFixture) {
    return fallbackFixture;
  }

  return {
    agent: {
      id: agentId,
      name: summaryAgent?.name ?? "Unknown agent",
      slug: agentId,
      description: null,
      businessId: "unavailable",
      environment: summaryAgent?.environment ?? "unknown",
      lifecycleStatus: "unavailable",
      activeRevisionId: summaryAgent?.activeRevisionId ?? null,
      activeRevisionState: summaryAgent?.activeRevisionState ?? "unknown",
    },
    revisions: [],
    releaseHistory: [],
    secretsHealth: null,
    recentAudit: [],
    usageSummary: { totalCount: 0, byKind: {}, bySourceKind: [], byAgent: [], updatedAt: "Unknown" },
    recentUsage: [],
    recentTurns: [],
    degradedSections: ["revisions", "releaseHistory", "secretsHealth", "recentAudit", "usage", "recentTurns"],
  };
}

export default function App() {
  const [activeWorkspace, setActiveWorkspace] = useState<WorkspaceId>("lead-machine");
  const [activeView, setActiveView] = useState<MissionControlView>("agents");
  const [searchValue, setSearchValue] = useState("");
  const [snapshot, setSnapshot] = useState<MissionControlSnapshot>(missionControlFixtures);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [dataSource, setDataSource] = useState<MissionControlDataSource>("fixture");
  const [agentsDataSource, setAgentsDataSource] = useState<MissionControlDataSource>("fixture");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedAgentDetail, setSelectedAgentDetail] = useState<AgentDetailData | null>(null);
  const [selectedAgentDetailSource, setSelectedAgentDetailSource] = useState<"api" | "fixture" | "degraded">("fixture");
  const [isAgentDetailLoading, setIsAgentDetailLoading] = useState(false);
  const [fallbackViews, setFallbackViews] = useState<MissionControlView[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoading(true);

      const [dashboard, inbox, tasks, approvals, runs, assets, governance] = await Promise.all([
        queryClient.fetch("dashboard", api.getDashboard, missionControlFixtures.dashboard),
        queryClient.fetch(
          `inbox:${selectedConversationId || "default"}`,
          () => api.getInbox(selectedConversationId || undefined),
          missionControlFixtures.inbox,
        ),
        queryClient.fetch("tasks", api.getTasks, missionControlFixtures.tasks),
        queryClient.fetch("approvals", api.getApprovals, missionControlFixtures.approvals),
        queryClient.fetch("runs", api.getRuns, missionControlFixtures.runs),
        queryClient.fetch("assets", api.getAssets, missionControlFixtures.assets),
        queryClient.fetch("governance", api.getGovernance, missionControlFixtures.governance),
      ]);
      let agents: { data: MissionControlSnapshot["agents"]; source: MissionControlDataSource };
      try {
        agents = { data: await api.getAgents(), source: "api" };
      } catch {
        agents = { data: missionControlFixtures.agents, source: "fixture" };
      }

      if (!isMounted) {
        return;
      }

      setSnapshot({
        dashboard: dashboard.data,
        inbox: inbox.data,
        tasks: tasks.data,
        approvals: approvals.data,
        runs: runs.data,
        turns: missionControlFixtures.turns,
        agents: agents.data,
        assets: assets.data,
        governance: governance.data,
      });
      setDataSource(
        [dashboard, inbox, tasks, approvals, runs, agents, assets, governance].some((result) => result.source === "fixture")
          ? "fixture"
          : "api",
      );
      setAgentsDataSource(agents.source);
      setFallbackViews(
        (
          [
            ["dashboard", dashboard.source],
            ["inbox", inbox.source],
            ["tasks", tasks.source],
            ["approvals", approvals.source],
            ["runs", runs.source],
            ["agents", agents.source],
            ["settings", governance.source === "fixture" || assets.source === "fixture" ? "fixture" : "api"],
            ["suppression", dashboard.source],
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

  useEffect(() => {
    if (!selectedAgentId) {
      setSelectedAgentDetail(null);
      setSelectedAgentDetailSource("fixture");
      setIsAgentDetailLoading(false);
      return;
    }

    const agentId = selectedAgentId;
    let isMounted = true;

    async function loadAgentDetail() {
      setIsAgentDetailLoading(true);
      try {
        const detail = await api.getAgentDetail(agentId);
        if (!isMounted) {
          return;
        }
        setSelectedAgentDetail(detail);
        setSelectedAgentDetailSource("api");
      } catch {
        if (!isMounted) {
          return;
        }
        setSelectedAgentDetail(fallbackAgentDetailForSnapshot(snapshot, agentId, agentsDataSource === "fixture"));
        setSelectedAgentDetailSource(agentsDataSource === "fixture" ? "fixture" : "degraded");
      } finally {
        if (isMounted) {
          setIsAgentDetailLoading(false);
        }
      }
    }

    void loadAgentDetail();

    return () => {
      isMounted = false;
    };
  }, [selectedAgentId, snapshot, agentsDataSource]);

  useEffect(() => {
    if (activeView !== "agents" || agentsDataSource !== "fixture") {
      return;
    }

    let isMounted = true;

    async function refreshAgents() {
      try {
        const liveAgents = await api.getAgents();
        if (!isMounted) {
          return;
        }
        setSnapshot((current) => ({ ...current, agents: liveAgents }));
        setAgentsDataSource("api");
      } catch {
        // Keep the current fixture-backed agents surface until the next explicit retry opportunity.
      }
    }

    void refreshAgents();

    return () => {
      isMounted = false;
    };
  }, [activeView, agentsDataSource]);

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

  const filteredAgents = useMemo(
    () =>
      snapshot.agents.filter((agent) =>
        includesSearch(
          [
            agent.name,
            agent.id,
            agent.activeRevisionId,
            agent.activeRevisionState,
            agent.environment,
            agent.release?.eventType,
            agent.release?.releaseChannel,
          ],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.agents],
  );

  const selectedAgentSummary = useMemo(
    () => snapshot.agents.find((agent) => agent.id === selectedAgentId) ?? null,
    [selectedAgentId, snapshot.agents],
  );
  const selectedAgentIsVisible = Boolean(selectedAgentId && filteredAgents.some((agent) => agent.id === selectedAgentId));
  const canRenderSelectedAgentDetail = Boolean(
    selectedAgentId &&
      selectedAgentIsVisible &&
      selectedAgentDetail &&
      selectedAgentDetail.agent.id === selectedAgentId,
  );

  useEffect(() => {
    if (!selectedAgentId) {
      return;
    }

    if (!selectedAgentIsVisible) {
      setSelectedAgentId(null);
    }
  }, [selectedAgentIsVisible, selectedAgentId]);

  const selectedAgentContextItems = selectedAgentDetail
    ? [
        selectedAgentDetail.degradedSections.includes("revisions")
          ? "Revision data is temporarily unavailable from the current live read models"
          : `${selectedAgentDetail.revisions.length} revisions are tracked for this agent`,
        selectedAgentDetail.degradedSections.includes("releaseHistory")
          ? "Release history is temporarily unavailable from the current live read models"
          : `${selectedAgentDetail.releaseHistory.length} release events are visible in the runtime history`,
        selectedAgentDetail.degradedSections.includes("secretsHealth")
          ? "Secrets health is temporarily unavailable from the current live read models"
          : selectedAgentDetail.secretsHealth
            ? `${selectedAgentDetail.secretsHealth.missingSecretCount} missing secrets on the active revision`
            : "No active revision secrets posture is available",
      ]
    : ["Select an agent to inspect runtime lifecycle detail."];

  const filteredApprovals = useMemo(
    () =>
      snapshot.approvals.filter((approval) =>
        includesSearch(
          [approval.title, approval.reason, approval.commandType, approval.payloadPreview, approval.riskLevel, approval.status],
          normalizedSearchValue,
        ),
      ),
    [normalizedSearchValue, snapshot.approvals],
  );

  const filteredOpportunityStages = useMemo(
    () =>
      (snapshot.dashboard.opportunityPipelineSummary?.laneStageSummaries ??
        snapshot.dashboard.opportunityStageSummaries ??
        []
      ).filter((stage) => includesSearch([stage.sourceLane, stage.stage, stage.count], normalizedSearchValue)),
    [
      normalizedSearchValue,
      snapshot.dashboard.opportunityPipelineSummary?.laneStageSummaries,
      snapshot.dashboard.opportunityStageSummaries,
    ],
  );

  const settingsPage: WorkspacePage = {
    title: "Settings / Governance",
    subtitle: "Read-only governance posture for approvals, secrets, audit, and usage.",
    mainContent: <SettingsPage governance={snapshot.governance} assets={snapshot.assets} />,
    contextContent: (
      <ContextPanel
        eyebrow="Governance posture"
        title="Operator trust surface"
        items={[
          `${snapshot.governance.pendingApprovals.length} pending approvals are visible`,
          `${snapshot.governance.secretsHealth.attentionRevisionCount} active revisions need secret attention`,
          `${snapshot.governance.recentAudit.length} recent audit events are surfaced read-only`,
        ]}
      />
    ),
  };

  const workspaces: ShellWorkspace[] = [
    { id: "lead-machine", label: "Lead Machine" },
    { id: "marketing", label: "Marketing" },
    { id: "pipeline", label: "Pipeline" },
  ];

  const leadMachineOperatorViews: AgentsPageOperatorView[] = [
    {
      id: "dashboard",
      label: "Queue",
      metricLabel: "ready leads",
      metricValue: snapshot.dashboard.outboundProbateSummary?.readyLeadCount ?? snapshot.dashboard.pendingLeadCount ?? 0,
      description: "Review the outbound probate queue alongside the active agents.",
    },
    {
      id: "inbox",
      label: "Replies",
      metricLabel: "open threads",
      metricValue: filteredConversations.length,
      description: "Keep human reply review adjacent to the agents in the current workspace.",
    },
    {
      id: "approvals",
      label: "Approvals",
      metricLabel: "pending decisions",
      metricValue: filteredApprovals.length,
      description: "Operator approvals stay visible beside release posture and runtime state.",
    },
    {
      id: "runs",
      label: "Campaign State",
      metricLabel: "tracked runs",
      metricValue: filteredRuns.length,
      description: "Root and child automation runs remain attached to the agents that triggered them.",
    },
  ];

  const marketingOperatorViews: AgentsPageOperatorView[] = [
    {
      id: "dashboard",
      label: "Overview",
      metricLabel: "pending leads",
      metricValue: snapshot.dashboard.inboundLeaseOptionSummary?.pendingLeadCount ?? snapshot.dashboard.pendingLeadCount ?? 0,
      description: "See the current operator workspace from the agents outward.",
    },
    {
      id: "inbox",
      label: "Submissions",
      metricLabel: "visible threads",
      metricValue: filteredConversations.length,
      description: "New submissions and replies stay adjacent to the agents handling follow-up.",
    },
    {
      id: "approvals",
      label: "Approvals",
      metricLabel: "pending decisions",
      metricValue: filteredApprovals.length,
      description: "Human checkpoints remain explicit before marketing agents advance.",
    },
    {
      id: "runs",
      label: "Runs",
      metricLabel: "tracked runs",
      metricValue: filteredRuns.length,
      description: "Inspect runtime execution without leaving the agent-centered workspace.",
    },
  ];

  const workspaceDefinitions: Record<WorkspaceId, WorkspaceDefinition> = {
    "lead-machine": {
      label: "Lead Machine",
      defaultView: "agents",
      navSections: [
        {
          title: "Agents",
          items: [{ id: "agents", label: "Agents", badge: filteredAgents.length }],
        },
        {
          title: "Operator views",
          items: [
            {
              id: "dashboard",
              label: "Queue",
              badge: snapshot.dashboard.outboundProbateSummary?.readyLeadCount ?? snapshot.dashboard.pendingLeadCount ?? 0,
            },
            { id: "inbox", label: "Replies", badge: snapshot.dashboard.unreadConversationCount },
            { id: "approvals", label: "Approvals", badge: filteredApprovals.length },
            { id: "runs", label: "Campaign State", badge: filteredRuns.length },
            { id: "suppression", label: "Suppression", badge: snapshot.dashboard.repliesNeedingReviewCount ?? 0 },
            {
              id: "tasks",
              label: "Tasks",
              badge: snapshot.dashboard.outboundProbateSummary?.openTaskCount ?? snapshot.dashboard.dueManualCallCount ?? 0,
            },
            {
              id: "settings",
              label: "Settings",
              badge: snapshot.governance.pendingApprovals.length,
            },
          ],
        },
      ],
      pages: {
        agents: {
          title: selectedAgentId && selectedAgentIsVisible && selectedAgentSummary ? `Lead Machine / ${selectedAgentSummary.name}` : "Lead Machine / Agents",
          subtitle: selectedAgentId && selectedAgentIsVisible
            ? "Read-only lifecycle detail for the selected agent. Publish and rollback remain runtime-owned in this bounded slice."
            : "Agents are the first stop in this workspace; queue, replies, approvals, and runs stay adjacent operator views.",
          mainContent: selectedAgentId && selectedAgentIsVisible ? (
            isAgentDetailLoading || !canRenderSelectedAgentDetail ? (
              <section className="panel-stack">
                <div className="section-heading">
                  <h3>Loading agent lifecycle</h3>
                  <span>{selectedAgentSummary?.name ?? selectedAgentId}</span>
                </div>
                <p className="panel-copy">Fetching revisions, release posture, secrets health, audit, usage, and recent turns.</p>
              </section>
            ) : (
              <AgentDetailPage
                dataSource={selectedAgentDetailSource}
                detail={selectedAgentDetail!}
                onBack={() => setSelectedAgentId(null)}
              />
            )
          ) : (
            <AgentsPage
              agents={filteredAgents}
              dataSource={agentsDataSource}
              onSelectAgent={setSelectedAgentId}
              operatorViews={leadMachineOperatorViews}
              selectedAgentId={selectedAgentId}
              workspaceLabel="Lead Machine"
            />
          ),
          contextContent: selectedAgentId && selectedAgentIsVisible ? (
            <ContextPanel
              eyebrow="Selected agent"
              title={selectedAgentSummary?.name ?? "Agent lifecycle"}
              items={selectedAgentContextItems}
            />
          ) : (
            <ContextPanel
              eyebrow="Agent posture"
              title="Agent-centered operator cockpit"
              items={[
                `${filteredAgents.length} agents are visible in this workspace`,
                `${filteredApprovals.length} approvals remain pending next to the active agents`,
                `${filteredRuns.length} runtime runs stay attached to operator context`,
              ]}
            />
          ),
        },
        dashboard: {
          title: "Lead Machine / Queue",
          subtitle: "Outbound probate queue, campaign posture, and operator attention in one lane.",
          mainContent: <DashboardPage data={snapshot.dashboard} />,
          contextContent: (
            <ContextPanel
              eyebrow="Probate lane"
              title="Outbound machine posture"
              items={[
                `${snapshot.dashboard.outboundProbateSummary?.readyLeadCount ?? snapshot.dashboard.pendingLeadCount ?? 0} probate leads ready for operator review`,
                `${snapshot.dashboard.outboundProbateSummary?.activeCampaignCount ?? snapshot.dashboard.activeRunCount} active campaign flows`,
                `${snapshot.dashboard.outboundProbateSummary?.openTaskCount ?? snapshot.dashboard.dueManualCallCount ?? 0} follow-ups waiting on a human`,
              ]}
            />
          ),
        },
        inbox: {
          title: "Lead Machine / Replies",
          subtitle: "Review reply context, suppression signals, and next actions without leaving the agent-centered workspace.",
          mainContent: (
            <InboxPage
              data={{ ...snapshot.inbox, conversations: filteredConversations }}
              selectedConversationId={visibleConversationId}
              onSelectConversation={setSelectedConversationId}
              onSendSmsTest={unsupportedSend}
              onSendEmailTest={unsupportedSend}
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
        approvals: {
          title: "Lead Machine / Approvals",
          subtitle: "Human approval decisions remain adjacent to the agents and runs that triggered them.",
          mainContent: <ApprovalsPage approvals={filteredApprovals} />,
          contextContent: (
            <ContextPanel
              eyebrow="Approval posture"
              title="Human checkpoints stay explicit"
              items={[
                `${filteredApprovals.length} approvals are visible in the current workspace`,
                "Approvals remain attached to the agents and runtime state that requested them.",
              ]}
            />
          ),
        },
        suppression: {
          title: "Lead Machine / Suppression",
          subtitle: "Track review queues, blocked leads, and the exceptions that stop the lane cold.",
          mainContent: (
            <SuppressionPage
              dashboard={snapshot.dashboard}
              inbox={snapshot.inbox}
              runs={filteredRuns}
              tasks={{ dueCount: filteredTasks.length, tasks: filteredTasks }}
            />
          ),
          contextContent: (
            <ContextPanel
              eyebrow="Suppression posture"
              title="Exceptions stay explicit"
              items={[
                `${snapshot.dashboard.repliesNeedingReviewCount ?? 0} replies need review`,
                `${snapshot.dashboard.failedRunCount} failed runs`,
                `${filteredTasks.length} tasks waiting on human action`,
              ]}
            />
          ),
        },
        runs: {
          title: "Lead Machine / Campaign State",
          subtitle: "Inspect outbound automation runs and keep campaign lineage visible beside the active agents.",
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
        settings: settingsPage,
      },
    },
    marketing: {
      label: "Marketing",
      defaultView: "agents",
      navSections: [
        {
          title: "Agents",
          items: [{ id: "agents", label: "Agents", badge: filteredAgents.length }],
        },
        {
          title: "Operator views",
          items: [
            {
              id: "dashboard",
              label: "Overview",
              badge:
                snapshot.dashboard.inboundLeaseOptionSummary?.pendingLeadCount ?? snapshot.dashboard.pendingLeadCount ?? 0,
            },
            { id: "inbox", label: "Submissions", badge: snapshot.dashboard.unreadConversationCount },
            { id: "approvals", label: "Approvals", badge: filteredApprovals.length },
            { id: "runs", label: "Runs", badge: filteredRuns.length },
            {
              id: "tasks",
              label: "Tasks",
              badge:
                snapshot.dashboard.inboundLeaseOptionSummary?.dueManualCallCount ??
                snapshot.dashboard.dueManualCallCount ??
                0,
            },
            {
              id: "settings",
              label: "Settings",
              badge: snapshot.governance.pendingApprovals.length,
            },
          ],
        },
      ],
      pages: {
        agents: {
          title: selectedAgentId && selectedAgentIsVisible && selectedAgentSummary ? `Marketing / ${selectedAgentSummary.name}` : "Marketing / Agents",
          subtitle: selectedAgentId && selectedAgentIsVisible
            ? "Read-only lifecycle detail for the selected agent. Publish and rollback remain runtime-owned in this bounded slice."
            : "Agents are the first stop in this workspace while submissions, approvals, and runs stay visible around them.",
          mainContent: selectedAgentId && selectedAgentIsVisible ? (
            isAgentDetailLoading || !canRenderSelectedAgentDetail ? (
              <section className="panel-stack">
                <div className="section-heading">
                  <h3>Loading agent lifecycle</h3>
                  <span>{selectedAgentSummary?.name ?? selectedAgentId}</span>
                </div>
                <p className="panel-copy">Fetching revisions, release posture, secrets health, audit, usage, and recent turns.</p>
              </section>
            ) : (
              <AgentDetailPage
                dataSource={selectedAgentDetailSource}
                detail={selectedAgentDetail!}
                onBack={() => setSelectedAgentId(null)}
              />
            )
          ) : (
            <AgentsPage
              agents={filteredAgents}
              dataSource={agentsDataSource}
              onSelectAgent={setSelectedAgentId}
              operatorViews={marketingOperatorViews}
              selectedAgentId={selectedAgentId}
              workspaceLabel="Marketing"
            />
          ),
          contextContent: selectedAgentId && selectedAgentIsVisible ? (
            <ContextPanel
              eyebrow="Selected agent"
              title={selectedAgentSummary?.name ?? "Agent lifecycle"}
              items={selectedAgentContextItems}
            />
          ) : (
            <ContextPanel
              eyebrow="Agent posture"
              title="Agent-centered marketing workspace"
              items={[
                `${filteredAgents.length} agents are visible in this workspace`,
                `${filteredApprovals.length} approvals are waiting on operator review`,
                `${filteredRuns.length} runs remain visible beside the current agents`,
              ]}
            />
          ),
        },
        dashboard: {
          title: "Marketing / Overview",
          subtitle: "Lease-option submissions, booked vs pending, and non-booker follow-up health.",
          mainContent: <DashboardPage data={snapshot.dashboard} />,
          contextContent: (
            <ContextPanel
              eyebrow="Lease-option lane"
              title="Inbound marketing posture"
              items={[
                `${snapshot.dashboard.inboundLeaseOptionSummary?.pendingLeadCount ?? snapshot.dashboard.pendingLeadCount ?? 0} pending lease-option leads`,
                `${snapshot.dashboard.inboundLeaseOptionSummary?.bookedLeadCount ?? snapshot.dashboard.bookedLeadCount ?? 0} booked consultations`,
                `${snapshot.dashboard.inboundLeaseOptionSummary?.activeNonBookerEnrollmentCount ?? snapshot.dashboard.activeNonBookerEnrollmentCount ?? 0} active non-booker sequences`,
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
              onSendSmsTest={unsupportedSend}
              onSendEmailTest={unsupportedSend}
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
        approvals: {
          title: "Marketing / Approvals",
          subtitle: "Keep human review adjacent to the marketing agents and outbound actions that requested approval.",
          mainContent: <ApprovalsPage approvals={filteredApprovals} />,
          contextContent: (
            <ContextPanel
              eyebrow="Approval posture"
              title="Operator checkpoints remain explicit"
              items={[
                `${filteredApprovals.length} approvals are visible in the current marketing lane`,
                "Approvals stay attached to the agents and live runtime posture, not hidden behind a separate shell.",
              ]}
            />
          ),
        },
        runs: {
          title: "Marketing / Runs",
          subtitle: "Inspect marketing automation runs without leaving the agent-first workspace.",
          mainContent: <RunsPage runs={filteredRuns} />,
          contextContent: (
            <ContextPanel
              eyebrow="Runtime posture"
              title="Marketing execution remains visible"
              items={[
                `${filteredRuns.length} runs match the current search scope`,
                "Agent operations and runtime lineage stay in the same cockpit.",
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
                `${snapshot.dashboard.inboundLeaseOptionSummary?.repliesNeedingReviewCount ?? snapshot.dashboard.repliesNeedingReviewCount ?? 0} replies need review`,
                `${snapshot.dashboard.inboundLeaseOptionSummary?.dueManualCallCount ?? filteredTasks.length} manual call checkpoints remain active`,
              ]}
            />
          ),
        },
        settings: settingsPage,
      },
    },
    pipeline: {
      label: "Pipeline",
      defaultView: "pipeline",
      navSections: [
        {
          title: "Pipeline",
          items: [
            {
              id: "pipeline",
              label: "Board",
              badge:
                snapshot.dashboard.opportunityPipelineSummary?.totalOpportunityCount ??
                snapshot.dashboard.opportunityCount ??
                0,
            },
            {
              id: "settings",
              label: "Settings",
              badge: snapshot.governance.pendingApprovals.length,
            },
          ],
        },
      ],
      pages: {
        pipeline: {
          title: "Pipeline Board",
          subtitle: "Minimal downstream opportunity stages without collapsing lane boundaries.",
          mainContent: (
            <PipelinePage
              stages={filteredOpportunityStages}
              totalCount={
                snapshot.dashboard.opportunityPipelineSummary?.totalOpportunityCount ??
                snapshot.dashboard.opportunityCount ??
                filteredOpportunityStages.length
              }
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
        settings: settingsPage,
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
  const isFullFixtureMode = fallbackViews.length === 8;
  const statusBadge = isLoading
    ? "Loading shell"
    : dataSource === "api"
      ? "Live API"
      : isFullFixtureMode
        ? "Fixture mode"
        : `API + fixture fallback${fallbackLabel}`;
  const footerNote = isLoading
    ? "Collecting Mission Control surfaces..."
    : dataSource === "api"
      ? "Mission Control is reading Hermes runtime data."
      : isFullFixtureMode
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
        setSelectedAgentId(null);
      }}
      activeItemId={activeView}
      onNavigate={(itemId) => {
        setActiveView(itemId as MissionControlView);
        if (itemId !== "agents") {
          setSelectedAgentId(null);
        }
      }}
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
