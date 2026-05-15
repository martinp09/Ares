from __future__ import annotations

import html
import http.client
import http.cookiejar
import re
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any, Mapping

from app.models.source_runs import SourceCounty
from app.services.probate_source_adapter_service import probate_source_adapter_service

HARRIS_PROBATE_SEARCH_URL = "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch_R.aspx?CaseType=Probate"
MONTGOMERY_ODYSSEY_LOGIN_URL = "https://odyssey.mctx.org/County/Login.aspx?ReturnUrl=%2fCounty%2fdefault.aspx"
MONTGOMERY_ODYSSEY_DEFAULT_URL = "https://odyssey.mctx.org/County/default.aspx"
MONTGOMERY_ODYSSEY_SEARCH_URL = "https://odyssey.mctx.org/County/Search.aspx?ID=200"
PROBATE_LIVE_SOURCE_ADAPTER_VERSION = "probate_live_source_adapter_v1"

_HARRIS_USER_AGENT = "Mozilla/5.0 (compatible; AresProbateAutopilot/1.0; +https://github.com/martinp09/Ares)"
_MONTGOMERY_ALL_COUNTY_COURTS_NODE_ID = "100,105,110,120,130,140,150,160,180"
_MONTGOMERY_ALL_COUNTY_COURTS_NODE_DESC = "All County Courts"
_MONTGOMERY_SESSION_ATTEMPTS = 6


@dataclass(frozen=True)
class CountyProbateSourceFetch:
    county: SourceCounty
    source_url: str
    rows: list[dict[str, Any]]
    source_reported_count: int
    raw_count: int
    parser_warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ProbateLiveSourceAdapterService:
    """Fetch public Harris/Montgomery probate case rows for no-send source runs.

    These adapters perform read-only public county source lookups and return rows
    in the same canonical contract used by local export files. They never write
    CRM records, enroll leads, send messages, skiptrace, or make provider calls.
    """

    def fetch_window(
        self,
        *,
        counties: list[SourceCounty],
        window_start: Any = None,
        window_end: Any = None,
        live_source_calls_enabled: bool = False,
        source_provider_approval: Mapping[str, Any] | None = None,
    ) -> dict[SourceCounty, CountyProbateSourceFetch]:
        if not live_source_calls_enabled:
            raise RuntimeError("live probate source adapters require LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true")
        if not isinstance(source_provider_approval, Mapping) or source_provider_approval.get("approved") is not True:
            raise RuntimeError("live probate source adapters require source_provider_approval.approved=true")
        if source_provider_approval.get("no_send") is not True or source_provider_approval.get("provider_sends_enabled") is not False:
            raise RuntimeError("live probate source adapters require source_provider_approval.no_send=true and provider_sends_enabled=false")
        start_date, end_date = _date_window(window_start, window_end)
        if (end_date - start_date).days > 45:
            raise ValueError("live probate source windows are capped at 45 days per run")
        results: dict[SourceCounty, CountyProbateSourceFetch] = {}
        for county in counties:
            if county == "harris":
                results[county] = HarrisCountyProbateLiveAdapter().fetch(start_date=start_date, end_date=end_date)
            elif county == "montgomery":
                results[county] = MontgomeryCountyProbateLiveAdapter().fetch(start_date=start_date, end_date=end_date)
        return results


class HarrisCountyProbateLiveAdapter:
    source_url = HARRIS_PROBATE_SEARCH_URL

    def fetch(self, *, start_date: date, end_date: date) -> CountyProbateSourceFetch:
        opener = _opener()
        initial_html = _request_text(opener, self.source_url, headers={"User-Agent": _HARRIS_USER_AGENT})
        form = _extract_form_defaults(initial_html)
        form.update(
            {
                "ctl00$ContentPlaceHolder1$ddlCourt": "All",
                "ctl00$ContentPlaceHolder1$DropDownListStatus": "-All",
                "ctl00$ContentPlaceHolder1$txtDateFrom": _mmddyyyy(start_date),
                "ctl00$ContentPlaceHolder1$txtDateTo": _mmddyyyy(end_date),
                "ctl00$ContentPlaceHolder1$btnSearch": "Search",
            }
        )
        response_html = _request_text(
            opener,
            self.source_url,
            data=form,
            headers={"User-Agent": _HARRIS_USER_AGENT, "Referer": self.source_url},
        )
        if not _looks_like_harris_results_page(response_html):
            raise RuntimeError("Harris probate live source did not return the expected search-results page")
        rows = _parse_harris_probate_rows(response_html)
        normalized = probate_source_adapter_service.normalize_rows(rows, county="harris", source_uri=self.source_url)
        for row in normalized:
            row["source_portal"] = "harris_county_clerk_web_inquiry"
            row["source_adapter"] = "harris_county_probate_live_v1"
            row["source_adapter_version"] = PROBATE_LIVE_SOURCE_ADAPTER_VERSION
        return CountyProbateSourceFetch(
            county="harris",
            source_url=self.source_url,
            rows=normalized,
            source_reported_count=len(normalized),
            raw_count=len(rows),
            parser_warnings=[] if rows else ["harris_live_source_returned_no_rows_for_window"],
            metadata={"date_from": _mmddyyyy(start_date), "date_to": _mmddyyyy(end_date)},
        )


