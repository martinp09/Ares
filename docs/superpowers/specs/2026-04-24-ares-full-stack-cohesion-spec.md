# Ares Full-Stack Cohesion Spec

Status: active implementation gate

## Goal

Ares is the deterministic runtime for Hermes-operated real-estate workflows. The stack is cohesive when Hermes can command Ares, Ares can persist and schedule work, providers can report side effects back to Ares, and Mission Control can explain the full chain from backend-owned read models.

## Boundaries

Hermes owns operator chat, coordination, approvals, summaries, browser-heavy work, and human-facing workflow choices. Hermes calls Ares over HTTP through `HERMES_RUNTIME_API_BASE_URL` and `HERMES_RUNTIME_API_KEY`; it does not own Ares business state or provider policy.

Ares owns typed runtime commands, policy, state integration, provider adapter invocation, Trigger callback ingestion, replay rules, audit/usage facts, and Mission Control read models. Ares exposes explicit FastAPI contracts and keeps storage/provider details behind deterministic adapters.

Supabase owns canonical durable records for runtime state, lead/contact/message/task facts, workflow-visible events, audit, and usage. Supabase is not called directly by Hermes or Mission Control. Local development defaults to memory-backed state until a Supabase slice is deliberately enabled.

Trigger.dev owns durable async execution, schedules, retries, and delays. Trigger jobs call Ares runtime endpoints and report business-visible lifecycle state back to Ares. Trigger internal logs are not the product source of truth.

Providers own side-effect transport only. TextGrid sends/receives SMS, Resend sends transactional or opt-in email, Cal.com reports booking lifecycle, and Instantly/Smartlead later handle cold outbound transport. Provider callbacks must become Ares state before operators rely on them.

Mission Control owns the operator UI. It reads Ares backend read models only and never calls Supabase or providers directly. In local Vite dev, the dev server proxies runtime API calls and injects the server-side runtime key so the browser never reads a public `VITE_RUNTIME_API_KEY`.

## Lead-Machine Happy Path

1. Hermes, a landing page, or an API client submits a lead to Ares.
2. Ares validates tenant scope and persists the lead/contact/conversation/event state.
3. Ares queues allowed provider side effects and durable Trigger work.
4. Trigger calls Ares internal runtime endpoints as work progresses.
5. TextGrid, Resend, Cal.com, and later outbound email providers report delivery, replies, booking, and campaign events back into Ares.
6. Ares updates messages, tasks, sequence state, suppression, audit, usage, and run lifecycle facts.
7. Mission Control shows lead timeline, provider status, workflow runs, pending approvals, failed side effects, and human tasks from Ares-owned read models.

## Non-Goals

- Do not install Ares into Hermes.
- Do not make Hermes, Trigger.dev, providers, or Mission Control the database.
- Do not let Mission Control call Supabase directly.
- Do not rewrite already-applied baseline migrations in place.
- Do not remove `business_id + environment` while adding `org_id`.
- Do not run live SMS/email smoke tests without explicit opt-in recipient flags.
- Do not push production Supabase migrations from an unverified environment.

## Required Smoke Tests

- API health: `GET /health`.
- Hermes discovery: `GET /hermes/tools` with runtime API auth.
- Safe command invocation through the Hermes tool surface.
- No-live-send lead intake with simulated Trigger/provider callbacks.
- Mission Control readback for dashboard, runs, lead/provider state, and failed side effects.
- Audit/event/task/message assertions for every business-visible transition.

## Phase Gate

Phase 0/1 completion requires the mega plan, this spec, `.env.example`, the local runbook, config contract tests, Trigger static contract tests, and no runtime migrations or live provider sends.
