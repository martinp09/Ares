from __future__ import annotations

import re
from typing import Any, Iterable, Mapping

from app.models.probate_leads import ProbateContactConfidence, ProbateHCADMatchStatus, ProbateLeadRecord


class ProbateHCADMatchService:
    def match_lead(self, lead: ProbateLeadRecord | Mapping[str, Any], hcad_rows: Iterable[Mapping[str, Any]]) -> ProbateLeadRecord:
        record = lead if isinstance(lead, ProbateLeadRecord) else ProbateLeadRecord.model_validate(lead)
        ranked_candidates = sorted(
            (_candidate_rank(record, candidate) for candidate in hcad_rows),
            key=lambda ranked: (-ranked[0], ranked[1].get("account", ranked[1].get("acct", ""))),
        )
        ranked_candidates = [ranked for ranked in ranked_candidates if ranked[0] > 0]
        if not ranked_candidates:
            return record.model_copy(
                update={
                    "hcad_match_status": ProbateHCADMatchStatus.UNMATCHED,
                    "matched_candidate_count": 0,
                    "contact_confidence": ProbateContactConfidence.NONE,
                }
            )

        top_score = ranked_candidates[0][0]
        top_candidates = [candidate for score, candidate in ranked_candidates if score == top_score]
        if len(top_candidates) > 1:
            return record.model_copy(
                update={
                    "hcad_match_status": ProbateHCADMatchStatus.MULTIPLE,
                    "matched_candidate_count": len(top_candidates),
                    "contact_confidence": ProbateContactConfidence.LOW,
                }
            )

        candidate = top_candidates[0]
        property_address = _normalize_text(candidate.get("property_address") or candidate.get("site_address") or candidate.get("situs_address"))
        mailing_address = _normalize_text(candidate.get("mailing_address") or candidate.get("mail_to"))
        return record.model_copy(
            update={
                "hcad_match_status": ProbateHCADMatchStatus.MATCHED,
                "hcad_acct": _trim_hcad_account(candidate.get("account") or candidate.get("acct")),
                "owner_name": _normalize_text(candidate.get("owner_name") or candidate.get("owner")),
                "mailing_address": record.mailing_address or mailing_address,
                "property_address": record.property_address or property_address,
                "matched_candidate_count": 1,
                "contact_confidence": _confidence_for_score(top_score),
            }
        )


def _candidate_rank(record: ProbateLeadRecord, candidate: Mapping[str, Any]) -> tuple[int, Mapping[str, Any]]:
    owner_name = _normalize_person_name(candidate.get("owner_name") or candidate.get("owner"))
    property_address = _normalize_address(candidate.get("property_address") or candidate.get("site_address") or candidate.get("situs_address"))
    mailing_address = _normalize_address(candidate.get("mailing_address") or candidate.get("mail_to"))

    lead_name_variants = {
        value
        for value in {
            _normalize_person_name(record.decedent_name),
            _normalize_person_name(record.estate_name),
        }
        if value
    }
    score = 0
    if owner_name and owner_name in lead_name_variants:
        score += 3
    if property_address and property_address == _normalize_address(record.property_address):
        score += 3
    if mailing_address and mailing_address == _normalize_address(record.mailing_address):
        score += 2
    return score, candidate


_word_pattern = re.compile(r"[A-Z0-9]+")
_whitespace_pattern = re.compile(r"\s+")
_name_noise_pattern = re.compile(r"\b(ESTATE|DECEASED|OF|THE)\b")
_address_noise_pattern = re.compile(r"[^A-Z0-9 ]+")


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = _whitespace_pattern.sub(" ", str(value).strip())
    if not text:
        return None
    return text


def _normalize_person_name(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    text = _name_noise_pattern.sub(" ", text.upper())
    tokens = sorted(_word_pattern.findall(text))
    if not tokens:
        return None
    return " ".join(tokens)


def _normalize_address(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    text = _address_noise_pattern.sub(" ", text.upper())
    tokens = _whitespace_pattern.sub(" ", text).strip().split(" ")
    if not tokens:
        return None
    return " ".join(tokens)


def _trim_hcad_account(value: Any) -> str | None:
    text = _normalize_text(value)
    if not text:
        return None
    trimmed = text.lstrip("0")
    return trimmed or "0"


def _confidence_for_score(score: int) -> ProbateContactConfidence:
    if score >= 6:
        return ProbateContactConfidence.HIGH
    if score >= 3:
        return ProbateContactConfidence.MEDIUM
    return ProbateContactConfidence.LOW