class MontgomeryCountyProbateLiveAdapter:
    login_url = MONTGOMERY_ODYSSEY_LOGIN_URL
    source_url = MONTGOMERY_ODYSSEY_SEARCH_URL

    def fetch(self, *, start_date: date, end_date: date) -> CountyProbateSourceFetch:
        start = _mmddyyyy(start_date)
        end = _mmddyyyy(end_date)
        errors: list[str] = []
        for attempt in range(1, _MONTGOMERY_SESSION_ATTEMPTS + 1):
            opener = _opener(cookie_jar=http.cookiejar.CookieJar())
            try:
                search_html = _open_montgomery_search_form(opener)
                form = _prepare_montgomery_date_filed_probate_form(search_html, start=start, end=end)
                response_html = _request_text(
                    opener,
                    self.source_url,
                    data=form,
                    headers={"Referer": self.source_url},
                )
                if not _looks_like_montgomery_results_page(response_html):
                    raise RuntimeError("search-results page missing Record Count/CaseDetail markers")
                return _montgomery_fetch_from_results(response_html=response_html, source_url=self.source_url, start=start, end=end)
            except Exception as exc:  # noqa: BLE001 - Odyssey public access can bounce sessions; retry cleanly.
                errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
                if attempt < _MONTGOMERY_SESSION_ATTEMPTS:
                    time.sleep(min(2.0, 0.35 * attempt))
        raise RuntimeError("Montgomery Odyssey live source failed after session retries; " + "; ".join(errors[-2:]))


probate_live_source_adapter_service = ProbateLiveSourceAdapterService()


def _open_montgomery_search_form(opener: urllib.request.OpenerDirector) -> str:
    _request_text(opener, MONTGOMERY_ODYSSEY_LOGIN_URL)
    _request_text(opener, MONTGOMERY_ODYSSEY_DEFAULT_URL)
    search_html = _request_text(
        opener,
        MONTGOMERY_ODYSSEY_SEARCH_URL,
        data=_montgomery_search_launch_payload(),
        headers={"Referer": MONTGOMERY_ODYSSEY_DEFAULT_URL},
    )
    if _looks_like_montgomery_search_form(search_html):
        return search_html
    search_html = _request_text(
        opener,
        MONTGOMERY_ODYSSEY_SEARCH_URL,
        data=_montgomery_search_launch_payload(),
        headers={"Referer": MONTGOMERY_ODYSSEY_DEFAULT_URL},
    )
    if _looks_like_montgomery_search_form(search_html):
        return search_html
    raise RuntimeError("case-search form missing after Odyssey node launch POST")


def _montgomery_search_launch_payload() -> dict[str, str]:
    return {
        "NodeID": _MONTGOMERY_ALL_COUNTY_COURTS_NODE_ID,
        "NodeDesc": _MONTGOMERY_ALL_COUNTY_COURTS_NODE_DESC,
    }


