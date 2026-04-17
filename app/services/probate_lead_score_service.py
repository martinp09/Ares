from __future__ import annotations

from typing import Any, Mapping

from app.models.probate_leads import ProbateContactConfidence, ProbateHCADMatchStatus, ProbateLeadRecord


_BASE_FILING_TYPE_SCORES = {
    "PROBATE OF WILL (INDEPENDENT ADMINISTRATION)": 68,
    "INDEPENDENT ADMINISTRATION": 60,
    "APP FOR INDEPENDENT ADMINISTRATION WITH WILL ANNEXED": 60,
    "APP FOR INDEPENDENT ADMINISTRATION WITH AN HEIRSHIP": 64,
    "APP TO DETERMINE HEIRSHIP": 64,
}


class ProbateLeadScoreService:
    def score(self, lead: ProbateLeadRecord | Mapping[str, Any]) -> float:
        record = lead if isinstance(lead, ProbateLeadRecord) else ProbateLeadRecord.model_validate(lead)
        score = _BASE_FILING_TYPE_SCORES.get(record.filing_type, 35)
        score += 12 if record.keep_now else -25

        pain_stack = record.pain_stack if isinstance(record.pain_stack, dict) else {}
        tax_delinquent = bool(record.tax_delinquent or pain_stack.get("tax_delinquent"))
        estate_of = bool(record.estate_of or pain_stack.get("estate_of"))
        if tax_delinquent:
            score += 8
        if estate_of:
            score += 6
        if tax_delinquent and estate_of:
            score += 4

        if record.hcad_match_status == ProbateHCADMatchStatus.MATCHED:
            score += 14
        elif record.hcad_match_status == ProbateHCADMatchStatus.MULTIPLE:
            score -= 10
        else:
            score -= 18
        if record.contact_confidence == ProbateContactConfidence.HIGH:
            score += 10
        elif record.contact_confidence == ProbateContactConfidence.MEDIUM:
            score += 5
        elif record.contact_confidence == ProbateContactConfidence.NONE:
            score -= 6
        if record.mailing_address:
            score += 6
        else:
            score -= 10
        if record.property_address:
            score += 4
        if record.matched_candidate_count > 1:
            score -= 6
        if not record.decedent_name and record.estate_name:
            score -= 5
        return float(max(0, min(100, score)))

    def score_lead(self, lead: ProbateLeadRecord | Mapping[str, Any]) -> ProbateLeadRecord:
        record = lead if isinstance(lead, ProbateLeadRecord) else ProbateLeadRecord.model_validate(lead)
        return record.model_copy(update={"lead_score": self.score(record)})


def score_probate_lead(lead: ProbateLeadRecord | Mapping[str, Any]) -> float:
    return ProbateLeadScoreService().score(lead)
