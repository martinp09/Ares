begin;

create table if not exists public.slack_notifications (
  id text primary key,
  business_id bigint not null,
  environment text not null,
  route text not null,
  dedupe_key text not null,
  channel_id text,
  status text not null,
  slack_message_ts text,
  payload jsonb not null default '{}'::jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  sent_at timestamptz,
  constraint slack_notifications_business_fkey
    foreign key (business_id, environment)
    references public.businesses (business_id, environment)
    on delete cascade,
  constraint slack_notifications_scope_route_dedupe_unique
    unique (business_id, environment, route, dedupe_key),
  constraint slack_notifications_route_check
    check (route in ('lead_runs', 'hot_leads', 'instantly_replies', 'lease_option_inbound', 'sms_calls', 'errors')),
  constraint slack_notifications_status_check
    check (status in ('skipped', 'sent', 'failed')),
  constraint slack_notifications_payload_check
    check (jsonb_typeof(payload) = 'object')
);

create index if not exists slack_notifications_scope_route_created_idx
  on public.slack_notifications (business_id, environment, route, created_at desc);

create index if not exists slack_notifications_scope_status_created_idx
  on public.slack_notifications (business_id, environment, status, created_at desc);

alter table public.slack_notifications enable row level security;

drop policy if exists slack_notifications_tenant_isolation on public.slack_notifications;
create policy slack_notifications_tenant_isolation on public.slack_notifications
for all
using (
  business_id = public.current_tenant_business_id()
  and environment = public.current_tenant_environment()
)
with check (
  business_id = public.current_tenant_business_id()
  and environment = public.current_tenant_environment()
);

commit;
