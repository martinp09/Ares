# Ares Copywriting Brain — Hormozi/Sultanic Offer Engine Plan

## Goal

Beef up the actual Ares copywriting brain so it becomes a top-tier offer + copy intelligence layer for Texas seller outreach, starting with:

1. **Alex Hormozi offer architecture** — create the offer before writing campaigns.
2. **Alen Sultanic pain-first/direct-response style** — sharper hooks, pain agreement, mechanism, and conversion logic.
3. **Persistent example memory** — ingest and organize examples from Ares docs, campaign outputs, LLM Wiki, and later Obsidian.
4. **Operational Ares integration** — move from markdown-only copy to typed, reusable copy/offer assets with approval gates.

This plan is intentionally research-first. Do not wire live Instantly/TextGrid sends in this phase.

## Current context

Existing Ares assets:

- `docs/marketing/copywriting-domain-expertise-plan.md`
  - high-level copy brain strategy exists.
  - calls for principles, market truths, swipe file, performance memory, compliance, and copy-loop critique.
- `docs/marketing/2026-04-30-harris-probate-hot-warm-cold-campaign.md`
  - first real Harris probate HOT/WARM/COLD campaign draft exists.
  - includes email, SMS, direct mail, cadence, provider rules.
- `app/services/ares_copy_service.py`
  - current backend copy service exists but is skeletal and generic.
- `tests/services/test_ares_copy_service.py`
  - current tests only prove basic lead brief/draft generation and human approval gating.
- `docs/marketing/exports/harris-probate-2026-04-30/manifest.json`
  - current Harris probate batch is direct-mail-ready only; no email/SMS-ready contacts yet.

Key direction:

- Treat seller outreach as an **offer system**, not just copy snippets.
- The first domain is **Harris probate / inherited property / possible tax distress**.
- Lease-option messaging remains a separate lane.
- No auto-send. All production outreach remains approval-gated.

## Non-goals for this slice

- Do not auto-send email/SMS/direct mail.
- Do not upload leads to Instantly.
- Do not create an overbroad generic copy platform.
- Do not rely only on model memory of Hormozi/Sultanic; use researched, source-backed notes.
- Do not install/configure Obsidian Sync until we confirm vault path and desired sync model.

## Proposed architecture

### 1. Copy Brain Knowledge Base

Create a repo-local wiki under:

`docs/copywriting-wiki/`

Use LLM Wiki structure:

```text
docs/copywriting-wiki/
├── SCHEMA.md
├── index.md
├── log.md
├── raw/
│   ├── articles/
│   ├── transcripts/
│   ├── books-notes/
│   └── swipe-examples/
├── entities/
│   ├── alex-hormozi.md
│   └── alen-sultanic.md
├── concepts/
│   ├── grand-slam-offer.md
│   ├── value-equation.md
│   ├── pain-first-copy.md
│   ├── mechanism-based-offer.md
│   ├── texas-probate-seller-psychology.md
│   └── inherited-property-offer-architecture.md
├── examples/
│   ├── probate-hot-offer-examples.md
│   ├── probate-direct-mail-examples.md
│   ├── probate-email-examples.md
│   └── sms-permission-openers.md
└── queries/
```

Why repo-local:

- Ares owns this specific operating brain.
- It stays versioned with Ares implementation.
- Later, Obsidian can open/sync this exact folder as a vault or sub-vault.

### 2. Offer Asset Model

Add an Ares-native offer layer before copy assets.

Likely model:

```python
class OfferAsset:
    id: str
    name: str
    source_lane: probate | tax_delinquency | tired_landlord | expired | dom45 | lease_option
    segment: hot | warm | cold | all
    audience: str
    pain_points: list[str]
    dream_outcome: str
    likelihood_boosters: list[str]
    time_delay_reducers: list[str]
    effort_reducers: list[str]
    risk_reversal: str | None
    unique_mechanism: str
    proof_points: list[str]
    value_stack: list[str]
    constraints: list[str]
    truth_risk_notes: list[str]
    status: draft | review_required | approved | retired
```

This makes Hormozi explicit:

`Value = (Dream Outcome × Perceived Likelihood) / (Time Delay × Effort/Sacrifice)`

For probate sellers, the offer might become something like:

> “A simple inherited-property exit path for families who do not want to repair, clean out, list, or untangle every title/tax issue before exploring an as-is sale.”

Need research before final phrasing.

### 3. Copy Asset Model

