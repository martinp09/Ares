from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.domains.ares.models import AresCounty


class TaxOverlayStatus(StrEnum):
    NOT_CHECKED = "tax_overlay_not_checked"
    SOFT_NO_SIGNAL = "tax_overlay_soft_no_signal"
    SOFT_SIGNAL = "tax_overlay_soft_signal"
    VERIFIED_CURRENT = "tax_overlay_verified_current"
    VERIFIED_DELINQUENT = "tax_overlay_verified_delinquent"
    AMBIGUOUS = "tax_overlay_ambiguous"
    BLOCKED = "tax_overlay_blocked"


class TaxOverlayResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    county: AresCounty
    account: str | None = None
    owner_name: str | None = None
    property_address: str | None = None
    status: TaxOverlayStatus
    is_delinquent: bool | None = None
    amount_owed: float | None = None
    current_year_owed: float | None = None
    prior_years_owed: float | None = None
    estimated_years_delinquent: int | None = None
    tax_value: float | None = None
    tax_value_spread: float | None = None
    tax_to_value_pct: float | None = None
    taxes_under_suit: bool | None = None
    homestead_or_exemption_clues: list[str] = Field(default_factory=list)
    search_method: str
    confidence: str
    source_url: str | None = None
    parser_warnings: list[str] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


class HarrisTaxStatementParser:
    county = AresCounty.HARRIS

    def parse(self, html_text: str, *, account: str | None = None, source_url: str | None = None) -> TaxOverlayResult:
        clean_html = _strip_scripts(html_text)
        text = _normalize_text(_strip_tags(clean_html))
        fields = _extract_labeled_fields(clean_html)

        owner_field = _first_field(fields, "assessed owner", "owner name", "owner")
        owner_name = _owner_from_owner_field(owner_field)
        property_address = _first_field(fields, "property address", "situs address", "site address") or _address_from_owner_field(owner_field) or _address_from_property_description(_first_field(fields, "property description"))
        parsed_account = account or _first_field(fields, "account number", "account")

        tax_value = _first_not_none(_money_from_fields(fields, "total market value", "market value"), _money_after_label(text, "total market value"))
        current_due = _first_not_none(_money_from_fields(fields, "total current taxes due", "current taxes due", "current tax due"), _money_after_label(text, "total current taxes due"))
        prior_due = _first_not_none(_money_from_fields(fields, "prior year taxes due", "prior year tax due", "prior year"), _money_after_label(text, "prior year taxes due"))
        amount_owed = _first_not_none(_money_from_fields(fields, "total amount due", "amount due", "total due"), _money_after_label(text, "total amount due"))

        no_delinquent_phrase = bool(
            re.search(r"no\s+delinquent\s+taxes\s+exist|not\s+delinquent|no\s+delinquent", text, re.IGNORECASE)
        )
        delinquent_phrase = bool(re.search(r"delinquent\s+taxes\s+exist", text, re.IGNORECASE)) and not no_delinquent_phrase
        taxes_under_suit = bool(re.search(r"tax\s+suit|under\s+suit|litigation|judgment|foreclosure", text, re.IGNORECASE))

        if amount_owed is None:
            amount_owed = 0.0 if no_delinquent_phrase else None
        if current_due is None:
            current_due = 0.0 if no_delinquent_phrase else None
        if prior_due is None:
            prior_due = 0.0 if no_delinquent_phrase else None

        is_delinquent = bool(delinquent_phrase or (amount_owed is not None and amount_owed > 0 and prior_due is not None and prior_due > 0))
        if no_delinquent_phrase and not delinquent_phrase and (amount_owed or 0) <= 0:
            is_delinquent = False

        parser_warnings: list[str] = []
        if not owner_name:
            parser_warnings.append("missing_owner_name")
        if tax_value is None or tax_value <= 0:
            parser_warnings.append("missing_tax_value")
        if amount_owed is None:
            parser_warnings.append("missing_amount_owed")

        if parser_warnings:
            status = TaxOverlayStatus.AMBIGUOUS
            confidence = "low"
        elif is_delinquent:
            status = TaxOverlayStatus.VERIFIED_DELINQUENT
            confidence = "high"
        else:
            status = TaxOverlayStatus.VERIFIED_CURRENT
            confidence = "high"

        tax_value_spread = None
        tax_to_value_pct = None
        if tax_value is not None and amount_owed is not None:
            tax_value_spread = tax_value - amount_owed
            tax_to_value_pct = round((amount_owed / tax_value) * 100, 2) if tax_value > 0 else None

        estimated_years = None
        if is_delinquent and prior_due and current_due and current_due > 0:
            estimated_years = max(1, int(round(prior_due / current_due)))
        elif is_delinquent:
            estimated_years = 1
        else:
            estimated_years = 0 if status == TaxOverlayStatus.VERIFIED_CURRENT else None

        return TaxOverlayResult(
            county=self.county,
            account=_clean_or_none(parsed_account),
            owner_name=_clean_or_none(owner_name),
            property_address=_clean_or_none(property_address),
            status=status,
            is_delinquent=is_delinquent,
            amount_owed=amount_owed,
            current_year_owed=current_due,
            prior_years_owed=prior_due,
            estimated_years_delinquent=estimated_years,
            tax_value=tax_value,
            tax_value_spread=tax_value_spread,
            tax_to_value_pct=tax_to_value_pct,
            taxes_under_suit=taxes_under_suit,
            homestead_or_exemption_clues=_exemption_clues(text),
            search_method="harris_tax_statement",
            confidence=confidence,
            source_url=source_url,
            parser_warnings=parser_warnings,
            raw={"labeled_fields": fields},
        )


