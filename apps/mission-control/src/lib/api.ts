export type MissionControlView =
  | "dashboard"
  | "inbox"
  | "approvals"
  | "runs"
  | "agents"
  | "settings"
  | "tasks"
  | "pipeline"
  | "suppression";
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
  pendingLeadCount?: number;
  bookedLeadCount?: number;
  activeNonBookerEnrollmentCount?: number;
  dueManualCallCount?: number;
  repliesNeedingReviewCount?: number;
  opportunityCount?: number;
  opportunityStageSummaries?: OpportunityStageSummary[];
  outboundProbateSummary?: OutboundProbateSummary;
  inboundLeaseOptionSummary?: InboundLeaseOptionSummary;
  opportunityPipelineSummary?: OpportunityPipelineSummary;
  systemStatus: SystemStatus;
  updatedAt: string;
}

export interface OpportunityStageSummary {
  sourceLane: string;
  stage: string;
  count: number;
}

export interface OutboundProbateSummary {
  activeCampaignCount: number;
  readyLeadCount: number;
  activeLeadCount: number;
  interestedLeadCount: number;
  suppressedLeadCount: number;
  openTaskCount: number;
}

export interface InboundLeaseOptionSummary {
  pendingLeadCount: number;
  bookedLeadCount: number;
  activeNonBookerEnrollmentCount: number;
  dueManualCallCount: number;
  repliesNeedingReviewCount: number;
}