def _prepare_montgomery_date_filed_probate_form(html_text: str, *, start: str, end: str) -> dict[str, str]:
    if not _looks_like_montgomery_search_form(html_text):
        raise RuntimeError("Montgomery Odyssey live source did not return the expected case-search form")
    form = _extract_form_defaults(html_text)
    form.update(
        {
            "NodeID": _MONTGOMERY_ALL_COUNTY_COURTS_NODE_ID,
            "NodeDesc": _MONTGOMERY_ALL_COUNTY_COURTS_NODE_DESC,
            "SearchBy": "6",
            "DateFiledOnAfter": start,
            "DateFiledOnBefore": end,
            "CaseStatusType": "0",
            "SortBy": "fileddate",
            "SearchSubmit": "Search",
            "SearchType": "CASE",
            "SearchMode": "FILED",
            "StatusType": "true",
            "AllStatusTypes": "true",
            "CaseCategories": "PR",
            "SearchParams": (
                "DateFiled~~Search By:~~6~~Date Filed"
                "||chkExactName~~Exact Name:~~on~~on"
                "||AllOption~~All~~0~~All"
                f"||DateFiledOnAfter~~Date Filed On or After:~~{start}~~{start}"
                f"||DateFiledOnBefore~~Date Filed On or Before:~~{end}~~{end}"
                "||CaseCategories~~Case Categories:~~PR~~Probate and Mental Health"
                "||selectSortBy~~Sort By:~~Filed Date~~Filed Date"
            ),
        }
    )
    for name in (
        "chkCriminal",
        "chkFamily",
        "chkCivil",
        "chkDtRangeCriminal",
        "chkDtRangeFamily",
        "chkDtRangeCivil",
        "chkCriminalMagist",
        "chkFamilyMagist",
        "chkCivilMagist",
    ):
        form.pop(name, None)
    for name in ("ExactName", "chkProbate", "chkDtRangeProbate", "chkProbateMagist"):
        form[name] = "on"
    return form


def _montgomery_fetch_from_results(*, response_html: str, source_url: str, start: str, end: str) -> CountyProbateSourceFetch:
    portal_record_count = _montgomery_record_count(response_html)
    rows = _parse_montgomery_probate_rows(response_html)
    normalized = probate_source_adapter_service.normalize_rows(rows, county="montgomery", source_uri=source_url)
    for row in normalized:
        row["source_portal"] = "montgomery_odyssey_public_access"
        row["source_adapter"] = "montgomery_county_probate_live_v1"
        row["source_adapter_version"] = PROBATE_LIVE_SOURCE_ADAPTER_VERSION
    warnings = [] if rows else ["montgomery_live_source_returned_no_probate_rows_for_window"]
    return CountyProbateSourceFetch(
        county="montgomery",
        source_url=source_url,
        rows=normalized,
        source_reported_count=len(normalized),
        raw_count=len(rows),
        parser_warnings=warnings,
        metadata={
            "date_from": start,
            "date_to": end,
            "portal_record_count_before_probate_filter": portal_record_count,
        },
    )


def _opener(
    *,
    cookie_jar: http.cookiejar.CookieJar | None = None,
) -> urllib.request.OpenerDirector:
    jar = cookie_jar or http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def _request_text(
    opener: urllib.request.OpenerDirector,
    url: str,
    *,
    data: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
) -> str:
    body = urllib.parse.urlencode({key: value for key, value in (data or {}).items() if value is not None}).encode(
        "utf-8"
    ) if data is not None else None
    request_headers = {
        "User-Agent": _HARRIS_USER_AGENT,
        **(dict(headers or {})),
    }
    if body is not None:
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=request_headers)
    with opener.open(request, timeout=45) as response:  # noqa: S310 - public county portals
        try:
            return response.read().decode("utf-8", errors="replace")
        except http.client.IncompleteRead as exc:
            return exc.partial.decode("utf-8", errors="replace")


class _FormParser(HTMLParser):
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
    parser = _FormParser()
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


def _looks_like_harris_results_page(html_text: str) -> bool:
    return "ListViewCases" in html_text and "btnSelect" in html_text


def _looks_like_montgomery_search_form(html_text: str) -> bool:
    return "SearchParameters" in html_text and "DateFiledOnAfter" in html_text and "chkProbate" in html_text


def _looks_like_montgomery_results_page(html_text: str) -> bool:
    return "Record Count" in html_text and "CaseDetail.aspx" in html_text and "Case Number" in html_text


