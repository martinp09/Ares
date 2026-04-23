begin;

alter table public.tasks
  add column if not exists title text,
  add column if not exists lead_id text,
  add column if not exists automation_run_id text,
  add column if not exists source_event_id text,
  add column if not exists run_external_id text,
  add column if not exists idempotency_key text;

update public.tasks
set
  title = coalesce(nullif(btrim(title), ''), nullif(btrim(details ->> 'title'), '')),
  lead_id = coalesce(nullif(btrim(lead_id), ''), nullif(btrim(details ->> 'contact_external_id'), '')),
  run_external_id = coalesce(
    nullif(btrim(run_external_id), ''),
    case
      when run_id is not null then 'run_' || run_id::text
      else nullif(btrim(details ->> 'contact_external_id'), '')
    end
  )
where
  title is null
  or lead_id is null
  or run_external_id is null;

update public.tasks
set idempotency_key = concat(
  'manual_call:',
  coalesce(nullif(btrim(lead_id), ''), nullif(btrim(details ->> 'contact_external_id'), '')),
  ':',
  coalesce(nullif(btrim(title), ''), nullif(btrim(details ->> 'title'), ''))
)
where
  idempotency_key is null
  and task_type = 'manual_call'
  and coalesce(nullif(btrim(lead_id), ''), nullif(btrim(details ->> 'contact_external_id'), '')) is not null
  and coalesce(nullif(btrim(title), ''), nullif(btrim(details ->> 'title'), '')) is not null;

with duplicate_keys as (
  select
    id,
    row_number() over (
      partition by business_id, environment, idempotency_key
      order by created_at asc, id asc
    ) as row_rank
  from public.tasks
  where idempotency_key is not null
)
update public.tasks as tasks
set idempotency_key = null
from duplicate_keys
where
  tasks.id = duplicate_keys.id
  and duplicate_keys.row_rank > 1;

alter table public.tasks drop constraint if exists tasks_status_check;
alter table public.tasks
  add constraint tasks_status_check
  check (status in ('open', 'in_progress', 'blocked', 'completed', 'cancelled', 'failed'));

create index if not exists tasks_scope_lead_idx
  on public.tasks (business_id, environment, lead_id, created_at desc);

create unique index if not exists tasks_scope_idempotency_key_unique
  on public.tasks (business_id, environment, idempotency_key)
  where idempotency_key is not null;

commit;
