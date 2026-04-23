begin;

update public.organizations_runtime
set
  slug = coalesce(nullif(btrim(payload_json ->> 'slug'), ''), slug),
  is_internal = coalesce((payload_json ->> 'is_internal')::boolean, is_internal)
where slug is null or payload_json ? 'is_internal';

update public.memberships_runtime
set
  actor_id = coalesce(nullif(btrim(payload_json ->> 'actor_id'), ''), actor_id),
  actor_type = coalesce(nullif(btrim(payload_json ->> 'actor_type'), ''), actor_type),
  role_name = coalesce(nullif(btrim(payload_json ->> 'role_name'), ''), role_name)
where actor_id is null or actor_type is null or role_name is null;

update public.catalog_entries_runtime
set slug = coalesce(nullif(btrim(payload_json ->> 'slug'), ''), slug)
where slug is null;

update public.agent_installs_runtime
set
  catalog_entry_id = coalesce(nullif(btrim(payload_json ->> 'catalog_entry_id'), ''), catalog_entry_id),
  installed_agent_id = coalesce(nullif(btrim(payload_json ->> 'installed_agent_id'), ''), installed_agent_id)
where catalog_entry_id is null or installed_agent_id is null;

do $$
begin
  if exists (
    select 1
    from public.organizations_runtime
    where slug is not null
    group by lower(btrim(slug))
    having count(*) > 1
  ) then
    raise exception 'organizations_runtime contains duplicate normalized slugs'
      using hint = 'Resolve duplicate lower(trim(slug)) values before applying 202604230002.';
  end if;
end
$$;

do $$
begin
  if exists (
    select 1
    from public.memberships_runtime
    where actor_id is not null
    group by org_id, actor_id
    having count(*) > 1
  ) then
    raise exception 'memberships_runtime contains duplicate org_id/actor_id pairs'
      using hint = 'Resolve duplicate membership keys before applying 202604230002.';
  end if;
end
$$;

do $$
begin
  if exists (
    select 1
    from public.catalog_entries_runtime
    where slug is not null
    group by org_id, lower(btrim(slug))
    having count(*) > 1
  ) then
    raise exception 'catalog_entries_runtime contains duplicate normalized slugs per org'
      using hint = 'Resolve duplicate lower(trim(slug)) catalog keys before applying 202604230002.';
  end if;
end
$$;

alter table public.memberships_runtime
  alter column actor_id set not null,
  alter column actor_type set not null;

alter table public.catalog_entries_runtime
  alter column slug set not null;

alter table public.agent_installs_runtime
  alter column catalog_entry_id set not null,
  alter column installed_agent_id set not null;

drop index if exists organizations_runtime_slug_idx;
create unique index if not exists organizations_runtime_slug_idx
  on public.organizations_runtime (lower(btrim(slug)))
  where slug is not null;

create unique index if not exists catalog_entries_runtime_org_slug_norm_idx
  on public.catalog_entries_runtime (org_id, lower(btrim(slug)));

commit;
