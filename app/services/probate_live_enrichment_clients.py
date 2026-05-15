from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from typing import Any, Mapping

from app.domains.ares.models import AresCounty
from app.models.probate_leads import ProbateLeadRecord
from app.services.tax_overlay_service import ActWebTaxDetailParser, HarrisTaxStatementParser, TaxOverlayResult, TaxOverlayStatus

HARRIS_HCTAX_DELINQUENT_URL = "https://www.hctax.net/Property/DelinquentTax"
HARRIS_HCTAX_SEARCH_URL = "https://www.hctax.net/Property/Actions/DelAccountsList"
HARRIS_HCTAX_ENCRYPT_URL = "https://www.hctax.net/Property/AccountEncrypt"
HARRIS_HCTAX_STATEMENT_URL = "https://www.hctax.net/Property/TaxStatement"
HARRIS_CLERK_RP_URL = "https://www.cclerk.hctx.net/applications/websearch/RP.aspx"
MONTGOMERY_MCAD_ARCGIS_URL = (
    "https://services1.arcgis.com/PRoAPGnMSUqvTrzq/arcgis/rest/services/Tax_Parcel_view/FeatureServer/0/query"
)
MONTGOMERY_ACT_INDEX_URL = "https://actweb.acttax.com/act_webdev/montgomery/index.jsp"
MONTGOMERY_ACT_SHOWLIST_URL = "https://actweb.acttax.com/act_webdev/montgomery/showlist.jsp"
MONTGOMERY_ACT_DETAIL_URL = "https://actweb.acttax.com/act_webdev/montgomery/showdetail2.jsp"
MONTGOMERY_PUBLICSEARCH_RESULTS_URL = "https://montgomery.tx.publicsearch.us/results"

_USER_AGENT = "Mozilla/5.0 (compatible; AresProbateAutopilot/1.0; +https://github.com/martinp09/Ares)"


