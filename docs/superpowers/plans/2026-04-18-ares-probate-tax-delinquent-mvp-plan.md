# Ares Probate + Tax Delinquent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first useful Ares slice: probate-first lead sourcing across five Texas counties, tax-delinquent overlays, a separate tax-delinquent `estate of` lane, ranked lead briefs, and outreach drafts for human approval.

**Architecture:** Keep Ares as a small domain pipeline with four clean boundaries: source ingest, matching/overlay, ranking, and copy generation. The core logic should be pure and deterministic so it can run against stubbed source gateways in tests now and county connectors later without changing the business rules. The API should only orchestrate and serialize; it should not own matching or scoring logic.

**Tech Stack:** Python 3.13, FastAPI, Pydantic, pytest, uv.

---

## Working Rules

- Keep Ares isolated from Mission Control and the marketing runtime; no cross-feature borrowing unless a shared helper is truly generic.
- TDD first: write the failing test, watch it fail, then implement the smallest thing that makes it pass.
- Keep data models small and explicit; do not hide business logic in routers.
- Do not add auto-send, escrow, dispo, or buyer-matching behavior in this slice.
- Commit after each task once its tests pass.
- If a task spans Python and API wiring, verify both sides before moving on.

## File Map

### New files

- `app/models/ares.py` — Ares enums, lead records, ranking response models, and request/response contracts.
- `app/services/ares_service.py` — source-gateway interface, probate/tax overlay matching, tiering, and run orchestration.
- `app/services/ares_copy_service.py` — lead brief and outreach draft generation.
- `app/api/ares.py` — FastAPI router for the Ares run endpoint.
- `tests/domains/ares/test_models.py` — model and enum behavior.
- `tests/services/test_ares_service.py` — overlay, ranking, and orchestration logic.
- `tests/services/test_ares_copy_service.py` — lead brief and draft generation.
- `tests/api/test_ares_runtime.py` — end-to-end API contract.

### Existing files to modify

- `app/main.py` — mount the new Ares router.
- `tests/test_package_layout.py` — keep the importability guard current.
- `README.md` — document the new Ares route in the runtime surface.
- `CONTEXT.md` — update the live repo TODO to mention the Ares MVP slice.
- `memory.md` — capture the stable Ares lead-source rule so it is not lost.

---

### Task 1: Lock the Ares domain models and county/source contracts

**Files:**
- Create: `app/models/ares.py`
- Create: `tests/domains/ares/test_models.py`
- Modify: `tests/test_package_layout.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.models.ares import AresCounty, AresLeadRecord, AresRunRequest, AresSourceLane


def test_counties_cover_the_five_target_markets() -> None:
    assert [county.value for county in AresCounty] == [
        "harris",
        "tarrant",
        "montgomery",
        "dallas",
        "travis",
    ]


def test_run_request_coerces_counties_and_defaults_to_briefs_and_drafts() -> None:
    request = AresRunRequest(counties=["harris", "travis"])
    assert request.counties == [AresCounty.HARRIS, AresCounty.TRAVIS]
    assert request.include_briefs is True
    assert request.include_drafts is True


def test_estate_of_detection_is_explicit_on_the_record() -> None:
    lead = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
    )
    assert lead.estate_of is True
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/domains/ares/test_models.py tests/test_package_layout.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'app.models.ares'` until the new model module exists.

- [ ] **Step 3: Write the minimal implementation**

Create the Ares enums and request/record models in `app/models/ares.py`.
Keep the model set small and explicit:

```python
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AresCounty(StrEnum):
    HARRIS = "harris"
    TARRANT = "tarrant"
    MONTGOMERY = "montgomery"
    DALLAS = "dallas"
    TRAVIS = "travis"


class AresSourceLane(StrEnum):
    PROBATE = "probate"
    TAX_DELINQUENT_ESTATE_OF = "tax_delinquent_estate_of"


class AresLeadTier(StrEnum):
    TIER_A = "tier_a"
    TIER_B = "tier_b"
    TIER_C = "tier_c"


class AresLeadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    county: AresCounty
    source_lane: AresSourceLane
    property_address: str = Field(min_length=1)
    owner_name: str | None = None
    estate_of: bool = False
    tax_delinquent: bool = False
    tax_amount_due: int | None = None
    source_id: str | None = None
    notes: list[str] = Field(default_factory=list)
    confidence: float = 1.0

    @model_validator(mode="after")
    def infer_estate_of(self) -> "AresLeadRecord":
        if self.owner_name and "estate of" in self.owner_name.lower():
            self.estate_of = True
        return self


class AresRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counties: list[AresCounty] = Field(min_length=1)
    include_briefs: bool = True
    include_drafts: bool = True


class AresRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counties: list[AresCounty]
    lead_count: int
    leads: list[dict[str, Any]] = Field(default_factory=list)
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/domains/ares/test_models.py tests/test_package_layout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/models/ares.py tests/domains/ares/test_models.py tests/test_package_layout.py
git commit -m "feat: add ares lead models and county enums"
```

