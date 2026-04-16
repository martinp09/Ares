# Harris County Probate Keep-Now Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fixture-backed Harris County probate intake slice that only keeps the high-alpha probate categories and surfaces them in Ares/Mission Control, without backend wiring yet.

**Architecture:** Use the Harris County Clerk probate search as the source of truth, pull filings on a scheduled cadence, and filter immediately to the keep-now probate categories only. Normalize raw filings into a stable lead shape, enrich them against HCAD when possible, and expose the result through Mission Control fixture data and operator views. No Supabase migrations, no live DB wiring, no production dispatch yet.

**Tech Stack:** Python 3.12+, browser-use/browser automation, existing HCAD_Query project, pytest, FastAPI read surfaces already in repo, TypeScript/Vite Mission Control fixtures.

---

## Keep-Now Probate Filter

Only retain these categories for the first slice:
- Probate of Will (Independent Administration)
- Independent Administration
- App for Independent Administration with Will Annexed
- App for Independent Administration with an Heirship
- App to Determine Heirship

Everything else stays out of the first MVP:
- Dependent Administration
- Small Estate
- Guardianship
- Miscellaneous probate buckets until we decide they are worth the noise

Keep later, but do not prioritize yet:
- Ancillary Administration
- Muniment of Title cases hidden inside "Probate of Will (All Other Estate Proceedings)"

---

## Data Shape

The normalized probate lead record should include:
- case_number
- file_date
- court_number
- status
- filing_type
- filing_subtype
- estate_name
- decedent_name
- source = `harris_county_probate`
- keep_now = true/false
- hcad_match_status
- hcad_acct
- owner_name
- mailing_address
- contact_confidence
- lead_score
- outreach_status
- last_seen_at

---

## Task 1: Build the Harris County probate puller

**Files:**
- Create: `scripts/harris_probate_pull.py`
- Create: `data/harris-probate/raw/`
- Create: `data/harris-probate/normalized/`
- Test: `tests/scripts/test_harris_probate_pull.py`

- [ ] **Step 1: Write the puller contract test**

```python
from scripts.harris_probate_pull import normalize_probate_case, keep_now_probate_case


def test_keep_now_filter_accepts_only_target_types():
    assert keep_now_probate_case({"type": "PROBATE OF WILL (INDEPENDENT ADMINISTRATION)"}) is True
    assert keep_now_probate_case({"type": "DEPENDENT ADMINISTRATION"}) is False
    assert keep_now_probate_case({"type": "SMALL ESTATE"}) is False
```

- [ ] **Step 2: Run the test and confirm it fails before implementation**

Run: `uv run pytest tests/scripts/test_harris_probate_pull.py -q`
Expected: FAIL because the puller functions do not exist yet.

- [ ] **Step 3: Implement the puller and normalization**

The puller should:
- query the Harris County Clerk probate search page by file-date range
- scrape only the filing table rows
- save raw rows to `data/harris-probate/raw/YYYY-MM-DD.json`
- save normalized keep-now rows to `data/harris-probate/normalized/YYYY-MM-DD.json`

Pseudo-shape:

```python
KEEP_NOW_TYPES = {
    "PROBATE OF WILL (INDEPENDENT ADMINISTRATION)",
    "INDEPENDENT ADMINISTRATION",
    "APP FOR INDEPENDENT ADMINISTRATION WITH WILL ANNEXED",
    "APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP",
    "APP TO DETERMINE HEIRSHIP",
}
```

- [ ] **Step 4: Run the test and confirm it passes**

Run: `uv run pytest tests/scripts/test_harris_probate_pull.py -q`
Expected: PASS.

- [ ] **Step 5: Commit the puller slice**

```bash
git add scripts/harris_probate_pull.py tests/scripts/test_harris_probate_pull.py data/harris-probate
git commit -m "feat: add Harris County probate puller"
```

**Acceptance gate:** A daily or hourly run can fetch probate rows, apply the keep-now filter, and write raw plus normalized JSON without touching Supabase or any live backend.

---

## Task 2: Add HCAD matching and probate lead scoring

**Files:**
- Create: `app/models/probate_leads.py`
- Create: `app/services/probate_hcad_match_service.py`
- Create: `app/services/probate_lead_score_service.py`
- Test: `tests/services/test_probate_hcad_match_service.py`
- Test: `tests/services/test_probate_lead_score_service.py`

- [ ] **Step 1: Write the scoring test**

```python
from app.services.probate_lead_score_service import score_probate_lead


def test_independent_admin_with_hcad_match_scores_highest():
    lead = {
        "filing_type": "PROBATE OF WILL (INDEPENDENT ADMINISTRATION)",
        "keep_now": True,
        "hcad_match_status": "matched",
        "contact_confidence": "high",
    }
    assert score_probate_lead(lead) >= 90
```

