# Hermes Ares Runtime Adapter Contract

Status: Phase 3 contract

## Boundary

Hermes is the operator shell. Ares is the runtime. Hermes calls Ares over HTTP and never reads Supabase, Trigger.dev, TextGrid, Resend, Cal.com, or Mission Control frontend state directly.

## Environment

```bash
HERMES_RUNTIME_API_BASE_URL=http://127.0.0.1:8000
HERMES_RUNTIME_API_KEY=dev-runtime-key
```

Fallback names are also supported by Trigger and smoke tooling:

```bash
RUNTIME_API_BASE_URL=http://127.0.0.1:8000
RUNTIME_API_KEY=dev-runtime-key
```

## Headers

Every protected Ares request uses:

```http
Authorization: Bearer <runtime-api-key>
Content-Type: application/json
```

Optional operator context:

```http
X-Ares-Org-Id: org_internal
X-Ares-Actor-Id: hermes-operator
X-Ares-Actor-Type: user
```

## Tool Discovery

```bash
curl -sS \
  -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" \
  "$HERMES_RUNTIME_API_BASE_URL/hermes/tools"
```

Response:

```json
{
  "tools": [
    {
      "name": "run_market_research",
      "approval_mode": "safe_autonomous",
      "permission_mode": "always_allow",
      "capability_allowed": true,
      "payload_schema": { "type": "object" },
      "idempotency_scope": "business_id + environment + command_type + idempotency_key"
    }
  ]
}
```

Hermes may pass `agent_revision_id` as a query param to see the tool surface for a specific published agent revision.

## Tool Invocation

```bash
curl -sS \
  -X POST \
  -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" \
  -H "Content-Type: application/json" \
  "$HERMES_RUNTIME_API_BASE_URL/hermes/tools/run_market_research/invoke" \
  -d '{
    "business_id": "limitless",
    "environment": "dev",
    "idempotency_key": "hermes-smoke-001",
    "payload": { "topic": "houston tired landlords" }
  }'
```

The response is the same command-ingest shape as `POST /commands`. A safe command returns a `run_id`. An approval-gated command returns an `approval_id`.

## Approval Flow

```bash
curl -sS \
  -X POST \
  -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" \
  -H "Content-Type: application/json" \
  "$HERMES_RUNTIME_API_BASE_URL/approvals/$APPROVAL_ID/approve" \
  -d '{ "actor_id": "hermes-operator" }'
```

Approving an approval-required command creates exactly one run. Re-approval returns the existing run.

## Run Polling

```bash
curl -sS \
  -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" \
  "$HERMES_RUNTIME_API_BASE_URL/runs/$RUN_ID"
```

Hermes should treat Ares run state as the runtime truth. Trigger lifecycle callbacks, provider callbacks, replay events, and artifacts must flow back into Ares before Hermes summarizes them as business facts.

## Mission Control Readback

Hermes can read operator state through the same protected runtime API:

```bash
curl -sS -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" "$HERMES_RUNTIME_API_BASE_URL/mission-control/dashboard"
curl -sS -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" "$HERMES_RUNTIME_API_BASE_URL/mission-control/approvals"
curl -sS -H "Authorization: Bearer $HERMES_RUNTIME_API_KEY" "$HERMES_RUNTIME_API_BASE_URL/mission-control/runs"
```

Mission Control read models are Ares-owned. Hermes should not reconstruct them from provider or database calls.

## Error Behavior

- `401`: missing or wrong runtime API key.
- `403`: tool is forbidden by agent permission, capability, or skill surface.
- `422`: request payload is invalid or selected agent revision cannot dispatch.
- `404`: referenced run or approval does not exist.
- `200` on duplicate idempotency means the command was deduped.
- `201` means Ares accepted a new command/run or replay.
