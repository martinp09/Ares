-- Mission Control runtime persistence compatibility seam.
-- Additive only: keeps 202604130001 core schema intact while introducing
-- runtime-compatible IDs and fields for repository-layer mapping.

begin;

alter table public.commands
  add column if not exists runtime_id text,
  add column if not exists runtime_status text,
  add column if not exists runtime_policy text;

update public.commands
set
  runtime_id = coalesce(runtime_id, 'cmd_legacy_' || id::text),
  runtime_status = coalesce(
    runtime_status,
    case status
      when 'approval_required' then 'awaiting_approval'
      when 'queued' then 'queued'
      when 'rejected' then 'rejected'
      else 'queued'
    end
  ),
  runtime_policy = coalesce(
    runtime_policy,
    case policy_result
      when 'safe_autonomous' then 'safe_autonomous'
      when 'approval_required' then 'approval_required'
      when 'blocked' then 'forbidden'
      else 'approval_required'
    end
  );

create unique index if not exists commands_runtime_id_unique_idx
  on public.commands (runtime_id)
  where runtime_id is not null;

create index if not exists commands_runtime_status_idx
  on public.commands (runtime_status);

alter table public.approvals
  add column if not exists runtime_id text,
  add column if not exists command_runtime_id text,
  add column if not exists actor_id text,
  add column if not exists approved_at timestamptz;

update public.approvals
set
  runtime_id = coalesce(runtime_id, 'apr_legacy_' || id::text),
  actor_id = coalesce(actor_id, approved_by),
  approved_at = coalesce(approved_at, decided_at);

update public.approvals as a
set command_runtime_id = c.runtime_id
from public.commands as c
where a.command_id = c.id
  and a.business_id = c.business_id
  and a.environment = c.environment
  and a.command_runtime_id is null;

create unique index if not exists approvals_runtime_id_unique_idx
  on public.approvals (runtime_id)
  where runtime_id is not null;

create index if not exists approvals_command_runtime_id_idx
  on public.approvals (command_runtime_id);

alter table public.runs
  add column if not exists runtime_id text,
  add column if not exists command_runtime_id text,
  add column if not exists parent_runtime_id text,
  add column if not exists replay_source_runtime_id text,
  add column if not exists runtime_status text,
  add column if not exists runtime_policy text;

update public.runs
set
  runtime_id = coalesce(runtime_id, 'run_legacy_' || id::text),
  runtime_status = coalesce(
    runtime_status,
    case status
      when 'running' then 'in_progress'
      when 'completed' then 'completed'
      when 'failed' then 'failed'
      when 'cancelled' then 'failed'
      else 'queued'
    end
  );

update public.runs as r
set
  command_runtime_id = c.runtime_id,
  runtime_policy = coalesce(r.runtime_policy, c.runtime_policy)
from public.commands as c
where r.command_id = c.id
  and r.business_id = c.business_id
  and r.environment = c.environment
  and (r.command_runtime_id is null or r.runtime_policy is null);

update public.runs as child
set parent_runtime_id = parent.runtime_id
from public.runs as parent
where child.parent_run_id = parent.id
  and child.business_id = parent.business_id
  and child.environment = parent.environment
  and child.parent_runtime_id is null;

update public.runs as child
set replay_source_runtime_id = source.runtime_id
from public.runs as source
where child.replay_source_run_id = source.id
  and child.business_id = source.business_id
  and child.environment = source.environment
  and child.replay_source_runtime_id is null;

create unique index if not exists runs_runtime_id_unique_idx
  on public.runs (runtime_id)
  where runtime_id is not null;

create index if not exists runs_runtime_status_idx
  on public.runs (runtime_status);

create index if not exists runs_command_runtime_id_idx
  on public.runs (command_runtime_id);

create index if not exists runs_parent_runtime_id_idx
  on public.runs (parent_runtime_id);

alter table public.events
  add column if not exists runtime_id text,
  add column if not exists run_runtime_id text,
  add column if not exists command_runtime_id text;

update public.events
set runtime_id = coalesce(runtime_id, 'evt_legacy_' || id::text);

update public.events as e
set run_runtime_id = r.runtime_id
from public.runs as r
where e.run_id = r.id
  and e.business_id = r.business_id
  and e.environment = r.environment
  and e.run_runtime_id is null;

update public.events as e
set command_runtime_id = c.runtime_id
from public.commands as c
where e.command_id = c.id
  and e.business_id = c.business_id
  and e.environment = c.environment
  and e.command_runtime_id is null;

create unique index if not exists events_runtime_id_unique_idx
  on public.events (runtime_id)
  where runtime_id is not null;

create index if not exists events_run_runtime_id_idx
  on public.events (run_runtime_id);

alter table public.artifacts
  add column if not exists runtime_id text,
  add column if not exists run_runtime_id text,
  add column if not exists payload jsonb;

update public.artifacts
set
  runtime_id = coalesce(runtime_id, 'art_legacy_' || id::text),
  payload = coalesce(payload, data);

update public.artifacts as a
set run_runtime_id = r.runtime_id
from public.runs as r
where a.run_id = r.id
  and a.business_id = r.business_id
  and a.environment = r.environment
  and a.run_runtime_id is null;

create unique index if not exists artifacts_runtime_id_unique_idx
  on public.artifacts (runtime_id)
  where runtime_id is not null;

create index if not exists artifacts_run_runtime_id_idx
  on public.artifacts (run_runtime_id);

commit;