class ActWebTaxDetailParser:
    def __init__(self, *, county: AresCounty) -> None:
        if county not in {AresCounty.DALLAS, AresCounty.MONTGOMERY}:
            raise ValueError("ACT Web tax parser only supports Dallas and Montgomery")
        self.county = county

    def parse(self, html_text: str, *, source_url: str | None = None) -> TaxOverlayResult:
        fields = _extract_labeled_fields(_strip_scripts(html_text))
        account = _first_field(fields, "account no", "account number", "account") or _account_from_url(source_url)
        owner_name = _first_field(fields, "owner name", "owner")
        property_address = _first_field(fields, "property site address", "property address", "site address", "situs address")
        amount_owed = _money_from_fields(fields, "total due", "amount due", "total amount due")
        base_tax = _money_from_fields(fields, "base tax", "tax due")
        penalty_interest = _money_from_fields(fields, "penalty interest", "penalty and interest", "penalty & interest")

        warnings: list[str] = []
        if not account:
            warnings.append("missing_account")
        if not owner_name:
            warnings.append("missing_owner_name")
        if amount_owed is None:
            warnings.append("missing_amount_owed")

        is_delinquent = amount_owed is not None and amount_owed > 0
        if warnings:
            status = TaxOverlayStatus.AMBIGUOUS
            confidence = "low"
        elif is_delinquent:
            status = TaxOverlayStatus.VERIFIED_DELINQUENT
            confidence = "high"
        else:
            status = TaxOverlayStatus.VERIFIED_CURRENT
            confidence = "high"

        return TaxOverlayResult(
            county=self.county,
            account=_clean_or_none(account),
            owner_name=_clean_or_none(owner_name),
            property_address=_clean_or_none(property_address),
            status=status,
            is_delinquent=is_delinquent,
            amount_owed=amount_owed,
            current_year_owed=base_tax,
            prior_years_owed=penalty_interest,
            search_method="act_web_detail",
            confidence=confidence,
            source_url=source_url,
            parser_warnings=warnings,
            raw={"labeled_fields": fields},
        )


class TravisTaxSearchAdapter:
    search_url = "https://travis.go2gov.net/cart/responsive/quickSearch.do"
    detail_base_url = "https://travis.go2gov.net"

    def __init__(self, post: Callable[[str, dict[str, str]], str] | None = None) -> None:
        self._post = post or _default_post

    def quick_search(self, query: str) -> list[TaxOverlayResult]:
        payload = {
            "formViewMode": "responsive",
            "criteria.searchStatus": "1",
            "pager.pageSize": "10",
            "pager.pageNumber": "1",
            "criteria.heuristicSearch": query,
        }
        response_html = self._post(self.search_url, payload)
        return TravisTaxSearchParser().parse(response_html)