---

### Task 2: Implement probate-first matching, tax overlays, and tiering

**Files:**
- Create: `app/services/ares_service.py`
- Create: `tests/services/test_ares_service.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.models.ares import AresCounty, AresLeadRecord, AresLeadTier, AresSourceLane
from app.services.ares_service import overlay_tax_delinquency, rank_ares_leads


def test_tax_overlay_marks_probate_leads_when_county_and_address_match() -> None:
    probate = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
    )
    tax = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.TAX_DELINQUENT_ESTATE_OF,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
        tax_delinquent=True,
        tax_amount_due=7123,
    )

    merged = overlay_tax_delinquency([probate], [tax])
    assert merged[0].tax_delinquent is True
    assert merged[0].tax_amount_due == 7123
    assert merged[0].estate_of is True


def test_rank_ares_leads_prioritizes_overlap_then_probate_then_tax_estate() -> None:
    probate_overlap = AresLeadRecord(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
        tax_delinquent=True,
        tax_amount_due=7123,
        estate_of=True,
    )
    probate_only = AresLeadRecord(
        county=AresCounty.DALLAS,
        source_lane=AresSourceLane.PROBATE,
        property_address="44 Elm St, Dallas, TX",
        owner_name="Estate of John Smith",
    )
    tax_estate = AresLeadRecord(
        county=AresCounty.TRAVIS,
        source_lane=AresSourceLane.TAX_DELINQUENT_ESTATE_OF,
        property_address="88 River Rd, Austin, TX",
        owner_name="Estate of Maria Lopez",
        tax_delinquent=True,
        tax_amount_due=4888,
        estate_of=True,
    )

    ranked = rank_ares_leads([probate_only, tax_estate, probate_overlap])
    assert [item.tier for item in ranked] == [AresLeadTier.TIER_A, AresLeadTier.TIER_B, AresLeadTier.TIER_C]
    assert ranked[0].reasons == ["probate source", "verified tax delinquent"]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/services/test_ares_service.py -q
```

Expected: fail because the matching and ranking functions do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Implement a small deterministic matcher and scorer in `app/services/ares_service.py`.
Use exact county + normalized address as the first match key, then prefer stronger owner-name agreement when present.
Keep the rules blunt:

```python
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Protocol

from app.models.ares import AresCounty, AresLeadRecord, AresLeadTier, AresRunRequest, AresRunResponse, AresSourceLane


def normalize_text(value: str) -> str:
    return " ".join(value.lower().replace(",", " ").split())


def is_estate_of(owner_name: str | None) -> bool:
    return bool(owner_name and "estate of" in owner_name.lower())


def build_match_key(lead: AresLeadRecord) -> tuple[AresCounty, str]:
    return lead.county, normalize_text(lead.property_address)


class AresSourceGateway(Protocol):
    def fetch_probate(self, county: AresCounty) -> list[AresLeadRecord]:
        ...

    def fetch_tax_delinquent(self, county: AresCounty) -> list[AresLeadRecord]:
        ...


@dataclass(slots=True)
class StaticAresSourceGateway:
    probate_by_county: dict[AresCounty, list[AresLeadRecord]]
    tax_by_county: dict[AresCounty, list[AresLeadRecord]]

    def fetch_probate(self, county: AresCounty) -> list[AresLeadRecord]:
        return list(self.probate_by_county.get(county, []))

    def fetch_tax_delinquent(self, county: AresCounty) -> list[AresLeadRecord]:
        return list(self.tax_by_county.get(county, []))


def overlay_tax_delinquency(
    probate_leads: Sequence[AresLeadRecord],
    tax_leads: Sequence[AresLeadRecord],
) -> list[AresLeadRecord]:
    tax_index: dict[tuple[AresCounty, str], AresLeadRecord] = {
        build_match_key(lead): lead for lead in tax_leads if lead.tax_delinquent
    }
    merged: list[AresLeadRecord] = []
    for lead in probate_leads:
        tax_hit = tax_index.get(build_match_key(lead))
        if tax_hit is None:
            merged.append(lead)
            continue
        merged.append(
            lead.model_copy(
                update={
                    "tax_delinquent": True,
                    "tax_amount_due": tax_hit.tax_amount_due,
                    "estate_of": lead.estate_of or tax_hit.estate_of or is_estate_of(lead.owner_name) or is_estate_of(tax_hit.owner_name),
                    "notes": lead.notes + ["tax overlay matched"],
                }
            )
        )
    return merged


class RankedAresLead(AresLeadRecord):
    tier: AresLeadTier
    score: int
    reasons: list[str]


def tier_and_score(lead: AresLeadRecord) -> tuple[AresLeadTier, int, list[str]]:
    if lead.source_lane == AresSourceLane.PROBATE and lead.tax_delinquent:
        return AresLeadTier.TIER_A, 100, ["probate source", "verified tax delinquent"]
    if lead.source_lane == AresSourceLane.PROBATE:
        return AresLeadTier.TIER_B, 70, ["probate source"]
    return AresLeadTier.TIER_C, 40, ["tax delinquent estate-of lane"]


def rank_ares_leads(leads: Sequence[AresLeadRecord]) -> list[RankedAresLead]:
    ranked: list[RankedAresLead] = []
    for lead in leads:
        tier, score, reasons = tier_and_score(lead)
        ranked.append(RankedAresLead.model_validate(lead.model_dump() | {"tier": tier, "score": score, "reasons": reasons}))
    return sorted(ranked, key=lambda item: (-item.score, item.county.value, normalize_text(item.property_address)))


def run_ares_pipeline(request: AresRunRequest, gateway: AresSourceGateway) -> AresRunResponse:
    probate_leads: list[AresLeadRecord] = []
    tax_leads: list[AresLeadRecord] = []
    for county in request.counties:
        probate_leads.extend(gateway.fetch_probate(county))
        tax_leads.extend(gateway.fetch_tax_delinquent(county))

    overlapped = overlay_tax_delinquency(probate_leads, tax_leads)
    overlap_keys = {build_match_key(lead) for lead in overlapped}
    tax_only_estate_of = [
        lead
        for lead in tax_leads
        if lead.tax_delinquent
        and lead.estate_of
        and lead.source_lane == AresSourceLane.TAX_DELINQUENT_ESTATE_OF
        and build_match_key(lead) not in overlap_keys
    ]
    ranked = rank_ares_leads(overlapped + tax_only_estate_of)

    from app.services.ares_copy_service import build_lead_brief, build_outreach_drafts

    leads: list[dict[str, object]] = []
    for lead in ranked:
        payload = lead.model_dump()
        if request.include_briefs:
            payload["brief"] = build_lead_brief(lead).__dict__
        if request.include_drafts:
            payload["drafts"] = [draft.__dict__ for draft in build_outreach_drafts(lead)]
        leads.append(payload)

    return AresRunResponse(
        counties=request.counties,
        lead_count=len(ranked),
        leads=leads,
    )
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/services/test_ares_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/ares_service.py tests/services/test_ares_service.py
git commit -m "feat: rank probate and tax delinquent ares leads"
```

---

### Task 3: Add lead briefs and outreach drafts

**Files:**
- Create: `app/services/ares_copy_service.py`
- Create: `tests/services/test_ares_copy_service.py`
- Modify: `app/services/ares_service.py` if the ranking model needs to expose brief/draft hooks

- [ ] **Step 1: Write the failing tests**

```python
from app.models.ares import AresCounty, AresLeadRecord, AresSourceLane
from app.services.ares_copy_service import build_lead_brief, build_outreach_drafts
from app.services.ares_service import RankedAresLead


def test_tier_a_brief_names_the_overlap_and_the_county() -> None:
    ranked = RankedAresLead(
        county=AresCounty.HARRIS,
        source_lane=AresSourceLane.PROBATE,
        property_address="123 Main St, Houston, TX",
        owner_name="Estate of Jane Doe",
        estate_of=True,
        tax_delinquent=True,
        tax_amount_due=7123,
        source_id="probate-001",
        notes=["tax overlay matched"],
        confidence=1.0,
        tier="tier_a",
        score=100,
        reasons=["probate source", "verified tax delinquent"],
    )

    brief = build_lead_brief(ranked)
    assert brief.headline == "Tier A: probate + tax delinquent"
    assert "Harris County" in brief.summary
    assert brief.outreach_angle == "inheritance and property pressure"


def test_outreach_drafts_cover_sms_email_voicemail_and_direct_mail() -> None:
    ranked = RankedAresLead(
        county=AresCounty.DALLAS,
        source_lane=AresSourceLane.PROBATE,
        property_address="44 Elm St, Dallas, TX",
        owner_name="Estate of John Smith",
        estate_of=False,
        tax_delinquent=False,
        source_id="probate-002",
        notes=[],
        confidence=1.0,
        tier="tier_b",
        score=70,
        reasons=["probate source"],
    )

    drafts = build_outreach_drafts(ranked)
    assert [draft.channel for draft in drafts] == ["sms", "email", "voicemail", "direct_mail"]
    assert drafts[0].body.startswith("Hi")
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/services/test_ares_copy_service.py -q
```