export interface OpportunityPipelineSummary {
  totalOpportunityCount: number;
  laneStageSummaries: OpportunityStageSummary[];
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
  bookingStatus?: string;
  nextSequenceStep?: string;
  manualCallDueAt?: string;
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
  email?: string | null;
  phone?: string | null;
  stage: string;
  nextBestAction: string;
  tags: string[];
  notes: string[];
  bookingStatus?: string;
  sequenceStatus?: string;
  nextSequenceStep?: string;
  manualCallDueAt?: string;
  recentReplyPreview?: string | null;
  replyNeedsReview?: boolean;
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

export interface TurnSummary {
  id: string;
  sessionId: string;
  businessId: string;
  environment: string;
  agentId: string;
  agentRevisionId: string;
  turnNumber: number;
  state: string;
  retryCount: number;
  resumedFromTurnId?: string | null;
  updatedAt: string;
}

export interface OutboundSendResponse {
  status: string;
  providerMessageId?: string | null;
  errorMessage?: string | null;
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
  tasks: TasksData;
  approvals: ApprovalItem[];
  runs: RunSummary[];
  turns: TurnSummary[];
  agents: AgentSummary[];
  assets: AssetSummary[];
}

export interface MissionControlApi {
  getDashboard(): Promise<DashboardSummaryData>;
  getInbox(selectedThreadId?: string): Promise<InboxData>;
  getTasks(): Promise<TasksData>;
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

type JsonRecord = Record<string, unknown>;

interface DashboardPayload {
  approval_count: number;
  active_run_count: number;
  failed_run_count: number;
  active_agent_count: number;
  unread_conversation_count?: number;
  busy_channel_count?: number;
  recent_completed_count?: number;
  pending_lead_count?: number;
  booked_lead_count?: number;
  active_non_booker_enrollment_count?: number;
  due_manual_call_count?: number;
  replies_needing_review_count?: number;
  opportunity_count?: number;
  opportunity_stage_summaries?: Array<{
    source_lane?: string;
    stage?: string;
    count?: number;
  }>;
  outbound_probate_summary?: {
    active_campaign_count?: number;
    ready_lead_count?: number;
    active_lead_count?: number;
    interested_lead_count?: number;
    suppressed_lead_count?: number;
    open_task_count?: number;
  };
  inbound_lease_option_summary?: {
    pending_lead_count?: number;
    booked_lead_count?: number;
    active_non_booker_enrollment_count?: number;
    due_manual_call_count?: number;
    replies_needing_review_count?: number;
  };
  opportunity_pipeline_summary?: {
    total_opportunity_count?: number;
    lane_stage_summaries?: Array<{
      source_lane?: string;
      stage?: string;
      count?: number;
    }>;
  };
  system_status?: string;
  updated_at?: string;
}

interface InboxContactPayload {
  display_name?: string;
  email?: string | null;
  phone?: string | null;
}

interface InboxMessagePayload {
  id?: string;
  direction?: string;
  body?: string;
  created_at?: string;
  message_type?: string;
}

interface InboxThreadSummaryPayload {
  thread_id: string;
  channel: string;
  status?: string;
  unread_count?: number;
  last_message_preview?: string | null;
  last_message_at?: string | null;
  requires_approval?: boolean;
  related_run_id?: string | null;
  related_approval_id?: string | null;
  booking_status?: string | null;
  sequence_status?: string | null;
  next_sequence_step?: string | null;
  manual_call_due_at?: string | null;
  recent_reply_preview?: string | null;
  reply_needs_review?: boolean;
  contact?: InboxContactPayload;
}

interface InboxThreadDetailPayload {
  thread_id: string;
  channel: string;
  status?: string;
  unread_count?: number;
  requires_approval?: boolean;
  related_run_id?: string | null;
  related_approval_id?: string | null;
  booking_status?: string | null;
  sequence_status?: string | null;
  next_sequence_step?: string | null;
  manual_call_due_at?: string | null;
  recent_reply_preview?: string | null;
  reply_needs_review?: boolean;
  contact?: InboxContactPayload;
  messages?: InboxMessagePayload[];
  context?: JsonRecord;
}

interface InboxPayload {
  summary?: {
    unread_count?: number;
  };
  threads?: InboxThreadSummaryPayload[];
  selected_thread_id?: string | null;
  selected_thread?: InboxThreadDetailPayload | null;
}

export interface TaskItem {
  threadId: string;
  leadName: string;
  channel: string;
  bookingStatus: string;
  sequenceStatus: string;
  nextSequenceStep: string;
  manualCallDueAt: string;
  recentReplyPreview: string | null;
  replyNeedsReview: boolean;
}

export interface TasksData {
  dueCount: number;
  tasks: TaskItem[];
}

interface TaskPayload {
  thread_id?: string;
  lead_name?: string;
  channel?: string;
  booking_status?: string | null;
  sequence_status?: string | null;
  next_sequence_step?: string | null;
  manual_call_due_at?: string;
  recent_reply_preview?: string | null;
  reply_needs_review?: boolean;
}

interface TasksPayload {
  due_count?: number;
  tasks?: TaskPayload[];
}

interface ApprovalPayload {
  id?: string;
  command_type?: string;
  status?: string;
  payload_snapshot?: unknown;
  created_at?: string;
  title?: string;
  reason?: string;
  risk_level?: string;
  payload_preview?: string;
}

interface MissionControlApprovalsPayload {
  approvals?: ApprovalPayload[];
}

interface RunPayload {
  id: string;
  command_type: string;
  status: string;
  business_id: string;
  environment: string;
  updated_at: string;
  parent_run_id?: string | null;
  trigger_run_id?: string | null;
  error_classification?: string | null;
  error_message?: string | null;
}

interface RunsPayload {
  runs: RunPayload[];
}

interface AgentPayload {
  id?: string;
  business_id?: string;
  environment?: string;
  name?: string;
  active_revision_id?: string | null;
  active_revision_state?: string;
  live_session_count?: number;
  delegated_work_count?: number;
}

interface AgentRevisionPayload {
  id?: string;
  state?: string;
}

interface AgentResponsePayload {
  agent?: AgentPayload;
  revisions?: AgentRevisionPayload[];
}

interface MissionControlAgentsPayload {
  agents?: Array<AgentPayload | AgentResponsePayload>;
}

interface AssetPayload {
  id?: string;
  business_id?: string;
  environment?: string;
  name?: string;
  label?: string;
  category?: string;
  asset_type?: string;
  status?: string;
  binding_target?: string;
  binding_reference?: string | null;
  connect_later?: boolean;
  updated_at?: string;
}

interface MissionControlAssetsPayload {
  assets?: AssetPayload[];
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

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null;
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNullableString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asBoolean(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : [];
}

function titleCase(value: string): string {
  return value
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1))
    .join(" ");
}

function normalizeSystemStatus(value: unknown): SystemStatus {
  if (value === "healthy" || value === "watch" || value === "degraded") {
    return value;
  }
  return "healthy";
}

function normalizeApprovalRisk(value: unknown, commandType: string): ApprovalRisk {
  if (value === "low" || value === "medium" || value === "high") {
    return value;
  }

  if (commandType.includes("call") || commandType.includes("voice")) {
    return "high";
  }

  if (commandType.includes("publish") || commandType.includes("send")) {
    return "medium";
  }

  return "low";
}

function normalizeApprovalStatus(value: unknown): ApprovalStatus {
  if (value === "pending" || value === "approved" || value === "rejected") {
    return value;
  }
  return "pending";
}

function normalizeRunStatus(value: unknown): RunStatus {
  if (value === "queued" || value === "in_progress" || value === "completed" || value === "failed") {
    return value;
  }
  return "queued";
}

function normalizeAssetStatus(value: unknown, connectLater: boolean): AssetStatus {
  if (value === "connected" || value === "attention" || value === "unbound") {
    return value;
  }

  if (value === "bound") {
    return "connected";
  }

  if (value === "unbound") {
    return connectLater ? "unbound" : "attention";
  }

  return connectLater ? "unbound" : "attention";
}

function deriveRunSummary(payload: RunPayload): string {
  if (payload.error_message) {
    return payload.error_classification
      ? `${payload.error_classification}: ${payload.error_message}`
      : payload.error_message;
  }

  const status = normalizeRunStatus(payload.status);
  if (status === "completed") {
    return "Run completed.";
  }
  if (status === "in_progress") {
    return "Run in progress.";
  }
  if (status === "failed") {
    return "Run failed.";
  }
  return "Queued for execution.";
}

function mapDashboard(payload: DashboardPayload): DashboardSummaryData {
  const stageSummaries = asArray<{ source_lane?: string; stage?: string; count?: number }>(
    payload.opportunity_stage_summaries,
  ).map((summary) => ({
    sourceLane: asString(summary.source_lane),
    stage: asString(summary.stage),
    count: asNumber(summary.count),
  }));
  const pipelineSummary = payload.opportunity_pipeline_summary;

  return {
    approvalCount: asNumber(payload.approval_count),
    activeRunCount: asNumber(payload.active_run_count),
    failedRunCount: asNumber(payload.failed_run_count),
    activeAgentCount: asNumber(payload.active_agent_count),
    unreadConversationCount: asNumber(payload.unread_conversation_count),
    busyChannelCount: asNumber(payload.busy_channel_count),
    recentCompletedCount: asNumber(payload.recent_completed_count),
    pendingLeadCount: asNumber(payload.pending_lead_count),
    bookedLeadCount: asNumber(payload.booked_lead_count),
    activeNonBookerEnrollmentCount: asNumber(payload.active_non_booker_enrollment_count),
    dueManualCallCount: asNumber(payload.due_manual_call_count),
    repliesNeedingReviewCount: asNumber(payload.replies_needing_review_count),
    opportunityCount: asNumber(payload.opportunity_count),
    opportunityStageSummaries: stageSummaries,
    outboundProbateSummary: payload.outbound_probate_summary
      ? {
          activeCampaignCount: asNumber(payload.outbound_probate_summary.active_campaign_count),
          readyLeadCount: asNumber(payload.outbound_probate_summary.ready_lead_count),
          activeLeadCount: asNumber(payload.outbound_probate_summary.active_lead_count),
          interestedLeadCount: asNumber(payload.outbound_probate_summary.interested_lead_count),
          suppressedLeadCount: asNumber(payload.outbound_probate_summary.suppressed_lead_count),
          openTaskCount: asNumber(payload.outbound_probate_summary.open_task_count),
        }
      : undefined,
    inboundLeaseOptionSummary: payload.inbound_lease_option_summary
      ? {
          pendingLeadCount: asNumber(payload.inbound_lease_option_summary.pending_lead_count),
          bookedLeadCount: asNumber(payload.inbound_lease_option_summary.booked_lead_count),
          activeNonBookerEnrollmentCount: asNumber(
            payload.inbound_lease_option_summary.active_non_booker_enrollment_count,
          ),
          dueManualCallCount: asNumber(payload.inbound_lease_option_summary.due_manual_call_count),
          repliesNeedingReviewCount: asNumber(payload.inbound_lease_option_summary.replies_needing_review_count),
        }
      : undefined,
    opportunityPipelineSummary: pipelineSummary
      ? {
          totalOpportunityCount: asNumber(pipelineSummary.total_opportunity_count),
          laneStageSummaries: asArray<{ source_lane?: string; stage?: string; count?: number }>(
            pipelineSummary.lane_stage_summaries,
          ).map((summary) => ({
            sourceLane: asString(summary.source_lane),
            stage: asString(summary.stage),
            count: asNumber(summary.count),
          })),
        }
      : undefined,
    systemStatus: normalizeSystemStatus(payload.system_status),
    updatedAt: asString(payload.updated_at, "Updated just now"),
  };
}

function mapThreadFromSummary(
  summary: InboxThreadSummaryPayload,
  stage: string,
  nextBestAction: string,
): SelectedThread {
  const displayName = asString(summary.contact?.display_name, "Unknown contact");
  const channel = asString(summary.channel, "channel");
  const status = asString(summary.status, "open");
  const requiresApproval = asBoolean(summary.requires_approval);

  return {
    conversationId: asString(summary.thread_id),
    leadName: displayName,
    company: asString(summary.contact?.email, asString(summary.contact?.phone, "Unknown account")),
    email: asNullableString(summary.contact?.email),
    phone: asNullableString(summary.contact?.phone),
    stage,
    nextBestAction,
    tags: [channel.toLowerCase(), status, requiresApproval ? "approval-required" : "clear"],
    notes: [],
    bookingStatus: asString(summary.booking_status, ""),
    sequenceStatus: asString(summary.sequence_status, ""),
    nextSequenceStep: asString(summary.next_sequence_step, ""),
    manualCallDueAt: asString(summary.manual_call_due_at, ""),
    recentReplyPreview: asNullableString(summary.recent_reply_preview),
    replyNeedsReview: asBoolean(summary.reply_needs_review),
    messages: [],
  };
}

function mapThreadDetail(detail: InboxThreadDetailPayload): SelectedThread {
  const context = isRecord(detail.context) ? detail.context : {};
  const displayName = asString(detail.contact?.display_name, "Unknown contact");
  const stage = asString(context.stage, "Uncategorized");
  const nextBestAction = asString(
    context.next_best_action,
    asBoolean(detail.requires_approval) ? "Review approval before responding." : "Continue the conversation.",
  );
  const notes = asArray<string>(context.notes).filter((entry): entry is string => typeof entry === "string");
  const tags = asArray<string>(context.tags).filter((entry): entry is string => typeof entry === "string");
  const status = asString(detail.status, "open");

  return {
    conversationId: asString(detail.thread_id),
    leadName: displayName,
    company: asString(detail.contact?.email, asString(detail.contact?.phone, "Unknown account")),
    email: asNullableString(detail.contact?.email),
    phone: asNullableString(detail.contact?.phone),
    stage,
    nextBestAction,
    tags: tags.length > 0 ? tags : [asString(detail.channel, "channel"), status],
    notes,
    bookingStatus: asString(detail.booking_status, ""),
    sequenceStatus: asString(detail.sequence_status, ""),
    nextSequenceStep: asString(detail.next_sequence_step, ""),
    manualCallDueAt: asString(detail.manual_call_due_at, ""),
    recentReplyPreview: asNullableString(detail.recent_reply_preview),
    replyNeedsReview: asBoolean(detail.reply_needs_review),
    messages: asArray<InboxMessagePayload>(detail.messages).map((message, index) => ({
      id: asString(message.id, `${asString(detail.thread_id)}-message-${index}`),
      author:
        message.direction === "inbound"
          ? displayName
          : message.direction === "internal"
            ? "Operator note"
            : "Hermes",
      direction:
        message.direction === "inbound" || message.direction === "outbound" || message.direction === "internal"
          ? message.direction
          : "internal",
      body: asString(message.body),
      timestamp: asString(message.created_at, "Unknown"),
      status: asString(message.message_type, "logged"),
    })),
  };
}

function mapInbox(payload: InboxPayload): InboxData {
  const threads = asArray<InboxThreadSummaryPayload>(payload.threads);
  const selectedDetail =
    payload.selected_thread && isRecord(payload.selected_thread)
      ? (payload.selected_thread as InboxThreadDetailPayload)
      : null;

  const selectedThreadIdFromPayload = asNullableString(payload.selected_thread_id);
  const selectedThreadId =
    selectedThreadIdFromPayload ?? asNullableString(selectedDetail?.thread_id) ?? asNullableString(threads[0]?.thread_id);

  const threadsById: Record<string, SelectedThread> = {};

  for (const thread of threads) {
    const threadId = asString(thread.thread_id);
    if (!threadId) {
      continue;
    }

    const isSelected = selectedThreadId !== null && threadId === selectedThreadId;
    const stage =
      isSelected && selectedDetail && isRecord(selectedDetail.context)
        ? asString(selectedDetail.context.stage, "Queued")
        : "Queued";
    const nextBestAction =
      isSelected && selectedDetail && isRecord(selectedDetail.context)
        ? asString(selectedDetail.context.next_best_action, "Open thread for latest context.")
        : "Open thread for latest context.";

    threadsById[threadId] = mapThreadFromSummary(thread, stage, nextBestAction);
  }

  if (selectedDetail && selectedThreadId) {
    threadsById[selectedThreadId] = mapThreadDetail(selectedDetail);
  }

  const selectedConversationId = selectedThreadId ?? Object.keys(threadsById)[0] ?? "";

  return {
    selectedConversationId,
    conversations: threads.map((thread) => ({
      id: asString(thread.thread_id),
      leadName: asString(thread.contact?.display_name, "Unknown contact"),
      channel: asString(thread.channel, "channel").toUpperCase(),
      stage: asString(thread.booking_status, "Queued"),
      owner: "Hermes",
      unreadCount: asNumber(thread.unread_count),
      lastMessage: asString(thread.last_message_preview, "No messages yet"),
      lastActivityAt: asString(thread.last_message_at, "Unknown"),
      sequenceState: asString(thread.sequence_status, asString(thread.status, "open")),
      bookingStatus: asString(thread.booking_status, ""),
      nextSequenceStep: asString(thread.next_sequence_step, ""),
      manualCallDueAt: asString(thread.manual_call_due_at, ""),
      recentReplyPreview: asNullableString(thread.recent_reply_preview),
      replyNeedsReview: asBoolean(thread.reply_needs_review),
    })),
    threadsById,
  };
}

function mapTasks(payload: TasksPayload): TasksData {
  const tasks = asArray<TaskPayload>(payload.tasks).map((task) => ({
    threadId: asString(task.thread_id),
    leadName: asString(task.lead_name, "Unknown contact"),
    channel: asString(task.channel, "channel"),
    bookingStatus: asString(task.booking_status, "pending"),
    sequenceStatus: asString(task.sequence_status, "active"),
    nextSequenceStep: asString(task.next_sequence_step, "manual_call"),
    manualCallDueAt: asString(task.manual_call_due_at, "Unknown"),
    recentReplyPreview: asNullableString(task.recent_reply_preview),
    replyNeedsReview: asBoolean(task.reply_needs_review),
  }));

  return {
    dueCount: asNumber(payload.due_count, tasks.length),
    tasks,
  };
}

function mapApprovals(payload: MissionControlApprovalsPayload | ApprovalPayload[]): ApprovalItem[] {
  const approvals = Array.isArray(payload)
    ? payload
    : isRecord(payload) && Array.isArray(payload.approvals)
      ? payload.approvals
      : [];

  return approvals.map((approval, index) => {
    const commandType = asString(approval.command_type, "unknown_command");
    const fallbackTitle = `Approve ${titleCase(commandType)}`;
    const payloadPreview =
      typeof approval.payload_snapshot === "string"
        ? approval.payload_snapshot
        : approval.payload_snapshot !== undefined
          ? JSON.stringify(approval.payload_snapshot)
          : "";

    return {
      id: asString(approval.id, `approval-${index}`),
      title: asString(approval.title, fallbackTitle),
      reason: asString(approval.reason, "Runtime policy requires operator approval."),
      riskLevel: normalizeApprovalRisk(approval.risk_level, commandType),
      status: normalizeApprovalStatus(approval.status),
      commandType,
      requestedAt: asString(approval.created_at, "Unknown"),
      payloadPreview: asString(approval.payload_preview, payloadPreview),
    };
  });
}

function mapRuns(payload: RunsPayload): RunSummary[] {
  return asArray<RunPayload>(payload.runs).map((run) => ({
    id: asString(run.id),
    commandType: asString(run.command_type),
    status: normalizeRunStatus(run.status),
    businessId: asString(run.business_id),
    environment: asString(run.environment),
    updatedAt: asString(run.updated_at),
    parentRunId: asNullableString(run.parent_run_id),
    triggerRunId: asNullableString(run.trigger_run_id),
    summary: deriveRunSummary(run),
  }));
}

function mapAgents(payload: MissionControlAgentsPayload | AgentPayload[] | AgentResponsePayload[]): AgentSummary[] {
  const agents = Array.isArray(payload)
    ? payload
    : isRecord(payload) && Array.isArray(payload.agents)
      ? payload.agents
      : [];

  return agents.map((entry, index) => {
    const hasAgentWrapper = isRecord(entry) && isRecord((entry as AgentResponsePayload).agent);
    const agent = (hasAgentWrapper ? (entry as AgentResponsePayload).agent : entry) as AgentPayload;
    const revisions = hasAgentWrapper ? asArray<AgentRevisionPayload>((entry as AgentResponsePayload).revisions) : [];
    const activeRevisionId = asNullableString(agent.active_revision_id);
    const activeRevisionState = asString(
      agent.active_revision_state,
      activeRevisionId
        ? "published"
        : revisions.find((revision) => revision.state === "draft")
          ? "draft"
          : "unpublished",
    );

    return {
      id: asString(agent.id, `agent-${index}`),
      name: asString(agent.name, "Unknown agent"),
      activeRevisionId,
      activeRevisionState,
      environment: asString(agent.environment, "unknown"),
      liveSessionCount: asNumber(agent.live_session_count),
      delegatedWorkCount: asNumber(agent.delegated_work_count),
    };
  });
}

function mapAssets(payload: MissionControlAssetsPayload | AssetPayload[]): AssetSummary[] {
  const assets = Array.isArray(payload)
    ? payload
    : isRecord(payload) && Array.isArray(payload.assets)
      ? payload.assets
      : [];

  return assets.map((asset, index) => {
    const connectLater = asBoolean(asset.connect_later, false);
    const status = normalizeAssetStatus(asset.status, connectLater);

    return {
      id: asString(asset.id, `asset-${index}`),
      name: asString(asset.name, asString(asset.label, "Unnamed asset")),
      category: asString(asset.category, asString(asset.asset_type, "asset")),
      status,
      bindingTarget: asString(
        asset.binding_target,
        asString(asset.binding_reference, connectLater ? "not set" : "connected"),
      ),
      updatedAt: asString(asset.updated_at, "Unknown"),
    };
  });
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
    getDashboard: async () => mapDashboard(await requestJson<DashboardPayload>("/mission-control/dashboard", resolvedOptions)),
    getInbox: async (selectedThreadId?: string) => {
      const inboxPath = selectedThreadId
        ? `/mission-control/inbox?selected_thread_id=${encodeURIComponent(selectedThreadId)}`
        : "/mission-control/inbox";
      return mapInbox(await requestJson<InboxPayload>(inboxPath, resolvedOptions));
    },
    getTasks: async () => mapTasks(await requestJson<TasksPayload>("/mission-control/tasks", resolvedOptions)),
    getApprovals: async () =>
      mapApprovals(
        await requestJson<MissionControlApprovalsPayload | ApprovalPayload[]>(
          "/mission-control/approvals",
          resolvedOptions,
        ),
      ),
    getRuns: async () => mapRuns(await requestJson<RunsPayload>("/mission-control/runs", resolvedOptions)),
    getAgents: async () =>
      mapAgents(
        await requestJson<MissionControlAgentsPayload | AgentPayload[] | AgentResponsePayload[]>(
          "/mission-control/agents",
          resolvedOptions,
        ),
      ),
    getAssets: async () =>
      mapAssets(
        await requestJson<MissionControlAssetsPayload | AssetPayload[]>(
          "/mission-control/settings/assets",
          resolvedOptions,
        ),
      ),
  };
}
