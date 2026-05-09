$ git diff --stat
 CONTEXT.md                                         |  4 +-
 README.md                                          |  4 +-
 TODO.md                                            |  8 +--
 app/services/booking_service.py                    |  9 +--
 app/services/marketing_lead_service.py             |  2 +
 memory.md                                          |  7 +-
 tests/services/test_booking_service.py             | 80 ++++++++++++++++++++++
 .../test_marketing_provider_notifications.py       | 47 +++++++++++++
 8 files changed, 146 insertions(+), 15 deletions(-)

$ git diff -- app/services/marketing_lead_service.py app/services/booking_service.py tests/services/test_marketing_provider_notifications.py tests/services/test_booking_service.py README.md TODO.md CONTEXT.md memory.md docs/qc/2026-05-09/pr7-merge-readiness-audit/REPORT.md
diff --git a/CONTEXT.md b/CONTEXT.md
index d59bb48..c5c0f48 100644
--- a/CONTEXT.md
+++ b/CONTEXT.md
@@ -10,7 +10,7 @@
 - Trigger project: `proj_puouljyhwiraonjkpiki`

 ## Current Scope
-- Landing-page -> Ares intake/SMS bridge is the active feature branch `feat/landing-ares-intake-sms-agent`: Ares now accepts full seller-form context through `POST /marketing/leads`, preserves consent/UTM metadata, returns side-effect status, sends booking-link confirmation SMS/email when live-gated providers are configured, scaffolds Slack intake alerts, and schedules Trigger-backed 24h/1h appointment reminders from Cal.com `starts_at`.
+- Landing-page -> Ares intake/SMS bridge is the active PR #7 branch `feat/landing-ares-intake-sms-agent`: Ares now accepts full seller-form context through `POST /marketing/leads`, preserves consent/UTM metadata, returns side-effect status, sends booking-link confirmation SMS/email when live-gated providers are configured, scaffolds Slack intake alerts behind the same live-send gate, and schedules Trigger-backed 24h/1h appointment reminders from Cal.com `starts_at` on booked/rescheduled events.
 - Approved local route smoke to Martin's phone/email reached Ares provider routes with `PROVIDER_LIVE_SENDS_ENABLED=true`; TextGrid returned `Balance is below 0` before SMS delivery and Resend was blocked by invalid `RESEND_FROM_EMAIL`, so provider funding/sender env remains the live-send gate.
 - Landing page branch `feat/landing-ares-intake-sms-agent` now routes `POST /api/contact` directly to Ares server-side; Supabase+n8n is no longer the active submit path.
 - Security-audit hardening is complete and ready to operate from `main` after the merge of `hardening/ares-security-audit-patches-2026-05-09`.
@@ -27,7 +27,7 @@
 4. Add dedicated Mission Control frontend campaign-launch review page for the Harris probate HOT/WARM/COLD API contract.

 ## Recent Change
-- 2026-05-09: Added live-gated intake provider bundle on the Ares branch: TextGrid booking-link SMS, Resend confirmation email, Slack intake scaffold, Cal.com `starts_at`, and Trigger-backed 24h/1h appointment reminders. Local approved route smoke hit TextGrid/Resend but delivery is blocked by TextGrid balance and invalid `RESEND_FROM_EMAIL`.
+- 2026-05-09: Added live-gated intake provider bundle on the Ares branch: TextGrid booking-link SMS, Resend confirmation email, Slack intake scaffold, Cal.com `starts_at`, and Trigger-backed 24h/1h appointment reminders. Merge-readiness audit then tightened Slack behind the global live-send gate and made rescheduled Cal.com events refresh reminder scheduling without duplicate confirmations. Local approved route smoke hit TextGrid/Resend but delivery is blocked by TextGrid balance and invalid `RESEND_FROM_EMAIL`.
 - 2026-05-09: Completed security-audit hardening patch set and QC at `docs/qc/2026-05-09/ares-security-audit-patches/`.
 - 2026-05-09: Merged Harris daily probate + HCAD `Estate Of` import foundation to `main` via PR #5; Vercel preview smoke passed and Slack remains intentionally last.
 - 2026-04-30: Added Harris probate campaign launch backend slice and QC at `docs/qc/2026-04-30/harris-probate-campaign-launch/`.
