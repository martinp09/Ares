# Ares Probate-to-Instantly Campaign Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first real probate-to-campaign path in Ares: ingest probate leads, clean/normalize them, enrich them with email data, push them into Instantly V2, and sync webhook outcomes back into the runtime.

**Architecture:** Keep the current Hermes Central Command runtime as the control plane and add a narrow probate pipeline beside it. Use the existing command/approval/run/replay patterns for orchestration, but keep the actual lead work in a new probate domain plus a thin Instantly adapter. The first shipable slice should work from an exported probate CSV before county scraping is added.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, httpx, uv, existing in-memory runtime patterns.

---

## Reality Check

I checked the repo. There is **no** real probate pipeline and **no** Instantly backend wiring yet.

What exists today:

- FastAPI runtime and control plane routes: commands, approvals, runs, replays, mission control, marketing, hermes tools, site events
- marketing scaffolding that returns placeholder campaign artifacts
- Mission Control read surfaces and in-memory runtime state
- docs for a probate/tax-delinquent direction and an autonomy roadmap

What is missing:

- probate CSV ingest or county scraper code
- lead cleaning / normalization / dedupe code
- email enrichment / skiptrace layer
- Instantly V2 client
- lead list creation and bulk lead upload
- webhook receiver for replies/bounces/unsubs
- control-plane wiring for a probate campaign flow

Also important: Instantly V2 lead creation expects an email field. That means an address-only probate list is not enough. The pipeline needs an email enrichment step before upload unless the input already has emails.

---

## Working Rules

- Start with a CSV-based probate ingest path. County scraping can come later.
- Do not block the first campaign slice on automated county crawlers.
- Keep the Instantly adapter thin and V2-only.
- Do not auto-send without a review gate.
- If a lead has no email, it stops at "needs enrichment" instead of pretending it is ready.
- Commit after each task once its tests pass.
- Use the existing runtime/approval model rather than inventing a parallel control plane.

---

## Phase 0: Prove the Spine Is Real

**What it is:**
A short readiness phase that confirms the repo can host the pipeline without a rewrite.

**Current files that matter:**

- `app/main.py`
- `app/core/config.py`
- `app/core/dependencies.py`
- `app/models/commands.py`
- `app/services/command_service.py`
- `app/services/run_service.py`
- `app/services/mission_control_service.py`
- `app/api/marketing.py`
- `app/api/mission_control.py`
- `app/domains/marketing/commands.py`
- `app/domains/marketing/service.py`
- `tests/api/test_marketing_runtime.py`
- `tests/api/test_mission_control_phase3.py`

**Exit criteria:**
The runtime control plane is stable, and the missing pieces are clearly isolated to probate ingest, email enrichment, and Instantly integration.

---

## Phase 1: Probate Lead Model, CSV Ingest, and Cleaning

**What it is:**
Turn a probate CSV export into a normalized lead batch that Ares can reason about.

**Files to create:**

- `app/domains/probate/models.py`
- `app/domains/probate/ingestion.py`
- `app/domains/probate/cleaning.py`
- `app/domains/probate/repository.py`
- `tests/domains/probate/test_models.py`
- `tests/domains/probate/test_ingestion.py`
- `tests/domains/probate/test_cleaning.py`

**Files to modify:**

- `app/api/marketing.py` or `app/api/probate.py` if we choose a dedicated route
- `app/main.py` to mount the new route
- `tests/test_package_layout.py`

### Task 1: Define the canonical probate lead model

**Files:**
- Create: `app/domains/probate/models.py`
- Create: `tests/domains/probate/test_models.py`
- Modify: `tests/test_package_layout.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.domains.probate.models import ProbateLead, ProbateLeadSource


def test_probate_lead_marks_estate_of_rows() -> None:
    lead = ProbateLead(
        county="harris",
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
        source=ProbateLeadSource.CSV_EXPORT,
        source_id="case-001",
    )

    assert lead.estate_of is True
    assert lead.county == "harris"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/domains/probate/test_models.py tests/test_package_layout.py -q
```

Expected: fail because the new probate model module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create a small Pydantic model set:

```python
from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProbateLeadSource(StrEnum):
    CSV_EXPORT = "csv_export"
    COUNTY_PORTAL = "county_portal"


class ProbateLead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    county: str = Field(min_length=1)
    property_address: str = Field(min_length=1)
    owner_name: str | None = None
    source: ProbateLeadSource
    source_id: str | None = None
    estate_of: bool = False
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def infer_estate_of(self) -> "ProbateLead":
        if self.owner_name and "estate of" in self.owner_name.lower():
            self.estate_of = True
        return self
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/domains/probate/test_models.py tests/test_package_layout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/domains/probate/models.py tests/domains/probate/test_models.py tests/test_package_layout.py
git commit -m "feat: add probate lead model"
```

### Task 2: Ingest and clean probate CSV exports

**Files:**
- Create: `app/domains/probate/ingestion.py`
- Create: `app/domains/probate/cleaning.py`
- Create: `app/domains/probate/repository.py`
- Create: `tests/domains/probate/test_ingestion.py`
- Create: `tests/domains/probate/test_cleaning.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.domains.probate.cleaning import clean_probate_leads
from app.domains.probate.models import ProbateLead, ProbateLeadSource


def test_clean_probate_leads_normalizes_addresses_and_dedupes() -> None:
    leads = [
        ProbateLead(
            county="Harris",
            property_address="123 main st, #2, Houston, TX",
            owner_name="Estate of Jane Doe",
            source=ProbateLeadSource.CSV_EXPORT,
            source_id="case-001",
        ),
        ProbateLead(
            county="harris",
            property_address="123 Main Street Apt 2 Houston TX",
            owner_name="Estate of Jane Doe",
            source=ProbateLeadSource.CSV_EXPORT,
            source_id="case-001-dup",
        ),
    ]

    cleaned = clean_probate_leads(leads)
    assert len(cleaned) == 1
    assert cleaned[0].county == "harris"
    assert cleaned[0].property_address == "123 main st apt 2 houston tx"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/domains/probate/test_ingestion.py tests/domains/probate/test_cleaning.py -q
```

Expected: fail because the ingest and cleaning modules do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Use `csv.DictReader` for CSV ingest, map the county export columns into `ProbateLead`, and keep the first pass deterministic:

```python
from csv import DictReader
from io import StringIO

from app.domains.probate.models import ProbateLead, ProbateLeadSource


def parse_probate_csv(raw_csv: str) -> list[ProbateLead]:
    rows = DictReader(StringIO(raw_csv))
    leads: list[ProbateLead] = []
    for row in rows:
        leads.append(
            ProbateLead(
                county=row["county"].strip().lower(),
                property_address=row["property_address"].strip(),
                owner_name=row.get("owner_name"),
                source=ProbateLeadSource.CSV_EXPORT,
                source_id=row.get("source_id"),
                email=row.get("email") or None,
                first_name=row.get("first_name") or None,
                last_name=row.get("last_name") or None,
                phone=row.get("phone") or None,
            )
        )
    return leads
```

Implement cleaning with simple canonicalization:

- lowercase county and address
- remove punctuation noise
- collapse whitespace
- dedupe on normalized county + address + owner name + source ID

Keep a repository in memory for now so the pipeline can run without adding a database before the process proves useful.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/domains/probate/test_ingestion.py tests/domains/probate/test_cleaning.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/domains/probate/ingestion.py app/domains/probate/cleaning.py app/domains/probate/repository.py tests/domains/probate/test_ingestion.py tests/domains/probate/test_cleaning.py
git commit -m "feat: ingest and clean probate csv exports"
```

---

## Phase 2: Email Enrichment Gate

**What it is:**
A required enrichment step before Instantly upload, because Instantly V2 lead creation needs an email address.

**Why this exists:**
Address-only probate data is not enough. If the input batch has no email, the pipeline should stop at `needs_enrichment` instead of pretending it can upload.

**Files to create:**

- `app/integrations/email_enrichment/__init__.py`
- `app/integrations/email_enrichment/client.py`
- `app/integrations/email_enrichment/schemas.py`
- `app/domains/probate/enrichment.py`
- `tests/integrations/email_enrichment/test_client.py`
- `tests/domains/probate/test_enrichment.py`

**Files to modify:**

- `app/domains/probate/models.py`
- `app/domains/probate/ingestion.py`
- `app/domains/probate/cleaning.py`

### Task 3: Add the enrichment contract and a file-backed fallback

**Files:**
- Create: `app/domains/probate/enrichment.py`
- Create: `tests/domains/probate/test_enrichment.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.domains.probate.enrichment import FileEmailEnrichmentProvider, enrich_probate_leads
from app.domains.probate.models import ProbateLead, ProbateLeadSource


