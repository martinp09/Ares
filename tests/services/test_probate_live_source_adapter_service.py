import pytest

from app.services.probate_live_source_adapter_service import (
    ProbateLiveSourceAdapterService,
    _parse_harris_probate_rows,
    _parse_montgomery_probate_rows,
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
