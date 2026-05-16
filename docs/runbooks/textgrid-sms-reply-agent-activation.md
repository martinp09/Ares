# TextGrid SMS Reply Agent Activation Runbook

## Scope

Activate the Ares TextGrid SMS reply agent in no-send mode first. This runbook covers provider dashboard setup, owned-number ingest smoke, local processor drain, and the approval gate before any deterministic auto-ack smoke.

This does not authorize bulk SMS, cold SMS, campaign enrollment, unowned-number sends, provider dashboard mutation beyond callback URL setup, or live auto replies.

## Preconditions

- Ares runtime is deployed and reachable at `https://<ares-runtime>`.
- TextGrid owns the Ares SMS number being configured.
- `TEXTGRID_WEBHOOK_SECRET` is configured in the Ares runtime.
- `PROVIDER_WEBHOOK_SIGNATURES_REQUIRED=true` remains enabled unless debugging in a local isolated environment.
- `PROVIDER_LIVE_SENDS_ENABLED=false`.
- `SMS_AGENT_AUTO_REPLIES_ENABLED=false`.
- Runtime API key is available only for the protected processor drain.

## Provider Setup

1. Set the TextGrid number inbound webhook to:

   ```text
   https://<ares-runtime>/sms-agent/webhooks/textgrid
   ```

2. Set the TextGrid status callback to:

   ```text
   https://<ares-runtime>/sms-agent/webhooks/textgrid
   ```

3. Confirm which signature headers TextGrid sends for inbound and status callbacks:

   ```text
   X-Twilio-Signature
   X-TextGrid-Signature
   ```

   Record whether TextGrid sends `X-Twilio-Signature`, `X-TextGrid-Signature`, or both before considering the callback setup complete. Ares accepts either header and prefers `X-TextGrid-Signature` when both are present.

## First Ingest Smoke

Keep these flags disabled for the first ingest smoke:

```text
PROVIDER_LIVE_SENDS_ENABLED=false
SMS_AGENT_AUTO_REPLIES_ENABLED=false
```

Send one inbound SMS from an owned operator phone to the Ares TextGrid number. Use neutral copy:

```text
Can you call me?
```

Optional local signed-form smoke against a running runtime:

```bash
uv run python scripts/smoke/textgrid_sms_reply_agent_smoke.py \
  --runtime-url http://localhost:8000 \
  --webhook-secret <textgrid-webhook-secret> \
  --from <owned-operator-number> \
  --to <ares-textgrid-number> \
  --body "Can you call me?"
```

If the runtime API key is provided, the smoke also drains the protected pending-job processor:

```bash
uv run python scripts/smoke/textgrid_sms_reply_agent_smoke.py \
  --runtime-url http://localhost:8000 \
  --webhook-secret <textgrid-webhook-secret> \
  --runtime-api-key <runtime-api-key> \
  --from <owned-operator-number> \
  --to <ares-textgrid-number> \
  --body "Can you call me?"
```

Do not include `--runtime-api-key` against any environment where provider sends or SMS auto replies are enabled unless Martin has approved that exact smoke.

## Verify No-Send Ingest

Verify all of the following before claiming activation:

1. TextGrid provider dashboard shows the inbound webhook delivery to `/sms-agent/webhooks/textgrid`.
2. Ares provider webhook receipt exists for the TextGrid event.
3. Ares message row exists for the inbound SMS.
4. SMS-agent job exists and is queued or completed.
5. SMS-agent decision exists after the processor drain.
6. Mission Control shows the review item/operator surface for the reply.
7. No TextGrid outbound send was created.
8. No provider dashboard setting changed except the inbound webhook/status callback URLs.

## Auto-Ack Gate

Only after Martin approves, enable one owned-number deterministic auto-ack smoke. Keep the recipient limited to the same owned operator phone and keep the message copy deterministic.

Required gate before auto-ack:

```text
PROVIDER_LIVE_SENDS_ENABLED=true
SMS_AGENT_AUTO_REPLIES_ENABLED=true
SMS_AGENT_MODE=auto_ack
```

After the auto-ack request is queued, poll or consume TextGrid delivery status callbacks before claiming delivery. Do not claim delivery from the immediate send response alone.

## Rollback

Set the TextGrid inbound webhook and status callback back to the prior approved URLs, then restore:

```text
PROVIDER_LIVE_SENDS_ENABLED=false
SMS_AGENT_AUTO_REPLIES_ENABLED=false
```

Confirm no pending SMS-agent jobs remain eligible for auto-send before ending the activation window.
