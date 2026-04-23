import { useEffect, useMemo, useRef, useState } from "react";

import { ContextPanel } from "./components/ContextPanel";
import {
  MissionControlShell,
  type ShellNavSection,
  type ShellWorkspace,
} from "./components/MissionControlShell";
import { OrgSwitcher } from "./components/OrgSwitcher";
import {
  createMissionControlApi,
  type AgentDetailData,
  type CatalogEntrySummary,
  type MissionControlDataSource,
  type MissionControlSnapshot,
  type MissionControlView,
  type OrganizationSummary,
  type OutboundSendResponse,
} from "./lib/api";
import {
  missionControlAgentDetailFixtures,
  missionControlCatalogFixtures,
  missionControlFixtures,
} from "./lib/fixtures";
import { queryClient } from "./lib/queryClient";
import { AgentDetailPage } from "./pages/AgentDetailPage";
import { AgentsPage, type AgentsPageOperatorView } from "./pages/AgentsPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { CatalogPage } from "./pages/CatalogPage";
import { DashboardPage } from "./pages/DashboardPage";
import { InboxPage } from "./pages/InboxPage";
import { PipelinePage } from "./pages/PipelinePage";
import { RunsPage } from "./pages/RunsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SuppressionPage } from "./pages/SuppressionPage";
import { TasksPage } from "./pages/TasksPage";

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

interface ScopeFilterOption {
  value: string;
  label: string;
}

interface MissionControlScopeState {
  orgId: string | null;
  businessId: string | null;
  environment: string | null;
}

interface CatalogInstallUiState {
  status: "submitting" | "succeeded" | "failed";
  message: string;
}

function getScopeKey(scope: MissionControlScopeState): string {
  return `${scope.orgId ?? "none"}:${scope.businessId ?? "all"}:${scope.environment ?? "all"}`;
}

function normalizeCatalogEntriesForScope(
  entries: CatalogEntrySummary[],
  scope: MissionControlScopeState,
): CatalogEntrySummary[] {
  const targetOrgId = scope.orgId ?? missionControlFixtures.governance.orgId;
  return entries.filter((entry) => entry.orgId === targetOrgId);
}

function collectScopeOptionValues(snapshot: MissionControlSnapshot): { businessIds: string[]; environments: string[] } {
  const businessValues = new Set<string>();
  const environmentValues = new Set<string>();

  for (const agent of snapshot.agents) {
    if (agent.businessId) {
      businessValues.add(agent.businessId);
    }
    if (agent.environment) {
      environmentValues.add(agent.environment);
    }
  }

  for (const run of snapshot.runs) {
    if (run.businessId) {
      businessValues.add(run.businessId);
    }
    if (run.environment) {
      environmentValues.add(run.environment);
    }
  }

  for (const revision of snapshot.governance.secretsHealth.revisions) {
    if (revision.businessId) {
      businessValues.add(revision.businessId);
    }
    if (revision.environment) {
      environmentValues.add(revision.environment);
    }
  }

  return {
    businessIds: Array.from(businessValues).sort((left, right) => left.localeCompare(right)),
    environments: Array.from(environmentValues).sort((left, right) => left.localeCompare(right)),
  };
}

function toFilterOptions(values: string[], emptyLabel: string, selectedValue: string | null): ScopeFilterOption[] {
  const normalizedValues = selectedValue && !values.includes(selectedValue) ? [...values, selectedValue] : values;
  return [{ value: "", label: emptyLabel }, ...normalizedValues.map((value) => ({ value, label: value }))];
}

function matchesSecondaryScope(
  businessId: string | null | undefined,
  environment: string | null | undefined,
  scope: MissionControlScopeState,
): boolean {
  if (scope.businessId && businessId !== scope.businessId) {
    return false;
  }

  if (scope.environment && environment !== scope.environment) {
    return false;
  }

  return true;
}