class TravisTaxSearchParser:
    detail_base_url = "https://travis.go2gov.net"
    account_pattern = re.compile(r"(?:account=|acct=)?(\d{8,17})", re.IGNORECASE)

    def parse(self, html_text: str) -> list[TaxOverlayResult]:
        blocks = _candidate_result_blocks(html_text)
        results: list[TaxOverlayResult] = []
        for block in blocks:
            block_text = _normalize_text(_strip_tags(block))
            account = self._account_from_block(block, block_text)
            if not account:
                continue
            source_url = self._source_url_from_block(block)
            owner_name = self._owner_from_block(block, block_text, account)
            property_address = self._address_from_block(block, block_text)
            amount_owed = _first_not_none(_money_after_label(block_text, "total due"), _first_money(block_text))
            results.append(
                TaxOverlayResult(
                    county=AresCounty.TRAVIS,
                    account=account,
                    owner_name=owner_name,
                    property_address=property_address,
                    status=TaxOverlayStatus.SOFT_SIGNAL,
                    is_delinquent=None,
                    amount_owed=amount_owed,
                    search_method="travis_quick_search",
                    confidence="medium" if owner_name or property_address else "low",
                    source_url=source_url,
                    parser_warnings=["quick_search_result_requires_detail_page_verification"],
                    raw={"result_text": block_text},
                )
            )
        return results

    def _account_from_block(self, block: str, block_text: str) -> str | None:
        href_match = re.search(r"href=[\"'][^\"']*(?:account=|acct=)(\d{8,17})", block, re.IGNORECASE)
        if href_match:
            return href_match.group(1)
        text_match = self.account_pattern.search(block_text)
        return text_match.group(1) if text_match else None

    def _source_url_from_block(self, block: str) -> str | None:
        href_match = re.search(r"href=[\"']([^\"']*(?:account=|acct=)[^\"']*)", block, re.IGNORECASE)
        if not href_match:
            return None
        href = html.unescape(href_match.group(1))
        return urllib.parse.urljoin(self.detail_base_url, href)

    def _owner_from_block(self, block: str, block_text: str, account: str) -> str | None:
        divs = [_normalize_text(_strip_tags(div)) for div in re.findall(r"<div[^>]*>(.*?)</div>", block, re.IGNORECASE | re.DOTALL)]
        divs = [div for div in divs if div]
        for index, div in enumerate(divs):
            if account in div:
                for candidate in divs[index + 1 :]:
                    if "$" in candidate or _looks_like_address(candidate):
                        continue
                    return candidate
        chunks = [chunk.strip(" -|:") for chunk in re.split(r"\s{2,}|\s+-\s+|\s+\|\s+", block_text) if chunk.strip()]
        for chunk in chunks:
            upper = chunk.upper()
            if account in chunk or "$" in chunk or "TOTAL DUE" in upper or _looks_like_address(chunk):
                continue
            if re.search(r"[A-Z]{2,}", upper):
                return chunk
        without_account = block_text.replace(account, " ")
        without_due = re.sub(r"\$\s*[\d,]+(?:\.\d{2})?", " ", without_account)
        without_due = re.sub(r"total\s+due\s*:?", " ", without_due, flags=re.IGNORECASE)
        address_match = re.search(r"\b\d{2,6}\s+[A-Z0-9 .'-]+\b", without_due, flags=re.IGNORECASE)
        if address_match:
            without_due = without_due.replace(address_match.group(0), " ")
        owner = _normalize_text(without_due)
        return owner or None

    def _address_from_block(self, block: str, block_text: str) -> str | None:
        divs = [_normalize_text(_strip_tags(div)) for div in re.findall(r"<div[^>]*>(.*?)</div>", block, re.IGNORECASE | re.DOTALL)]
        for div in divs:
            if _looks_like_address(div) and "$" not in div:
                return div.upper()
        match = _address_match(block_text)
        return _clean_or_none(match.upper() if match else None)


def _account_from_url(source_url: str | None) -> str | None:
    if not source_url:
        return None
    parsed = urllib.parse.urlparse(source_url)
    query = urllib.parse.parse_qs(parsed.query)
    for key in ("can", "account", "acct"):
        values = query.get(key)
        if values:
            return values[0]
    match = re.search(r"\b\d{8,17}\b", source_url)
    return match.group(0) if match else None


