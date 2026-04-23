export type MissionControlView =
  | "dashboard"
  | "inbox"
  | "approvals"
  | "runs"
  | "agents"
  | "catalog"
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
export type ReleaseEventType = "publish" | "rollback";
export type OutcomeStatus = "satisfied" | "failed";
export type ReplayRole = "parent" | "child";

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

export interface ReleaseEvaluationState {
  outcomeId: string;
  outcomeName: string;
  status: OutcomeStatus;
  satisfied: boolean;
  evaluatorResult: string;
  failureDetails: string[];
  rubricCriteria: string[];
  requirePassingEvaluation: boolean;
  blockedPromotion: boolean;
  rollbackReason?: string | null;
}

export interface AgentReleaseState {
  eventId: string;
  eventType: ReleaseEventType;
  releaseChannel?: string | null;
  createdAt: string;
  previousActiveRevisionId?: string | null;
  targetRevisionId: string;
  resultingActiveRevisionId: string;
  rollbackSourceRevisionId?: string | null;
  evaluation?: ReleaseEvaluationState;
}

export interface ReplayActorState {
  orgId: string;
  actorId: string;
  actorType: string;
}

export interface ReplayRevisionState {
  agentId?: string | null;
  agentRevisionId?: string | null;
  activeRevisionId?: string | null;
  revisionState?: string | null;
  releaseChannel?: string | null;
  releaseEventId?: string | null;
  releaseEventType?: ReleaseEventType | null;
}

export interface RunReplayState {
  role: ReplayRole;
  requestedAt: string;
  resolvedAt?: string | null;
  replayReason?: string | null;
  requiresApproval?: boolean | null;
  approvalId?: string | null;
  childRunId?: string | null;
  parentRunId?: string | null;
  triggeringActor?: ReplayActorState;
  source?: ReplayRevisionState;
  replay?: ReplayRevisionState;
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
  replay?: RunReplayState;
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
  slug: string;
  description: string | null;
  businessId: string;
  lifecycleStatus: string;
  activeRevisionId: string | null;
  activeRevisionState: string;
  environment: string;
  liveSessionCount: number;
  delegatedWorkCount: number;
  hostAdapter?: AgentHostAdapterSummary;
  release?: AgentReleaseState;
  createdAt: string;
  updatedAt: string;
}

export interface AgentHostAdapterSummary {
  kind: string;
  enabled: boolean;
  displayName: string;
  adapterDetailsLabel: string;
  capabilities: {
    dispatch: boolean;
    statusCorrelation: boolean;
    artifactReporting: boolean;
    cancellation: boolean;
  };
  disabledReason: string | null;
}

export interface AgentRecordState {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  businessId: string;
  environment: string;
  lifecycleStatus: string;
  activeRevisionId: string | null;
  activeRevisionState: string;
}

export interface AgentRevisionDetail {
  id: string;
  agentId: string;
  revisionNumber: number;
  state: string;
  hostAdapterKind: string;
  providerKind: string;
  providerCapabilities: string[];
  skillIds: string[];
  requiredSecrets: string[];
  releaseChannel: string;
  releaseNotes: string | null;
  createdAt: string;
  updatedAt: string;
  publishedAt: string | null;
  archivedAt: string | null;
  clonedFromRevisionId: string | null;
}

export interface AgentReleaseEvent {
  id: string;
  eventType: ReleaseEventType;
  actorId: string;
  actorType: string;
  previousActiveRevisionId: string | null;
  targetRevisionId: string;
  resultingActiveRevisionId: string;
  releaseChannel: string | null;
  notes: string | null;
  createdAt: string;
  evaluation?: ReleaseEvaluationState;
}

export interface AgentSecretsHealth {
  revisionId: string;
  status: "healthy" | "attention";
  requiredSecretCount: number;
  configuredSecretCount: number;
  missingSecretCount: number;
  requiredSecrets: string[];
  configuredSecrets: string[];
  missingSecrets: string[];
}

export type AgentDetailDegradedSection = "revisions" | "releaseHistory" | "secretsHealth" | "recentAudit" | "usage" | "recentTurns";

export interface AgentDetailData {
  agent: AgentRecordState;
  revisions: AgentRevisionDetail[];
  releaseHistory: AgentReleaseEvent[];
  secretsHealth: AgentSecretsHealth | null;
  recentAudit: GovernanceAuditEvent[];
  usageSummary: GovernanceUsageSummary;
  recentUsage: GovernanceUsageEvent[];
  recentTurns: TurnSummary[];
  degradedSections: AgentDetailDegradedSection[];
}

export interface AssetSummary {
  id: string;
  name: string;
  category: string;
  status: AssetStatus;
  bindingTarget: string;
  updatedAt: string;
}

export interface GovernanceSecretsRevision {
  agentId: string;
  agentName: string;
  agentRevisionId: string;
  businessId: string;
  environment: string;
  status: "healthy" | "attention";
  requiredSecretCount: number;
  configuredSecretCount: number;
  missingSecretCount: number;
  requiredSecrets: string[];
  configuredSecrets: string[];
  missingSecrets: string[];
}

export interface GovernanceSecretsHealth {
  activeRevisionCount: number;
  healthyRevisionCount: number;
  attentionRevisionCount: number;
  requiredSecretCount: number;
  configuredSecretCount: number;
  missingSecretCount: number;
  revisions: GovernanceSecretsRevision[];
}

export interface GovernanceAuditEvent {
  id: string;
  eventType: string;
  summary: string;
  resourceType: string | null;
  resourceId: string | null;
  createdAt: string;
}

export interface GovernanceUsageBucket {
  key: string;
  label: string;
  count: number;
  lastUsedAt: string | null;
}

export interface GovernanceUsageSummary {
  totalCount: number;
  byKind: Record<string, number>;
  bySourceKind: GovernanceUsageBucket[];
  byAgent: GovernanceUsageBucket[];
  updatedAt: string;
}

