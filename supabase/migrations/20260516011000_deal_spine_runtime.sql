begin;

create table if not exists public.deal_records_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  source_lane text,
  strategy_lane text,
  stage text,
  county text,
  no_send boolean,
  provider_sends_enabled boolean,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.deal_parties_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  deal_id text not null,
  role text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.deal_tasks_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  deal_id text not null,
  task_type text,
  status text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.deal_document_requirements_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  deal_id text not null,
  document_type text,
  required_stage text,
  status text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.deal_audit_events_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  deal_id text not null,
  event_type text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.deal_stage_events_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  deal_id text not null,
  to_stage text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.deal_risk_flags_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  deal_id text not null,
  severity text,
  active boolean,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists deal_records_runtime_scope_idx on public.deal_records_runtime (business_id, environment, stage, updated_at desc);
create index if not exists deal_records_runtime_strategy_idx on public.deal_records_runtime (business_id, environment, strategy_lane, updated_at desc);
create index if not exists deal_parties_runtime_deal_idx on public.deal_parties_runtime (deal_id, role, updated_at desc);
create index if not exists deal_tasks_runtime_deal_idx on public.deal_tasks_runtime (deal_id, status, updated_at desc);
create index if not exists deal_document_requirements_runtime_deal_idx on public.deal_document_requirements_runtime (deal_id, required_stage, status, updated_at desc);
create index if not exists deal_audit_events_runtime_deal_idx on public.deal_audit_events_runtime (deal_id, created_at desc);
create index if not exists deal_stage_events_runtime_deal_idx on public.deal_stage_events_runtime (deal_id, created_at desc);
create index if not exists deal_risk_flags_runtime_deal_idx on public.deal_risk_flags_runtime (deal_id, active, severity, updated_at desc);

commit;