diff --git a/README.md b/README.md
index 59840ae..d84f24e 100644
--- a/README.md
+++ b/README.md
@@ -108,13 +108,13 @@ Current side effects:

 - `confirmation_sms`: TextGrid confirmation with booking link and STOP language when `sms_consent=true`, TextGrid config exists, and `PROVIDER_LIVE_SENDS_ENABLED=true`.
 - `confirmation_email`: Resend confirmation with the same booking link when Resend config exists and `PROVIDER_LIVE_SENDS_ENABLED=true`.
-- `operator_slack_notification`: Slack `chat.postMessage` operator alert with lead/booking context when `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` are configured; otherwise skipped safely.
+- `operator_slack_notification`: Slack `chat.postMessage` operator alert with lead/booking context when `PROVIDER_LIVE_SENDS_ENABLED=true` and `SLACK_BOT_TOKEN` plus `SLACK_CHANNEL_INTAKE` or `SLACK_CHANNEL_LEADS` are configured; otherwise skipped safely.
 - `trigger_non_booker_check`: delayed Trigger follow-up check when Trigger config exists and `PROVIDER_LIVE_SENDS_ENABLED=true`.

 Appointment reminder flow:

 - Cal.com booking webhooks now preserve `starts_at` when provided.
-- Booked leads schedule Trigger reminder jobs for `24h` and `1h` before the appointment when `PROVIDER_LIVE_SENDS_ENABLED=true`, `MARKETING_APPOINTMENT_REMINDERS_ENABLED=true`, and `TRIGGER_SECRET_KEY` is set.
+- Booked or rescheduled leads schedule Trigger reminder jobs for `24h` and `1h` before the appointment when `PROVIDER_LIVE_SENDS_ENABLED=true`, `MARKETING_APPOINTMENT_REMINDERS_ENABLED=true`, and `TRIGGER_SECRET_KEY` is set.
 - Trigger task `marketing-send-appointment-reminder` calls `POST /marketing/internal/appointment-reminder` with bearer runtime auth.
 - Reminder dispatch sends TextGrid SMS only for opted-in booked/rescheduled leads and sends Resend email when an email is present; both outbound message IDs are logged when providers return IDs.

diff --git a/TODO.md b/TODO.md
index 7b7ba98..46124b5 100644
--- a/TODO.md
+++ b/TODO.md
@@ -1,7 +1,7 @@
 ---
 title: "Ares TODO / Handoff"
 status: active
-updated_at: "2026-05-09T22:10:00Z"
+updated_at: "2026-05-09T22:25:23Z"
 repo: "martinp09/Ares"
 local_checkout: "/root/Ares-inspect"
 current_branch: "feat/landing-ares-intake-sms-agent"
@@ -41,9 +41,9 @@ Known caveats:
 - [done] Return `side_effects` so the landing page can show/log whether confirmation SMS/email/Trigger work was queued, skipped, or failed.
 - [done] Add TextGrid confirmation SMS with E.164 normalization, booking link, and STOP language.
 - [done] Add Resend confirmation email using the same booking link copy.
