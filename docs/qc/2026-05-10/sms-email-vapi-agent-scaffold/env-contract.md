# Env / Endpoint Contract — SMS / Vapi Scaffold

## SMS agent

### `POST /sms-agent/messages`

Protected by Ares runtime bearer auth.

Request fields:

- `business_id` string, required
- `environment` string, required
- `to` string, required
- `body` string, required
- `contact_id` string, optional for dry-run, required for live send
- `conversation_id` string, optional
- `sms_consent_confirmed` boolean, default `false`, required as `true` for live send
- `metadata` object, optional
- `dry_run_only` boolean, default `false`

Live-send gates:

- `PROVIDER_LIVE_SENDS_ENABLED=true`
- `TEXTGRID_ACCOUNT_SID`
- `TEXTGRID_AUTH_TOKEN`
- `TEXTGRID_FROM_NUMBER`
- request `contact_id`
- request `sms_consent_confirmed=true`

### `POST /sms-agent/webhooks/textgrid`

Protected by Ares runtime bearer auth and reuses the existing TextGrid inbound/status processor.

Accepts JSON, form-urlencoded, or multipart TextGrid callback payloads.

## Vapi voice agent

### Env

```bash
VAPI_API_KEY=<vapi-api-key>
VAPI_BASE_URL=https://api.vapi.ai
VAPI_WEBHOOK_URL=https://<ares-runtime>/voice/vapi/webhook
VAPI_WEBHOOK_SECRET=<shared-secret-sent-as-x-vapi-secret>
VAPI_DEFAULT_ASSISTANT_ID=<optional-existing-assistant-id>
VAPI_DEFAULT_PHONE_NUMBER_ID=<optional-existing-phone-number-id>
VAPI_PROVIDER_LIVE_SENDS_ENABLED=false
VAPI_DEFAULT_MODEL_PROVIDER=openai
VAPI_DEFAULT_MODEL=gpt-4o
VAPI_DEFAULT_VOICE_PROVIDER=11labs
VAPI_DEFAULT_VOICE_ID=cgSgspJ2msm6clMCkdW9
```

### `POST /voice/assistants`

Protected by Ares runtime bearer auth.

Builds Vapi `POST /assistant` payloads. Provider mutation occurs only when:

- `PROVIDER_LIVE_SENDS_ENABLED=true`
- `VAPI_PROVIDER_LIVE_SENDS_ENABLED=true`
- `VAPI_API_KEY` is present
- request `dry_run_only=false`

### `POST /voice/phone-numbers`

Protected by Ares runtime bearer auth.

Builds Vapi `POST /phone-number` payloads with `provider: vapi`, optional `assistantId`, optional desired area code, and optional `server.url`.

### `POST /voice/calls/outbound`

Protected by Ares runtime bearer auth.

Builds Vapi `POST /call` payloads. Provider call creation occurs only when both live gates are enabled and a `phoneNumberId` is available from request or `VAPI_DEFAULT_PHONE_NUMBER_ID`.

### `POST /voice/vapi/webhook`

Protected by Ares runtime bearer auth.

When `PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true`, the request must include:

```http
X-Vapi-Secret: <VAPI_WEBHOOK_SECRET>
```

Supported Vapi Server URL message types in this scaffold:

- `assistant-request`: returns configured `assistantId` or a transient assistant payload
- `tool-calls`: returns Vapi `results[]` with unsupported-tool responses until tools are wired
- `status-update`: accepted
- `transcript`: accepted
- `end-of-call-report`: accepted

## Resend CLI smoke

Resend CLI is operational outside the Ares route path:

- CLI: `resend-cli v2.2.1`
- Verified sending domain: `send.limitleshome.com`
- Test recipient: `delivered@resend.dev`
- Email id: `1d4172f1-765a-42cf-9a4a-029a5d2f5e5d`
- Final event: `delivered`