export interface GovernanceUsageEvent {
  id: string;
  kind: string;
  count: number;
  sourceKind: string | null;
  createdAt: string;
}

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string | null;
  metadata: Record<string, unknown>;
  isInternal: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface GovernanceData {
  orgId: string;
  pendingApprovals: ApprovalItem[];
  secretsHealth: GovernanceSecretsHealth;
  recentAudit: GovernanceAuditEvent[];
  usageSummary: GovernanceUsageSummary;
  recentUsage: GovernanceUsageEvent[];
}

export interface CatalogEntrySummary {
  id: string;
  orgId: string;
  agentId: string;
  agentRevisionId: string;
  slug: string;
  name: string;
  summary: string;
  description: string | null;
  visibility: string;
  marketplacePublicationEnabled: boolean;
  hostAdapterKind: string;
  providerKind: string;
  providerCapabilities: string[];
  requiredSkillIds: string[];
  requiredSecretNames: string[];
  releaseChannel: string;
  metadata: JsonRecord;
  createdAt: string;
  updatedAt: string;
}

export interface CatalogInstallRequest {
  catalogEntryId: string;
  businessId: string;
  environment: string;
  name?: string;
}

export interface CatalogInstallRecord {
  id: string;
  catalogEntryId: string;
  sourceAgentId: string;
  sourceAgentRevisionId: string;
  installedAgentId: string;
  installedAgentRevisionId: string;
  businessId: string;
  environment: string;
  createdAt: string;
  updatedAt: string;
}

