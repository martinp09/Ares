# Full-Stack Cohesion Smoke

Phase 9 smoke is local and deterministic by default. It uses the FastAPI app in-process with memory-backed state and does not start a server, Docker, Colima, Trigger, Supabase, TextGrid, Resend, or Cal.com.

## No-Live-Sends Smoke

```bash
uv run pytest tests/smoke/test_full_stack_contract.py -q
uv run python scripts/smoke_full_stack_cohesion.py --no-live-sends
```

The smoke proves:

- `/health` responds.
- Hermes can discover tools and invoke `run_market_research`.
- Trigger lifecycle callbacks mutate the run and append audit/usage.
- Marketing lead intake creates a canonical contact without live provider sends.
- A fake manual-call task payload is accepted.
- Cal.com booking webhook updates booking state.
- TextGrid inbound webhook records an inbound message.
- Mission Control dashboard/runs read models load.
- Audit, usage, tasks, messages, and booking events are present.

## Provider Readiness

```bash
uv run python scripts/smoke_provider_readiness.py
```

This validates TextGrid and Resend request shapes without sending.

Live provider flags must be explicit:

```bash
ARES_SMOKE_SEND_SMS=1 ARES_SMOKE_TO_PHONE=+15551234567 uv run python scripts/smoke_provider_readiness.py --allow-live
ARES_SMOKE_SEND_EMAIL=1 ARES_SMOKE_TO_EMAIL=operator@example.com uv run python scripts/smoke_provider_readiness.py --allow-live
```

The full-stack smoke intentionally remains no-live-sends only.
