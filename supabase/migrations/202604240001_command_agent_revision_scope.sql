alter table public.commands
  add column if not exists agent_revision_id text;

create index if not exists commands_agent_revision_id_idx
  on public.commands (agent_revision_id)
  where agent_revision_id is not null;
