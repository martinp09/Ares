import pytest

from app.services.probate_live_source_adapter_service import (
    MONTGOMERY_ODYSSEY_DEFAULT_URL,
    MONTGOMERY_ODYSSEY_LOGIN_URL,
    MONTGOMERY_ODYSSEY_SEARCH_URL,
    MontgomeryCountyProbateLiveAdapter,
    ProbateLiveSourceAdapterService,
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
            <td><a id="ctl00_ContentPlaceHolder1_ListViewCases_ctrl0_btnSelect">SYN-H-0001</a></td>
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
    assert "<table" not in str(rows)


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