def test_enrich_probate_leads_merges_email_fields_from_lookup_file(tmp_path) -> None:
    lookup = tmp_path / "emails.csv"
    lookup.write_text(
        "source_id,email,first_name,last_name,phone\ncase-001,jane@example.com,Jane,Doe,+15551234567\n"
    )

    lead = ProbateLead(
        county="harris",
        property_address="123 main st houston tx",
        owner_name="Estate of Jane Doe",
        source=ProbateLeadSource.CSV_EXPORT,
        source_id="case-001",
    )

    enriched = enrich_probate_leads([lead], FileEmailEnrichmentProvider(str(lookup)))
    assert enriched[0].email == "jane@example.com"
    assert enriched[0].first_name == "Jane"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/domains/probate/test_enrichment.py -q
```

Expected: fail because the enrichment module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Define a small provider protocol and one file-backed implementation so the pipeline can run tonight even before a paid skiptrace API is wired:

```python
class EmailEnrichmentProvider(Protocol):
    def enrich(self, lead: ProbateLead) -> ProbateLead: ...

class FileEmailEnrichmentProvider:
    def __init__(self, path: str) -> None: ...
    def enrich(self, lead: ProbateLead) -> ProbateLead: ...
```

The file-backed adapter is the stopgap. Later, swap in a real enrichment API without changing the pipeline.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/domains/probate/test_enrichment.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/domains/probate/enrichment.py tests/domains/probate/test_enrichment.py
git commit -m "feat: add probate email enrichment gate"
```

---

## Phase 3: Instantly V2 Client, Lead Lists, and Bulk Upload

**What it is:**
The actual Instantly integration: create a lead list, upload enriched probate leads in bulk, and support lead/campaign metadata.

**Instanly V2 facts to honor:**

- Bearer token auth
- V2 is not compatible with V1
- lead lists endpoints exist
- lead upload endpoints exist
- webhook endpoints exist

**Endpoints to support first:**

- `POST /api/v2/lead-lists`
- `GET /api/v2/lead-lists`
- `POST /api/v2/leads/add`
- `POST /api/v2/leads`
- `GET /api/v2/webhooks`
- `POST /api/v2/webhooks`
- `POST /api/v2/webhooks/{id}/test`

**Files to create:**

- `app/integrations/instantly/config.py`
- `app/integrations/instantly/client.py`
- `app/integrations/instantly/schemas.py`
- `app/domains/probate/publish.py`
- `tests/integrations/instantly/test_client.py`
- `tests/domains/probate/test_publish.py`

**Files to modify:**

- `app/core/config.py`
- `app/main.py`

### Task 4: Add Instantly config and a thin V2 client

**Files:**
- Create: `app/integrations/instantly/config.py`
- Create: `app/integrations/instantly/client.py`
- Create: `app/integrations/instantly/schemas.py`
- Create: `tests/integrations/instantly/test_client.py`

- [ ] **Step 1: Write the failing tests**

```python
import httpx

from app.integrations.instantly.client import InstantlyClient


def test_create_lead_list_posts_bearer_token_and_returns_id() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "list-123", "name": "Probate - Harris"})

    client = InstantlyClient(
        api_key="instantly-test-key",
        base_url="https://api.instantly.ai",
        transport=httpx.MockTransport(handler),
    )

    result = client.create_lead_list(name="Probate - Harris")
    assert result.id == "list-123"
    assert requests[0].headers["Authorization"] == "Bearer instantly-test-key"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/integrations/instantly/test_client.py -q
```

Expected: fail because the Instantly client module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create a thin HTTP client with `httpx` and V2-only methods:

```python
class InstantlyClient:
    def create_lead_list(self, name: str, has_enrichment_task: bool = False) -> LeadListResponse: ...
    def list_lead_lists(self) -> list[LeadListResponse]: ...
    def add_leads_to_list(self, list_id: str, leads: list[LeadPayload]) -> BulkLeadResponse: ...
    def create_webhook(self, url: str, event_types: list[str]) -> WebhookResponse: ...
    def list_webhooks(self) -> list[WebhookResponse]: ...
```

The client should:

- use `Authorization: Bearer <token>`
- retry 429s once or twice with a short backoff
- raise a clear error on 4xx/5xx responses
- keep payload schemas in Pydantic models so the lead mapping stays testable

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/integrations/instantly/test_client.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/integrations/instantly/config.py app/integrations/instantly/client.py app/integrations/instantly/schemas.py tests/integrations/instantly/test_client.py app/core/config.py
git commit -m "feat: add instantly v2 client"
```

### Task 5: Map enriched probate leads into Instantly lead uploads

**Files:**
- Create: `app/domains/probate/publish.py`
- Create: `tests/domains/probate/test_publish.py`
- Modify: `app/api/marketing.py` or `app/api/probate.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.domains.probate.models import ProbateLead, ProbateLeadSource
from app.domains.probate.publish import build_instantly_lead_payloads


def test_build_instantly_lead_payloads_maps_email_and_custom_vars() -> None:
    lead = ProbateLead(
        county="harris",
        property_address="123 main st houston tx",
        owner_name="Estate of Jane Doe",
        source=ProbateLeadSource.CSV_EXPORT,
        source_id="case-001",
        email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
        phone="+15551234567",
    )

    payload = build_instantly_lead_payloads(list_id="list-123", leads=[lead])[0]
    assert payload.email == "jane@example.com"
    assert payload.list_id == "list-123"
    assert payload.custom_variables["county"] == "harris"
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/domains/probate/test_publish.py -q
```

Expected: fail because the publish module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Build a mapper that sends the required Instantly fields:

- `email`
- `first_name`
- `last_name`
- `phone`
- `list_id`
- `custom_variables` with probate-specific data
- `verify_leads_on_import=true` when the operator wants Instantly to validate imports

For the first pass, use a lead list as the primary destination. Campaign attachment can stay manual until the pipeline proves itself.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/domains/probate/test_publish.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/domains/probate/publish.py tests/domains/probate/test_publish.py app/api/marketing.py app/api/probate.py
git commit -m "feat: map probate leads into instantly payloads"
```

---

## Phase 4: Webhooks, Outcomes, and Suppression

**What it is:**
Capture replies, bounces, unsubscribes, and interest changes from Instantly and write them back into the runtime.

**Files to create:**

- `app/api/webhooks.py`
- `app/domains/probate/outcomes.py`
- `tests/api/test_webhooks_instantly.py`
- `tests/domains/probate/test_outcomes.py`

**Files to modify:**

- `app/main.py`
- `app/domains/probate/repository.py`
- `app/services/mission_control_service.py`

### Task 6: Add webhook ingestion and lead outcome sync

**Files:**
- Create: `app/api/webhooks.py`
- Create: `app/domains/probate/outcomes.py`
- Create: `tests/api/test_webhooks_instantly.py`
- Create: `tests/domains/probate/test_outcomes.py`

- [ ] **Step 1: Write the failing tests**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.webhooks import router as webhooks_router


def test_instantly_webhook_marks_lead_replied() -> None:
    app = FastAPI()
    app.include_router(webhooks_router)
    client = TestClient(app)

    response = client.post(
        "/webhooks/instantly/test-secret",
        json={"event_type": "lead_replied", "email": "jane@example.com"},
    )

    assert response.status_code == 200
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/api/test_webhooks_instantly.py tests/domains/probate/test_outcomes.py -q
```

Expected: fail because the webhook receiver does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create a webhook route that accepts Instantly event payloads and updates the internal lead status store.

Concrete first-pass approach:

- protect the endpoint with a shared secret path segment or header from our runtime config
- parse `lead_replied`, `lead_bounced`, `lead_unsubscribed`, and `interest_status_changed`
- update the lead record and mark suppression where needed
- surface the event in Mission Control so the operator can see it

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/api/test_webhooks_instantly.py tests/domains/probate/test_outcomes.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/webhooks.py app/domains/probate/outcomes.py tests/api/test_webhooks_instantly.py tests/domains/probate/test_outcomes.py app/main.py
git commit -m "feat: add instantly webhook outcomes"
```