export interface CatalogInstalledAgent {
  id: string;
  orgId: string;
  businessId: string;
  environment: string;
  name: string;
  slug: string;
  description: string | null;
  visibility: string;
  lifecycleStatus: string;
  packagingMetadata: Record<string, unknown>;
  activeRevisionId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CatalogInstallResult {
  install: CatalogInstallRecord;
  agent: CatalogInstalledAgent;
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
  governance: GovernanceData;
}

export interface MissionControlApi {
  getOrganizations(): Promise<OrganizationSummary[]>;
  getDashboard(): Promise<DashboardSummaryData>;
  getInbox(selectedThreadId?: string): Promise<InboxData>;
  getTasks(): Promise<TasksData>;
  getApprovals(): Promise<ApprovalItem[]>;
  getRuns(): Promise<RunSummary[]>;
  getAgents(): Promise<AgentSummary[]>;
  getAgentDetail(agentId: string): Promise<AgentDetailData>;
  getCatalogEntries(): Promise<CatalogEntrySummary[]>;
  installCatalogEntry(request: CatalogInstallRequest): Promise<CatalogInstallResult>;
  getAssets(): Promise<AssetSummary[]>;
  getGovernance(): Promise<GovernanceData>;
}

export interface MissionControlApiOptions {
  baseUrl?: string;
  runtimeApiKey?: string;
  fetchImpl?: typeof fetch;
  orgId?: string;
  businessId?: string;
  environment?: string;
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

interface ReleaseEvaluationPayload {
  outcome_id?: string;
  outcome_name?: string;
  status?: string;
  satisfied?: boolean;
  evaluator_result?: string;
  failure_details?: string[];
  rubric_criteria?: string[];
  require_passing_evaluation?: boolean;
  blocked_promotion?: boolean;
  rollback_reason?: string | null;
}

interface AgentReleasePayload {
  event_id?: string;
  event_type?: string;
  release_channel?: string | null;
  created_at?: string;
  previous_active_revision_id?: string | null;
  target_revision_id?: string;
  resulting_active_revision_id?: string;
  rollback_source_revision_id?: string | null;
  evaluation?: ReleaseEvaluationPayload | null;
}

interface ReplayActorPayload {
  org_id?: string;
  actor_id?: string;
  actor_type?: string;
}

interface ReplayRevisionPayload {
  agent_id?: string | null;
  agent_revision_id?: string | null;
  active_revision_id?: string | null;
  revision_state?: string | null;
  release_channel?: string | null;
  release_event_id?: string | null;
  release_event_type?: string | null;
}

interface RunReplayPayload {
  role?: string;
  requested_at?: string;
  resolved_at?: string | null;
  replay_reason?: string | null;
  requires_approval?: boolean | null;
  approval_id?: string | null;
  child_run_id?: string | null;
  parent_run_id?: string | null;
  triggering_actor?: ReplayActorPayload | null;
  source?: ReplayRevisionPayload | null;
  replay?: ReplayRevisionPayload | null;
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
  replay?: RunReplayPayload | null;
}

interface RunsPayload {
  runs: RunPayload[];
}

interface AgentPayload {
  id?: string;
  org_id?: string;
  business_id?: string;
  environment?: string;
  name?: string;
  slug?: string;
  description?: string | null;
  visibility?: string;
  lifecycle_status?: string;
  packaging_metadata?: Record<string, unknown>;
  active_revision_id?: string | null;
  active_revision_state?: string;
  live_session_count?: number;
  delegated_work_count?: number;
  host_adapter?: {
    kind?: string;
    enabled?: boolean;
    display_name?: string;
    adapter_details_label?: string;
    capabilities?: {
      dispatch?: boolean;
      status_correlation?: boolean;
      artifact_reporting?: boolean;
      cancellation?: boolean;
    } | null;
    disabled_reason?: string | null;
  } | null;
  release?: AgentReleasePayload | null;
  created_at?: string;
  updated_at?: string;
}

interface AgentRevisionPayload {
  id?: string;
  agent_id?: string;
  revision_number?: number;
  state?: string;
  host_adapter_kind?: string;
  provider_kind?: string;
  provider_capabilities?: string[];
  skill_ids?: string[];
  compatibility_metadata?: Record<string, unknown>;
  release_channel?: string;
  release_notes?: string | null;
  created_at?: string;
  updated_at?: string;
  published_at?: string | null;
  archived_at?: string | null;
  cloned_from_revision_id?: string | null;
}

interface AgentResponsePayload {
  agent?: AgentPayload;
  revisions?: AgentRevisionPayload[];
}

interface MissionControlAgentsPayload {
  agents?: Array<AgentPayload | AgentResponsePayload>;
}

interface ReleaseEventPayload {
  id?: string;
  event_type?: string;
  actor_id?: string;
  actor_type?: string;
  previous_active_revision_id?: string | null;
  target_revision_id?: string;
  resulting_active_revision_id?: string;
  release_channel?: string | null;
  notes?: string | null;
  evaluation_summary?: ReleaseEvaluationPayload | null;
  created_at?: string;
}

interface ReleaseEventListPayload {
  events?: ReleaseEventPayload[];
}

interface SecretBindingPayload {
  binding_name?: string;
}

interface SecretBindingListPayload {
  bindings?: SecretBindingPayload[];
}

interface AuditPayload {
  id?: string;
  event_type?: string;
  summary?: string;
  resource_type?: string | null;
  resource_id?: string | null;
  created_at?: string;
}

interface AuditListPayload {
  events?: AuditPayload[];
}

interface UsageBucketPayload {
  key?: string;
  label?: string;
  count?: number;
  last_used_at?: string | null;
}

interface UsageEventPayload {
  id?: string;
  kind?: string;
  count?: number;
  source_kind?: string | null;
  created_at?: string;
}

interface UsageResponsePayload {
  summary?: {
    total_count?: number;
    by_kind?: Record<string, number>;
    by_source_kind?: UsageBucketPayload[];
    by_agent?: UsageBucketPayload[];
    updated_at?: string;
  };
  events?: UsageEventPayload[];
}

interface TurnPayload {
  id?: string;
  session_id?: string;
  business_id?: string;
  environment?: string;
  agent_id?: string;
  agent_revision_id?: string;
  turn_number?: number;
  state?: string;
  retry_count?: number;
  resumed_from_turn_id?: string | null;
  updated_at?: string;
}

interface TurnsPayload {
  turns?: TurnPayload[];
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

interface GovernanceSecretsRevisionPayload {
  agent_id?: string;
  agent_name?: string;
  agent_revision_id?: string;
  business_id?: string;
  environment?: string;
  status?: string;
  required_secret_count?: number;
  configured_secret_count?: number;
  missing_secret_count?: number;
  required_secrets?: string[];
  configured_secrets?: string[];
  missing_secrets?: string[];
}

interface GovernancePayload {
  org_id?: string;
  pending_approvals?: ApprovalPayload[];
  secrets_health?: {
    active_revision_count?: number;
    healthy_revision_count?: number;
    attention_revision_count?: number;
    required_secret_count?: number;
    configured_secret_count?: number;
    missing_secret_count?: number;
    revisions?: GovernanceSecretsRevisionPayload[];
  };
  recent_audit?: Array<{
    id?: string;
    event_type?: string;
    summary?: string;
    resource_type?: string | null;
    resource_id?: string | null;
    created_at?: string;
  }>;
  usage_summary?: {
    total_count?: number;
    by_kind?: Record<string, number>;
    by_source_kind?: Array<{
      key?: string;
      label?: string;
      count?: number;
      last_used_at?: string | null;
    }>;
    by_agent?: Array<{
      key?: string;
      label?: string;
      count?: number;
      last_used_at?: string | null;
    }>;
    updated_at?: string;
  };
  recent_usage?: Array<{
    id?: string;
    kind?: string;
    count?: number;
    source_kind?: string | null;
    created_at?: string;
  }>;
}

interface OrganizationPayload {
  id?: string;
  name?: string;
  slug?: string | null;
  metadata?: Record<string, unknown>;
  is_internal?: boolean;
  created_at?: string;
  updated_at?: string;
}

interface OrganizationListPayload {
  organizations?: OrganizationPayload[];
}

interface CatalogEntryPayload {
  id?: string;
  org_id?: string;
  agent_id?: string;
  agent_revision_id?: string;
  slug?: string;
  name?: string;
  summary?: string;
  description?: string | null;
  visibility?: string;
  marketplace_publication_enabled?: boolean;
  host_adapter_kind?: string;
  provider_kind?: string;
  provider_capabilities?: string[];
  required_skill_ids?: string[];
  required_secret_names?: string[];
  release_channel?: string;
  metadata?: JsonRecord;
  created_at?: string;
  updated_at?: string;
}

interface CatalogEntryListPayload {
  entries?: CatalogEntryPayload[];
}

interface AgentInstallPayload {
  id?: string;
  catalog_entry_id?: string;
  source_agent_id?: string;
  source_agent_revision_id?: string;
  installed_agent_id?: string;
  installed_agent_revision_id?: string;
  business_id?: string;
  environment?: string;
  created_at?: string;
  updated_at?: string;
}

interface AgentInstallResponsePayload {
  install?: AgentInstallPayload;
  agent?: AgentPayload;
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

function withQueryParams(path: string, params: Record<string, string | undefined>): string {
  const [pathname, search = ""] = path.split("?", 2);
  const searchParams = new URLSearchParams(search);

  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      searchParams.set(key, value);
    }
  });

  const nextSearch = searchParams.toString();
  return nextSearch ? `${pathname}?${nextSearch}` : pathname;
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

