import pytest

from app.services.probate_source_adapter_service import probate_source_adapter_service
from app.services.probate_live_source_adapter_service import (
    MONTGOMERY_ODYSSEY_DEFAULT_URL,
    MONTGOMERY_ODYSSEY_LOGIN_URL,
    MONTGOMERY_ODYSSEY_SEARCH_URL,
    MontgomeryCountyProbateLiveAdapter,
    ProbateLiveSourceAdapterService,
    _looks_like_harris_results_page,
    _looks_like_montgomery_results_page,
    _parse_harris_probate_rows,
    _parse_montgomery_probate_rows,
    _prepare_montgomery_date_filed_probate_form,
)


def test_live_source_adapter_service_requires_env_gate_before_network():
    with pytest.raises(RuntimeError, match="LEAD_MACHINE_LIVE_SOURCE_CALLS_ENABLED=true"):
        ProbateLiveSourceAdapterService().fetch_window(
            counties=["harris"],
            window_start="2026-05-14T00:00:00+00:00",
            window_end="2026-05-15T00:00:00+00:00",
            source_provider_approval={"approved": True},
        )


def test_live_source_adapter_service_requires_explicit_approval_before_network():
    with pytest.raises(RuntimeError, match="source_provider_approval.approved=true"):
        ProbateLiveSourceAdapterService().fetch_window(
            counties=["harris"],
            window_start="2026-05-14T00:00:00+00:00",
            window_end="2026-05-15T00:00:00+00:00",
            live_source_calls_enabled=True,
            source_provider_approval={"approved": False},
        )


def test_live_source_adapter_service_requires_explicit_no_send_approval_before_network(monkeypatch):
    monkeypatch.setattr(
        "app.services.probate_live_source_adapter_service._date_window",
        lambda window_start, window_end: (_ for _ in ()).throw(AssertionError("date window should not be parsed before approval gate")),
    )

    with pytest.raises(RuntimeError, match="source_provider_approval.no_send=true"):
        ProbateLiveSourceAdapterService().fetch_window(
            counties=["harris"],
            window_start="2026-05-14T00:00:00+00:00",
            window_end="2026-05-15T00:00:00+00:00",
            live_source_calls_enabled=True,
            source_provider_approval={"approved": True},
        )


def test_harris_live_parser_extracts_public_probate_rows_without_html_artifacts():
    rows = _parse_harris_probate_rows(
        """
        <table id="ctl00_ContentPlaceHolder1_ListViewCases">
          <tr>
            <td><a id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_btnSelect" href="javascript:__doPostBack('ctl00$ContentPlaceHolder1$ListViewCases$ctrl0$btnSelect','')">SYN-H-0001</a></td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td9">05/14/2026</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td17">Open</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td8">INDEPENDENT ADMINISTRATION</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td7">LETTERS TESTAMENTARY</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_TdStyle">IN THE ESTATE OF: SAMPLE TEST OWNER, DECEASED</td>
          </tr>
        </table>
        """
    )

    assert rows == [
        {
            "county": "harris",
            "case_number": "SYN-H-0001",
            "file_date": "05/14/2026",
            "status": "Open",
            "filing_type": "INDEPENDENT ADMINISTRATION",
            "filing_subtype": "LETTERS TESTAMENTARY",
            "style": "IN THE ESTATE OF: SAMPLE TEST OWNER, DECEASED",
            "case_detail_postback_target": "ctl00$ContentPlaceHolder1$ListViewCases$ctrl0$btnSelect",
            "case_detail_source_url": "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch_R.aspx?CaseType=Probate",
            "source_url": "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch_R.aspx?CaseType=Probate",
            "raw_live_row": {
                "case": "SYN-H-0001",
                "file_date": "05/14/2026",
                "status": "Open",
                "filing_type": "INDEPENDENT ADMINISTRATION",
                "filing_subtype": "LETTERS TESTAMENTARY",
                "style": "IN THE ESTATE OF: SAMPLE TEST OWNER, DECEASED",
            },
        }
    ]
    assert "<table" not in str(rows)


def test_harris_live_parser_uses_same_row_postback_target_not_page_loginstatus():
    rows = _parse_harris_probate_rows(
        """
        <a id="ctl00_LoginStatus1" href="javascript:__doPostBack('ctl00$LoginStatus1$ctl00','')">Login</a>
        <table id="ctl00_ContentPlaceHolder1_ListViewCases">
          <tr>
            <td><a id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_btnSelect" href="javascript:__doPostBack('ctl00$ContentPlaceHolder1$ListViewCases$ctrl0$btnSelect','')">SYN-H-0002</a></td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td9">05/15/2026</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td17">Open</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td8">MUNIMENT OF TITLE</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_Td7">LETTERS TESTAMENTARY</td>
            <td id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_TdStyle">IN THE ESTATE OF: SAMPLE TWO, DECEASED</td>
          </tr>
        </table>
        """
    )

    assert len(rows) == 1
    assert rows[0]["case_number"] == "SYN-H-0002"
    assert rows[0]["case_detail_postback_target"] == "ctl00$ContentPlaceHolder1$ListViewCases$ctrl0$btnSelect"


