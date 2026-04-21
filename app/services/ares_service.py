from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import re
from typing import Iterable

from app.domains.ares import AresLeadRecord, AresSourceLane


_ADDRESS_WHITESPACE_PATTERN = re.compile(r"\s+")


class AresLeadTier(IntEnum):
    PROBATE_WITH_VERIFIED_TAX = 1
    PROBATE_ONLY = 2
    TAX_ONLY_ESTATE_VERIFIED = 3


@dataclass(frozen=True)
class RankedAresLead:
    lead: AresLeadRecord
    tier: AresLeadTier
    rank: int
    tax_delinquent: bool


class AresMatchingService:
    def rank_leads(
        self,
        *,
        probate_records: Iterable[AresLeadRecord],
        tax_records: Iterable[AresLeadRecord],
    ) -> list[RankedAresLead]:
        probate = [record for record in probate_records if record.source_lane == AresSourceLane.PROBATE]
        verified_tax_by_key = {
            self._record_key(record): record
            for record in tax_records
            if self._is_verified_tax_delinquent(record)
        }

        ranked: list[RankedAresLead] = []
        matched_tax_keys: set[tuple[str, str]] = set()
        probate_counties = {record.county for record in probate}
        for record in probate:
            key = self._record_key(record)
            has_tax_overlay = key in verified_tax_by_key
            if has_tax_overlay:
                matched_tax_keys.add(key)
            ranked.append(
                RankedAresLead(
                    lead=record,
                    tier=AresLeadTier.PROBATE_WITH_VERIFIED_TAX if has_tax_overlay else AresLeadTier.PROBATE_ONLY,
                    rank=0,
                    tax_delinquent=has_tax_overlay,
                )
            )

        for key, record in verified_tax_by_key.items():
            if key in matched_tax_keys:
                continue
            if not record.estate_of:
                continue
            if record.county in probate_counties:
                continue
            ranked.append(
                RankedAresLead(
                    lead=record,
                    tier=AresLeadTier.TAX_ONLY_ESTATE_VERIFIED,
                    rank=0,
                    tax_delinquent=True,
                )
            )

        ranked.sort(key=lambda item: (item.tier, item.lead.county.value, self._normalize_address(item.lead.property_address)))

        return [
            RankedAresLead(
                lead=item.lead,
                tier=item.tier,
                rank=index,
                tax_delinquent=item.tax_delinquent,
            )
            for index, item in enumerate(ranked, start=1)
        ]

    def _is_verified_tax_delinquent(self, record: AresLeadRecord) -> bool:
        return record.source_lane == AresSourceLane.TAX_DELINQUENT

    def _record_key(self, record: AresLeadRecord) -> tuple[str, str]:
        return (record.county.value, self._normalize_address(record.property_address))

    def _normalize_address(self, address: str) -> str:
        normalized = _ADDRESS_WHITESPACE_PATTERN.sub(" ", address).strip().lower()
        return normalized
