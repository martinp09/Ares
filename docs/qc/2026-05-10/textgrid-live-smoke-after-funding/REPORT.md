# TextGrid Live Smoke After Funding — 2026-05-10

## Scope

One explicitly approved TextGrid SMS test to Martin's owned phone after Martin said funds were added.

## Routes hit

- `GET /mission-control/providers/status`
- `POST /mission-control/outbound/sms/test`

## Safety

- Used `/opt/ares/Ares/.env` in-process only.
- Did not copy or print raw secrets.
- Added `Authorization: Bearer <RUNTIME_API_KEY>` in-process for the protected Mission Control routes.
- Set `PROVIDER_LIVE_SENDS_ENABLED=true` only for this local smoke process.
- Sent one SMS to the already-approved operator-owned number `+1***5914`.

## Initial Result

- Provider status route: `200`
- TextGrid configured: `true`
- TextGrid can_send: `true`
- SMS test route: `201`
- Ares immediate provider result: `queued`
- Error: `null`
- From: `+1***1390`
- To: `+1***5914`
- Provider message id: masked in artifact

## Delivery diagnostic after Martin did not receive it

- Queried TextGrid messages for the target `+1***5914`.
- The original smoke message was sent to the correct number but later resolved to `failed - Blocked by Textgrid Content Filter`.
- A minimal retry body, `Ares test 2.`, through the same Ares Mission Control route returned `201` initially and then TextGrid reported `delivered` after polling.
- Martin confirmed receipt of the retry SMS: `Ares Test 2.`

## Interpretation

The previous TextGrid funding blocker cleared and Ares provider routing works. The first no-receipt was not a wrong-number issue: it was provider-side content filtering after Ares returned the initial queued response. Future live smoke must poll TextGrid status or consume delivery callbacks before claiming delivery, and the production confirmation/reminder copy needs a TextGrid content-filter check before broad live sends.

## Remaining activation blockers from the follow-up sanitized readiness run

- `PROVIDER_LIVE_SENDS_ENABLED=false` remains the safe default in the env file.
- `RESEND_FROM_EMAIL` is still not a valid sender identity.
- Slack token/channel are still missing, intentionally optional for now.
- `CAL_WEBHOOK_SECRET` is still missing.
