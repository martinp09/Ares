from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProbateLeadSource(StrEnum):
    HARRIS_COUNTY_PROBATE = "harris_county_probate"


class ProbateHCADMatchStatus(StrEnum):
    UNMATCHED = "unmatched"
    MATCHED = "matched"
    MULTIPLE = "multiple"


class ProbateContactConfidence(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ProbateLeadRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_number: str = Field(min_length=1)
    file_date: date | None = None
    court_number: str | None = None
    status: str | None = None
    filing_type: str = Field(min_length=1)
    filing_subtype: str | None = None
    estate_name: str | None = None
    decedent_name: str | None = None
    source: ProbateLeadSource = ProbateLeadSource.HARRIS_COUNTY_PROBATE
    keep_now: bool = False
    hcad_match_status: ProbateHCADMatchStatus = ProbateHCADMatchStatus.UNMATCHED
    hcad_acct: str | None = None
    owner_name: str | None = None
    mailing_address: str | None = None
    property_address: str | None = None
    contact_confidence: ProbateContactConfidence = ProbateContactConfidence.NONE
    lead_score: float | None = None
    outreach_status: str | None = None
    matched_candidate_count: int = Field(default=0, ge=0)
    last_seen_at: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    def identity_key(self) -> str:
        return f"{self.source}:{self.case_number.strip().casefold()}"
