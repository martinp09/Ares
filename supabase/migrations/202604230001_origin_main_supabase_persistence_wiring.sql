begin;

create table if not exists public.organizations_runtime (
  id text primary key,
  name text not null,
  slug text,
  is_internal boolean not null default false,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.memberships_runtime (
  id text primary key,
  org_id text not null,
  actor_id text not null,
  actor_type text not null,
  role_name text,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, actor_id)
);

create table if not exists public.catalog_entries_runtime (
  id text primary key,
  org_id text not null,
  agent_id text not null,
  agent_revision_id text not null,
  slug text not null,
  name text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, slug)
);

create table if not exists public.agent_installs_runtime (
  id text primary key,
  org_id text not null,
  catalog_entry_id text not null,
  installed_agent_id text not null,
  business_id text not null,
  environment text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.release_events_runtime (
  id text primary key,
  org_id text not null,
  agent_id text not null,
  event_type text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.ares_plans_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (business_id, environment)
);

create table if not exists public.ares_execution_runs_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (business_id, environment)
);

create table if not exists public.ares_operator_runs_runtime (
  id text primary key,
  business_id text not null,
  environment text not null,
  payload_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (business_id, environment)
);

create unique index if not exists organizations_runtime_slug_idx
  on public.organizations_runtime (lower(slug))
  where slug is not null;
create index if not exists memberships_runtime_org_idx on public.memberships_runtime (org_id, updated_at desc);
create index if not exists memberships_runtime_actor_idx on public.memberships_runtime (actor_id, updated_at desc);
create index if not exists catalog_entries_runtime_org_idx on public.catalog_entries_runtime (org_id, updated_at desc);
create index if not exists catalog_entries_runtime_agent_idx on public.catalog_entries_runtime (agent_id, updated_at desc);
create index if not exists agent_installs_runtime_org_idx on public.agent_installs_runtime (org_id, updated_at desc);
create index if not exists agent_installs_runtime_scope_idx
  on public.agent_installs_runtime (business_id, environment, updated_at desc);
create index if not exists release_events_runtime_agent_idx on public.release_events_runtime (agent_id, created_at desc);
create index if not exists release_events_runtime_org_idx on public.release_events_runtime (org_id, created_at desc);
create index if not exists ares_plans_runtime_scope_idx on public.ares_plans_runtime (business_id, environment, updated_at desc);
create index if not exists ares_execution_runs_runtime_scope_idx
  on public.ares_execution_runs_runtime (business_id, environment, updated_at desc);
create index if not exists ares_operator_runs_runtime_scope_idx
  on public.ares_operator_runs_runtime (business_id, environment, updated_at desc);

commit;
