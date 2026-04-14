export type MissionControlView = "intake" | "dashboard" | "inbox" | "approvals" | "runs" | "agents" | "settings";
export type MissionControlDataSource = "api" | "fixture";
export type SystemStatus = "healthy" | "watch" | "degraded";
export type ApprovalRisk = "low" | "medium" | "high";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type RunStatus = "queued" | "in_progress" | "completed" | "failed";
export type AssetStatus = "connected" | "attention" | "unbound";

export interface DashboardSummaryData {
  approvalCount: number;
  activeRunCount: number;
  failedRunCount: number;
  activeAgentCount: number;
  unreadConversationCount: number;
  busyChannelCount: number;
  recentCompletedCount: number;
  systemStatus: SystemStatus;
  updatedAt: string;
}

export interface ConversationSummary {
  id: string;
  leadName: string;
  channel: string;
  stage: string;
  owner: string;
  unreadCount: number;
  lastMessage: string;
  lastActivityAt: string;
  sequenceState: string;
}

export interface ThreadEntry {
  id: string;
  author: string;
  direction: "inbound" | "outbound" | "internal";
  body: string;
  timestamp: string;
  status: string;
}

export interface SelectedThread {
  conversationId: string;
  leadName: string;
  company: string;
  stage: string;
  nextBestAction: string;
  tags: string[];
  notes: string[];
  messages: ThreadEntry[];
}

export interface InboxData {
  conversations: ConversationSummary[];
  selectedConversationId: string;
  threadsById: Record<string, SelectedThread>;
}

export interface ApprovalItem {
  id: string;
  title: string;
  reason: string;
  riskLevel: ApprovalRisk;
  status: ApprovalStatus;
  commandType: string;
  requestedAt: string;
  payloadPreview: string;
}

export interface RunSummary {
  id: string;
  commandType: string;
  status: RunStatus;
  businessId: string;
  environment: string;
  updatedAt: string;
  parentRunId: string | null;
  triggerRunId: string | null;
  summary: string;
}

export interface AgentSummary {
  id: string;
  name: string;
  activeRevisionId: string | null;
  activeRevisionState: string;
  environment: string;
  liveSessionCount: number;
  delegatedWorkCount: number;
}

export interface AssetSummary {
  id: string;
  name: string;
  category: string;
  status: AssetStatus;
  bindingTarget: string;
  updatedAt: string;
}

export interface MissionControlSnapshot {
  dashboard: DashboardSummaryData;
  inbox: InboxData;
  approvals: ApprovalItem[];
  runs: RunSummary[];
  agents: AgentSummary[];
  assets: AssetSummary[];
}

export interface MissionControlApi {
  getDashboard(): Promise<DashboardSummaryData>;
  getInbox(): Promise<InboxData>;
  getApprovals(): Promise<ApprovalItem[]>;
  getRuns(): Promise<RunSummary[]>;
  getAgents(): Promise<AgentSummary[]>;
  getAssets(): Promise<AssetSummary[]>;
}

export interface MissionControlApiOptions {
  baseUrl?: string;
  runtimeApiKey?: string;
  fetchImpl?: typeof fetch;
}

const defaultBaseUrl = import.meta.env.VITE_RUNTIME_API_BASE_URL ?? "";
const defaultRuntimeApiKey = import.meta.env.VITE_RUNTIME_API_KEY;

function trimTrailingSlash(value: string): string {
  return value.replace(/\/$/, "");
}

function buildUrl(baseUrl: string, path: string): string {
  const normalizedBaseUrl = trimTrailingSlash(baseUrl);
  return normalizedBaseUrl ? `${normalizedBaseUrl}${path}` : path;
}

async function requestJson<T>(
  path: string,
  options: MissionControlApiOptions,
): Promise<T> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  if (options.runtimeApiKey) {
    headers.Authorization = `Bearer ${options.runtimeApiKey}`;
  }

  const response = await fetchImpl(buildUrl(options.baseUrl ?? defaultBaseUrl, path), {
    headers,
  });

  if (!response.ok) {
    throw new Error(`Mission Control API request failed: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}

export function createMissionControlApi(
  options: MissionControlApiOptions = {},
): MissionControlApi {
  const resolvedOptions: MissionControlApiOptions = {
    baseUrl: options.baseUrl ?? defaultBaseUrl,
    runtimeApiKey: options.runtimeApiKey ?? defaultRuntimeApiKey,
    fetchImpl: options.fetchImpl,
  };

  return {
    getDashboard: () => requestJson<DashboardSummaryData>("/mission-control/dashboard", resolvedOptions),
    getInbox: () => requestJson<InboxData>("/mission-control/inbox", resolvedOptions),
    getApprovals: () => requestJson<ApprovalItem[]>("/mission-control/approvals", resolvedOptions),
    getRuns: () => requestJson<RunSummary[]>("/mission-control/runs", resolvedOptions),
    getAgents: () => requestJson<AgentSummary[]>("/mission-control/agents", resolvedOptions),
    getAssets: () => requestJson<AssetSummary[]>("/mission-control/settings/assets", resolvedOptions),
  };
}