def _parse_harris_probate_rows(html_text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"btnSelect[^>]*>\s*(?P<case>[^<]+)\s*</a>.*?"
        r"ListViewCases_ctrl(?P<idx>\d+)_Td9[^>]*>(?P<file_date>.*?)</td>.*?"
        r"ListViewCases_ctrl(?P=idx)_Td17[^>]*>(?P<status>.*?)</td>.*?"
        r"ListViewCases_ctrl(?P=idx)_Td8[^>]*>(?P<filing_type>.*?)</td>.*?"
        r"ListViewCases_ctrl(?P=idx)_Td7[^>]*>(?P<filing_subtype>.*?)</td>.*?"
        r"ListViewCases_ctrl(?P=idx)_TdStyle[^>]*>(?P<style>.*?)</td>",
        re.IGNORECASE | re.DOTALL,
    )
    rows: list[dict[str, Any]] = []
    for match in pattern.finditer(html_text):
        row = {key: _cell_text(match.group(key)) for key in ("case", "file_date", "status", "filing_type", "filing_subtype", "style")}
        rows.append(
            {
                "county": "harris",
                "case_number": row["case"],
                "file_date": row["file_date"],
                "status": row["status"],
                "filing_type": row["filing_type"],
                "filing_subtype": row["filing_subtype"],
                "style": row["style"],
                "source_url": HARRIS_PROBATE_SEARCH_URL,
                "raw_live_row": row,
            }
        )
    return rows


def _parse_montgomery_probate_rows(html_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_html in re.findall(r"<tr[^>]*>.*?</tr>", html_text, re.IGNORECASE | re.DOTALL):
        if "CaseDetail.aspx" not in row_html:
            continue
        cells = [_cell_text(cell) for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.IGNORECASE | re.DOTALL)]
        cells = [cell for cell in cells if cell or len(cells) >= 5]
        if len(cells) < 5:
            continue
        case_number = cells[0]
        style = cells[2]
        filed_location = cells[3]
        type_status = cells[4]
        if not _looks_like_montgomery_probate(case_number=case_number, filed_location=filed_location, type_status=type_status):
            continue
        file_date, court_number = _split_montgomery_filed_location(filed_location)
        filing_type, status = _split_montgomery_type_status(type_status)
        rows.append(
            {
                "county": "montgomery",
                "case_number": case_number,
                "file_date": file_date,
                "court_number": court_number,
                "status": status,
                "filing_type": filing_type,
                "style": style,
                "source_url": MONTGOMERY_ODYSSEY_SEARCH_URL,
                "raw_live_row": {
                    "case_number": case_number,
                    "style": style,
                    "filed_location": filed_location,
                    "type_status": type_status,
                },
            }
        )
    return rows


def _looks_like_montgomery_probate(*, case_number: str, filed_location: str, type_status: str) -> bool:
    haystack = f"{case_number} {filed_location} {type_status}".upper()
    return "PROBATE" in haystack or case_number.upper().endswith("-P") or any(
        token in haystack
        for token in (
            "ADMINISTRATION",
            "HEIRSHIP",
            "MUNIMENT",
            "LETTERS TESTAMENTARY",
            "WILL-INDEPENDENT",
            "WILL ANNEXED",
        )
    )


def _split_montgomery_filed_location(value: str) -> tuple[str | None, str | None]:
    match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", value)
    if not match:
        return None, value or None
    date_text = match.group(0)
    court = _clean_text(value.replace(date_text, " "))
    return date_text, court or None


def _split_montgomery_type_status(value: str) -> tuple[str, str | None]:
    normalized = _clean_text(value)
    for status in ("Active", "Pending", "Closed", "Disposed", "Inactive"):
        if normalized.upper().endswith(status.upper()):
            return normalized[: -len(status)].strip(" -"), status
    return normalized, None


def _montgomery_record_count(html_text: str) -> int | None:
    match = re.search(r"Record\s+Count\s*:?\s*</td>\s*<td[^>]*>\s*(\d+)", html_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    text = _clean_text(html_text)
    match = re.search(r"Record\s+Count\s*:?\s*(\d+)", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


def _date_window(window_start: Any, window_end: Any) -> tuple[date, date]:
    end = _coerce_date(window_end) or date.today()
    start = _coerce_date(window_start) or end
    if start > end:
        start, end = end, start
    return start, end


def _coerce_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    for parser in (datetime.fromisoformat,):
        try:
            return parser(text).date()
        except ValueError:
            pass
    try:
        return datetime.strptime(text, "%m/%d/%Y").date()
    except ValueError:
        return None


def _mmddyyyy(value: date) -> str:
    return value.strftime("%m/%d/%Y")


def _cell_text(value: str) -> str:
    with_breaks = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    return _clean_text(with_breaks)


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()