function buildPendingScopeSnapshot(scope: MissionControlScopeState): MissionControlSnapshot {
  return {
    dashboard: {
      ...missionControlFixtures.dashboard,
      approvalCount: 0,
      activeRunCount: 0,
      failedRunCount: 0,
      activeAgentCount: 0,
      unreadConversationCount: 0,
      busyChannelCount: 0,
      recentCompletedCount: 0,
      pendingLeadCount: 0,
      bookedLeadCount: 0,
      activeNonBookerEnrollmentCount: 0,
      dueManualCallCount: 0,
      repliesNeedingReviewCount: 0,
      opportunityCount: 0,
      opportunityStageSummaries: [],
      outboundProbateSummary: {
        activeCampaignCount: 0,
        readyLeadCount: 0,
        activeLeadCount: 0,
        interestedLeadCount: 0,
        suppressedLeadCount: 0,
        openTaskCount: 0,
      },
      inboundLeaseOptionSummary: {
        pendingLeadCount: 0,
        bookedLeadCount: 0,
        activeNonBookerEnrollmentCount: 0,
        dueManualCallCount: 0,
        repliesNeedingReviewCount: 0,
      },
      opportunityPipelineSummary: {
        totalOpportunityCount: 0,
        laneStageSummaries: [],
      },
      updatedAt: "Loading scope...",
    },
    inbox: {
      conversations: [],
      selectedConversationId: "",
      threadsById: {},
    },
    tasks: {
      dueCount: 0,
      tasks: [],
    },
    approvals: [],
    runs: [],
    turns: [],
    agents: [],
    assets: [],
    governance: {
      ...missionControlFixtures.governance,
      orgId: scope.orgId ?? missionControlFixtures.governance.orgId,
      pendingApprovals: [],
      secretsHealth: {
        activeRevisionCount: 0,
        healthyRevisionCount: 0,
        attentionRevisionCount: 0,
        requiredSecretCount: 0,
        configuredSecretCount: 0,
        missingSecretCount: 0,
        revisions: [],
      },
      recentAudit: [],
      usageSummary: {
        totalCount: 0,
        byKind: {},
        bySourceKind: [],
        byAgent: [],
        updatedAt: "Loading scope...",
      },
      recentUsage: [],
    },
  };
}