After offers exist, copy assets reference offers.

Likely model:

```python
class CopyAsset:
    id: str
    offer_id: str
    asset_type: email | sms | direct_mail | call_script | landing_page | voicemail
    channel: instantly | textgrid | direct_mail | manual_call | web
    source_lane: probate | tax_delinquency | tired_landlord | expired | dom45 | lease_option
    segment: hot | warm | cold
    framework: hormozi_offer | sultanic_pain_first | hybrid
    awareness_level: unaware | problem_aware | solution_aware | product_aware | most_aware
    headline_or_subject: str | None
    body: str
    hook_variants: list[str]
    critique_notes: list[str]
    truth_risk_notes: list[str]
    template_variables: list[str]
    status: draft | review_required | approved | retired
```

### 4. Example / Swipe Library

Create structured example records for:

- source examples from researched public material
- internal Ares campaign examples
- generated variants that are approved/rejected
- response-backed winners later

Each example should include:

- source/type
- channel
- audience
- why it works
- what not to copy blindly
- reusable pattern
- compliance risk

### 5. Research + Draft + Critique Loop

Implement the brain as a deterministic workflow first:

1. Pull relevant wiki pages and examples.
2. Build the offer using Hormozi fields.
3. Draft using Sultanic pain-first structure.
4. Critique against:
   - empathy
   - specificity
   - believability
   - unique mechanism clarity
   - CTA clarity
   - probate sensitivity
   - Texas real-estate compliance risk
   - channel fit
5. Rewrite only weak sections.
6. Store offer + copy assets as `review_required`.
7. Operator approves before campaign enrollment.

## Research plan

Use parallel subagents for the research phase after this plan is approved.

### Research Stream A — Alex Hormozi offer framework

Goal:

- Build a source-backed Ares note on offer creation for distressed real-estate sellers.

Sources to inspect:

- Hormozi official content / Acquisition.com resources
- public talks/interviews/posts about Grand Slam Offers
- public summaries only where first-party source is unavailable
- existing notes, if any, in Ares/Mailers docs

Extract:

- value equation
- dream outcome
- perceived likelihood
- time delay
- effort/sacrifice
- value stack
- guarantees/risk reversal, with real-estate compliance caveats
- urgency/scarcity constraints without fake pressure
- naming offers
- bonus/stack logic translated to seller services

Output wiki pages:

- `entities/alex-hormozi.md`
- `concepts/grand-slam-offer.md`
- `concepts/value-equation.md`
- `concepts/inherited-property-offer-architecture.md`

### Research Stream B — Alen Sultanic pain-first copy style

Goal:

- Build a source-backed note on how to turn pain, mechanism, and offer into conversion copy.

Sources to inspect:

- public Alen Sultanic content and interviews
- Nothing Held Back / Copy Accelerator public material if accessible
- public examples, breakdowns, and sales-letter analysis

Extract:

- pain-first opening
- mechanism before pitch
- belief-shift structure
- hard contrast / failed solution contrast
- micro-agreements
- specificity and plainspoken persuasion
- what is stylistic vs what is strategic

Output wiki pages:

- `entities/alen-sultanic.md`
- `concepts/pain-first-copy.md`
- `concepts/mechanism-based-offer.md`
- `examples/sultanic-style-patterns-for-probate.md`

### Research Stream C — Real estate seller psychology / probate offer translation

Goal:

- Translate Hormozi/Sultanic principles into ethical, compliant Texas probate seller outreach.

Sources:

- Ares Harris probate campaign docs
- existing curative title notes/memory
- Texas probate/inherited property seller context from prior Ares docs
- competitor examples only as pattern references, not copy-paste

Extract:

- seller pains by segment:
  - HOT: urgent, tax/title/property pressure
  - WARM: inherited property uncertainty
  - COLD: weak signal, low pressure
- acceptable promise boundaries
- phrases to avoid
- direct-mail vs email vs SMS differences

Output wiki pages:

- `concepts/texas-probate-seller-psychology.md`
- `examples/probate-hot-offer-examples.md`
- `examples/probate-direct-mail-examples.md`
- `examples/sms-permission-openers.md`

### Browser-harness / browser use

Use browser tools for JS-heavy or visually structured pages.

Use `browser-harness` only if:

- the built-in browser cannot access key pages, or
- pages require DOM inspection / multi-tab extraction, or
- we need more durable browser automation.

First step before using harness:

```bash
command -v browser-harness
```