  return connectLater ? "unbound" : "attention";
}

function normalizeReleaseEventType(value: unknown): ReleaseEventType {
  return value === "rollback" ? "rollback" : "publish";
}

function normalizeOutcomeStatus(value: unknown): OutcomeStatus {
  return value === "failed" ? "failed" : "satisfied";
}

function normalizeReplayRole(value: unknown): ReplayRole {
  return value === "child" ? "child" : "parent";
}

function mapReleaseEvaluation(payload?: ReleaseEvaluationPayload | null): ReleaseEvaluationState | undefined {
  if (!payload) {
    return undefined;
  }
  return {
    outcomeId: asString(payload.outcome_id),
    outcomeName: asString(payload.outcome_name),
    status: normalizeOutcomeStatus(payload.status),
    satisfied: asBoolean(payload.satisfied, false),
    evaluatorResult: asString(payload.evaluator_result),
    failureDetails: asArray<string>(payload.failure_details).map((value) => asString(value)).filter(Boolean),
    rubricCriteria: asArray<string>(payload.rubric_criteria).map((value) => asString(value)).filter(Boolean),
    requirePassingEvaluation: asBoolean(payload.require_passing_evaluation, false),
    blockedPromotion: asBoolean(payload.blocked_promotion, false),
    rollbackReason: asNullableString(payload.rollback_reason),
  };
}

function mapReplayActor(payload?: ReplayActorPayload | null): ReplayActorState | undefined {
  if (!payload) {
    return undefined;
  }
  const orgId = asString(payload.org_id);
  const actorId = asString(payload.actor_id);
  const actorType = asString(payload.actor_type);
  if (!orgId || !actorId || !actorType) {
    return undefined;
  }
  return { orgId, actorId, actorType };
}

function mapReplayRevision(payload?: ReplayRevisionPayload | null): ReplayRevisionState | undefined {
  if (!payload) {
    return undefined;
  }
  return {
    agentId: asNullableString(payload.agent_id),
    agentRevisionId: asNullableString(payload.agent_revision_id),
    activeRevisionId: asNullableString(payload.active_revision_id),
    revisionState: asNullableString(payload.revision_state),
    releaseChannel: asNullableString(payload.release_channel),
    releaseEventId: asNullableString(payload.release_event_id),
    releaseEventType: payload.release_event_type ? normalizeReleaseEventType(payload.release_event_type) : null,
  };
}

function mapRunReplay(payload?: RunReplayPayload | null): RunReplayState | undefined {
  if (!payload) {
    return undefined;
  }
  return {
    role: normalizeReplayRole(payload.role),
    requestedAt: asString(payload.requested_at),
    resolvedAt: asNullableString(payload.resolved_at),
    replayReason: asNullableString(payload.replay_reason),
    requiresApproval: typeof payload.requires_approval === "boolean" ? payload.requires_approval : null,
    approvalId: asNullableString(payload.approval_id),
    childRunId: asNullableString(payload.child_run_id),
    parentRunId: asNullableString(payload.parent_run_id),
    triggeringActor: mapReplayActor(payload.triggering_actor),
    source: mapReplayRevision(payload.source),
    replay: mapReplayRevision(payload.replay),
  };
}

function mapAgentRelease(payload?: AgentReleasePayload | null): AgentReleaseState | undefined {
  if (!payload) {
    return undefined;
  }
  return {
    eventId: asString(payload.event_id),
    eventType: normalizeReleaseEventType(payload.event_type),
    releaseChannel: asNullableString(payload.release_channel),
    createdAt: asString(payload.created_at),
    previousActiveRevisionId: asNullableString(payload.previous_active_revision_id),
    targetRevisionId: asString(payload.target_revision_id),
    resultingActiveRevisionId: asString(payload.resulting_active_revision_id),
    rollbackSourceRevisionId: asNullableString(payload.rollback_source_revision_id),
    evaluation: mapReleaseEvaluation(payload.evaluation),
  };
}

function mapAgentHostAdapter(payload: AgentPayload["host_adapter"]): AgentHostAdapterSummary | undefined {
  if (!payload || !isRecord(payload)) {
    return undefined;
  }

  const kind = asString(payload.kind);
  const displayName = asString(payload.display_name, kind ? titleCase(kind) : "Host adapter");
  if (!kind && !displayName) {
    return undefined;
  }

  return {
    kind: kind || displayName.toLowerCase().replace(/\s+/g, "_"),
    enabled: asBoolean(payload.enabled, false),
    displayName,
    adapterDetailsLabel: asString(payload.adapter_details_label, "Adapter details"),
    capabilities: {
      dispatch: asBoolean(payload.capabilities?.dispatch, false),
      statusCorrelation: asBoolean(payload.capabilities?.status_correlation, false),
      artifactReporting: asBoolean(payload.capabilities?.artifact_reporting, false),
      cancellation: asBoolean(payload.capabilities?.cancellation, false),
    },
    disabledReason: asNullableString(payload.disabled_reason),
  };
}

function deriveRunSummary(payload: RunPayload, replay?: RunReplayState): string {
  if (payload.error_message) {
    return payload.error_classification
      ? `${payload.error_classification}: ${payload.error_message}`
      : payload.error_message;
  }

  if (replay?.role === "child" && replay.parentRunId) {
    return `Replay child bound to ${replay.parentRunId}.`;
  }
  if (replay?.role === "parent" && replay.requiresApproval) {
    return replay.approvalId ? `Replay awaiting approval ${replay.approvalId}.` : "Replay awaiting approval.";
  }
  if (replay?.role === "parent" && replay.childRunId) {
    return `Replay launched child run ${replay.childRunId}.`;
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
  return asArray<RunPayload>(payload.runs).map((run) => {
    const replay = mapRunReplay(run.replay);
    return {
      id: asString(run.id),
      commandType: asString(run.command_type),
      status: normalizeRunStatus(run.status),
      businessId: asString(run.business_id),
      environment: asString(run.environment),
      updatedAt: asString(run.updated_at),
      parentRunId: asNullableString(run.parent_run_id),
      triggerRunId: asNullableString(run.trigger_run_id),
      summary: deriveRunSummary(run, replay),
      replay,
    };
  });
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
      slug: asString(agent.slug, asString(agent.id, `agent-${index}`)),
      description: asNullableString(agent.description),
      businessId: asString(agent.business_id, "default"),
      lifecycleStatus: asString(agent.lifecycle_status, "unavailable"),
      activeRevisionId,
      activeRevisionState,
      environment: asString(agent.environment, "unknown"),
      liveSessionCount: asNumber(agent.live_session_count),
      delegatedWorkCount: asNumber(agent.delegated_work_count),
      hostAdapter: mapAgentHostAdapter(agent.host_adapter),
      release: mapAgentRelease(agent.release),
      createdAt: asString(agent.created_at, "Unknown"),
      updatedAt: asString(agent.updated_at, "Unknown"),
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

function declaredSecretNames(compatibilityMetadata: unknown): string[] {
  if (!isRecord(compatibilityMetadata)) {
    return [];
  }

  return asArray<string>(compatibilityMetadata.requires_secrets)
    .map((value) => asString(value))
    .filter(Boolean);
}

function mapAuditEvents(events: AuditPayload[] | Array<Record<string, unknown>>): GovernanceAuditEvent[] {
  return events.map((event, index) => ({
    id: asString(event.id, `audit-${index}`),
    eventType: asString(event.event_type, "event"),
    summary: asString(event.summary, "Audit event"),
    resourceType: asNullableString(event.resource_type),
    resourceId: asNullableString(event.resource_id),
    createdAt: asString(event.created_at, "Unknown"),
  }));
}

function mapUsageSummary(payload?: UsageResponsePayload["summary"] | Record<string, unknown>): GovernanceUsageSummary {
  const summary = payload && isRecord(payload) ? payload : {};

  return {
    totalCount: asNumber(summary.total_count),
    byKind: isRecord(summary.by_kind)
      ? Object.fromEntries(Object.entries(summary.by_kind).map(([key, value]) => [key, asNumber(value)]))
      : {},
    bySourceKind: asArray<UsageBucketPayload>(summary.by_source_kind).map((bucket, index) => ({
      key: asString(bucket.key, `source-${index}`),
      label: asString(bucket.label, asString(bucket.key, `source-${index}`)),
      count: asNumber(bucket.count),
      lastUsedAt: asNullableString(bucket.last_used_at),
    })),
    byAgent: asArray<UsageBucketPayload>(summary.by_agent).map((bucket, index) => ({
      key: asString(bucket.key, `agent-${index}`),
      label: asString(bucket.label, asString(bucket.key, `agent-${index}`)),
      count: asNumber(bucket.count),
      lastUsedAt: asNullableString(bucket.last_used_at),
    })),
    updatedAt: asString(summary.updated_at, "Unknown"),
  };
}

function mapUsageEvents(events: UsageEventPayload[] | Array<Record<string, unknown>>): GovernanceUsageEvent[] {
  return events.map((event, index) => ({
    id: asString(event.id, `usage-${index}`),
    kind: asString(event.kind, "usage"),
    count: asNumber(event.count),
    sourceKind: asNullableString(event.source_kind),
    createdAt: asString(event.created_at, "Unknown"),
  }));
}

function mapTurns(payload: TurnsPayload): TurnSummary[] {
  return asArray<TurnPayload>(payload.turns).map((turn, index) => ({
    id: asString(turn.id, `turn-${index}`),
    sessionId: asString(turn.session_id),
    businessId: asString(turn.business_id, "default"),
    environment: asString(turn.environment, "dev"),
    agentId: asString(turn.agent_id),
    agentRevisionId: asString(turn.agent_revision_id),
    turnNumber: asNumber(turn.turn_number, index + 1),
    state: asString(turn.state, "queued"),
    retryCount: asNumber(turn.retry_count),
    resumedFromTurnId: asNullableString(turn.resumed_from_turn_id),
    updatedAt: asString(turn.updated_at, "Unknown"),
  }));
}

function mapAgentRecord(
  payload: AgentPayload,
  revisions: AgentRevisionPayload[] = [],
  fallbackState = "unpublished",
): AgentRecordState {
  const activeRevisionId = asNullableString(payload.active_revision_id);
  const activeRevisionState = asString(
    payload.active_revision_state,
    activeRevisionId
      ? "published"
      : revisions.find((revision) => revision.state === "draft")
        ? "draft"
        : fallbackState,
  );

  return {
    id: asString(payload.id),
    name: asString(payload.name, "Unknown agent"),
    slug: asString(payload.slug, asString(payload.id, "agent")),
    description: asNullableString(payload.description),
    businessId: asString(payload.business_id, "default"),
    environment: asString(payload.environment, "unknown"),
    lifecycleStatus: asString(payload.lifecycle_status, activeRevisionState),
    activeRevisionId,
    activeRevisionState,
  };
}

function mapAgentRevision(payload: AgentRevisionPayload, index: number): AgentRevisionDetail {
  return {
    id: asString(payload.id, `revision-${index}`),
    agentId: asString(payload.agent_id),
    revisionNumber: asNumber(payload.revision_number, index + 1),
    state: asString(payload.state, "draft"),
    hostAdapterKind: asString(payload.host_adapter_kind, "unknown"),
    providerKind: asString(payload.provider_kind, "unknown"),
    providerCapabilities: asArray<string>(payload.provider_capabilities).map((value) => asString(value)).filter(Boolean),
    skillIds: asArray<string>(payload.skill_ids).map((value) => asString(value)).filter(Boolean),
    requiredSecrets: declaredSecretNames(payload.compatibility_metadata),
    releaseChannel: asString(payload.release_channel, "internal"),
    releaseNotes: asNullableString(payload.release_notes),
    createdAt: asString(payload.created_at, "Unknown"),
    updatedAt: asString(payload.updated_at, "Unknown"),
    publishedAt: asNullableString(payload.published_at),
    archivedAt: asNullableString(payload.archived_at),
    clonedFromRevisionId: asNullableString(payload.cloned_from_revision_id),
  };
}

function mapAgentReleaseEvents(payload: ReleaseEventListPayload): AgentReleaseEvent[] {
  return asArray<ReleaseEventPayload>(payload.events).map((event, index) => ({
    id: asString(event.id, `release-${index}`),
    eventType: normalizeReleaseEventType(event.event_type),
    actorId: asString(event.actor_id, "system"),
    actorType: asString(event.actor_type, "service"),
    previousActiveRevisionId: asNullableString(event.previous_active_revision_id),
    targetRevisionId: asString(event.target_revision_id),
    resultingActiveRevisionId: asString(event.resulting_active_revision_id),
    releaseChannel: asNullableString(event.release_channel),
    notes: asNullableString(event.notes),
    createdAt: asString(event.created_at, "Unknown"),
    evaluation: mapReleaseEvaluation(event.evaluation_summary),
  }));
}

function mapAgentSecretsHealth(
  revisionId: string | null,
  bindingsPayload: SecretBindingListPayload | null,
  revisions: AgentRevisionDetail[],
  bindingsUnavailable = false,
): AgentSecretsHealth | null {
  if (!revisionId || bindingsUnavailable) {
    return null;
  }

  const activeRevision = revisions.find((revision) => revision.id === revisionId);
  if (!activeRevision) {
    return null;
  }

  const configuredSecrets = asArray<SecretBindingPayload>(bindingsPayload?.bindings)
    .map((binding) => asString(binding.binding_name))
    .filter(Boolean);
  const missingSecrets = activeRevision.requiredSecrets.filter((secretName) => !configuredSecrets.includes(secretName));

  return {
    revisionId,
    status: missingSecrets.length > 0 ? "attention" : "healthy",
    requiredSecretCount: activeRevision.requiredSecrets.length,
    configuredSecretCount: configuredSecrets.length,
    missingSecretCount: missingSecrets.length,
    requiredSecrets: activeRevision.requiredSecrets,
    configuredSecrets,
    missingSecrets,
  };
}

function mapAgentDetail(
  payload: AgentResponsePayload,
  releaseHistoryPayload: ReleaseEventListPayload,
  auditPayload: AuditListPayload,
  usagePayload: UsageResponsePayload,
  turnsPayload: TurnsPayload,
  bindingsPayload: SecretBindingListPayload | null,
  degradedSections: AgentDetailDegradedSection[] = [],
): AgentDetailData {
  const revisionsPayload = asArray<AgentRevisionPayload>(payload.revisions);
  const revisions = revisionsPayload.map((revision, index) => mapAgentRevision(revision, index));
  const agent = mapAgentRecord(payload.agent ?? {}, revisionsPayload);

  return {
    agent,
    revisions,
    releaseHistory: mapAgentReleaseEvents(releaseHistoryPayload),
    secretsHealth: mapAgentSecretsHealth(agent.activeRevisionId, bindingsPayload, revisions, degradedSections.includes("secretsHealth")),
    recentAudit: mapAuditEvents(asArray<AuditPayload>(auditPayload.events)),
    usageSummary: mapUsageSummary(usagePayload.summary),
    recentUsage: mapUsageEvents(asArray<UsageEventPayload>(usagePayload.events)),
    recentTurns: mapTurns(turnsPayload)
      .filter((turn) => turn.agentId === agent.id)
      .slice(0, 6),
    degradedSections,
  };
}

function mapGovernance(payload: GovernancePayload): GovernanceData {
  const secretsHealth = isRecord(payload.secrets_health) ? payload.secrets_health : {};
  const usageSummary = isRecord(payload.usage_summary) ? payload.usage_summary : {};

  return {
    orgId: asString(payload.org_id, "default"),
    pendingApprovals: mapApprovals({ approvals: asArray<ApprovalPayload>(payload.pending_approvals) }),
    secretsHealth: {
      activeRevisionCount: asNumber(secretsHealth.active_revision_count),
      healthyRevisionCount: asNumber(secretsHealth.healthy_revision_count),
      attentionRevisionCount: asNumber(secretsHealth.attention_revision_count),
      requiredSecretCount: asNumber(secretsHealth.required_secret_count),
      configuredSecretCount: asNumber(secretsHealth.configured_secret_count),
      missingSecretCount: asNumber(secretsHealth.missing_secret_count),
      revisions: asArray<GovernanceSecretsRevisionPayload>(secretsHealth.revisions).map((revision, index) => ({
        agentId: asString(revision.agent_id, `agent-${index}`),
        agentName: asString(revision.agent_name, "Unknown agent"),
        agentRevisionId: asString(revision.agent_revision_id, `revision-${index}`),
        businessId: asString(revision.business_id, "default"),
        environment: asString(revision.environment, "dev"),
        status: revision.status === "attention" ? "attention" : "healthy",
        requiredSecretCount: asNumber(revision.required_secret_count),
        configuredSecretCount: asNumber(revision.configured_secret_count),
        missingSecretCount: asNumber(revision.missing_secret_count),
        requiredSecrets: asArray<string>(revision.required_secrets).map((value) => asString(value)).filter(Boolean),
        configuredSecrets: asArray<string>(revision.configured_secrets).map((value) => asString(value)).filter(Boolean),
        missingSecrets: asArray<string>(revision.missing_secrets).map((value) => asString(value)).filter(Boolean),
      })),
    },
    recentAudit: asArray<Record<string, unknown>>(payload.recent_audit).map((event, index) => ({
      id: asString(event.id, `audit-${index}`),
      eventType: asString(event.event_type, "event"),
      summary: asString(event.summary, "Audit event"),
      resourceType: asNullableString(event.resource_type),
      resourceId: asNullableString(event.resource_id),
      createdAt: asString(event.created_at, "Unknown"),
    })),
    usageSummary: {
      totalCount: asNumber(usageSummary.total_count),
      byKind: isRecord(usageSummary.by_kind)
        ? Object.fromEntries(
            Object.entries(usageSummary.by_kind).map(([key, value]) => [key, asNumber(value)]),
          )
        : {},
      bySourceKind: asArray<Record<string, unknown>>(usageSummary.by_source_kind).map((bucket, index) => ({
        key: asString(bucket.key, `source-${index}`),
        label: asString(bucket.label, asString(bucket.key, `source-${index}`)),
        count: asNumber(bucket.count),
        lastUsedAt: asNullableString(bucket.last_used_at),
      })),
      byAgent: asArray<Record<string, unknown>>(usageSummary.by_agent).map((bucket, index) => ({
        key: asString(bucket.key, `agent-${index}`),
        label: asString(bucket.label, asString(bucket.key, `agent-${index}`)),
        count: asNumber(bucket.count),
        lastUsedAt: asNullableString(bucket.last_used_at),
      })),
      updatedAt: asString(usageSummary.updated_at, "Unknown"),
    },
    recentUsage: asArray<Record<string, unknown>>(payload.recent_usage).map((event, index) => ({
      id: asString(event.id, `usage-${index}`),
      kind: asString(event.kind, "usage"),
      count: asNumber(event.count),
      sourceKind: asNullableString(event.source_kind),
      createdAt: asString(event.created_at, "Unknown"),
    })),
  };
}

function mapOrganizations(payload: OrganizationListPayload | OrganizationPayload[]): OrganizationSummary[] {
  const organizations = Array.isArray(payload) ? payload : asArray<OrganizationPayload>(payload.organizations);
  return organizations.map((organization, index) => ({
    id: asString(organization.id, `org-${index}`),
    name: asString(organization.name, "Unknown organization"),
    slug: asNullableString(organization.slug),
    metadata: isRecord(organization.metadata) ? organization.metadata : {},
    isInternal: asBoolean(organization.is_internal, false),
    createdAt: asString(organization.created_at, "Unknown"),
    updatedAt: asString(organization.updated_at, "Unknown"),
  }));
}

function mapCatalogEntries(payload: CatalogEntryListPayload | CatalogEntryPayload[]): CatalogEntrySummary[] {
  const entries = Array.isArray(payload) ? payload : asArray<CatalogEntryPayload>(payload.entries);
  return entries.map((entry, index) => ({
    id: asString(entry.id, `cat-${index}`),
    orgId: asString(entry.org_id, "org_internal"),
    agentId: asString(entry.agent_id, `agent-${index}`),
    agentRevisionId: asString(entry.agent_revision_id, `revision-${index}`),
    slug: asString(entry.slug, `catalog-${index}`),
    name: asString(entry.name, "Unknown catalog entry"),
    summary: asString(entry.summary, "No summary available."),
    description: asNullableString(entry.description),
    visibility: asString(entry.visibility, "internal"),
    marketplacePublicationEnabled: Boolean(entry.marketplace_publication_enabled),
    hostAdapterKind: asString(entry.host_adapter_kind, "unknown"),
    providerKind: asString(entry.provider_kind, "unknown"),
    providerCapabilities: asArray<string>(entry.provider_capabilities).map((value) => asString(value)).filter(Boolean),
    requiredSkillIds: asArray<string>(entry.required_skill_ids).map((value) => asString(value)).filter(Boolean),
    requiredSecretNames: asArray<string>(entry.required_secret_names).map((value) => asString(value)).filter(Boolean),
    releaseChannel: asString(entry.release_channel, "internal"),
    metadata: isRecord(entry.metadata) ? entry.metadata : {},
    createdAt: asString(entry.created_at, "Unknown"),
    updatedAt: asString(entry.updated_at, "Unknown"),
  }));
}

function mapCatalogInstalledAgent(payload: AgentPayload): CatalogInstalledAgent {
  const rawPackagingMetadata = isRecord(payload.packaging_metadata) ? payload.packaging_metadata : {};
  return {
    id: asString(payload.id, "agt-installed"),
    orgId: asString(payload.org_id, "org_internal"),
    businessId: asString(payload.business_id, "default"),
    environment: asString(payload.environment, "dev"),
    name: asString(payload.name, "Installed agent"),
    slug: asString(payload.slug, "installed-agent"),
    description: asNullableString(payload.description),
    visibility: asString(payload.visibility, "internal"),
    lifecycleStatus: asString(payload.lifecycle_status, "draft"),
    packagingMetadata: {
      ...rawPackagingMetadata,
      catalogEntryId: asNullableString(rawPackagingMetadata.catalog_entry_id) ?? asNullableString(rawPackagingMetadata.catalogEntryId),
      sourceAgentId: asNullableString(rawPackagingMetadata.source_agent_id) ?? asNullableString(rawPackagingMetadata.sourceAgentId),
      sourceAgentRevisionId:
        asNullableString(rawPackagingMetadata.source_agent_revision_id) ?? asNullableString(rawPackagingMetadata.sourceAgentRevisionId),
    },
    activeRevisionId: asNullableString(payload.active_revision_id),
    createdAt: asString(payload.created_at, "Unknown"),
    updatedAt: asString(payload.updated_at, "Unknown"),
  };
}

function mapCatalogInstallResult(payload: AgentInstallResponsePayload): CatalogInstallResult {
  const install = isRecord(payload.install) ? payload.install : {};
  const agent = isRecord(payload.agent) ? payload.agent : {};
  return {
    install: {
      id: asString(install.id, "ins-1"),
      catalogEntryId: asString(install.catalog_entry_id, "catalog-entry"),
      sourceAgentId: asString(install.source_agent_id, "source-agent"),
      sourceAgentRevisionId: asString(install.source_agent_revision_id, "source-revision"),
      installedAgentId: asString(install.installed_agent_id, "installed-agent"),
      installedAgentRevisionId: asString(install.installed_agent_revision_id, "installed-revision"),
      businessId: asString(install.business_id, "default"),
      environment: asString(install.environment, "dev"),
      createdAt: asString(install.created_at, "Unknown"),
      updatedAt: asString(install.updated_at, "Unknown"),
    },
    agent: mapCatalogInstalledAgent(agent as AgentPayload),
  };
}

type RequestScope = "none" | "mission-control" | "governance";

function buildRequestPath(
  path: string,
  options: MissionControlApiOptions,
  scope: RequestScope = "none",
): string {
  if (scope !== "mission-control") {
    return path;
  }

  return withQueryParams(path, {
    business_id: options.businessId,
    environment: options.environment,
  });
}

async function requestJson<T>(
  path: string,
  options: MissionControlApiOptions,
  scope: RequestScope = "none",
  init?: RequestInit,
): Promise<T> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const requestHeaders = new Headers(init?.headers);
  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  requestHeaders.forEach((value, key) => {
    headers[key] = value;
  });

  if (options.runtimeApiKey) {
    headers.Authorization = `Bearer ${options.runtimeApiKey}`;
  }

  if (options.orgId) {
    headers["X-Ares-Org-Id"] = options.orgId;
  }

  const response = await fetchImpl(buildUrl(options.baseUrl ?? defaultBaseUrl, buildRequestPath(path, options, scope)), {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail.trim().length > 0) {
        detail = payload.detail;
      }
    } catch {
      const text = await response.text().catch(() => "");
      if (text.trim().length > 0) {
        detail = text.trim();
      }
    }
    throw new Error(`Mission Control API request failed: ${detail}`);
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
    orgId: options.orgId,
    businessId: options.businessId,
    environment: options.environment,
  };

  return {
    getOrganizations: async () =>
      mapOrganizations(await requestJson<OrganizationListPayload | OrganizationPayload[]>("/organizations", resolvedOptions)),
    getDashboard: async () =>
      mapDashboard(await requestJson<DashboardPayload>("/mission-control/dashboard", resolvedOptions, "mission-control")),
    getInbox: async (selectedThreadId?: string) => {
      const inboxPath = selectedThreadId
        ? `/mission-control/inbox?selected_thread_id=${encodeURIComponent(selectedThreadId)}`
        : "/mission-control/inbox";
      return mapInbox(await requestJson<InboxPayload>(inboxPath, resolvedOptions, "mission-control"));
    },
    getTasks: async () => mapTasks(await requestJson<TasksPayload>("/mission-control/tasks", resolvedOptions, "mission-control")),
    getApprovals: async () =>
      mapApprovals(
        await requestJson<MissionControlApprovalsPayload | ApprovalPayload[]>(
          "/mission-control/approvals",
          resolvedOptions,
          "mission-control",
        ),
      ),
    getRuns: async () => mapRuns(await requestJson<RunsPayload>("/mission-control/runs", resolvedOptions, "mission-control")),
    getAgents: async () =>
      mapAgents(
        await requestJson<MissionControlAgentsPayload | AgentPayload[] | AgentResponsePayload[]>(
          "/mission-control/agents",
          resolvedOptions,
          "mission-control",
        ),
      ),
    getAgentDetail: async (agentId: string) => {
      const agentPath = `/agents/${encodeURIComponent(agentId)}`;
      const releasePath = `/release-management/agents/${encodeURIComponent(agentId)}/events`;
      const auditPath = `/mission-control/audit?agent_id=${encodeURIComponent(agentId)}&limit=8`;
      const usagePath = `/usage?agent_id=${encodeURIComponent(agentId)}&limit=8`;
      const turnsPath = "/mission-control/turns";

      const agentPayload = await requestJson<AgentResponsePayload>(agentPath, resolvedOptions);
      const degradedSections: AgentDetailDegradedSection[] = [];
      const [releaseHistoryResult, auditResult, usageResult, turnsResult] = await Promise.allSettled([
        requestJson<ReleaseEventListPayload>(releasePath, resolvedOptions),
        requestJson<AuditListPayload>(auditPath, resolvedOptions, "mission-control"),
        requestJson<UsageResponsePayload>(usagePath, resolvedOptions),
        requestJson<TurnsPayload>(turnsPath, resolvedOptions, "mission-control"),
      ]);

      const releaseHistoryPayload = releaseHistoryResult.status === "fulfilled" ? releaseHistoryResult.value : (degradedSections.push("releaseHistory"), { events: [] });
      const auditPayload = auditResult.status === "fulfilled" ? auditResult.value : (degradedSections.push("recentAudit"), { events: [] });
      const usagePayload = usageResult.status === "fulfilled"
        ? usageResult.value
        : (degradedSections.push("usage"), { summary: { total_count: 0, by_kind: {}, by_source_kind: [], by_agent: [], updated_at: "Unknown" }, events: [] });
      const turnsPayload = turnsResult.status === "fulfilled" ? turnsResult.value : (degradedSections.push("recentTurns"), { turns: [] });

      const activeRevisionId = asNullableString(agentPayload.agent?.active_revision_id);
      let bindingsPayload: SecretBindingListPayload | null = null;
      if (activeRevisionId) {
        try {
          bindingsPayload = await requestJson<SecretBindingListPayload>(
            `/mission-control/settings/secrets/revisions/${encodeURIComponent(activeRevisionId)}`,
            resolvedOptions,
            "mission-control",
          );
        } catch {
          degradedSections.push("secretsHealth");
        }
      }

      return mapAgentDetail(agentPayload, releaseHistoryPayload, auditPayload, usagePayload, turnsPayload, bindingsPayload, degradedSections);
    },
    getCatalogEntries: async () => mapCatalogEntries(await requestJson<CatalogEntryListPayload>("/catalog", resolvedOptions)),
    installCatalogEntry: async (request) =>
      mapCatalogInstallResult(
        await requestJson<AgentInstallResponsePayload>(
          "/agent-installs",
          resolvedOptions,
          "none",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              catalog_entry_id: request.catalogEntryId,
              business_id: request.businessId,
              environment: request.environment,
              name: request.name,
            }),
          },
        ),
      ),
    getAssets: async () =>
      mapAssets(
        await requestJson<MissionControlAssetsPayload | AssetPayload[]>(
          "/mission-control/settings/assets",
          resolvedOptions,
          "mission-control",
        ),
      ),
    getGovernance: async () =>
      mapGovernance(
        await requestJson<GovernancePayload>(
          "/mission-control/settings/governance",
          resolvedOptions,
          "governance",
        ),
      ),
  };
}