def test_probate_source_adapter_preserves_harris_postback_fields_top_level():
    normalized = probate_source_adapter_service.normalize_row(
        {
            "case_number": "SYN-H-0003",
            "file_date": "05/15/2026",
            "style": "IN THE ESTATE OF: SAMPLE THREE, DECEASED",
            "case_detail_postback_target": "ctl00$ContentPlaceHolder1$ListViewCases$ctrl2$btnSelect",
            "case_detail_source_url": "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch_R.aspx?CaseType=Probate",
        },
        county="harris",
        source_uri="https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch_R.aspx?CaseType=Probate",
        row_index=1,
    )

    assert normalized["case_detail_postback_target"] == "ctl00$ContentPlaceHolder1$ListViewCases$ctrl2$btnSelect"
    assert normalized["case_detail_source_url"] == "https://www.cclerk.hctx.net/Applications/WebSearch/CourtSearch_R.aspx?CaseType=Probate"
    assert normalized["raw_export_row"]["case_detail_postback_target"] == "ctl00$ContentPlaceHolder1$ListViewCases$ctrl2$btnSelect"


def test_harris_results_page_accepts_zero_row_search_results():
    zero_results = """
    <table id="ctl00_ContentPlaceHolder1_ListViewCases">
    </table>
    <input id="ctl00_ContentPlaceHolder1_txtDateFrom" value="05/16/2026" />
    """

    assert _looks_like_harris_results_page(zero_results)
    assert _parse_harris_probate_rows(zero_results) == []


def test_montgomery_live_parser_filters_to_probate_case_rows():
    rows = _parse_montgomery_probate_rows(
        """
        <table>
          <tr><th>Case Number</th><th>Citation Number</th><th>Style/Defendant Info</th><th>Filed/Location</th><th>Type/Status</th></tr>
          <tr>
            <td><a href="CaseDetail.aspx?CaseID=1">SYN-CIV-0001</a></td><td></td>
            <td>Sample Civil Plaintiff vs. Sample Civil Defendant</td>
            <td>05/14/2026 County Court at Law #6</td>
            <td>Eviction Pending</td>
          </tr>
          <tr>
            <td><a href="CaseDetail.aspx?CaseID=2">SYN-M-0001-P</a></td><td></td>
            <td>Estate of: SAMPLE MONTGOMERY OWNER</td>
            <td>05/14/2026 Probate Court #1</td>
            <td>Administration-Heirship-Independent Active</td>
          </tr>
        </table>
        """
    )

    assert len(rows) == 1
    assert rows[0]["county"] == "montgomery"
    assert rows[0]["case_number"] == "SYN-M-0001-P"
    assert rows[0]["file_date"] == "05/14/2026"
    assert rows[0]["court_number"] == "Probate Court #1"
    assert rows[0]["filing_type"] == "Administration-Heirship-Independent"
    assert rows[0]["status"] == "Active"
    assert rows[0]["style"] == "Estate of: SAMPLE MONTGOMERY OWNER"
    assert rows[0]["case_detail_url"] == "https://odyssey.mctx.org/County/CaseDetail.aspx?CaseID=2"
    assert "<table" not in str(rows)


def test_montgomery_results_page_accepts_zero_record_count_without_case_links():
    zero_results = """
    <table><tr><td>Record Count:</td><td>0</td></tr></table>
    <table>
      <tr><th>Case Number</th><th>Citation Number</th><th>Style/Defendant Info</th><th>Filed/Location</th><th>Type/Status</th></tr>
    </table>
    """

    assert _looks_like_montgomery_results_page(zero_results)
    assert _parse_montgomery_probate_rows(zero_results) == []


