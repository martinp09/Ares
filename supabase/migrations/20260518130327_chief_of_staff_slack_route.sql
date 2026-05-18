begin;

alter table public.slack_notifications
  drop constraint if exists slack_notifications_route_check;

alter table public.slack_notifications
  add constraint slack_notifications_route_check
  check (route in (
    'lead_runs',
    'hot_leads',
    'chief_of_staff_digest',
    'instantly_replies',
    'lease_option_inbound',
    'sms_calls',
    'errors'
  ));

commit;