class PublicProbateLiveCadClient:
    """Read-only public property/CAD evidence client for probate-autopilot enrichment."""

    def __init__(self, *, harris_tax_client: HarrisHcTaxClient | None = None) -> None:
        self.harris_tax_client = harris_tax_client or HarrisHcTaxClient()
        self.montgomery_cad_client = MontgomeryCadArcGisClient()

    def fetch_candidates(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        county = _county_from(record=record, source_row=source_row)
        if county == "montgomery":
            return self.montgomery_cad_client.fetch_candidates(record=record, source_row=source_row)
        if county == "harris":
            return self._harris_candidates_from_hctax(record=record, source_row=source_row)
        return []

    def _harris_candidates_from_hctax(
        self,
        *,
        record: ProbateLeadRecord,
        source_row: Mapping[str, Any],
    ) -> list[Mapping[str, Any]]:
        candidates: list[dict[str, Any]] = []
        seen_accounts: set[str] = set()
        for col_search, query in _harris_tax_search_queries(record=record, source_row=source_row):
            try:
                records = self.harris_tax_client.search(col_search=col_search, search_text=query, page_size=25)
            except Exception as exc:  # noqa: BLE001 - public county endpoint should not break whole run.
                candidates.append(_blocked_candidate(county="harris", source="hctax_property_candidate", error=exc))
                continue
            for item in records:
                account = str(item.get("Account") or item.get("account") or "").strip()
                if not account or account in seen_accounts:
                    continue
                seen_accounts.add(account)
                candidates.append(
                    {
                        "acct": account,
                        "account": account,
                        "owner_name": _clean_text(item.get("Name") or item.get("owner_name")),
                        "property_address": _clean_text(item.get("Address") or item.get("property_address")),
                        "mailing_address": None,
                        "source": "harris_hctax_delinquent_public_search",
                        "source_url": HARRIS_HCTAX_SEARCH_URL,
                        "search_method": f"hctax_{col_search}",
                        "live_calls_attempted": True,
                    }
                )
        return candidates


class PublicProbateLiveTaxClient:
    """Read-only public tax-overlay client. Search order: owner, property address, account."""

    def __init__(self, *, harris_tax_client: HarrisHcTaxClient | None = None) -> None:
        self.harris_tax_client = harris_tax_client or HarrisHcTaxClient()
        self.montgomery_tax_client = MontgomeryActTaxClient()

    def fetch_tax_overlay(
        self,
        *,
        record: ProbateLeadRecord,
        source_row: Mapping[str, Any],
    ) -> TaxOverlayResult | Mapping[str, Any] | None:
        county = _county_from(record=record, source_row=source_row)
        try:
            if county == "montgomery":
                return self.montgomery_tax_client.fetch_tax_overlay(record=record, source_row=source_row)
            if county == "harris":
                return self.harris_tax_client.fetch_tax_overlay(record=record, source_row=source_row)
        except Exception as exc:  # noqa: BLE001 - persist blocked evidence instead of killing the scheduled run.
            return _tax_result(
                county=AresCounty.MONTGOMERY if county == "montgomery" else AresCounty.HARRIS,
                status=TaxOverlayStatus.BLOCKED,
                search_method="live_public_tax_lookup",
                confidence="none",
                parser_warnings=[f"live_tax_lookup_blocked:{type(exc).__name__}:{exc}"],
            )
        return None


class PublicProbateLiveLandRecordClient:
    """Read-only public land-record metadata client. Images/authenticated docs remain operator-gated."""

    def __init__(self) -> None:
        self.harris_land_records = HarrisClerkRealPropertyClient()
        self.montgomery_land_records = MontgomeryPublicSearchLandRecordClient()

    def fetch_land_records(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        county = _county_from(record=record, source_row=source_row)
        try:
            if county == "montgomery":
                return self.montgomery_land_records.fetch_land_records(record=record, source_row=source_row)
            if county == "harris":
                return self.harris_land_records.fetch_land_records(record=record, source_row=source_row)
        except Exception as exc:  # noqa: BLE001 - land portals can block/bounce; record the blocked stage.
            return [
                {
                    "status": "blocked",
                    "instrument_type": "LIVE LAND RECORD SEARCH BLOCKED",
                    "source_ref": f"{county or 'unknown'}_land_record_public_lookup",
                    "source_url": HARRIS_CLERK_RP_URL if county == "harris" else MONTGOMERY_PUBLICSEARCH_RESULTS_URL,
                    "parser_warnings": [f"live_land_record_lookup_blocked:{type(exc).__name__}:{exc}"],
                    "live_calls_attempted": True,
                }
            ]
        return []


class HarrisHcTaxClient:
    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        self._primed = False

    def search(self, *, col_search: str, search_text: str, page_size: int = 25) -> list[dict[str, Any]]:
        search_text = str(search_text or "").strip()
        if not search_text:
            return []
        payload = {
            "jtStartIndex": "0",
            "jtPageSize": str(page_size),
            "jtSorting": "Name ASC",
            "colSearch": col_search,
            "searchText": search_text,
        }
        response = _request_text(
            self._opener,
            HARRIS_HCTAX_SEARCH_URL,
            data=payload,
            headers={
                "Referer": HARRIS_HCTAX_DELINQUENT_URL,
                "X-Requested-With": "XMLHttpRequest",
                "Accept": "application/json, text/javascript, */*; q=0.01",
            },
            timeout=30,
        )
        data = json.loads(response)
        records = data.get("Records") if isinstance(data, Mapping) else []
        return [dict(item) for item in records if isinstance(item, Mapping)]

    def fetch_tax_overlay(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> TaxOverlayResult:
        search_records: list[dict[str, Any]] = []
        query_methods: list[str] = []
        for col_search, query in _harris_tax_search_queries(record=record, source_row=source_row):
            query_methods.append(f"{col_search}:{query}")
            search_records.extend(self.search(col_search=col_search, search_text=query, page_size=30))
            match = _best_harris_hctax_record(record=record, records=search_records)
            if match is not None:
                return self._detail_result(account=str(match["Account"]), search_method=f"hctax_{col_search}")
        return _tax_result(
            county=AresCounty.HARRIS,
            account=record.hcad_acct,
            owner_name=record.owner_name or record.decedent_name,
            property_address=record.property_address,
            status=TaxOverlayStatus.SOFT_NO_SIGNAL,
            is_delinquent=False,
            amount_owed=0.0,
            search_method="hctax_owner_address_account_search",
            confidence="low",
            source_url=HARRIS_HCTAX_SEARCH_URL,
            parser_warnings=["no_hctax_delinquent_record_matched_owner_address_or_account", f"queries={query_methods[:3]}"],
        )

    def _detail_result(self, *, account: str, search_method: str) -> TaxOverlayResult:
        self._prime_session()
        token = _request_text(
            self._opener,
            HARRIS_HCTAX_ENCRYPT_URL + "?" + urllib.parse.urlencode({"account": account}),
            headers={"Referer": HARRIS_HCTAX_DELINQUENT_URL, "X-Requested-With": "XMLHttpRequest"},
            timeout=30,
        ).strip()
        source_url = HARRIS_HCTAX_STATEMENT_URL + "?" + urllib.parse.urlencode({"account": token})
        html_text = _request_text(
            self._opener,
            source_url,
            headers={"Referer": HARRIS_HCTAX_DELINQUENT_URL},
            timeout=45,
        )
        parsed = HarrisTaxStatementParser().parse(html_text, account=account, source_url=HARRIS_HCTAX_STATEMENT_URL)
        raw = dict(parsed.raw)
        raw["live_lookup"] = {"search_method": search_method, "account": account, "source": "hctax_public_statement"}
        return parsed.model_copy(update={"search_method": search_method, "raw": raw})

    def _prime_session(self) -> None:
        if self._primed:
            return
        _request_text(self._opener, HARRIS_HCTAX_DELINQUENT_URL, timeout=30)
        self._primed = True


class MontgomeryCadArcGisClient:
    def fetch_candidates(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        queries = _montgomery_cad_queries(record=record, source_row=source_row)
        candidates: list[dict[str, Any]] = []
        seen_pins: set[str] = set()
        for where, method in queries:
            payload = {
                "where": where,
                "outFields": "PIN,ownerName,ownerAddress,situs,stateCd,legalDescription,imprvMainArea,imprvActualYearBuilt,exemptions",
                "returnGeometry": "false",
                "f": "json",
                "resultRecordCount": "10",
            }
            url = MONTGOMERY_MCAD_ARCGIS_URL + "?" + urllib.parse.urlencode(payload)
            text = _request_text(None, url, timeout=30)
            data = json.loads(text)
            for feature in data.get("features", []) if isinstance(data, Mapping) else []:
                attrs = feature.get("attributes") if isinstance(feature, Mapping) else None
                if not isinstance(attrs, Mapping):
                    continue
                pin = str(attrs.get("PIN") or attrs.get("pid") or "").strip()
                if not pin or pin in seen_pins:
                    continue
                seen_pins.add(pin)
                candidates.append(
                    {
                        "acct": pin,
                        "account": pin,
                        "tax_cad_reference": f"R{pin}",
                        "owner_name": _clean_text(attrs.get("ownerName")),
                        "mailing_address": _clean_text(attrs.get("ownerAddress")),
                        "property_address": _clean_text(attrs.get("situs")),
                        "legal_description": _clean_text(attrs.get("legalDescription")),
                        "state_code": attrs.get("stateCd"),
                        "source": "montgomery_mcad_arcgis_public_parcel",
                        "source_url": url,
                        "search_method": method,
                        "live_calls_attempted": True,
                    }
                )
        return candidates


class MontgomeryActTaxClient:
    def fetch_tax_overlay(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> TaxOverlayResult:
        pin = _montgomery_pin(record=record, source_row=source_row)
        if not pin:
            return _tax_result(
                county=AresCounty.MONTGOMERY,
                owner_name=record.owner_name or record.decedent_name,
                property_address=record.property_address,
                status=TaxOverlayStatus.SOFT_NO_SIGNAL,
                is_delinquent=False,
                amount_owed=0.0,
                search_method="montgomery_act_requires_cad_reference",
                confidence="low",
                source_url=MONTGOMERY_ACT_SHOWLIST_URL,
                parser_warnings=["no_montgomery_pin_or_cad_reference_after_property_match"],
            )
        cad_ref = pin if pin.upper().startswith("R") else f"R{pin}"
        list_html = _request_text(
            None,
            MONTGOMERY_ACT_SHOWLIST_URL,
            data={"searchby": "5", "criteria": cad_ref},
            headers={"Referer": MONTGOMERY_ACT_INDEX_URL},
            timeout=45,
            encoding="ISO-8859-1",
        )
        account = _montgomery_act_account_from_list(list_html, cad_ref=cad_ref)
        if not account:
            return _tax_result(
                county=AresCounty.MONTGOMERY,
                account=cad_ref,
                owner_name=record.owner_name or record.decedent_name,
                property_address=record.property_address,
                status=TaxOverlayStatus.SOFT_NO_SIGNAL,
                is_delinquent=False,
                amount_owed=0.0,
                search_method="montgomery_act_cad_reference_search",
                confidence="low",
                source_url=MONTGOMERY_ACT_SHOWLIST_URL,
                parser_warnings=["no_montgomery_act_tax_account_for_cad_reference"],
            )
        detail_url = MONTGOMERY_ACT_DETAIL_URL + "?" + urllib.parse.urlencode({"can": account, "ownerno": "0"})
        detail_html = _request_text(None, detail_url, headers={"Referer": MONTGOMERY_ACT_SHOWLIST_URL}, timeout=45, encoding="ISO-8859-1")
        parsed = ActWebTaxDetailParser(county=AresCounty.MONTGOMERY).parse(detail_html, source_url=detail_url)
        raw = dict(parsed.raw)
        raw["live_lookup"] = {"cad_reference": cad_ref, "account": account, "source": "montgomery_act_public_detail"}
        return parsed.model_copy(update={"search_method": "montgomery_act_cad_reference_detail", "raw": raw})


class HarrisClerkRealPropertyClient:
    def fetch_land_records(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        name = _person_search_name(record=record, source_row=source_row, last_first=True)
        if not name:
            return []
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
        initial_html = _request_text(opener, HARRIS_CLERK_RP_URL, timeout=30)
        form = _extract_form_defaults(initial_html)
        form.update({"ctl00$ContentPlaceHolder1$txtOR": name, "ctl00$ContentPlaceHolder1$btnSearch": "Search"})
        response_html = _request_text(
            opener,
            HARRIS_CLERK_RP_URL,
            data=form,
            headers={"Referer": HARRIS_CLERK_RP_URL},
            timeout=60,
        )
        return _parse_harris_rp_rows(response_html, source_url=HARRIS_CLERK_RP_URL)[:10]


class MontgomeryPublicSearchLandRecordClient:
    def fetch_land_records(self, *, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        name = _person_search_name(record=record, source_row=source_row, last_first=False)
        if not name:
            return []
        params = {
            "department": "RP",
            "keywordSearch": "false",
            "recordedDateRange": "16000101,20260515",
            "searchOcrText": "false",
            "searchType": "quickSearch",
            "searchValue": name,
        }
        url = MONTGOMERY_PUBLICSEARCH_RESULTS_URL + "?" + urllib.parse.urlencode(params)
        html_text = _request_text(None, url, timeout=45)
        rows = _parse_montgomery_publicsearch_embedded_rows(html_text, source_url=url)
        if rows:
            return rows[:10]
        return [
            {
                "status": "review_needed",
                "instrument_type": "MONTGOMERY PUBLICSEARCH INDEX REVIEW",
                "source_ref": "montgomery_publicsearch_rendered_results",
                "source_url": url,
                "search_method": "montgomery_publicsearch_http_shell",
                "parser_warnings": ["publicsearch_results_require_rendered_browser_or_websocket_for_document_rows"],
                "live_calls_attempted": True,
            }
        ]


class _FormDefaultsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.inputs: list[dict[str, str]] = []
        self.selects: dict[str, list[dict[str, str]]] = {}
        self._select_name: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "input":
            self.inputs.append(values)
        elif tag == "select":
            self._select_name = values.get("name")
            if self._select_name:
                self.selects[self._select_name] = []
        elif tag == "option" and self._select_name:
            self.selects[self._select_name].append(values)

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._select_name = None


def _extract_form_defaults(html_text: str) -> dict[str, str]:
    parser = _FormDefaultsParser()
    parser.feed(html_text)
    form: dict[str, str] = {}
    for item in parser.inputs:
        name = item.get("name")
        if not name:
            continue
        input_type = (item.get("type") or "text").lower()
        if input_type in {"submit", "button", "reset", "image"}:
            continue
        if input_type in {"checkbox", "radio"}:
            if "checked" in item:
                form[name] = item.get("value") or "on"
            continue
        form[name] = item.get("value") or ""
    for name, options in parser.selects.items():
        selected = next((option for option in options if "selected" in option), options[0] if options else {})
        form[name] = selected.get("value") or ""
    return form


def _request_text(
    opener: urllib.request.OpenerDirector | None,
    url: str,
    *,
    data: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: int = 30,
    encoding: str = "utf-8",
) -> str:
    body = urllib.parse.urlencode({key: value for key, value in (data or {}).items() if value is not None}).encode("utf-8") if data is not None else None
    request_headers = {"User-Agent": _USER_AGENT, **dict(headers or {})}
    if body is not None:
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=request_headers)
    active_opener = opener or urllib.request.build_opener()
    with active_opener.open(request, timeout=timeout) as response:  # noqa: S310 - public county source portals.
        return response.read().decode(encoding, errors="replace")


def _harris_tax_search_queries(*, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[tuple[str, str]]:
    queries: list[tuple[str, str]] = []
    owner = record.owner_name or _person_search_name(record=record, source_row=source_row, last_first=False)
    if owner:
        queries.append(("name", _strip_estate_noise(owner)))
    if record.property_address:
        queries.append(("address", _street_number_or_address(record.property_address)))
    account = record.hcad_acct or _first_text(source_row, "hctax_account", "tax_account", "account", "acct", "hcad_account")
    if account:
        queries.append(("account", re.sub(r"\D+", "", account)))
    return _dedupe_pairs([(col, query) for col, query in queries if query])


def _best_harris_hctax_record(*, record: ProbateLeadRecord, records: list[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if not records:
        return None
    desired_account = re.sub(r"\D+", "", record.hcad_acct or "")
    desired_owner = _token_set(record.owner_name or record.decedent_name or record.estate_name)
    desired_address = _token_set(record.property_address)
    ranked: list[tuple[int, Mapping[str, Any]]] = []
    for item in records:
        score = 0
        account = re.sub(r"\D+", "", str(item.get("Account") or ""))
        owner_tokens = _token_set(item.get("Name"))
        address_tokens = _token_set(item.get("Address"))
        if desired_account and desired_account == account:
            score += 8
        if desired_owner and owner_tokens:
            score += min(5, len(desired_owner & owner_tokens))
        if desired_address and address_tokens:
            score += min(3, len(desired_address & address_tokens))
        if score > 0:
            ranked.append((score, item))
    if not ranked:
        return records[0] if len(records) == 1 else None
    return sorted(ranked, key=lambda item: -item[0])[0][1]


def _montgomery_cad_queries(*, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> list[tuple[str, str]]:
    clauses: list[tuple[str, str]] = []
    owner = record.owner_name or _person_search_name(record=record, source_row=source_row, last_first=False)
    if owner:
        terms = [token for token in _name_tokens(_strip_estate_noise(owner)) if len(token) >= 3]
        if terms:
            clauses.append((" AND ".join(f"UPPER(ownerName) LIKE '%{_sql_like_escape(token)}%'" for token in terms[:3]), "mcad_owner_name"))
    if record.property_address:
        street_number = _street_number(record.property_address)
        if street_number:
            clauses.append((f"UPPER(situs) LIKE '%{_sql_like_escape(street_number)}%'", "mcad_situs_street_number"))
    return clauses


def _montgomery_pin(*, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> str | None:
    for value in (
        record.hcad_acct,
        _first_text(source_row, "tax_cad_reference", "cad_reference", "pin", "PIN", "account", "acct", "hcad_account"),
    ):
        if value:
            text = str(value).strip().upper()
            match = re.search(r"R?\s*(\d{4,})", text)
            if match:
                return match.group(1)
    return None


def _montgomery_act_account_from_list(html_text: str, *, cad_ref: str) -> str | None:
    exact_ref = re.escape(cad_ref.upper())
    rows = re.findall(r"<tr[^>]*>.*?</tr>", html_text, flags=re.IGNORECASE | re.DOTALL)
    for row in rows:
        text = _clean_text(row).upper()
        if cad_ref.upper() not in text:
            continue
        match = re.search(r"showdetail2\.jsp\?can=([0-9A-Za-z]+)&ownerno=([0-9]+)", row, flags=re.IGNORECASE)
        if match and re.search(exact_ref, text):
            return match.group(1)
    match = re.search(r"showdetail2\.jsp\?can=([0-9A-Za-z]+)&ownerno=([0-9]+)", html_text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _parse_harris_rp_rows(html_text: str, *, source_url: str) -> list[Mapping[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_html in re.findall(r"<tr[^>]*>.*?</tr>", html_text, flags=re.IGNORECASE | re.DOTALL):
        if "lblFileNo" not in row_html:
            continue
        file_no = _label_span(row_html, "lblFileNo")
        if not file_no:
            continue
        rows.append(
            {
                "instrument_number": file_no,
                "file_number": file_no,
                "file_date": _label_span(row_html, "lblFileDate"),
                "instrument_type": _label_span(row_html, "lblDocType") or _cell_by_position(row_html, 3),
                "grantor": _first_matching_text(row_html, "lblGrantor", "lblGrantors") or None,
                "grantee": _first_matching_text(row_html, "lblGrantee", "lblGrantees") or None,
                "source_url": source_url,
                "search_method": "harris_clerk_real_property_grantor",
                "live_calls_attempted": True,
            }
        )
    return rows


def _parse_montgomery_publicsearch_embedded_rows(html_text: str, *, source_url: str) -> list[Mapping[str, Any]]:
    rows: list[dict[str, Any]] = []
    # The React shell includes lookup tables/document descriptions in HTML; actual result rows may require the WS path.
    for match in re.finditer(r'"documentNumber":"([^"]+)".*?"documentType":"([^"]+)"', html_text):
        rows.append(
            {
                "instrument_number": html.unescape(match.group(1)),
                "instrument_type": html.unescape(match.group(2)),
                "source_url": source_url,
                "search_method": "montgomery_publicsearch_embedded_state",
                "live_calls_attempted": True,
            }
        )
    return rows


def _label_span(row_html: str, label_suffix: str) -> str | None:
    pattern = rf'id="[^"]*{re.escape(label_suffix)}"[^>]*>(.*?)</span>'
    match = re.search(pattern, row_html, flags=re.IGNORECASE | re.DOTALL)
    return _clean_text(match.group(1)) if match else None


def _first_matching_text(row_html: str, *label_suffixes: str) -> str | None:
    for suffix in label_suffixes:
        value = _label_span(row_html, suffix)
        if value:
            return value
    return None


def _cell_by_position(row_html: str, position: int) -> str | None:
    cells = [_clean_text(cell) for cell in re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.IGNORECASE | re.DOTALL)]
    cells = [cell for cell in cells if cell]
    return cells[position] if len(cells) > position else None


def _tax_result(
    *,
    county: AresCounty,
    status: TaxOverlayStatus,
    search_method: str,
    confidence: str,
    account: str | None = None,
    owner_name: str | None = None,
    property_address: str | None = None,
    is_delinquent: bool | None = None,
    amount_owed: float | None = None,
    source_url: str | None = None,
    parser_warnings: list[str] | None = None,
) -> TaxOverlayResult:
    return TaxOverlayResult(
        county=county,
        account=account,
        owner_name=owner_name,
        property_address=property_address,
        status=status,
        is_delinquent=is_delinquent,
        amount_owed=amount_owed,
        current_year_owed=0.0 if amount_owed == 0 else None,
        prior_years_owed=0.0 if amount_owed == 0 else None,
        estimated_years_delinquent=0 if is_delinquent is False else None,
        search_method=search_method,
        confidence=confidence,
        source_url=source_url,
        parser_warnings=parser_warnings or [],
        raw={"live_lookup": True},
    )


def _county_from(*, record: ProbateLeadRecord, source_row: Mapping[str, Any]) -> str | None:
    raw = source_row.get("raw") if isinstance(source_row.get("raw"), Mapping) else {}
    for value in (source_row.get("county"), raw.get("county"), record.raw_payload.get("county")):
        normalized = str(value or "").strip().lower().replace(" county", "")
        if normalized in {"harris", "montgomery"}:
            return normalized
    return "harris"


def _person_search_name(*, record: ProbateLeadRecord, source_row: Mapping[str, Any], last_first: bool) -> str | None:
    raw = source_row.get("raw") if isinstance(source_row.get("raw"), Mapping) else {}
    name = (
        record.decedent_name
        or record.owner_name
        or _first_text(source_row, "decedent_name", "owner_name", "owner", "style", "estate_name")
        or _first_text(raw, "decedent_name", "owner_name", "owner", "style", "estate_name")
        or record.estate_name
    )
    cleaned = _strip_estate_noise(name)
    if not cleaned:
        return None
    tokens = _name_tokens(cleaned)
    if last_first and len(tokens) >= 2:
        return " ".join([tokens[-1], *tokens[:-1]])
    return " ".join(tokens)


def _strip_estate_noise(value: Any) -> str | None:
    if value is None:
        return None
    text = _clean_text(value).upper()
    text = re.sub(r"\b(IN THE MATTER OF|IN THE ESTATE OF|ESTATE OF|DECEASED|DECEDENT|THE|OF)\b", " ", text)
    text = re.sub(r"[^A-Z0-9 ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _name_tokens(value: Any) -> list[str]:
    text = _strip_estate_noise(value) or ""
    return [token for token in re.findall(r"[A-Z0-9]+", text) if token not in {"IN", "RE"}]


def _token_set(value: Any) -> set[str]:
    return set(_name_tokens(value))


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _clean_text(value: Any) -> str:
    text = re.sub(r"<br\s*/?>", " ", str(value or ""), flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _street_number(value: str) -> str | None:
    match = re.search(r"\b\d{2,6}\b", value)
    return match.group(0) if match else None


def _street_number_or_address(value: str) -> str:
    return _street_number(value) or value


def _sql_like_escape(value: str) -> str:
    return re.sub(r"[^A-Z0-9 ]+", "", value.upper()).replace("'", "''")


def _dedupe_pairs(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[tuple[str, str]] = []
    for col, query in pairs:
        item = (col, query.strip())
        if item[1] and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _blocked_candidate(*, county: str, source: str, error: Exception) -> dict[str, Any]:
    return {
        "source": source,
        "county": county,
        "status": "blocked",
        "parser_warnings": [f"live_property_lookup_blocked:{type(error).__name__}:{error}"],
        "live_calls_attempted": True,
    }


public_probate_live_cad_client = PublicProbateLiveCadClient()
public_probate_live_tax_client = PublicProbateLiveTaxClient()
public_probate_live_land_record_client = PublicProbateLiveLandRecordClient()