-- [done] Add server-side Slack `chat.postMessage` intake notifier scaffold with safe no-op when token/channel are missing.
-- [done] Add Cal.com `starts_at` preservation plus Trigger-backed 24h/1h appointment reminder scheduling and `/marketing/internal/appointment-reminder` dispatch.
-- [done] Gate confirmation SMS/email, appointment reminders, and non-booker Trigger scheduling behind `PROVIDER_LIVE_SENDS_ENABLED`; first deploy remains no-live-send by default.
+- [done] Add server-side Slack `chat.postMessage` intake notifier scaffold with safe no-op when live sends are disabled or token/channel are missing.
+- [done] Add Cal.com `starts_at` preservation plus Trigger-backed 24h/1h appointment reminder scheduling and `/marketing/internal/appointment-reminder` dispatch, including reschedule reminder refresh.
+- [done] Gate confirmation SMS/email, Slack intake alerts, appointment reminders, and non-booker Trigger scheduling behind `PROVIDER_LIVE_SENDS_ENABLED`; first deploy remains no-live-send by default.
 - [done] Replace the landing page active submit path with a server-side Ares bearer-auth handoff and remove Supabase+n8n active code.
 - [blocked] Approved local route smoke to Martin `+1***5914` / email reached Ares; TextGrid needs account funds and Resend needs valid `RESEND_FROM_EMAIL` before delivery succeeds.
 - [ ] Set landing runtime envs in the deployment target: `BUSINESS_RUNTIME_MARKETING_LEADS_URL`, `BUSINESS_RUNTIME_API_KEY`, `BUSINESS_RUNTIME_BUSINESS_ID`, `BUSINESS_RUNTIME_ENVIRONMENT`.
diff --git a/app/services/booking_service.py b/app/services/booking_service.py
index c29b7b1..bd17f9b 100644
--- a/app/services/booking_service.py
+++ b/app/services/booking_service.py
@@ -712,11 +712,12 @@ class BookingService:
                     lead=lead,
                     provider_message_ids=provider_message_ids,
                 )
-                try:
-                    self.appointment_reminder_scheduler.schedule_appointment_reminders(lead=lead, event=event)
-                except Exception:
-                    pass
             self._sync_opportunity(lead, event)
+        if lead is not None and event.booking_status in {"booked", "rescheduled"}:
+            try:
+                self.appointment_reminder_scheduler.schedule_appointment_reminders(lead=lead, event=event)
+            except Exception:
+                pass
         if event.booking_status in {"booked", "rescheduled"}:
             self.sequence_service.suppress_for_booked_lead(lead_id=event.lead_id)
         self.webhook_receipts.mark_processed(receipt_id)
diff --git a/app/services/marketing_lead_service.py b/app/services/marketing_lead_service.py
index 557bd23..aa00396 100644
--- a/app/services/marketing_lead_service.py
+++ b/app/services/marketing_lead_service.py
@@ -626,6 +626,8 @@ class MarketingLeadService:

     @staticmethod
     def _build_operator_notifier(settings: Settings, *, request_sender: RequestSender) -> OperatorNotifier:
+        if not settings.provider_live_sends_enabled:
+            return _NoopOperatorNotifier()
         channel = settings.slack_channel_intake or settings.slack_channel_leads
         if settings.slack_bot_token and channel:
             return _ConfiguredSlackOperatorNotifier(
diff --git a/memory.md b/memory.md
index a89c8ff..e3d4cdf 100644
--- a/memory.md
+++ b/memory.md
@@ -63,7 +63,7 @@
 - The current MVP path is a two-lane cut:
   - outbound probate as source lane with cold email as outbound method
   - inbound lease-option marketing as a separate first-class lane
-- Lease-options landing contact intake now belongs in Ares `POST /marketing/leads`: preserve rich seller context/consent/UTM fields, return booking and side-effect statuses, and keep provider sends gated by `PROVIDER_LIVE_SENDS_ENABLED`.
+- Lease-options landing contact intake now belongs in Ares `POST /marketing/leads`: preserve rich seller context/consent/UTM fields, return booking and side-effect statuses, keep SMS/email/Slack/Trigger sends gated by `PROVIDER_LIVE_SENDS_ENABLED`, and refresh appointment reminders on booked/rescheduled Cal.com events.
 - Supabase should be the canonical backend for both live MVP lanes
 - The runtime should preserve a thin contract-to-close skeleton even while the MVP stays focused on lead intake, outreach, replies, and operator handoff
 - Mission Control now has CRM Records, saved views, row/bulk actions, promotion, Pipeline config/stage history, and stage movement UI/API. Records prefer canonical CRM rows and fall back to live lead-machine leads when no canonical records exist.
@@ -210,8 +210,9 @@

 ### 2026-05-09 Live SMS/Resend/Slack Reminder Finish

-- Extended `feat/landing-ares-intake-sms-agent` so Ares lead intake sends live-gated TextGrid confirmation SMS with booking link/STOP copy, Resend confirmation email, and server-side Slack intake alerts when configured.
-- Added Cal.com `starts_at` preservation, Trigger task `marketing-send-appointment-reminder`, and `/marketing/internal/appointment-reminder` dispatch for 24h/1h booked-lead reminders.
+- Extended `feat/landing-ares-intake-sms-agent` so Ares lead intake sends live-gated TextGrid confirmation SMS with booking link/STOP copy, Resend confirmation email, and server-side Slack intake alerts when configured and `PROVIDER_LIVE_SENDS_ENABLED=true`.
+- Added Cal.com `starts_at` preservation, Trigger task `marketing-send-appointment-reminder`, and `/marketing/internal/appointment-reminder` dispatch for 24h/1h booked/rescheduled-lead reminders.
+- Merge-readiness audit tightened Slack behind the same global live-send gate and made Cal.com reschedule events refresh reminder scheduling without sending duplicate booking confirmations.
 - Approved route smoke to Martin's phone/email reached Ares; TextGrid returned an account balance blocker and Resend now fails fast on invalid `RESEND_FROM_EMAIL`, so no delivery is claimed until provider env/funding is fixed.

 ### 2026-05-09 Landing Page Ares Intake Bridge
diff --git a/tests/services/test_booking_service.py b/tests/services/test_booking_service.py
index 93bb5ae..8d627dc 100644
--- a/tests/services/test_booking_service.py
+++ b/tests/services/test_booking_service.py
@@ -84,6 +84,86 @@ def test_booked_calcom_event_creates_lease_option_opportunity() -> None:
     }


+def test_rescheduled_calcom_event_reschedules_reminders_without_new_confirmation() -> None:
+    client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
+    contacts = ContactsRepository(client)
+    lead = contacts.upsert_lead(
+        LeadUpsertRequest(
+            business_id="limitless",
+            environment="dev",
+            first_name="Maya",
+            phone="+155****4567",
+            email="maya@example.com",
+            property_address="123 Main St, Houston, TX",
+            sms_consent=True,
+        )
+    )
+    contacts.update_booking_status(lead.id, "booked")
+
+    class StubCalcomAdapter:
+        def normalize(self, payload, *, signature, raw_body=None):
+            return NormalizedBookingEvent(
+                lead_id=lead.id,
+                booking_status="rescheduled",
+                event_name="booking.rescheduled",
+                external_booking_id="book_rescheduled_123",
+                starts_at="2026-05-13T16:00:00Z",
+            )
+
+    class StubAppointmentNotifier:
+        def __init__(self) -> None:
+            self.confirmations = 0
+
+        def send_appointment_confirmation(self, *, lead_id: str):
+            self.confirmations += 1
+            raise AssertionError("rescheduled events should not send a new booking confirmation")
+
+        def send_appointment_reminder(self, *, lead_id: str, reminder_label: str, starts_at: str | None = None):
+            return {"sms": f"SM_REMINDER_{reminder_label}", "email": f"email_reminder_{reminder_label}"}
+
+    class StubSequenceService:
+        def __init__(self) -> None:
+            self.suppressed = 0
+
+        def suppress_for_booked_lead(self, *, lead_id: str) -> None:
+            self.suppressed += 1
+
+        def enroll_non_booker(self, *, lead_id: str, business_id: str, environment: str) -> None:
+            return None
+
+    class StubReminderScheduler:
+        def __init__(self) -> None:
+            self.calls = []
+
+        def schedule_appointment_reminders(self, *, lead, event):
+            self.calls.append((lead, event))
+            return [{"name": "appointment_reminder_24h", "status": "scheduled", "delay": "86400s"}]
+
+    notifier = StubAppointmentNotifier()
+    sequence = StubSequenceService()
+    scheduler = StubReminderScheduler()
+    service = BookingService(
+        calcom_adapter=StubCalcomAdapter(),
+        booking_repository=_MarketingBookingStateRepository(
+            contacts=contacts,
+            bookings=BookingsRepository(client),
+        ),
+        appointment_notifier=notifier,
+        appointment_reminder_scheduler=scheduler,
+        sequence_service=sequence,
+        contacts=contacts,
+    )
+
+    result = service.handle_calcom_webhook({}, signature=None)
+
+    assert result == {"status": "processed", "lead_id": lead.id, "booking_status": "rescheduled"}
+    assert notifier.confirmations == 0
+    assert sequence.suppressed == 1
+    assert len(scheduler.calls) == 1
+    assert scheduler.calls[0][0].id == lead.id
+    assert scheduler.calls[0][1].starts_at == "2026-05-13T16:00:00Z"
+
+
 def test_sequence_guard_uses_latest_sequence_state_for_pending_leads() -> None:
     client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
     contacts = ContactsRepository(client)
