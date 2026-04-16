export type MissionControlView =
  | "intake"
  | "dashboard"
  | "inbox"
  | "approvals"
  | "runs"
  | "turns"
  | "agents"
  | "settings";

export type MissionControlDataSource = "api" | "fixture";
export type SystemStatus = "healthy" | "watch" | "degraded";
export type ApprovalRisk = "low" | "medium" | "high";
export type ApprovalStatus = "pending" | "approved" | "rejected";
export type RunStatus = "queued" | "in_progress" | "completed" | "failed";
export type TurnState = "running" | "waiting_for_tool" | "completed" | "failed";
export type AssetStatus = "connected" | "attention" | "unbound";
export type ProviderName = "textgrid" | "resend";
export type ProviderChannel = "sms" | "email";
export type OutboundSendStatus = "queued" | "sent" | "failed";

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
  pendingLeadCount?: number;
  bookedLeadCount?: number;
  activeNonBookerEnrollmentCount?: number;
  dueManualCallCount?: number;
  repliesNeedingReviewCount?: number;
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
  bookingStatus?: string | null;
  nextSequenceStep?: string | null;
  manualCallDueAt?: string | null;
  recentReplyPreview?: string | null;
  replyNeedsReview?: boolean;
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
  bookingStatus?: string | null;
  sequenceStatus?: string | null;
  nextSequenceStep?: string | null;
  manualCallDueAt?: string | null;
  recentReplyPreview?: string | null;
  replyNeedsReview?: boolean;
  relatedRunId?: string | null;
  relatedApprovalId?: string | null;
  phone?: string | null;
  email?: string | null;
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
  childRunIds?: string[];
  errorClassification?: string | null;
  errorMessage?: string | null;
}