---

## Phase 5: Control Plane Wiring and Mission Control Preview

**What it is:**
Expose the probate pipeline through the existing runtime patterns so the operator can approve, run, and monitor batches from the cockpit.

**Files to create:**

- `app/domains/probate/commands.py`
- `app/api/probate.py` if not already created
- `tests/api/test_probate_runtime.py`

**Files to modify:**

- `app/services/command_service.py`
- `app/domains/marketing/commands.py` if we keep the current registry shape
- `app/services/mission_control_service.py`
- `app/api/mission_control.py`
- `app/main.py`
- `tests/api/test_commands.py`
- `tests/api/test_mission_control_phase3.py`

### Task 7: Wire the probate pipeline into the runtime control plane

**Files:**
- Create: `app/domains/probate/commands.py`
- Modify: `app/services/command_service.py`
- Modify: `app/api/mission_control.py`
- Create: `tests/api/test_probate_runtime.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.domains.probate.commands import ProbateCommandType
from app.models.commands import CommandPolicy
from app.services.command_service import command_service


def test_probate_ingest_command_is_supported() -> None:
    assert "ingest_probate_csv" in ProbateCommandType.__args__
    assert command_service.classify("ingest_probate_csv") != CommandPolicy.FORBIDDEN
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/api/test_probate_runtime.py tests/api/test_mission_control_phase3.py -q
```

Expected: fail because probate commands and the runtime wiring do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Add probate command types for:

- `ingest_probate_csv`
- `clean_probate_batch`
- `enrich_probate_batch`
- `create_instantly_lead_list`
- `push_probate_batch_to_instantly`
- `sync_instantly_webhook`

Keep the first two commands safe/autonomous if they only transform local data. Keep the push command approval-required until you trust the data and the contact hygiene.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/api/test_probate_runtime.py tests/api/test_mission_control_phase3.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/domains/probate/commands.py app/services/command_service.py app/api/mission_control.py tests/api/test_probate_runtime.py
git commit -m "feat: wire probate pipeline into runtime control plane"
```

---

## Phase 6: Docs, Operator Flow, and Tonight’s Launch Path

**What it is:**
Make the pipeline understandable to the next human and usable tonight.

**Files to modify:**

- `README.md`
- `CONTEXT.md`
- `memory.md`
- `docs/superpowers/plans/2026-04-18-ares-phased-implementation-plan.md` if needed for cross-linking

### Task 8: Update repo docs with the actual launch path

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`

- [ ] **Step 1: Write the docs update**

Add the blunt reality:

- there is no probate-to-Instantly backend yet
- the first working slice is CSV ingest → clean → enrich → upload to Instantly lead list → webhook sync
- if there is no email enrichment, the batch stops before Instantly
- the current marketing scaffold is not the real pipeline

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
uv run pytest tests/domains/probate tests/integrations/instantly tests/api/test_webhooks_instantly.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md CONTEXT.md memory.md
git commit -m "docs: align ares probate instantly launch path"
```

**Exit criteria for the whole plan:**

- A probate CSV can be ingested and cleaned
- the batch can be enriched with emails
- Instantly V2 can receive a lead list and bulk leads
- webhook outcomes update the runtime
- Mission Control can show the batch state
- the operator can launch a real campaign without hand-wiring the world

---

## What Stays Out of Scope for This Plan

- full county scraping for every Texas county
- tax-delinquent overlay logic
- autonomous outbound sends without review
- escrow, contracts, dispo, buyer matching
- a database migration
- a full planner/autonomy loop

Those belong in the broader Ares roadmap, not in the first probate-to-Instantly lane.

---

## Bottom Line

If you want to run a probate campaign tonight, this is the real path:

1. get a probate CSV
2. clean it
3. enrich it with emails
4. create an Instantly lead list
5. push the batch
6. verify the webhook loop
7. show it in Mission Control

Everything else is a later problem. Fun, but later.