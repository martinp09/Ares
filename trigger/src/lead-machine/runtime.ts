export const LEAD_MACHINE_ENDPOINTS = {
  leadIntake: "/lead-machine/intake",
  probateIntake: "/lead-machine/probate/intake",
  probatePropertyTaxTitleEnrichment: "/lead-machine/internal/probate-property-tax-title-enrichment",
  outboundEnqueue: "/lead-machine/outbound/enqueue",
  instantlyWebhookIngest: "/lead-machine/webhooks/instantly",
  followupStepRunner: "/lead-machine/internal/followup-step-runner",
  nightlySourcePull: "/lead-machine/internal/nightly-source-pull",
  morningBrief: "/lead-machine/internal/morning-brief",
  suppressionSync: "/lead-machine/internal/suppression-sync",
  taskReminderOrOverdue: "/lead-machine/internal/task-reminder-or-overdue",
} as const;

export type LeadMachineRunContext = {
  run_id?: string;
  command_id?: string;
  idempotency_key?: string;
  trigger_run_id?: string;
};

export type ProbateIntakeRecordInput = {
  case_number?: string;
  cause_number?: string;
  filing_type?: string;
  type?: string;
  hcad_candidates?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

export type ProbateIntakePayload = {
  business_id: string;
  environment: string;
  records: ProbateIntakeRecordInput[];
  keep_only?: boolean;
} & LeadMachineRunContext;

export type ProbateIntakeResponse = {
  processed_count: number;
  keep_now_count: number;
  bridged_count: number;
  records: Array<{
    case_number: string;
    keep_now: boolean;
    lead_score: number | null;
    hcad_match_status: string;
    contact_confidence: string;
    bridged_lead_id: string | null;
  }>;
};

export type ProbatePropertyTaxTitleEnrichmentPayload = {
  business_id: string;
  environment: string;
  keep_now_rows?: Array<Record<string, unknown>>;
  hcad_candidates_by_case?: Record<string, Array<Record<string, unknown>>>;
  tax_overlays_by_case?: Record<string, Record<string, unknown>>;
  tax_overlays_by_account?: Record<string, Record<string, unknown>>;
  land_record_rows_by_case?: Record<string, Array<Record<string, unknown>>>;
  live_cad_calls?: boolean;
  live_tax_calls?: boolean;
  live_land_record_calls?: boolean;
} & LeadMachineRunContext;

export type ProbatePropertyTaxTitleEnrichmentResponse = {
  business_id: string;
  environment: string;
  received_count: number;
  enriched_count: number;
  property_match_completed_count: number;
  property_match_unmatched_count: number;
  tax_overlay_completed_count: number;
  tax_overlay_ambiguous_count: number;
  title_friction_completed_count: number;
  title_friction_review_count: number;
  hubspot_mirror_blocked_until_approval_count: number;
  outbound_blocked_until_explicit_approval_count: number;
  no_send: boolean;
  provider_sends_enabled: boolean;
  outbound_allowed: boolean;
  live_cad_calls_attempted: boolean;
  live_tax_calls_attempted: boolean;
  live_land_record_calls_attempted: boolean;
  records: Array<Record<string, unknown>>;
};

export type LeadIntakePayload = {
  business_id: string;
  environment: string;
  source?: string;
  source_record_id?: string | null;
  campaign_key?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  phone?: string | null;
  email?: string | null;
  property_address?: string | null;
  county?: string | null;
  status?: string;
  pipeline_stage?: string | null;
  priority?: string | null;
  dedupe_key?: string | null;
  metadata?: Record<string, unknown>;
} & LeadMachineRunContext;

export type LeadIntakeResponse = {
  status: "created" | "deduped" | "queued" | "skipped";
  lead_id: string;
  event_id: string;
  queued: boolean;
  skipped: boolean;
  failed_side_effects: string[];
};

export type OutboundEnqueuePayload = {
  business_id: string;
  environment: string;
  lead_ids: string[];
  campaign_id?: string | null;
  list_id?: string | null;
  skip_if_in_workspace?: boolean;
  skip_if_in_campaign?: boolean;
  skip_if_in_list?: boolean;
  blocklist_id?: string | null;
  assigned_to?: string | null;
  verify_leads_on_import?: boolean;
  operator_approval?: boolean;
  chunk_size?: number | null;
  wait_seconds?: number | null;
} & LeadMachineRunContext;

export type OutboundEnqueueResponse = {
  automation_run_ids: string[];
  membership_ids: string[];
  suppressed_lead_ids: string[];
  provider_batches: Array<Record<string, unknown>>;
};

export type InstantlyWebhookPayload = {
  business_id: string;
  environment: string;
  payload: Record<string, unknown>;
  trusted?: boolean;
  trust_reason?: string | null;
} & LeadMachineRunContext;

export type InstantlyWebhookResponse = {
  status: string;
  receipt_id: string;
  event_id?: string | null;
  lead_id?: string | null;
  suppression_id?: string | null;
  membership_id?: string | null;
  task_id?: string | null;
};

export type FollowupStepRunnerPayload = {
  business_id: string;
  environment: string;
  lead_id: string;
  day: number;
  channel: "sms" | "email";
  template_id: string;
  manual_call_checkpoint?: boolean;
  campaign_id?: string | null;
} & LeadMachineRunContext;

export type FollowupStepRunnerResponse = {
  message_id: string;
  channel: "sms" | "email";
  status: string;
  suppressed: boolean;
};

export type SuppressionSyncPayload = {
  business_id: string;
  environment: string;
  lead_id: string;
  campaign_id?: string | null;
  lead_email?: string | null;
  event_type: string;
  provider_name?: string | null;
  provider_event_id?: string | null;
  event_timestamp?: string | null;
  idempotency_key?: string | null;
} & LeadMachineRunContext;

export type SuppressionSyncResponse = {
  status: string;
  suppression_id?: string | null;
  reason?: string | null;
  active: boolean;
  event_type: string;
};

export type TaskReminderOrOverduePayload = {
  business_id: string;
  environment: string;
  task_id: string;
  task_title: string;
  due_at: string;
  status: string;
  lead_id?: string | null;
  assigned_to?: string | null;
  priority?: "low" | "normal" | "high" | "urgent" | null;
} & LeadMachineRunContext;

export type TaskReminderOrOverdueResponse = {
  status: string;
  reminder_task_id?: string | null;
  overdue: boolean;
  reminder_created: boolean;
};

export type SourceRunArtifact = {
  path: string;
  artifact_type: string;
  record_count?: number;
  checksum?: string | null;
  warnings?: string[];
  metadata?: Record<string, unknown>;
};

export type SourceRunLane =
  | "harris_county_probate"
  | "montgomery_county_probate"
  | "hcad_estate_of"
  | "hctax_delinquency_overlay"
  | "harris_land_records"
  | "harris_hcad_property_match"
  | "montgomery_cad_property_match"
  | "harris_hctax_overlay"
  | "montgomery_act_tax_overlay"
  | "montgomery_land_records"
  | "skiptrace_contact_enrichment"
  | "copy_asset_generation"
  | "hubspot_crm_mirror";

export type SourceRunCounty = "harris" | "montgomery";

export type SourceRunKind =
  | "morning_catchup"
  | "midday"
  | "end_of_day"
  | "daily_reconciliation"
  | "weekly_reconciliation"
  | "manual";

export type SourceRunManifest = {
  source_key: string;
  source_label: string;
  source_lane: SourceRunLane;
  county?: SourceRunCounty | null;
  run_kind?: SourceRunKind | null;
  window_start?: string | null;
  window_end?: string | null;
  idempotency_key?: string | null;
  source_reported_count?: number | null;
  raw_count?: number | null;
  parsed_count?: number | null;
  keep_now_count?: number | null;
  artifacts?: SourceRunArtifact[];
  record_count?: number | null;
  warnings?: string[];
  failed?: boolean;
  error_message?: string | null;
  metadata?: Record<string, unknown>;
};

export type NightlySourcePullPayload = {
  business_id: string;
  environment: string;
  source_runs?: SourceRunManifest[];
  live_source_calls?: boolean;
  metadata?: Record<string, unknown>;
} & LeadMachineRunContext;

export type MorningBriefPayload = {
  business_id: string;
  environment: string;
  source_run_ids?: string[];
  metadata?: Record<string, unknown>;
} & LeadMachineRunContext;

export type SourceRunResponse = {
  id: string;
  business_id: string;
  environment: string;
  source_key: string;
  source_label: string;
  source_lane: string;
  county?: SourceRunCounty | null;
  run_kind?: SourceRunKind | null;
  window_start?: string | null;
  window_end?: string | null;
  idempotency_key?: string | null;
  source_reported_count?: number | null;
  raw_count?: number | null;
  parsed_count?: number | null;
  keep_now_count?: number | null;
  status: "pending" | "running" | "completed" | "failed";
  record_count: number;
  artifact_count: number;
  warning_count: number;
  error_message?: string | null;
  artifacts: SourceRunArtifact[];
  metadata: Record<string, unknown>;
};

export type MorningBriefResponse = {
  id: string;
  business_id: string;
  environment: string;
  generated_at: string;
  source_runs: SourceRunResponse[];
  new_record_count: number;
  hot_lead_count: number;
  warm_lead_count: number;
  blocked_count: number;
  approval_required_count: number;
  sections: Record<string, unknown>;
  warnings: string[];
};

export type NightlySourcePullResponse = {
  status: "completed";
  would_call_external_sources: boolean;
  live_source_calls_enabled: boolean;
  source_runs: SourceRunResponse[];
  morning_brief: MorningBriefResponse;
  warnings: string[];
  duplicate?: boolean;
  replayed?: boolean;
};