Expected: fail because the copy-generation module does not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Keep the copy generator deterministic and template-based. No LLM call yet.

```python
from __future__ import annotations

from dataclasses import dataclass

from app.models.ares import AresLeadTier
from app.services.ares_service import RankedAresLead


@dataclass(slots=True)
class AresLeadBrief:
    headline: str
    summary: str
    outreach_angle: str
    next_action: str


@dataclass(slots=True)
class AresOutreachDraft:
    channel: str
    subject: str
    body: str


def build_lead_brief(ranked: RankedAresLead) -> AresLeadBrief:
    county_label = f"{ranked.county.value.title()} County"
    if ranked.tier == AresLeadTier.TIER_A:
        return AresLeadBrief(
            headline="Tier A: probate + tax delinquent",
            summary=f"{county_label} lead at {ranked.property_address} is a probate record that also verifies as tax delinquent.",
            outreach_angle="inheritance and property pressure",
            next_action="review and draft outreach for human approval",
        )
    if ranked.tier == AresLeadTier.TIER_B:
        return AresLeadBrief(
            headline="Tier B: probate only",
            summary=f"{county_label} probate lead at {ranked.property_address} with no tax overlap yet.",
            outreach_angle="inheritance and clean-up pressure",
            next_action="review and draft outreach for human approval",
        )
    return AresLeadBrief(
        headline="Tier C: tax delinquent estate-of",
        summary=f"{county_label} tax-delinquent estate-of lead at {ranked.property_address}.",
        outreach_angle="estate resolution and back-tax pressure",
        next_action="review and draft outreach for human approval",
    )


def build_outreach_drafts(ranked: RankedAresLead) -> list[AresOutreachDraft]:
    brief = build_lead_brief(ranked)
    address = ranked.property_address
    county_label = f"{ranked.county.value.title()} County"
    return [
        AresOutreachDraft(
            channel="sms",
            subject="",
            body=f"Hi, I’m reaching out about {address} in {county_label}. We work with probate and inherited-property situations and wanted to see if you’d be open to a simple as-is conversation.",
        ),
        AresOutreachDraft(
            channel="email",
            subject=f"Quick question about {address}",
            body=f"{brief.summary}\n\nIf you are the right contact, we can keep this simple and discuss an as-is path that reduces friction.",
        ),
        AresOutreachDraft(
            channel="voicemail",
            subject="",
            body=f"Hi, this is Ares. I’m calling about {address} in {county_label}. We help with probate and inherited-property situations. If this is relevant, please call back and we can keep it simple.",
        ),
        AresOutreachDraft(
            channel="direct_mail",
            subject="",
            body=f"We noticed a probate / estate-related situation tied to {address} in {county_label}. If you are open to a simple as-is conversation, we can help reduce the back-and-forth.",
        ),
    ]
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/services/test_ares_copy_service.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/services/ares_copy_service.py tests/services/test_ares_copy_service.py app/services/ares_service.py
git commit -m "feat: generate ares lead briefs and outreach drafts"
```

---

### Task 4: Add the Ares API route and wire it into the app

**Files:**
- Create: `app/api/ares.py`
- Modify: `app/main.py`
- Create: `tests/api/test_ares_runtime.py`
- Modify: `tests/test_package_layout.py`

- [ ] **Step 1: Write the failing tests**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.ares import get_ares_source_gateway, router as ares_router
from app.models.ares import AresCounty, AresLeadRecord, AresSourceLane
from app.services.ares_service import StaticAresSourceGateway

AUTH_HEADERS = {"Authorization": "Bearer dev-runtime-key"}


def build_client(gateway: StaticAresSourceGateway) -> TestClient:
    app = FastAPI()
    app.include_router(ares_router)
    app.dependency_overrides[get_ares_source_gateway] = lambda: gateway
    return TestClient(app)