If missing or broken, follow `browser-harness-bootstrap` skill.

## Obsidian plan

Do not install/configure Obsidian yet during the first implementation slice unless explicitly approved.

Proposed setup after wiki exists:

1. Use the repo-local wiki as the vault:
   - `/opt/ares/Ares/docs/copywriting-wiki`
2. Set `OBSIDIAN_VAULT_PATH=/opt/ares/Ares/docs/copywriting-wiki` in Hermes env if we want the Obsidian skill to target it.
3. If Martin wants phone/laptop sync:
   - evaluate `obsidian-headless`
   - requires Obsidian account/sync credentials
   - configure continuous sync only after confirmation.

Alternative:

- Keep Ares repo as source of truth.
- Open the folder from desktop Obsidian manually after git pull.
- Avoid server-side Obsidian Sync complexity until the brain proves valuable.

## Implementation phases

### Phase 0 — Research and wiki initialization

Files to add:

- `docs/copywriting-wiki/SCHEMA.md`
- `docs/copywriting-wiki/index.md`
- `docs/copywriting-wiki/log.md`
- raw source notes under `docs/copywriting-wiki/raw/...`
- entity/concept/example pages listed above

Tests:

- add a wiki lint script or test to verify:
  - frontmatter exists
  - index includes every non-raw page
  - no broken wikilinks
  - required core pages exist

QC artifact:

- `docs/qc/YYYY-MM-DD/copywriting-brain-research/REPORT.md`
- include source manifest, pages created, limitations, and claims requiring caution.

Exit criteria:

- Ares has source-backed Hormozi/Sultanic notes.
- Ares has a probate seller psychology page.
- Ares has examples/patterns ready for the first offer draft.

### Phase 1 — Offer Engine v1

Files likely to add:

- `app/models/copy_offers.py`
- `app/services/copy_offer_service.py`
- `tests/services/test_copy_offer_service.py`

Behavior:

- Build a structured `OfferAsset` for Harris probate HOT/WARM/COLD.
- Score the offer using Hormozi fields.
- Store status as `review_required`.
- Include truth/risk notes by default.

Initial offer outputs:

- Harris Probate HOT offer
- Harris Probate WARM offer
- Harris Probate COLD offer

Exit criteria:

- Tests prove the offer has:
  - dream outcome
  - likelihood boosters
  - time/effort reducers
  - unique mechanism
  - risk notes
  - no auto-send path

### Phase 2 — Copy Asset Engine v1

Files likely to add/modify:

- `app/models/copy_assets.py`
- `app/services/copy_asset_service.py`
- `app/services/ares_copy_service.py`
- `tests/services/test_copy_asset_service.py`
- `tests/services/test_ares_copy_service.py`

Behavior:

- Generate channel-specific copy from an approved/reviewable offer.
- Use Sultanic structure for drafts:
  - pain hook
  - agreement/micro-yes
  - failed solution/contrast
  - unique mechanism
  - offer
  - CTA
- Keep all assets `review_required` by default.

Exit criteria:

- Existing Harris campaign copy is represented as structured copy assets.
- New copy service output is materially better than the current generic draft.
- Tests assert compliance notes and human approval gate.

### Phase 3 — Ares API / Mission Control read surface

Files likely to add/modify:

- `app/api/mission_control.py`
- `app/models/mission_control.py`
- `app/services/mission_control_service.py`
- `tests/api/test_mission_control_copy_assets.py`

Endpoints, likely:

- `GET /mission-control/copy/offers`
- `GET /mission-control/copy/assets`
- `POST /mission-control/copy/offers/{id}/approval`
- `POST /mission-control/copy/assets/{id}/approval`

Exit criteria:

- Operator can inspect offers and copy assets from API.
- Approval creates auditable command/approval state.
- No provider enrollment happens here.

### Phase 4 — Performance memory loop

Later, after campaigns run:

- Ingest Instantly/TextGrid/direct-mail outcomes.
- Attach metrics to copy assets:
  - sent
  - delivered
  - reply
  - positive reply
  - wrong person
  - opt-out
  - booked call
  - complaint/risk flag
- Generate monthly copy report into wiki:
  - winning hooks
  - losing hooks
  - objections
  - language to avoid

## First offer to create after research

Working title candidates, not final:

- `Inherited Property Exit Option`
- `Harris County Inherited Property Relief Offer`
- `As-Is Probate Property Option`
- `Family Property Exit Plan`