def _default_post(url: str, data: dict[str, str]) -> str:
    encoded = urllib.parse.urlencode(data).encode()
    request = urllib.request.Request(
        url,
        data=encoded,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://travis.go2gov.net/cart/responsive/search.do",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:  # noqa: S310 - public county tax portal
        return response.read().decode("utf-8", errors="replace")


def _strip_scripts(html_text: str) -> str:
    html_text = re.sub(r"<script[^>]*>.*?</script>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)
    return re.sub(r"<style[^>]*>.*?</style>", " ", html_text, flags=re.IGNORECASE | re.DOTALL)


def _strip_tags(html_text: str) -> str:
    return re.sub(r"<[^>]+>", " ", html.unescape(html_text))


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def _clean_or_none(value: str | None) -> str | None:
    cleaned = _normalize_text(value or "")
    return cleaned or None


def _extract_labeled_fields(html_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    table_pattern = re.compile(r"<table[^>]*>(.*?)</table>", re.IGNORECASE | re.DOTALL)
    row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
    cell_pattern = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.IGNORECASE | re.DOTALL)

    for table_match in table_pattern.finditer(html_text):
        rows = []
        for row_match in row_pattern.finditer(table_match.group(1)):
            cells = [_cell_text(cell) for cell in cell_pattern.findall(row_match.group(1))]
            cells = [cell for cell in cells if cell]
            if cells:
                rows.append(cells)
        if (
            len(rows) >= 2
            and len(rows[0]) == len(rows[1])
            and len(rows[0]) > 1
            and all(_looks_like_label(label) for label in rows[0])
        ):
            for label, value in zip(rows[0], rows[1], strict=False):
                fields[_label_key(label)] = value
        for cells in rows:
            if len(cells) >= 2 and _looks_like_label(cells[0]):
                fields[_label_key(cells[0])] = cells[1]

    definition_pattern = re.compile(
        r"<[^>]*class=[\"'][^\"']*(?:label|title)[^\"']*[\"'][^>]*>(.*?)</[^>]+>\s*<[^>]*>(.*?)</[^>]+>",
        re.IGNORECASE | re.DOTALL,
    )
    for label, value in definition_pattern.findall(html_text):
        label_text = _normalize_text(_strip_tags(label))
        value_text = _normalize_text(_strip_tags(value))
        if label_text and value_text:
            fields.setdefault(_label_key(label_text), value_text)
    return fields


def _cell_text(cell_html: str) -> str:
    with_breaks = re.sub(r"<br\s*/?>", "\n", cell_html, flags=re.IGNORECASE)
    lines = [_normalize_text(line) for line in _strip_tags(with_breaks).splitlines()]
    return "\n".join(line for line in lines if line)


def _looks_like_label(value: str) -> bool:
    lowered = value.lower()
    return any(token in lowered for token in ("account", "owner", "address", "description", "value", "due", "tax", "current as of"))


def _owner_from_owner_field(value: str | None) -> str | None:
    if not value:
        return None
    for line in value.splitlines():
        cleaned = _normalize_text(line)
        if cleaned and not re.search(r"\d{3,}", cleaned) and not _looks_like_address(cleaned):
            return cleaned
    cleaned = _normalize_text(value)
    address = _address_from_owner_field(value)
    if address:
        cleaned = cleaned.split(address, 1)[0].strip()
    return cleaned or None


def _address_from_owner_field(value: str | None) -> str | None:
    if not value:
        return None
    for line in value.splitlines():
        cleaned = _normalize_text(line)
        if _looks_like_address(cleaned):
            return cleaned.upper()
    return _address_from_property_description(value)


def _address_from_property_description(value: str | None) -> str | None:
    if not value:
        return None
    match = _address_match(_normalize_text(value))
    return match.upper() if match else None


def _address_match(value: str) -> str | None:
    pattern = re.compile(
        r"\b\d{2,6}\s+(?:[A-Z0-9.'-]+\s+){0,5}?(?:ST|STREET|RD|ROAD|AVE|AVENUE|DR|DRIVE|LN|LANE|CT|COURT|BLVD|PKWY|CIR|TRL|TRAIL)\b",
        re.IGNORECASE,
    )
    matches = [match.group(0) for match in pattern.finditer(value)]
    if not matches:
        return None
    return min(matches, key=len)


def _label_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _first_field(fields: dict[str, str], *labels: str) -> str | None:
    for label in labels:
        key = _label_key(label)
        if key in fields:
            return fields[key]
    for label in labels:
        key = _label_key(label)
        for field_key, value in fields.items():
            if key in field_key:
                return value
    return None


def _first_not_none(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _money_from_fields(fields: dict[str, str], *labels: str) -> float | None:
    value = _first_field(fields, *labels)
    return _parse_money(value) if value is not None else None


def _parse_money(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"\$?\s*([\d,]+(?:\.\d{1,2})?)", value)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def _first_money(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.search(r"\$\s*([\d,]+(?:\.\d{1,2})?)", value)
    return float(match.group(1).replace(",", "")) if match else None


def _money_after_label(text: str, label: str) -> float | None:
    pattern = r"\s+".join(re.escape(part) for part in label.split()) + r"\s*:?\s*\$?\s*([\d,]+(?:\.\d{1,2})?)"
    match = re.search(pattern, text, re.IGNORECASE)
    return float(match.group(1).replace(",", "")) if match else None


def _exemption_clues(text: str) -> list[str]:
    clues = []
    for clue in ("homestead", "over 65", "disabled", "ag exemption"):
        if re.search(re.escape(clue), text, re.IGNORECASE):
            clues.append(clue)
    return clues


def _candidate_result_blocks(html_text: str) -> list[str]:
    row_blocks = re.findall(r"<tr[^>]*>.*?</tr>", html_text, re.IGNORECASE | re.DOTALL)
    account_rows = [row for row in row_blocks if re.search(r"(?:account=|acct=|\d{8,17})", row, re.IGNORECASE)]
    if account_rows:
        return account_rows
    div_blocks = re.findall(r"<div[^>]*>(?:(?!</div>).)*(?:account=|acct=|\d{8,17})(?:(?!</div>).)*</div>", html_text, re.IGNORECASE | re.DOTALL)
    return div_blocks


def _looks_like_address(value: str) -> bool:
    return bool(re.search(r"\b\d{2,6}\s+", value) and re.search(r"\b(ST|STREET|RD|ROAD|AVE|DR|LN|CT|BLVD|PKWY|CIR|TRL)\b", value, re.IGNORECASE))
