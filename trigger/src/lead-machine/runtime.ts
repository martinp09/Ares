export const LEAD_MACHINE_ENDPOINTS = {
  probateIntake: "/lead-machine/probate/intake",
  outboundEnqueue: "/lead-machine/outbound/enqueue",
  instantlyWebhookIngest: "/lead-machine/webhooks/instantly",
  followupStepRunner: "/lead-machine/internal/followup-step-runner",
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
