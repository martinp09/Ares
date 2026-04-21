begin;

create table if not exists public.agents_runtime (
  id text primary key,
  org_id text not null,
  business_id text not null,
  environment text not null,
  agent_id text,
  name text,
  status text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.agent_revisions_runtime (
  id text primary key,
  agent_id text not null,
  status text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.sessions_runtime (
  id text primary key,
  org_id text not null,
  business_id text not null,
  environment text not null,
  agent_id text not null,
  agent_revision_id text not null,
  status text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.session_memory_summaries_runtime (
  id text primary key,
  session_id text not null unique,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.turns_runtime (
  id text primary key,
  session_id text not null,
  org_id text not null,
  agent_id text not null,
  agent_revision_id text not null,
  status text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.turn_events_runtime (
  id text primary key,
  turn_id text not null,
  session_id text not null,
  event_type text not null,
  payload_json jsonb not null default '{}'::jsonb,
  sequence_number integer not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.permissions_runtime (
  id text primary key,
  agent_revision_id text not null,
  tool_name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (agent_revision_id, tool_name)
);

create table if not exists public.org_roles_runtime (
  id text primary key,
  org_id text not null,
  name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, name)
);

create table if not exists public.org_role_grants_runtime (
  id text primary key,
  role_id text not null,
  tool_name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (role_id, tool_name)
);

create table if not exists public.org_role_assignments_runtime (
  id text primary key,
  agent_revision_id text not null,
  role_id text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (agent_revision_id, role_id)
);

create table if not exists public.org_policies_runtime (
  id text primary key,
  org_id text not null,
  tool_name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, tool_name)
);

create table if not exists public.secrets_runtime (
  id text primary key,
  org_id text not null,
  name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, name)
);

create table if not exists public.secret_bindings_runtime (
  id text primary key,
  org_id text not null,
  agent_revision_id text not null,
  binding_name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (agent_revision_id, binding_name)
);

create table if not exists public.audit_events_runtime (
  id text primary key,
  org_id text not null,
  event_type text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.usage_events_runtime (
  id text primary key,
  org_id text not null,
  kind text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.outcomes_runtime (
  id text primary key,
  status text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.agent_assets_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  agent_id text not null,
  status text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.mission_control_threads_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  status text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.skills_runtime (
  id text primary key,
  name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (name)
);

create table if not exists public.host_adapter_dispatches_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  agent_id text not null,
  agent_revision_id text not null,
  status text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists agents_runtime_scope_idx on public.agents_runtime (business_id, environment, updated_at desc);
create index if not exists sessions_runtime_scope_idx on public.sessions_runtime (business_id, environment, updated_at desc);
create index if not exists turns_runtime_session_idx on public.turns_runtime (session_id, updated_at desc);
create index if not exists turn_events_runtime_turn_idx on public.turn_events_runtime (turn_id, sequence_number);
create index if not exists audit_events_runtime_org_idx on public.audit_events_runtime (org_id, created_at desc);
create index if not exists usage_events_runtime_org_idx on public.usage_events_runtime (org_id, created_at desc);
create index if not exists mission_control_threads_runtime_scope_idx on public.mission_control_threads_runtime (business_id, environment, updated_at desc);

commit;