diff --git a/tests/services/test_marketing_provider_notifications.py b/tests/services/test_marketing_provider_notifications.py
index 89430fb..0293deb 100644
--- a/tests/services/test_marketing_provider_notifications.py
+++ b/tests/services/test_marketing_provider_notifications.py
@@ -120,6 +120,53 @@ def test_lead_intake_sends_confirmation_sms_email_and_slack_with_booking_link()
     assert "123 Main St" in json.dumps(slack_request["payload"])


+def test_lead_intake_skips_slack_when_live_sends_are_disabled_even_if_configured() -> None:
+    class StubLeadRepository:
+        def upsert_lead(self, payload: LeadIntakePayload) -> str:
+            return "lead_safe_123"
+
+    def request_sender(_outbound_request):
+        raise AssertionError("Slack/TextGrid requests should not be sent when live sends are disabled")
+
+    def resend_sender(*_args, **_kwargs):
+        raise AssertionError("Resend requests should not be sent when live sends are disabled")
+
+    service = MarketingLeadService(
+        settings=Settings(
+            _env_file=None,
+            provider_live_sends_enabled=False,
+            textgrid_account_sid="acct_123",
+            textgrid_auth_token="token_123",
+            textgrid_from_number="3462891390",
+            resend_api_key="re_123",
+            resend_from_email="Martin at Limitless <martin@example.com>",
+            slack_bot_token="xoxb-test",
+            slack_channel_intake="CINTAKE",
+            cal_booking_url="https://cal.com/limitless/lease-option-review",
+        ),
+        lead_repository=StubLeadRepository(),
+        request_sender=request_sender,
+        resend_email_sender=resend_sender,
+    )
+
+    result = service.intake_lead(
+        LeadIntakePayload(
+            business_id="limitless",
+            environment="prod",
+            first_name="Maya",
+            phone="5551234567",
+            email="maya@example.com",
+            property_address="123 Main St, Houston, TX",
+            sms_consent=True,
+        )
+    )
+
+    side_effects = {effect["name"]: effect["status"] for effect in result["side_effects"]}
+    assert side_effects["confirmation_sms"] == "skipped"
+    assert side_effects["confirmation_email"] == "skipped"
+    assert side_effects["operator_slack_notification"] == "skipped"
+
+
 def test_booking_service_schedules_appointment_reminders_when_calcom_booking_is_created() -> None:
     client = InMemoryControlPlaneClient(InMemoryControlPlaneStore())
     contacts = ContactsRepository(client)
