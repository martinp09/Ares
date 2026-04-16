# Curative Title Cold Email Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cold-email machine for curative title that Ares can orchestrate, while keeping cold outbound separate from transactional/opt-in email and avoiding backend wiring until the lead-intake slice is validated.

**Architecture:** Ares owns the brain: decide who should be emailed, when, with what sequence, and when to stop. Cold outbound transport should be handled by a dedicated cold-email provider layer, while Resend stays reserved for opt-in nurture, confirmations, and transactional mail. Mission Control should show campaign state, mailbox health, and reply status using fixtures first; live provider integration comes later.

**Tech Stack:** Python 3.12+, existing FastAPI services, TypeScript/Vite Mission Control fixtures, pytest, provider adapter seam, Resend API, Smartlead or Instantly as cold-outbound provider targets.

---

## Provider Decision Matrix

Use the right hammer for the right job:
- Smartlead or Instantly: cold outbound, inbox rotation, warm-up, sequence sending, deliverability tooling
- Resend: transactional mail, opt-in nurture, inbound follow-up after consent, broadcast-style non-cold email

Ares should treat the provider as a transport adapter, not the product identity.

---

## Campaign State Model

The cold-email machine needs these states:
- draft
- ready
- warming
- sending
- paused
- bounced
- replied
- suppressed
- exhausted
- failed

And these safety dimensions:
- consent_status
- unsubscribe_status
- bounce_status
- mailbox_health
- domain_health
- lead_source
- sequence_step
- last_touch_at

---

## Task 1: Define the cold-email provider contract

**Files:**
- Create: `app/models/email_campaigns.py`
- Create: `app/models/email_providers.py`
- Create: `app/services/email_provider_registry_service.py`
- Create: `app/services/email_providers/base.py`
- Create: `app/services/email_providers/resend.py`
- Create: `app/services/email_providers/smartlead.py`
- Create: `app/services/email_providers/instantly.py`
- Test: `tests/services/test_email_provider_registry_service.py`
- Test: `tests/services/test_email_provider_clients.py`

- [ ] **Step 1: Write the provider routing test**

```python
from app.services.email_provider_registry_service import resolve_email_provider


def test_cold_outbound_routes_to_dedicated_cold_provider():
    assert resolve_email_provider({"kind": "cold_outbound"}) in {"smartlead", "instantly"}


def test_resend_is_not_the_cold_outbound_default():
    assert resolve_email_provider({"kind": "transactional"}) == "resend"
```

- [ ] **Step 2: Run the test and confirm it fails before implementation**

Run: `uv run pytest tests/services/test_email_provider_registry_service.py -q`
Expected: FAIL because the provider contract does not exist yet.

- [ ] **Step 3: Implement the provider registry**

Rules:
- Smartlead/Instantly are valid for cold outbound
- Resend is valid for transactional / opt-in / nurture
- provider choice must be explicit, not hidden behind env sniffing
- provider capability metadata must be part of the contract

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/services/test_email_provider_registry_service.py tests/services/test_email_provider_clients.py -q`
Expected: PASS.

- [ ] **Step 5: Commit the provider contract slice**

```bash
git add app/models/email_campaigns.py app/models/email_providers.py app/services/email_provider_registry_service.py app/services/email_providers tests/services/test_email_provider_registry_service.py tests/services/test_email_provider_clients.py
git commit -m "feat: add email provider contract"
```

**Acceptance gate:** Ares can distinguish cold outbound from opt-in/transactional email and route each to the correct provider family.

---

## Task 2: Define the sequence and suppression state machine

**Files:**
- Create: `app/models/email_sequences.py`
- Create: `app/services/email_sequence_service.py`
- Create: `app/services/email_suppression_service.py`
- Test: `tests/services/test_email_sequence_service.py`
- Test: `tests/services/test_email_suppression_service.py`

- [ ] **Step 1: Write the sequence test**

```python
from app.services.email_sequence_service import next_sequence_step


def test_replied_leads_stop_the_sequence():
    lead = {"reply_status": "replied", "sequence_step": 2}
    assert next_sequence_step(lead) is None
