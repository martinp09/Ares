---
title: "Ares Copywriting Domain Expertise Plan"
status: active
created_at: "2026-04-30"
owner: "Martin Perales"
---

# Ares Copywriting Domain Expertise Plan

## Goal

Make Hermes/Ares materially better at seller-facing copy by building a reusable real-estate copy intelligence layer, not by relying on generic copywriting advice.

The target domain is distressed Texas real-estate outreach across:

- curative title / heirs / probate
- delinquent tax and inherited-property pain
- tired landlords / FRBO / expireds / DOM > 45
- lease-option seller/buyer messaging as a separate lane

## Operating model

### 1. Build a copy brain

Create a living copy library with four layers:

1. **Principles** — Hopkins/Ogilvy/Schwartz/Halbert/Kennedy/Sugarman/Bencivenga/Settle/Carlton/Hormozi/Sultanic/Luke Alexander.
2. **Market truths** — Texas seller situations, probate language, title friction, tax pressure, inherited-property fatigue, landlord burnout.
3. **Swipe file** — direct mail, SMS, email, voicemail, landing pages, postcards, agent/wholesaler letters, probate letters, tax-delinquency letters.
4. **Performance memory** — what got replies, complaints, opt-outs, appointments, signed contracts, dead leads.

### 2. Make copy channel-specific

Never write one generic message and shrink it.

- Email: subject/preview/body/CTA/unsub compliance.
- SMS: permission-based, one question, short, opt-out when needed.
- Direct mail: scene + problem + simple option + phone CTA.
- Call opener: identity + permission + reason + one qualifying question.
- Landing page: problem-aware hero + mechanism + proof + FAQ + CTA.

### 3. Use a draft → critique → rewrite loop

Every production campaign asset should run:

1. Brief parse: audience, pain, offer, proof, CTA, compliance constraints.
2. First draft using the correct framework.
3. Critique for empathy, specificity, believability, channel fit, compliance.
4. Rewrite weak parts only.
5. Save final asset and risk notes into Ares.

### 4. Add a compliance/risk layer

Every copy asset must flag:

- unverified factual claims
- urgency/limited claims
- title/legal-advice risk
- broker/licensing implication risk
- TCPA/SMS risk
- probate sensitivity risk
- lease-option Texas disclosure risk when relevant

### 5. Feed response outcomes back into copy

Ares should eventually store per-template metrics:

- sent count
- delivered count
- reply count
- positive reply count
- opt-out count
- wrong-person count
- booked-call count
- deal-created count
- complaint/risk flags

The copy brain improves from actual seller behavior, not vibes.

## Practical build path

### Phase 1 — now

- Keep `copywriter-agent` as the first-draft engine.
- Keep `copy-loop` as the critique/rewrite workflow.
- Save campaign-specific copy docs under `docs/marketing/copy/`.
- For every campaign, include:
  - strategy note
  - final copy by channel
  - hook variants
  - truth/risk note
  - approved/not-approved status

### Phase 2 — Ares asset library

Add typed Ares copy assets:

- `asset_type`: email, sms, direct_mail, call_script, landing_page
- `source_lane`: probate, tax_delinquency, expired, dom45, tired_landlord, lease_option
- `segment`: hot, warm, cold
- `awareness_level`: unaware/problem_aware/solution_aware/product_aware/most_aware
- `status`: draft, review_required, approved, retired
- `truth_risk_notes`
- `template_variables`

### Phase 3 — copy evaluation loop

Add an evaluator that scores each asset 1-5 on:

- empathy
- specificity
- proof/believability
- mechanism clarity
- CTA clarity
- channel fit
- compliance risk

Require approval before campaign enrollment.

### Phase 4 — performance-trained playbook

After campaigns run, Ares writes a monthly copy report:

- best subject lines
- best first SMS question
- best direct-mail CTA
- objections/replies by segment
- opt-out language that reduced complaints
- phrases to avoid
- new winning templates to promote

## Immediate copywriting expertise upgrade

Use this stack for every serious campaign:

1. Research agent builds a seller psychology brief.
2. Copywriter agent drafts actual assets.
3. Copy loop critiques and rewrites.
4. Ares stores approved versions as campaign assets.
5. Campaign events feed performance notes back into the copy library.

That is how Hermes becomes a domain expert: repeated domain-specific briefing, structured critique, compliance checks, and real response feedback saved into durable assets.