Core promise direction:

> Help families dealing with inherited Harris County property understand whether there is a simple as-is sale path without repairs, cleanout, listing, or having every title/tax issue solved before the first conversation.

Need refine after research.

Hormozi mapping draft:

- Dream outcome:
  - stop carrying an unwanted inherited property
  - get clarity and a simple exit path
  - avoid repairs, cleanout, MLS prep, and uncertainty
- Likelihood boosters:
  - local investor
  - works with as-is/probate/title/tax situations
  - clear next-step conversation
  - no listing prep needed
- Time delay reducers:
  - quick property review
  - simple call/text CTA
  - no prerequisite cleanup
- Effort reducers:
  - no repairs
  - no cleanup
  - no open houses
  - no need to solve every issue before talking
- Risk reversal / de-pressure:
  - no pressure
  - if keeping it, say so and we close notes
  - avoid “risk-free” or guarantees
- Unique mechanism:
  - Ares-powered property/probate/tax review + as-is investor path
  - must be described simply; do not make it sound like legal advice

Sultanic mapping draft:

- Pain-first hook:
  - “Inherited property decisions can get messy fast when repairs, taxes, title questions, and multiple family members are involved.”
- Agreement:
  - “Most families do not want another project right after probate paperwork.”
- Failed-solution contrast:
  - “A normal listing may not fit if the property needs repairs, cleanup, or title/tax issues are still unresolved.”
- Mechanism:
  - “I review the property as-is and let you know if a simple buyer option makes sense.”
- Offer:
  - “No repairs, cleanup, or listing prep before we talk.”
- CTA:
  - “Worth a quick call this week?”

## Risks / compliance notes

- Do not imply legal representation or probate advice.
- Do not guarantee purchase, price, closing, timeline, tax solution, or title cure.
- Avoid “risk-free,” “guaranteed,” “no risk,” “we solve everything.”
- SMS must be permission-based and suppression-aware.
- Probate copy must avoid sounding threatening, exploitative, or overly legalistic.
- Any “limited” or urgency claim must be factual.
- Lease-option copy must stay separate and include Texas-specific disclosures when used.

## Validation checklist

Research validation:

- Source manifest exists.
- Raw notes include URLs/dates/access notes.
- Wiki pages have frontmatter, sources, and cross-links.
- Claims that are interpretations are labeled as interpretations.

Code validation:

```bash
uv run pytest tests/services/test_copy_offer_service.py -q
uv run pytest tests/services/test_copy_asset_service.py tests/services/test_ares_copy_service.py -q
uv run pytest tests/api/test_mission_control_copy_assets.py -q
python3 -m compileall app/models/copy_offers.py app/models/copy_assets.py app/services/copy_offer_service.py app/services/copy_asset_service.py
```

Repo/QC validation:

```bash
git diff --check
```

QC artifacts:

- `docs/qc/YYYY-MM-DD/copywriting-brain-research/REPORT.md`
- `docs/qc/YYYY-MM-DD/copy-offer-engine/REPORT.md`
- `docs/qc/YYYY-MM-DD/copy-asset-engine/REPORT.md`

## Recommended execution order

1. Run research swarm for Hormozi, Sultanic, and probate seller psychology.
2. Initialize `docs/copywriting-wiki/` and ingest findings.
3. Draft the Harris probate offer assets first.
4. Upgrade `AresCopyService` so it pulls from offer + wiki patterns, not generic strings.
5. Structure the existing Harris campaign markdown into copy assets.
6. Add Mission Control read/approval surface.
7. Only after approval, wire assets toward Instantly/TextGrid/direct mail workflows.

## Open questions for Martin

These should not block research, but matter before final implementation:

1. Should the copywriting wiki live only in Ares, or also sync to a personal Obsidian vault?
2. Do you want the first offer to be strictly Harris probate, or a reusable “Inherited Property Exit Option” for all Texas counties?
3. Should the brand voice be more “local helpful buyer” or more “direct problem solver” for HOT leads?
4. For Obsidian: do you already have a vault/sync account we should target, or should Ares repo-local wiki be the first vault?

## Immediate next action after approval

Start Phase 0 with a research swarm:

- Subagent A: Hormozi offer framework source-backed notes.
- Subagent B: Sultanic pain-first copy source-backed notes.
- Subagent C: Texas probate seller offer translation and internal Ares examples.

Then synthesize into `docs/copywriting-wiki/` and create the first Harris probate offer draft.