def test_ares_run_returns_ranked_leads_and_drafts() -> None:
    gateway = StaticAresSourceGateway(
        probate_by_county={
            AresCounty.HARRIS: [
                AresLeadRecord(
                    county=AresCounty.HARRIS,
                    source_lane=AresSourceLane.PROBATE,
                    property_address="123 Main St, Houston, TX",
                    owner_name="Estate of Jane Doe",
                )
            ],
            AresCounty.TRAVIS: [
                AresLeadRecord(
                    county=AresCounty.TRAVIS,
                    source_lane=AresSourceLane.PROBATE,
                    property_address="88 River Rd, Austin, TX",
                    owner_name="Estate of Maria Lopez",
                )
            ],
        },
        tax_by_county={
            AresCounty.HARRIS: [
                AresLeadRecord(
                    county=AresCounty.HARRIS,
                    source_lane=AresSourceLane.TAX_DELINQUENT_ESTATE_OF,
                    property_address="123 Main St, Houston, TX",
                    owner_name="Estate of Jane Doe",
                    tax_delinquent=True,
                    tax_amount_due=7123,
                )
            ],
            AresCounty.TRAVIS: [],
        },
    )
    client = build_client(gateway)

    response = client.post(
        "/ares/run",
        json={"counties": ["harris", "travis"]},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counties"] == ["harris", "travis"]
    assert body["lead_count"] == 2
    assert body["leads"][0]["tier"] == "tier_a"
    assert body["leads"][0]["brief"]["headline"] == "Tier A: probate + tax delinquent"
    assert body["leads"][0]["drafts"][0]["channel"] == "sms"
```

```python
def test_package_layout_includes_ares_modules() -> None:
    from app.api.ares import router as ares_router
    from app.models.ares import AresRunRequest
    from app.services.ares_service import run_ares_pipeline

    assert ares_router is not None
    assert AresRunRequest is not None
    assert callable(run_ares_pipeline)
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
uv run pytest tests/api/test_ares_runtime.py tests/test_package_layout.py -q
```

Expected: fail because the router, dependency, and Ares API wiring do not exist yet.

- [ ] **Step 3: Write the minimal implementation**

Create `app/api/ares.py` as a thin router. It should accept a county list, pull records from the gateway dependency, run the Ares pipeline, and return the ranked response.

```python
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.models.ares import AresRunRequest, AresRunResponse
from app.services.ares_service import AresSourceGateway, StaticAresSourceGateway, run_ares_pipeline

router = APIRouter(prefix="/ares", tags=["ares"])


def get_ares_source_gateway() -> AresSourceGateway:
    return StaticAresSourceGateway(probate_by_county={}, tax_by_county={})


@router.post("/run", response_model=AresRunResponse)
def run_ares(
    request: AresRunRequest,
    gateway: AresSourceGateway = Depends(get_ares_source_gateway),
) -> AresRunResponse:
    return run_ares_pipeline(request, gateway)
```

Then mount the router in `app/main.py` alongside the existing routers.

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
uv run pytest tests/api/test_ares_runtime.py tests/test_package_layout.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/ares.py app/main.py tests/api/test_ares_runtime.py tests/test_package_layout.py
git commit -m "feat: add ares api runtime"
```

---

### Task 5: Update repo handoff docs and verify the full slice

**Files:**
- Modify: `README.md`
- Modify: `CONTEXT.md`
- Modify: `memory.md`

- [ ] **Step 1: Update the repo-facing docs**

Add the new Ares runtime surface to `README.md`, and update `CONTEXT.md` / `memory.md` so the next session knows the current Ares MVP rule is probate-first with a tax overlay, not a blended source soup.

Keep the wording short and operational. The docs should say:

- Ares is the real-estate lead machine slice.
- Probate is the primary lane.
- Tax delinquency is an overlay on probate.
- Tax-only work should focus on `estate of` properties.
- Outreach drafts are generated but not auto-sent.

- [ ] **Step 2: Run the full verification suite**

Run:

```bash
uv run pytest -q
```

Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add README.md CONTEXT.md memory.md
git commit -m "docs: align runtime notes with ares mvp slice"
```

---

## Self-Review Checklist

Before handing this to an engineer, verify:

1. Every spec requirement has a matching task.
2. No task says "TBD", "TODO", or "implement later".
3. The county list is fixed to the five Texas counties the user named.
4. Probate is the primary lane, tax delinquency is the overlay, and tax-only work is filtered to `estate of` properties.
5. The API does not auto-send anything.
6. The plan keeps the domain logic testable without live county integrations.
7. The file paths are exact and match the existing repo layout.