```

- [ ] **Step 2: Implement suppression rules**

The suppression service should stop sends for:
- replies
- unsubscribes
- hard bounces
- invalid mailbox states
- known bad domains
- duplicate leads already in an active sequence

- [ ] **Step 3: Implement lead-to-sequence rules**

Suggested sequence routing:
- website form lead -> Resend nurture or local follow-up sequence
- probate keep-now lead -> cold outbound sequence
- hot replied lead -> stop sequence and hand to operator inbox

- [ ] **Step 4: Run the tests and confirm they pass**

Run:
- `uv run pytest tests/services/test_email_sequence_service.py -q`
- `uv run pytest tests/services/test_email_suppression_service.py -q`

- [ ] **Step 5: Commit the state-machine slice**

```bash
git add app/models/email_sequences.py app/services/email_sequence_service.py app/services/email_suppression_service.py tests/services/test_email_sequence_service.py tests/services/test_email_suppression_service.py
git commit -m "feat: add email sequence safety rules"
```

**Acceptance gate:** Ares can decide whether a lead should keep receiving messages, pause, or stop completely.

---

## Task 3: Build a fixture-backed cold-email operator view in Mission Control

**Files:**
- Create: `apps/mission-control/src/pages/OutreachPage.tsx`
- Create: `apps/mission-control/src/components/CampaignStatusCard.tsx`
- Create: `apps/mission-control/src/components/SequenceTimeline.tsx`
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/lib/fixtures.ts`
- Modify: `apps/mission-control/src/lib/api.ts`
- Test: `apps/mission-control/src/pages/OutreachPage.test.tsx`

- [ ] **Step 1: Write the UI test**

```tsx
import { render, screen } from "@testing-library/react";
import { OutreachPage } from "./OutreachPage";

test("shows campaign health and suppression state", () => {
  render(<OutreachPage />);
  expect(screen.getByText(/cold email/i)).toBeInTheDocument();
  expect(screen.getByText(/suppressed/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Implement the page with fixtures only**

The page should show:
- active campaigns
- mailbox health
- send counts
- reply counts
- suppressed leads
- nurture vs cold routing

- [ ] **Step 3: Wire the page into Mission Control**

Add a visible operator surface for:
- `Outreach`
- `Campaigns`
- `Mailbox Health`

Keep it fixture-backed until the later backend wiring phase.

- [ ] **Step 4: Run the frontend checks**

Run:
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`

- [ ] **Step 5: Commit the operator view slice**

```bash
git add apps/mission-control/src/App.tsx apps/mission-control/src/lib/api.ts apps/mission-control/src/lib/fixtures.ts apps/mission-control/src/components/CampaignStatusCard.tsx apps/mission-control/src/components/SequenceTimeline.tsx apps/mission-control/src/pages/OutreachPage.tsx apps/mission-control/src/pages/OutreachPage.test.tsx
git commit -m "feat: add outreach operator surface"
```

**Acceptance gate:** Mission Control can show the cold-email machine’s state without live provider wiring and without pretending Resend is a cold-email sequencer.

---

## Task 4: Define the Resend vs cold-provider policy in docs

**Files:**
- Modify: `TODO.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Modify: `README.md` if needed
- Create: `docs/superpowers/specs/2026-04-16-curative-title-cold-email-policy.md`

- [ ] **Step 1: Document the policy clearly**

State:
- Resend is for transactional and opt-in nurture
- Smartlead/Instantly are for cold outbound
- Ares owns campaign logic, suppression, and operator visibility
- no live backend wiring yet for this slice

- [ ] **Step 2: Document the failure modes**

Call out the things that break cold email systems:
- sending from one mailbox forever
- not tracking bounce/reply/suppression state
- using a transactional API as if it were a deliverability platform
- ignoring mailbox/domain health

- [ ] **Step 3: Commit the policy doc**

```bash
git add TODO.md CONTEXT.md memory.md README.md docs/superpowers/specs/2026-04-16-curative-title-cold-email-policy.md
git commit -m "docs: add cold email policy handoff"
```

**Acceptance gate:** Future sessions can reconstruct the email architecture in one read and do not confuse cold outbound with Resend’s transactional/nurture lane.

---

## Verification

Run after each task and again at the end:
- `uv run pytest -q`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`
- `git diff --check`

## Exit gate

Do not connect live provider credentials or backend dispatch until:
- the provider policy is stable
- suppression rules are proven
- Mission Control renders the outreach state correctly
- the cold-email machine is clearly separated from transactional Resend usage