- [ ] **Step 2: Implement matching against HCAD**

The matcher should:
- normalize estate names
- try owner-name and decedent-name matching against HCAD data
- preserve the padded-acct trim rule already known in HCAD_Query
- mark unmatched records instead of inventing matches

- [ ] **Step 3: Implement the score rules**

Suggested priority order:
- `PROBATE OF WILL (INDEPENDENT ADMINISTRATION)` = highest priority
- `INDEPENDENT ADMINISTRATION` = high priority
- `APP FOR INDEPENDENT ADMINISTRATION WITH WILL ANNEXED` = high priority
- `APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP` = very high priority
- `APP TO DETERMINE HEIRSHIP` = very high priority

Score down:
- no HCAD match
- no mailing address
- ambiguous estate naming
- multiple likely property candidates

- [ ] **Step 4: Run the tests and confirm they pass**

Run:
- `uv run pytest tests/services/test_probate_hcad_match_service.py -q`
- `uv run pytest tests/services/test_probate_lead_score_service.py -q`

- [ ] **Step 5: Commit the enrichment slice**

```bash
git add app/models/probate_leads.py app/services/probate_hcad_match_service.py app/services/probate_lead_score_service.py tests/services/test_probate_hcad_match_service.py tests/services/test_probate_lead_score_service.py
git commit -m "feat: score and match probate leads"
```

**Acceptance gate:** A keep-now probate record can be matched to HCAD when possible, scored deterministically, and left unmatched when not.

---

## Task 3: Surface probate leads in Mission Control using fixtures only

**Files:**
- Create: `apps/mission-control/src/pages/ProbatesPage.tsx`
- Create: `apps/mission-control/src/components/ProbateLeadTable.tsx`
- Modify: `apps/mission-control/src/App.tsx`
- Modify: `apps/mission-control/src/lib/fixtures.ts`
- Modify: `apps/mission-control/src/lib/api.ts`
- Test: `apps/mission-control/src/pages/ProbatesPage.test.tsx`

- [ ] **Step 1: Write the UI test**

```tsx
import { render, screen } from "@testing-library/react";
import { ProbatesPage } from "./ProbatesPage";

test("shows keep-now probate counts and top leads", () => {
  render(<ProbatesPage />);
  expect(screen.getByText(/keep-now probates/i)).toBeInTheDocument();
  expect(screen.getByText(/independent administration/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Implement the page with fixture-backed data only**

The page should show:
- today’s probate count
- keep-now count
- matched vs unmatched
- top-scored leads
- filter chips for the keep-now categories

- [ ] **Step 3: Wire it into navigation**

Add a new Ares/Mission Control surface for:
- `Probates`
- `Lead Queue`
- `Email Outreach`

Do not add live backend fetches yet. Use fixture data only.

- [ ] **Step 4: Run the frontend checks**

Run:
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`

- [ ] **Step 5: Commit the operator surface slice**

```bash
git add apps/mission-control/src/App.tsx apps/mission-control/src/lib/api.ts apps/mission-control/src/lib/fixtures.ts apps/mission-control/src/components/ProbateLeadTable.tsx apps/mission-control/src/pages/ProbatesPage.tsx apps/mission-control/src/pages/ProbatesPage.test.tsx
git commit -m "feat: add probate operator surface"
```

**Acceptance gate:** Mission Control can show the keep-now probate lead queue without backend wiring, and the UI tells the truth about which records are worth working.

---

## Task 4: Document the cron cadence and handoff rules

**Files:**
- Modify: `TODO.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`
- Modify: `README.md` if needed

- [ ] **Step 1: Document the cadence**

State clearly:
- probate pull runs hourly or daily
- filter happens before scoring
- only keep-now categories move forward
- no backend wiring until this slice is validated in fixtures and local scripts

- [ ] **Step 2: Document the safe escalation path**

If a filing is:
- dependent admin
- small estate
- guardianship
- or otherwise noisy

it stays out of the curative-title queue for now.

- [ ] **Step 3: Commit the handoff docs**

```bash
git add TODO.md CONTEXT.md memory.md README.md
git commit -m "docs: add probate lead intake handoff"
```

**Acceptance gate:** A future session can reconstruct the probate rules and the no-backend boundary without re-asking you to translate probate alphabet soup.

---

## Verification

Run after each task and again at the end:
- `uv run pytest -q`
- `npm --prefix apps/mission-control run typecheck`
- `npm --prefix apps/mission-control run test -- --run`
- `npm --prefix apps/mission-control run build`
- `git diff --check`

## Exit gate

Do not wire live backend storage until:
- the keep-now probate filter is stable
- HCAD matching works on fixture data
- Mission Control renders the lead queue correctly
- the cron cadence and handoff rules are documented