export interface TurnSummary {
  id: string;
  sessionId: string;
  businessId: string;
  environment: string;
  agentId: string;
  agentRevisionId: string;
  turnNumber: number;
  state: TurnState;
  retryCount: number;
  resumedFromTurnId: string | null;
  updatedAt: string;
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

export interface TaskItem {
  threadId: string;
  leadName: string;
  channel: string;
  bookingStatus: string;
  sequenceStatus: string;
  nextSequenceStep: string;
  manualCallDueAt: string;
  recentReplyPreview?: string | null;
  replyNeedsReview?: boolean;
}

export interface TasksData {
  dueCount: number;
  tasks: TaskItem[];
}

export interface ProviderStatus {
  provider: ProviderName;
  configured: boolean;
  canSend: boolean;
  senderIdentity: string | null;
  endpoint: string | null;
  details: string | null;
  checkedAt: string;
}

export interface ProviderStatusData {
  sms: ProviderStatus;
  email: ProviderStatus;
}

export interface OutboundSendResponse {
  channel: ProviderChannel;
  provider: ProviderName;
  status: OutboundSendStatus;
  providerMessageId: string | null;
  to: string;
  fromIdentity: string | null;
  attemptedAt: string;
  errorMessage: string | null;
}

export interface MissionControlSnapshot {
  dashboard: DashboardSummaryData;
  inbox: InboxData;
  approvals: ApprovalItem[];
  runs: RunSummary[];
  turns: TurnSummary[];
  agents: AgentSummary[];
  assets: AssetSummary[];
  tasks?: TaskItem[];
}

export interface MissionControlApiOptions {
  baseUrl?: string;
  runtimeApiKey?: string;
  fetchImpl?: typeof fetch;
}

const defaultBaseUrl = import.meta.env.VITE_RUNTIME_API_BASE_URL ?? "";
const defaultRuntimeApiKey = import.meta.env.VITE_RUNTIME_API_KEY ?? "";

function trimTrailingSlash(value: string): string {
  return value.replace(/\/$/, "");
}

function buildUrl(baseUrl: string, path: string): string {
  const normalizedBaseUrl = trimTrailingSlash(baseUrl);
  return normalizedBaseUrl ? `${normalizedBaseUrl}${path}` : path;
}

async function requestJson<T>(path: string, options: MissionControlApiOptions, init: RequestInit = {}): Promise<T> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (options.runtimeApiKey) {
    headers.set("Authorization", `Bearer ${options.runtimeApiKey}`);
  }
  if (init.body && !headers.has("Content-Type") && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetchImpl(buildUrl(options.baseUrl ?? defaultBaseUrl, path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "");
    const suffix = errorBody ? `: ${errorBody}` : "";
    throw new Error(`Mission Control API request failed: ${response.status} ${response.statusText}${suffix}`);
  }

  return (await response.json()) as T;
}

function mapDashboardSummary(response: MissionControlDashboardResponseApi): DashboardSummaryData {
  return {
    approvalCount: response.approval_count,
    activeRunCount: response.active_run_count,
    failedRunCount: response.failed_run_count,
    activeAgentCount: response.active_agent_count,
    unreadConversationCount: response.unread_conversation_count,
    busyChannelCount: response.busy_channel_count,
    recentCompletedCount: response.recent_completed_count,
    systemStatus: response.system_status,
    updatedAt: response.updated_at,
    pendingLeadCount: response.pending_lead_count,
    bookedLeadCount: response.booked_lead_count,
    activeNonBookerEnrollmentCount: response.active_non_booker_enrollment_count,
    dueManualCallCount: response.due_manual_call_count,
    repliesNeedingReviewCount: response.replies_needing_review_count,
  };
}

function mapConversationSummary(response: MissionControlThreadSummaryApi): ConversationSummary {
  return {
    id: response.thread_id,
    leadName: response.contact.display_name,
    channel: response.channel.toUpperCase(),
    stage: response.sequence_status ?? response.status,
    owner: response.contact.display_name,
    unreadCount: response.unread_count,
    lastMessage: response.recent_reply_preview ?? response.last_message_preview ?? "",
    lastActivityAt: response.last_message_at ? formatTimestamp(response.last_message_at) : "—",
    sequenceState: response.sequence_status ?? "Idle",
    bookingStatus: response.booking_status ?? null,
    nextSequenceStep: response.next_sequence_step ?? null,
    manualCallDueAt: response.manual_call_due_at ?? null,
    recentReplyPreview: response.recent_reply_preview ?? null,
    replyNeedsReview: response.reply_needs_review,
  };
}

function mapThreadDetail(response: MissionControlThreadDetailApi | null | undefined, fallbackSummary: ConversationSummary): SelectedThread {
  const messages = (response?.messages ?? []).map((message) => ({
    id: message.id,
    author: message.direction === "inbound" ? fallbackSummary.leadName : message.direction === "internal" ? "Operator note" : "Hermes",
    direction: message.direction,
    body: message.body,
    timestamp: formatTimestamp(message.created_at),
    status: message.message_type,
  }));

  const context = response?.context ?? {};
  const tags = Array.isArray(context.tags) ? context.tags.map((tag) => String(tag)) : [fallbackSummary.channel, fallbackSummary.stage];
  const notes = Array.isArray(context.notes) ? context.notes.map((note) => String(note)) : [];

  return {
    conversationId: response?.thread_id ?? fallbackSummary.id,
    leadName: response?.contact.display_name ?? fallbackSummary.leadName,
    company: String(context.company ?? context.company_name ?? response?.contact.email ?? fallbackSummary.leadName),
    stage: String(context.stage ?? fallbackSummary.stage),
    nextBestAction: String(
      context.next_best_action ?? context.nextBestAction ?? response?.next_sequence_step ?? fallbackSummary.sequenceState,
    ),
    tags,
    notes,
    messages: messages.length > 0 ? messages : fallbackMessageStub(fallbackSummary),
    bookingStatus: response?.booking_status ?? fallbackSummary.bookingStatus ?? null,
    sequenceStatus: response?.sequence_status ?? fallbackSummary.sequenceState,
    nextSequenceStep: response?.next_sequence_step ?? fallbackSummary.nextSequenceStep ?? null,
    manualCallDueAt: response?.manual_call_due_at ?? fallbackSummary.manualCallDueAt ?? null,
    recentReplyPreview: response?.recent_reply_preview ?? fallbackSummary.recentReplyPreview ?? null,
    replyNeedsReview: response?.reply_needs_review ?? fallbackSummary.replyNeedsReview ?? false,
    relatedRunId: response?.related_run_id ?? null,
    relatedApprovalId: response?.related_approval_id ?? null,
    phone: response?.contact.phone ?? null,
    email: response?.contact.email ?? null,
  };
}

function fallbackMessageStub(summary: ConversationSummary): ThreadEntry[] {
  return summary.lastMessage
    ? [
        {
          id: `${summary.id}-preview`,
          author: summary.leadName,
          direction: "inbound",
          body: summary.lastMessage,
          timestamp: summary.lastActivityAt,
          status: "preview",
        },
      ]
    : [];
}

function mapInbox(response: MissionControlInboxResponseApi): InboxData {
  const conversations = response.threads.map(mapConversationSummary);
  const selectedConversationId = response.selected_thread_id ?? conversations[0]?.id ?? "";
  const selectedSummary = conversations.find((conversation) => conversation.id === selectedConversationId) ?? conversations[0];
  const selectedThread = mapThreadDetail(response.selected_thread, selectedSummary ?? conversations[0] ?? emptyConversationFallback());

  const threadsById: Record<string, SelectedThread> = {};
  for (const conversation of conversations) {
    threadsById[conversation.id] =
      conversation.id === selectedThread.conversationId
        ? selectedThread
        : mapThreadDetail(null, conversation);
  }
  if (selectedSummary) {
    threadsById[selectedConversationId] = selectedThread;
  }

  return {
    conversations,
    selectedConversationId,
    threadsById,
  };
}

function emptyConversationFallback(): ConversationSummary {
  return {
    id: "thread-empty",
    leadName: "Unknown lead",
    channel: "SMS",
    stage: "Idle",
    owner: "Hermes",
    unreadCount: 0,
    lastMessage: "",
    lastActivityAt: "—",
    sequenceState: "Idle",
  };
}

function mapApprovals(response: MissionControlApprovalsResponseApi): ApprovalItem[] {
  return response.approvals.map((approval) => ({
    id: approval.id,
    title: approval.title,
    reason: approval.reason,
    riskLevel: approval.risk_level,
    status: approval.status,
    commandType: approval.command_type,
    requestedAt: formatTimestamp(approval.requested_at),
    payloadPreview: approval.payload_preview,
  }));
}

function mapRuns(response: MissionControlRunsResponseApi): RunSummary[] {
  return response.runs.map((run) => ({
    id: run.id,
    commandType: run.command_type,
    status: run.status,
    businessId: run.business_id,
    environment: run.environment,
    updatedAt: formatTimestamp(run.updated_at),
    parentRunId: run.parent_run_id,
    triggerRunId: run.trigger_run_id,
    summary: run.error_message ?? run.command_type.replaceAll("_", " "),
    childRunIds: run.child_run_ids,
    errorClassification: run.error_classification,
    errorMessage: run.error_message,
  }));
}

function mapTurns(response: MissionControlTurnsResponseApi): TurnSummary[] {
  return response.turns.map((turn) => ({
    id: turn.id,
    sessionId: turn.session_id,
    businessId: turn.business_id,
    environment: turn.environment,
    agentId: turn.agent_id,
    agentRevisionId: turn.agent_revision_id,
    turnNumber: turn.turn_number,
    state: turn.state,
    retryCount: turn.retry_count,
    resumedFromTurnId: turn.resumed_from_turn_id,
    updatedAt: formatTimestamp(turn.updated_at),
  }));
}

function mapAgents(response: MissionControlAgentsResponseApi): AgentSummary[] {
  return response.agents.map((agent) => ({
    id: agent.id,
    name: agent.name,
    activeRevisionId: agent.active_revision_id,
    activeRevisionState: agent.active_revision_state,
    environment: agent.environment,
    liveSessionCount: agent.live_session_count,
    delegatedWorkCount: agent.delegated_work_count,
  }));
}

function mapAssets(response: MissionControlAssetsResponseApi): AssetSummary[] {
  return response.assets.map((asset) => ({
    id: asset.id,
    name: asset.name,
    category: asset.category,
    status: asset.status,
    bindingTarget: asset.binding_target,
    updatedAt: formatTimestamp(asset.updated_at),
  }));
}

function mapTasks(response: MissionControlTasksResponseApi): TaskItem[] {
  return response.tasks.map((task) => ({
    threadId: task.thread_id,
    leadName: task.lead_name,
    channel: task.channel,
    bookingStatus: task.booking_status,
    sequenceStatus: task.sequence_status,
    nextSequenceStep: task.next_sequence_step,
    manualCallDueAt: task.manual_call_due_at,
    recentReplyPreview: task.recent_reply_preview ?? null,
    replyNeedsReview: task.reply_needs_review,
  }));
}

function mapProviderStatus(response: MissionControlProviderStatusApi): ProviderStatus {
  return {
    provider: response.provider,
    configured: response.configured,
    canSend: response.can_send,
    senderIdentity: response.sender_identity,
    endpoint: response.endpoint,
    details: response.details,
    checkedAt: response.checked_at,
  };
}

function formatTimestamp(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toISOString();
}

export interface MissionControlApi {
  getDashboard(): Promise<DashboardSummaryData>;
  getInbox(selectedConversationId?: string): Promise<InboxData>;
  getTasks(): Promise<TasksData>;
  getApprovals(): Promise<ApprovalItem[]>;
  getRuns(): Promise<RunSummary[]>;
  getTurns(scope?: MissionControlScope): Promise<TurnSummary[]>;
  getAgents(): Promise<AgentSummary[]>;
  getAssets(): Promise<AssetSummary[]>;
  getProviderStatus(): Promise<ProviderStatusData>;
  sendTestSms(input: MissionControlSmsTestRequest): Promise<OutboundSendResponse>;
  sendTestEmail(input: MissionControlEmailTestRequest): Promise<OutboundSendResponse>;
}

export interface MissionControlScope {
  businessId?: string;
  environment?: string;
}

export interface MissionControlSmsTestRequest {
  to: string;
  body: string;
}

export interface MissionControlEmailTestRequest {
  to: string;
  subject: string;
  text: string;
  html?: string | null;
}

interface MissionControlDashboardResponseApi {
  approval_count: number;
  active_run_count: number;
  failed_run_count: number;
  active_agent_count: number;
  unread_conversation_count: number;
  busy_channel_count: number;
  recent_completed_count: number;
  pending_lead_count?: number;
  booked_lead_count?: number;
  active_non_booker_enrollment_count?: number;
  due_manual_call_count?: number;
  replies_needing_review_count?: number;
  system_status: SystemStatus;
  updated_at: string;
}

interface MissionControlContactRecordApi {
  id: string;
  display_name: string;
  phone: string | null;
  email: string | null;
}

interface MissionControlThreadSummaryApi {
  thread_id: string;
  channel: string;
  status: string;
  unread_count: number;
  last_message_preview: string | null;
  last_message_at: string | null;
  requires_approval: boolean;
  related_run_id: string | null;
  related_approval_id: string | null;
  contact: MissionControlContactRecordApi;
  booking_status?: string | null;
  sequence_status?: string | null;
  next_sequence_step?: string | null;
  manual_call_due_at?: string | null;
  recent_reply_preview?: string | null;
  reply_needs_review?: boolean;
}

interface MissionControlMessageRecordApi {
  id: string;
  direction: "inbound" | "outbound" | "internal";
  channel: string;
  body: string;
  created_at: string;
  message_type: string;
  approval_id: string | null;
  run_id: string | null;
}

interface MissionControlThreadDetailApi {
  thread_id: string;
  channel: string;
  status: string;
  unread_count: number;
  requires_approval: boolean;
  related_run_id: string | null;
  related_approval_id: string | null;
  contact: MissionControlContactRecordApi;
  booking_status?: string | null;
  sequence_status?: string | null;
  next_sequence_step?: string | null;
  manual_call_due_at?: string | null;
  recent_reply_preview?: string | null;
  reply_needs_review?: boolean;
  messages: MissionControlMessageRecordApi[];
  context: Record<string, unknown>;
}

interface MissionControlInboxSummaryApi {
  thread_count: number;
  unread_count: number;
  approval_required_count: number;
}

interface MissionControlInboxResponseApi {
  summary: MissionControlInboxSummaryApi;
  threads: MissionControlThreadSummaryApi[];
  selected_thread_id: string | null;
  selected_thread: MissionControlThreadDetailApi | null;
}

interface MissionControlApprovalApi {
  id: string;
  title: string;
  reason: string;
  risk_level: ApprovalRisk;
  status: ApprovalStatus;
  command_type: string;
  requested_at: string;
  payload_preview: string;
}

interface MissionControlApprovalsResponseApi {
  approvals: MissionControlApprovalApi[];
}

interface MissionControlRunSummaryApi {
  id: string;
  command_id: string;
  business_id: string;
  environment: string;
  command_type: string;
  status: RunStatus;
  parent_run_id: string | null;
  child_run_ids: string[];
  trigger_run_id: string | null;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  error_classification: string | null;
  error_message: string | null;
}

interface MissionControlRunsResponseApi {
  runs: MissionControlRunSummaryApi[];
}

interface MissionControlTurnSummaryApi {
  id: string;
  session_id: string;
  business_id: string;
  environment: string;
  agent_id: string;
  agent_revision_id: string;
  turn_number: number;
  state: TurnState;
  retry_count: number;
  resumed_from_turn_id: string | null;
  updated_at: string;
}

interface MissionControlTurnsResponseApi {
  turns: MissionControlTurnSummaryApi[];
}

interface MissionControlAgentSummaryApi {
  id: string;
  name: string;
  active_revision_id: string | null;
  active_revision_state: string;
  environment: string;
  live_session_count: number;
  delegated_work_count: number;
}

interface MissionControlAgentsResponseApi {
  agents: MissionControlAgentSummaryApi[];
}

interface MissionControlAssetSummaryApi {
  id: string;
  name: string;
  category: string;
  status: AssetStatus;
  binding_target: string;
  updated_at: string;
}

interface MissionControlAssetsResponseApi {
  assets: MissionControlAssetSummaryApi[];
}

interface MissionControlTaskSummaryApi {
  thread_id: string;
  lead_name: string;
  channel: string;
  booking_status: string;
  sequence_status: string;
  next_sequence_step: string;
  manual_call_due_at: string;
  recent_reply_preview?: string | null;
  reply_needs_review?: boolean;
}

interface MissionControlTasksResponseApi {
  due_count: number;
  tasks: MissionControlTaskSummaryApi[];
}

interface MissionControlProviderStatusApi {
  provider: ProviderName;
  configured: boolean;
  can_send: boolean;
  sender_identity: string | null;
  endpoint: string | null;
  details: string | null;
  checked_at: string;
}

interface MissionControlProvidersStatusResponseApi {
  sms: MissionControlProviderStatusApi;
  email: MissionControlProviderStatusApi;
}

interface MissionControlOutboundSendResponseApi {
  channel: ProviderChannel;
  provider: ProviderName;
  status: OutboundSendStatus;
  provider_message_id: string | null;
  to: string;
  from_identity: string | null;
  attempted_at: string;
  error_message: string | null;
}

export function createMissionControlApi(options: MissionControlApiOptions = {}): MissionControlApi {
  const resolvedOptions: MissionControlApiOptions = {
    baseUrl: options.baseUrl ?? defaultBaseUrl,
    runtimeApiKey: options.runtimeApiKey ?? defaultRuntimeApiKey,
    fetchImpl: options.fetchImpl,
  };

  return {
    async getDashboard() {
      return mapDashboardSummary(await requestJson<MissionControlDashboardResponseApi>("/mission-control/dashboard", resolvedOptions));
    },
    async getInbox(selectedConversationId?: string) {
      const searchParams = new URLSearchParams();
      if (selectedConversationId) {
        searchParams.set("selected_thread_id", selectedConversationId);
      }
      const query = searchParams.toString();
      const path = query ? `/mission-control/inbox?${query}` : "/mission-control/inbox";
      return mapInbox(await requestJson<MissionControlInboxResponseApi>(path, resolvedOptions));
    },
    async getTasks() {
      const response = await requestJson<MissionControlTasksResponseApi>("/mission-control/tasks", resolvedOptions);
      return {
        dueCount: response.due_count,
        tasks: mapTasks(response),
      };
    },
    async getApprovals() {
      return mapApprovals(await requestJson<MissionControlApprovalsResponseApi>("/mission-control/approvals", resolvedOptions));
    },
    async getRuns() {
      return mapRuns(await requestJson<MissionControlRunsResponseApi>("/mission-control/runs", resolvedOptions));
    },
    async getTurns(scope?: MissionControlScope) {
      const searchParams = new URLSearchParams();
      if (scope?.businessId) {
        searchParams.set("business_id", scope.businessId);
      }
      if (scope?.environment) {
        searchParams.set("environment", scope.environment);
      }
      const query = searchParams.toString();
      const path = query ? `/mission-control/turns?${query}` : "/mission-control/turns";
      return mapTurns(await requestJson<MissionControlTurnsResponseApi>(path, resolvedOptions));
    },
    async getAgents() {
      return mapAgents(await requestJson<MissionControlAgentsResponseApi>("/mission-control/agents", resolvedOptions));
    },
    async getAssets() {
      return mapAssets(await requestJson<MissionControlAssetsResponseApi>("/mission-control/settings/assets", resolvedOptions));
    },
    async getProviderStatus() {
      const response = await requestJson<MissionControlProvidersStatusResponseApi>("/mission-control/providers/status", resolvedOptions);
      return {
        sms: mapProviderStatus(response.sms),
        email: mapProviderStatus(response.email),
      };
    },
    async sendTestSms(input: MissionControlSmsTestRequest) {
      return mapOutboundSendResponse(
        await requestJson<MissionControlOutboundSendResponseApi>(
          "/mission-control/outbound/sms/test",
          resolvedOptions,
          {
            method: "POST",
            body: JSON.stringify(input),
          },
        ),
      );
    },
    async sendTestEmail(input: MissionControlEmailTestRequest) {
      return mapOutboundSendResponse(
        await requestJson<MissionControlOutboundSendResponseApi>(
          "/mission-control/outbound/email/test",
          resolvedOptions,
          {
            method: "POST",
            body: JSON.stringify(input),
          },
        ),
      );
    },
  };
}

function mapOutboundSendResponse(response: MissionControlOutboundSendResponseApi): OutboundSendResponse {
  return {
    channel: response.channel,
    provider: response.provider,
    status: response.status,
    providerMessageId: response.provider_message_id,
    to: response.to,
    fromIdentity: response.from_identity,
    attemptedAt: response.attempted_at,
    errorMessage: response.error_message,
  };
}