def test_montgomery_date_filed_probate_form_posts_probate_category_only():
    form = _prepare_montgomery_date_filed_probate_form(
        """
        <form name="SearchParameters">
          <input type="hidden" name="__VIEWSTATE" value="state" />
          <input type="radio" name="SearchBy" value="1" checked="checked" />
          <input type="radio" name="CaseStatusType" value="0" checked="checked" />
          <input type="checkbox" name="chkCivil" checked="checked" />
          <input type="checkbox" name="chkProbate" id="chkProbate" checked="checked" />
          <input type="text" name="DateFiledOnAfter" id="DateFiledOnAfter" />
          <input type="text" name="DateFiledOnBefore" id="DateFiledOnBefore" />
          <input type="hidden" name="SearchType" value="" />
          <input type="hidden" name="SearchMode" value="" />
          <input type="hidden" name="StatusType" value="" />
          <input type="hidden" name="AllStatusTypes" value="" />
          <input type="hidden" name="CaseCategories" value="" />
          <input type="hidden" name="SearchParams" value="" />
          <select name="SortBy"><option value="fileddate" selected="selected">Filed Date</option></select>
        </form>
        """,
        start="05/15/2026",
        end="05/15/2026",
    )

    assert form["SearchBy"] == "6"
    assert form["SearchType"] == "CASE"
    assert form["SearchMode"] == "FILED"
    assert form["CaseCategories"] == "PR"
    assert form["chkProbate"] == "on"
    assert "chkCivil" not in form
    assert "CaseCategories~~Case Categories:~~PR~~Probate and Mental Health" in form["SearchParams"]


def test_montgomery_live_adapter_launches_case_search_with_node_post(monkeypatch):
    calls = []
    search_form_html = """
    <form name="SearchParameters">
      <input type="hidden" name="__VIEWSTATE" value="state" />
      <input type="radio" name="SearchBy" value="1" checked="checked" />
      <input type="radio" name="CaseStatusType" value="0" checked="checked" />
      <input type="checkbox" name="chkProbate" id="chkProbate" checked="checked" />
      <input type="text" name="DateFiledOnAfter" id="DateFiledOnAfter" />
      <input type="text" name="DateFiledOnBefore" id="DateFiledOnBefore" />
      <input type="hidden" name="SearchType" value="" />
      <input type="hidden" name="SearchMode" value="" />
      <input type="hidden" name="StatusType" value="" />
      <input type="hidden" name="AllStatusTypes" value="" />
      <input type="hidden" name="CaseCategories" value="" />
      <input type="hidden" name="SearchParams" value="" />
      <select name="SortBy"><option value="fileddate" selected="selected">Filed Date</option></select>
    </form>
    """
    results_html = """
    <table><tr><td>Record Count:</td><td>1</td></tr></table>
    <table>
      <tr><th>Case Number</th><th>Citation Number</th><th>Style/Defendant Info</th><th>Filed/Location</th><th>Type/Status</th></tr>
      <tr>
        <td><a href="CaseDetail.aspx?CaseID=2">SYN-M-0001-P</a></td><td></td>
        <td>Estate of: SAMPLE MONTGOMERY OWNER</td>
        <td>05/15/2026 Probate Court #1</td>
        <td>Administration-Heirship-Independent Active</td>
      </tr>
    </table>
    """

    def fake_opener(*, cookie_jar=None):
        return object()

    def fake_request_text(opener, url, *, data=None, headers=None):
        calls.append({"url": url, "data": dict(data or {}), "headers": dict(headers or {})})
        if url == MONTGOMERY_ODYSSEY_LOGIN_URL:
            return '<a href="javascript:LaunchSearch(\'Search.aspx?ID=200\', false, true, sbxControlID2)">Civil &amp; Probate Case Records</a>'
        if url == MONTGOMERY_ODYSSEY_DEFAULT_URL:
            return '<a href="javascript:LaunchSearch(\'Search.aspx?ID=200\', false, true, sbxControlID2)">Civil &amp; Probate Case Records</a>'
        if url == MONTGOMERY_ODYSSEY_SEARCH_URL and data == {
            "NodeID": "100,105,110,120,130,140,150,160,180",
            "NodeDesc": "All County Courts",
        }:
            return search_form_html
        if url == MONTGOMERY_ODYSSEY_SEARCH_URL and data and data.get("SearchSubmit") == "Search":
            return results_html
        raise AssertionError(f"unexpected request: {url} {data}")

    monkeypatch.setattr("app.services.probate_live_source_adapter_service._opener", fake_opener)
    monkeypatch.setattr("app.services.probate_live_source_adapter_service._request_text", fake_request_text)

    fetched = MontgomeryCountyProbateLiveAdapter().fetch(start_date=__import__("datetime").date(2026, 5, 15), end_date=__import__("datetime").date(2026, 5, 15))

    assert fetched.raw_count == 1
    assert fetched.rows[0]["source_adapter"] == "montgomery_county_probate_live_v1"
    assert calls[0]["url"] == MONTGOMERY_ODYSSEY_LOGIN_URL
    assert calls[1]["url"] == MONTGOMERY_ODYSSEY_DEFAULT_URL
    assert calls[2]["url"] == MONTGOMERY_ODYSSEY_SEARCH_URL
    assert calls[2]["data"] == {"NodeID": "100,105,110,120,130,140,150,160,180", "NodeDesc": "All County Courts"}
    assert calls[3]["data"]["SearchBy"] == "6"
    assert calls[3]["data"]["CaseCategories"] == "PR"
