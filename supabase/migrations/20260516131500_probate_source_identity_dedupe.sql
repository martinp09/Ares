-- Probate source identity ledger for durable cross-run dedupe.
-- Ares keeps the operational file-backed source-run ledger today; this table is
-- the Supabase contract for promoting the same dedupe identity to the durable
-- control plane without mixing manual experiments into autonomous schedules.

create table if not exists public.probate_source_identities (
    id uuid primary key default gen_random_uuid(),
    business_id bigint not null,
    environment text not null,
    source_run_scope text not null default 'autonomous',
    county text not null,
    source_identity_key text not null,
    source_identity_version text not null default 'county_case_sha256_v1',
    first_source_run_id text,
    first_source_key text,
    first_idempotency_key text,
    first_seen_at timestamptz not null default now(),
    last_source_run_id text,
    last_source_key text,
    last_idempotency_key text,
    last_seen_at timestamptz not null default now(),
    seen_count integer not null default 1,
    latest_record_count integer not null default 1,
    latest_keep_now boolean,
    latest_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint probate_source_identities_business_fk foreign key (business_id, environment)
        references public.businesses (business_id, environment) on delete cascade,
    constraint probate_source_identities_scope_check check (source_run_scope in ('autonomous', 'manual')),
    constraint probate_source_identities_county_check check (county in ('harris', 'montgomery')),
    constraint probate_source_identities_key_check check (source_identity_key ~ '^probate_case_sha256:[0-9a-f]{64}$'),
    constraint probate_source_identities_version_check check (source_identity_version = 'county_case_sha256_v1'),
    constraint probate_source_identities_counts_check check (seen_count >= 1 and latest_record_count >= 0),
    constraint probate_source_identities_lower_check check (
        environment = lower(environment)
        and source_run_scope = lower(source_run_scope)
        and county = lower(county)
        and source_identity_key = lower(source_identity_key)
    ),
    unique (business_id, environment, source_run_scope, county, source_identity_key)
);

create index if not exists probate_source_identities_lookup_idx
    on public.probate_source_identities (business_id, environment, source_run_scope, county, last_seen_at desc);

create index if not exists probate_source_identities_first_seen_idx
    on public.probate_source_identities (business_id, environment, first_seen_at desc);

alter table public.probate_source_identities enable row level security;

drop policy if exists tenant_isolation_select_probate_source_identities on public.probate_source_identities;
create policy tenant_isolation_select_probate_source_identities
    on public.probate_source_identities
    for select
    using (
        business_id = public.current_tenant_business_id()
        and environment = public.current_tenant_environment()
    );

drop policy if exists tenant_isolation_insert_probate_source_identities on public.probate_source_identities;
create policy tenant_isolation_insert_probate_source_identities
    on public.probate_source_identities
    for insert
    with check (
        business_id = public.current_tenant_business_id()
        and environment = public.current_tenant_environment()
    );

drop policy if exists tenant_isolation_update_probate_source_identities on public.probate_source_identities;
create policy tenant_isolation_update_probate_source_identities
    on public.probate_source_identities
    for update
    using (
        business_id = public.current_tenant_business_id()
        and environment = public.current_tenant_environment()
    )
    with check (
        business_id = public.current_tenant_business_id()
        and environment = public.current_tenant_environment()
    );

drop trigger if exists probate_source_identities_touch_updated_at on public.probate_source_identities;
create trigger probate_source_identities_touch_updated_at
    before update on public.probate_source_identities
    for each row execute function public.touch_updated_at();