function normalizeSnapshotForScope(
  snapshot: MissionControlSnapshot,
  scope: MissionControlScopeState,
  fallbackViews: MissionControlView[],
): MissionControlSnapshot {
  const pendingSnapshot = buildPendingScopeSnapshot(scope);
  const isFixtureOrgMismatch = Boolean(scope.orgId && scope.orgId !== missionControlFixtures.governance.orgId);
  const hasSecondaryScope = Boolean(scope.businessId || scope.environment);
  const fallbackIncludes = (viewId: MissionControlView) => fallbackViews.includes(viewId);
  const shouldNeutralizeForOrgFallback = (viewId: MissionControlView) => isFixtureOrgMismatch && fallbackIncludes(viewId);
  const shouldNeutralizeListForOrgFallback = (viewId: MissionControlView) =>
    shouldNeutralizeForOrgFallback(viewId) && !hasSecondaryScope;
  const shouldNeutralizeForSecondaryScope = (viewId: MissionControlView) => hasSecondaryScope && fallbackIncludes(viewId);

  return {
    dashboard:
      shouldNeutralizeForOrgFallback("dashboard") || shouldNeutralizeForSecondaryScope("dashboard")
        ? pendingSnapshot.dashboard
        : snapshot.dashboard,
    inbox:
      shouldNeutralizeForOrgFallback("inbox") || shouldNeutralizeForSecondaryScope("inbox")
        ? pendingSnapshot.inbox
        : snapshot.inbox,
    tasks:
      shouldNeutralizeForOrgFallback("tasks") || shouldNeutralizeForSecondaryScope("tasks")
        ? pendingSnapshot.tasks
        : snapshot.tasks,
    approvals:
      shouldNeutralizeForOrgFallback("approvals") || shouldNeutralizeForSecondaryScope("approvals")
        ? pendingSnapshot.approvals
        : snapshot.approvals,
    runs:
      shouldNeutralizeListForOrgFallback("runs")
        ? pendingSnapshot.runs
        : snapshot.runs.filter((run) => matchesSecondaryScope(run.businessId, run.environment, scope)),
    turns:
      shouldNeutralizeListForOrgFallback("runs")
        ? pendingSnapshot.turns
        : snapshot.turns.filter((turn) => matchesSecondaryScope(turn.businessId, turn.environment, scope)),
    agents:
      shouldNeutralizeListForOrgFallback("agents")
        ? pendingSnapshot.agents
        : snapshot.agents.filter((agent) => matchesSecondaryScope(agent.businessId, agent.environment, scope)),
    assets:
      shouldNeutralizeForOrgFallback("settings") || shouldNeutralizeForSecondaryScope("settings")
        ? pendingSnapshot.assets
        : snapshot.assets,
    governance:
      shouldNeutralizeForOrgFallback("settings")
        ? pendingSnapshot.governance
        : {
            ...snapshot.governance,
            orgId: scope.orgId ?? snapshot.governance.orgId,
            secretsHealth: {
              ...snapshot.governance.secretsHealth,
              revisions: snapshot.governance.secretsHealth.revisions.filter((revision) =>
                matchesSecondaryScope(revision.businessId, revision.environment, scope),
              ),
            },
          },
  };
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

function deriveShellDataSource(fallbackViews: MissionControlView[]): MissionControlDataSource {
  return fallbackViews.length > 0 ? "fixture" : "api";
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
      slug: summaryAgent?.slug ?? agentId,
      description: summaryAgent?.description ?? null,
      businessId: summaryAgent?.businessId ?? "unknown",
      environment: summaryAgent?.environment ?? "unknown",
      lifecycleStatus: summaryAgent?.lifecycleStatus ?? "unavailable",
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
  const [catalogEntries, setCatalogEntries] = useState<CatalogEntrySummary[]>([]);
  const [catalogInstallStates, setCatalogInstallStates] = useState<Record<string, CatalogInstallUiState | undefined>>({});
  const [scopeOptionValues, setScopeOptionValues] = useState(() => collectScopeOptionValues(missionControlFixtures));
  const [organizations, setOrganizations] = useState<OrganizationSummary[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(missionControlFixtures.governance.orgId ?? null);
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);
  const [selectedEnvironment, setSelectedEnvironment] = useState<string | null>(null);
  const [selectedConversationId, setSelectedConversationId] = useState("");
  const [dataSource, setDataSource] = useState<MissionControlDataSource>("fixture");
  const [agentsDataSource, setAgentsDataSource] = useState<MissionControlDataSource>("fixture");
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
  const [selectedAgentDetail, setSelectedAgentDetail] = useState<AgentDetailData | null>(null);
  const [selectedAgentDetailSource, setSelectedAgentDetailSource] = useState<"api" | "fixture" | "degraded">("fixture");
  const [isAgentDetailLoading, setIsAgentDetailLoading] = useState(false);
  const [fallbackViews, setFallbackViews] = useState<MissionControlView[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const scope = useMemo<MissionControlScopeState>(
    () => ({
      orgId: selectedOrgId,
      businessId: selectedBusinessId,
      environment: selectedEnvironment,
    }),
    [selectedBusinessId, selectedEnvironment, selectedOrgId],
  );

  const bootstrapApi = useMemo(() => createMissionControlApi(), []);
  const api = useMemo(
    () =>
      createMissionControlApi({
        orgId: selectedOrgId ?? undefined,
        businessId: selectedBusinessId ?? undefined,
        environment: selectedEnvironment ?? undefined,
      }),
    [selectedBusinessId, selectedEnvironment, selectedOrgId],
  );
  const scopeRef = useRef(scope);

  useEffect(() => {
    scopeRef.current = scope;
  }, [scope]);

  useEffect(() => {
    let isMounted = true;

    async function loadOrganizations() {
      try {
        const liveOrganizations = await bootstrapApi.getOrganizations();
        if (!isMounted || liveOrganizations.length === 0) {
          return;
        }
        setOrganizations(liveOrganizations);
        setSelectedOrgId((currentOrgId) =>
          currentOrgId && liveOrganizations.some((organization) => organization.id === currentOrgId)
            ? currentOrgId
            : liveOrganizations[0].id,
        );
      } catch {
        if (!isMounted) {
          return;
        }
        const fallbackOrgId = snapshot.governance.orgId || missionControlFixtures.governance.orgId;
        const fallbackOrganizations = fallbackOrgId
          ? [{
              id: fallbackOrgId,
              name: fallbackOrgId,
              slug: null,
              metadata: {},
              isInternal: fallbackOrgId === "org_internal",
              createdAt: "Unknown",
              updatedAt: "Unknown",
            }]
          : [];
        setOrganizations(fallbackOrganizations);
        setSelectedOrgId((currentOrgId) => currentOrgId ?? fallbackOrgId ?? null);
      }
    }

    void loadOrganizations();

    return () => {
      isMounted = false;
    };
  }, [bootstrapApi, snapshot.governance.orgId]);

  useEffect(() => {
    setSnapshot(buildPendingScopeSnapshot(scope));
    setCatalogEntries([]);
    setSelectedConversationId("");
    setSelectedAgentId(null);
    setCatalogInstallStates({});
  }, [scope]);

  useEffect(() => {
    if (!selectedConversationId) {
      return;
    }

    setSnapshot((current) => {
      if (current.inbox.selectedConversationId === selectedConversationId) {
        return current;
      }

      return {
        ...current,
        inbox: {
          conversations: current.inbox.conversations,
          selectedConversationId: "",
          threadsById: {},
        },
      };
    });
  }, [selectedConversationId]);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      setIsLoading(true);

      const [dashboard, inbox, tasks, approvals, runs, catalog, assets, governance] = await Promise.all([
        queryClient.fetch(
          `dashboard:${selectedOrgId ?? "default"}:${selectedBusinessId ?? "all"}:${selectedEnvironment ?? "all"}`,
          api.getDashboard,
          missionControlFixtures.dashboard,
        ),
        queryClient.fetch(
          `inbox:${selectedOrgId ?? "default"}:${selectedBusinessId ?? "all"}:${selectedEnvironment ?? "all"}:${selectedConversationId || "default"}`,
          () => api.getInbox(selectedConversationId || undefined),
          missionControlFixtures.inbox,
        ),
        queryClient.fetch(
          `tasks:${selectedOrgId ?? "default"}:${selectedBusinessId ?? "all"}:${selectedEnvironment ?? "all"}`,
          api.getTasks,
          missionControlFixtures.tasks,
        ),
        queryClient.fetch(
          `approvals:${selectedOrgId ?? "default"}:${selectedBusinessId ?? "all"}:${selectedEnvironment ?? "all"}`,
          api.getApprovals,
          missionControlFixtures.approvals,
        ),
        queryClient.fetch(
          `runs:${selectedOrgId ?? "default"}:${selectedBusinessId ?? "all"}:${selectedEnvironment ?? "all"}`,
          api.getRuns,
          missionControlFixtures.runs,
        ),
        queryClient.fetch(
          `catalog:${selectedOrgId ?? "default"}`,
          api.getCatalogEntries,
          missionControlCatalogFixtures,
        ),
        queryClient.fetch(
          `assets:${selectedOrgId ?? "default"}:${selectedBusinessId ?? "all"}:${selectedEnvironment ?? "all"}`,
          api.getAssets,
          missionControlFixtures.assets,
        ),
        queryClient.fetch(
          `governance:${selectedOrgId ?? "default"}`,
          api.getGovernance,
          missionControlFixtures.governance,
        ),
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

      const nextFallbackViews = (
        [
          ["dashboard", dashboard.source],
          ["inbox", inbox.source],
          ["tasks", tasks.source],
          ["approvals", approvals.source],
          ["runs", runs.source],
          ["agents", agents.source],
          ["catalog", catalog.source],
          ["settings", governance.source === "fixture" || assets.source === "fixture" ? "fixture" : "api"],
          ["suppression", dashboard.source],
        ] as const
      )
        .filter(([, source]) => source === "fixture")
        .map(([viewId]) => viewId);
      const pendingSnapshot = buildPendingScopeSnapshot(scope);
      const loadedSnapshot = {
        dashboard: dashboard.data,
        inbox: inbox.source === "fixture" && selectedConversationId ? pendingSnapshot.inbox : inbox.data,
        tasks: tasks.data,
        approvals: approvals.data,
        runs: runs.data,
        turns: missionControlFixtures.turns,
        agents: agents.data,
        assets: assets.data,
        governance: governance.data,
      };
      const nextSnapshot = normalizeSnapshotForScope(
        loadedSnapshot,
        scope,
        nextFallbackViews,
      );
      const nextCatalogEntries = normalizeCatalogEntriesForScope(catalog.data, scope);
      setSnapshot(nextSnapshot);
      setCatalogEntries(nextCatalogEntries);
      setScopeOptionValues(collectScopeOptionValues(loadedSnapshot));
      setDataSource(deriveShellDataSource(nextFallbackViews));
      setAgentsDataSource(agents.source);
      setFallbackViews(nextFallbackViews);
      setIsLoading(false);
    }

    void load();

    return () => {
      isMounted = false;
    };
  }, [api, scope, selectedConversationId]);

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
      setSelectedAgentDetail(null);
      setSelectedAgentDetailSource("fixture");
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
        setFallbackViews((current) => {
          const next = current.filter((viewId) => viewId !== "agents");
          setDataSource(deriveShellDataSource(next));
          return next;
        });
      } catch {
        // Keep the current fixture-backed agents surface until the next explicit retry opportunity.
      }
    }

    void refreshAgents();

    return () => {
      isMounted = false;
    };
  }, [activeView, agentsDataSource, api]);

  const normalizedSearchValue = searchValue.trim().toLowerCase();
  const businessFilterOptions = useMemo(
    () => toFilterOptions(scopeOptionValues.businessIds, "All businesses", selectedBusinessId),
    [scopeOptionValues.businessIds, selectedBusinessId],
  );
  const environmentFilterOptions = useMemo(
    () => toFilterOptions(scopeOptionValues.environments, "All environments", selectedEnvironment),
    [scopeOptionValues.environments, selectedEnvironment],
  );
  const organizationOptions = useMemo(() => {
    if (organizations.length > 0) {
      return organizations;
    }

    const fallbackOrgId = selectedOrgId ?? snapshot.governance.orgId;
    return fallbackOrgId
      ? [{
          id: fallbackOrgId,
          name: fallbackOrgId,
          slug: null,
          metadata: {},
          isInternal: fallbackOrgId === "org_internal",
          createdAt: "Unknown",
          updatedAt: "Unknown",
        }]
      : [];
  }, [organizations, selectedOrgId, snapshot.governance.orgId]);

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
    (selectedConversationId ? undefined : snapshot.inbox.threadsById[snapshot.inbox.selectedConversationId]);
  const contextThread = visibleThread ?? {
    nextBestAction: "Select a thread to inspect context.",
    stage: "No thread selected",
    tags: [] as string[],
    notes: ["No conversation detail is currently available."],
  };
  const inboxMainContent = visibleThread ? (
    <InboxPage
      data={{ ...snapshot.inbox, conversations: filteredConversations }}
      selectedConversationId={visibleConversationId}
      onSelectConversation={setSelectedConversationId}
      onSendSmsTest={unsupportedSend}
      onSendEmailTest={unsupportedSend}
    />
  ) : (
    <section className="panel-stack">
      <div className="section-heading">
        <h3>{isLoading ? "Loading conversations" : "No conversations in scope"}</h3>
        <span>{selectedOrgId ?? "No organization selected"}</span>
      </div>
      <p className="panel-copy">
        {isLoading
          ? "Refreshing the selected scope. Prior-scope inbox content stays hidden until the reload settles."
          : "No conversation detail is available for the selected organization, business, and environment."}
      </p>
    </section>
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

  const filteredCatalogEntries = useMemo(
    () =>
      catalogEntries.filter((entry) =>
        includesSearch(
          [
            entry.name,
            entry.slug,
            entry.summary,
            entry.description,
            entry.hostAdapterKind,
            entry.providerKind,
            ...entry.providerCapabilities,
            ...entry.requiredSkillIds,
            ...entry.requiredSecretNames,
          ],
          normalizedSearchValue,
        ),
      ),
    [catalogEntries, normalizedSearchValue],
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
  const selectedAgentMatchedApiSummary =
    agentsDataSource === "api" &&
    selectedAgentDetailSource === "api" &&
    selectedAgentSummary &&
    selectedAgentDetail &&
    selectedAgentDetail.agent.id === selectedAgentSummary.id &&
    selectedAgentDetail.agent.activeRevisionId === selectedAgentSummary.activeRevisionId &&
    selectedAgentDetail.agent.activeRevisionState === selectedAgentSummary.activeRevisionState
      ? selectedAgentSummary
      : null;
  const selectedAgentHostAdapter = selectedAgentMatchedApiSummary?.hostAdapter;

  useEffect(() => {
    if (!selectedAgentId) {
      return;
    }

    if (!selectedAgentIsVisible) {
      setSelectedAgentId(null);
    }
  }, [selectedAgentIsVisible, selectedAgentId]);

  const selectedAgentContextItems = selectedAgentDetail
    ? canRenderSelectedAgentDetail
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
      : ["Fetching runtime lifecycle context for the selected agent."]
    : selectedAgentId && selectedAgentIsVisible
      ? ["Fetching runtime lifecycle context for the selected agent."]
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

  const isCatalogInstallEnabled = !fallbackViews.includes("catalog");
  const catalogInstallDisabledReason = isCatalogInstallEnabled
    ? undefined
    : "Install is unavailable while the catalog is running on fixture fallback.";

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

  async function handleCatalogInstall(entryId: string, request: { businessId: string; environment: string; name: string }) {
    const installScopeKey = getScopeKey(scopeRef.current);
    setCatalogInstallStates((current) => ({
      ...current,
      [entryId]: { status: "submitting", message: `Installing into ${request.businessId}/${request.environment}...` },
    }));

    try {
      const result = await api.installCatalogEntry({
        catalogEntryId: entryId,
        businessId: request.businessId,
        environment: request.environment,
        name: request.name,
      });
      if (installScopeKey !== getScopeKey(scopeRef.current)) {
        return;
      }

      const installMatchesCurrentView = matchesSecondaryScope(
        result.agent.businessId,
        result.agent.environment,
        scopeRef.current,
      );
      const successMessage = installMatchesCurrentView
        ? `Installed ${result.agent.name} as ${result.agent.slug} in ${result.agent.businessId}/${result.agent.environment}.`
        : `Installed ${result.agent.name} as ${result.agent.slug} in ${result.agent.businessId}/${result.agent.environment}. It landed outside the current filtered view.`;

      setCatalogInstallStates((current) => ({
        ...current,
        [entryId]: {
          status: "succeeded",
          message: successMessage,
        },
      }));

      if (!installMatchesCurrentView) {
        return;
      }

      try {
        const liveAgents = await api.getAgents();
        if (installScopeKey !== getScopeKey(scopeRef.current)) {
          return;
        }
        setSnapshot((current) => ({ ...current, agents: liveAgents }));
        setAgentsDataSource("api");
        setFallbackViews((current) => {
          const next = current.filter((viewId) => viewId !== "agents");
          setDataSource(deriveShellDataSource(next));
          return next;
        });
      } catch {
        // Keep the install success visible even if the follow-up agents refresh is unavailable.
      }
    } catch (error) {
      if (installScopeKey !== getScopeKey(scopeRef.current)) {
        return;
      }
      const message = error instanceof Error
        ? error.message.replace(/^Mission Control API request failed:\s*/, "")
        : "Catalog install failed.";
      setCatalogInstallStates((current) => ({
        ...current,
        [entryId]: { status: "failed", message },
      }));
    }
  }

  const catalogPageView: WorkspacePage = {
    title: "Internal catalog",
    subtitle: "Browse installable agent revisions, review compatibility requirements, and install into a selected target scope.",
    mainContent: (
      <CatalogPage
        entries={filteredCatalogEntries}
        installEnabled={isCatalogInstallEnabled}
        installDisabledReason={catalogInstallDisabledReason}
        hasActiveSearch={normalizedSearchValue.length > 0}
        installStates={catalogInstallStates}
        onInstall={handleCatalogInstall}
        selectedBusinessId={selectedBusinessId}
        selectedEnvironment={selectedEnvironment}
      />
    ),
    contextContent: (
      <ContextPanel
        eyebrow="Catalog posture"
        title="Install before runtime pain"
        items={[
          `${filteredCatalogEntries.length} catalog entries are visible in the current org scope`,
          `${filteredCatalogEntries.filter((entry) => entry.requiredSecretNames.length > 0).length} entries require secrets before install`,
          `${filteredCatalogEntries.filter((entry) => entry.requiredSkillIds.length > 0).length} entries carry skill dependencies`,
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
          items: [
            { id: "agents", label: "Agents", badge: filteredAgents.length },
            { id: "catalog", label: "Catalog", badge: filteredCatalogEntries.length },
          ],
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
                selectedAgentHostAdapter={selectedAgentHostAdapter}
                selectedAgentSummary={selectedAgentMatchedApiSummary}
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
          mainContent: inboxMainContent,
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
        catalog: catalogPageView,
      },
    },
    marketing: {
      label: "Marketing",
      defaultView: "agents",
      navSections: [
        {
          title: "Agents",
          items: [
            { id: "agents", label: "Agents", badge: filteredAgents.length },
            { id: "catalog", label: "Catalog", badge: filteredCatalogEntries.length },
          ],
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
                selectedAgentHostAdapter={selectedAgentHostAdapter}
                selectedAgentSummary={selectedAgentMatchedApiSummary}
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
          mainContent: inboxMainContent,
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
        catalog: catalogPageView,
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
              id: "catalog",
              label: "Catalog",
              badge: filteredCatalogEntries.length,
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
        catalog: catalogPageView,
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
  const isFullFixtureMode = fallbackViews.length === 9;
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
  const scopeControls = (
    <OrgSwitcher
      orgs={organizationOptions.map((organization) => ({
        id: organization.id,
        label: organization.name,
      }))}
      activeOrgId={selectedOrgId ?? organizationOptions[0]?.id ?? ""}
      onSelectOrg={(orgId) => {
        setSelectedBusinessId(null);
        setSelectedEnvironment(null);
        setSelectedOrgId(orgId || null);
      }}
      businessOptions={businessFilterOptions.map((option) => ({ id: option.value, label: option.label }))}
      activeBusinessId={selectedBusinessId ?? ""}
      onSelectBusiness={(businessId) => setSelectedBusinessId(businessId || null)}
      environmentOptions={environmentFilterOptions.map((option) => ({ id: option.value, label: option.label }))}
      activeEnvironment={selectedEnvironment ?? ""}
      onSelectEnvironment={(environment) => setSelectedEnvironment(environment || null)}
    />
  );

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
      headerSlot={scopeControls}
      mainContent={activePage.mainContent}
      contextContent={activePage.contextContent}
    />
  );
}
