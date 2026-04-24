from __future__ import annotations

from app.domains.ares.models import AresCounty
from app.services.tax_overlay_service import (
    ActWebTaxDetailParser,
    HarrisTaxStatementParser,
    TaxOverlayStatus,
    TravisTaxSearchAdapter,
)


def test_harris_parser_extracts_owner_from_assessed_owner_label_not_page_date() -> None:
    html = """
    <html><body>
      <div>April 23, 2026</div>
      <table>
        <tr><th>Account Number</th><td>1091100001181</td></tr>
        <tr><td>Assessed Owner</td><td>WILLIAMS TANGIE<br />1407 GREEN TRAIL DR<br />HOUSTON TX 77038</td></tr>
        <tr><td>Property Address</td><td>1407 GREEN TRAIL DR</td></tr>
        <tr><td>Total Market Value</td><td>$245,311.00</td></tr>
        <tr><td>Total Amount Due</td><td>$0.00</td></tr>
      </table>
      <p>No Delinquent Taxes Exist</p>
    </body></html>
    """

    result = HarrisTaxStatementParser().parse(html, account="1091100001181")

    assert result.county == AresCounty.HARRIS
    assert result.account == "1091100001181"
    assert result.owner_name == "WILLIAMS TANGIE"
    assert result.property_address == "1407 GREEN TRAIL DR"
    assert result.status == TaxOverlayStatus.VERIFIED_CURRENT
    assert result.is_delinquent is False
    assert result.amount_owed == 0
    assert result.tax_value == 245311
    assert result.confidence == "high"
    assert result.parser_warnings == []


def test_harris_parser_handles_header_row_layout_from_live_statement() -> None:
    html = """
    <html><body>
      <table class="values">
        <tr>
          <td class="Subtitle">Account Number</td>
          <td class="Subtitle">Current As Of:</td>
          <td class="Subtitle">Assessed Owner</td>
        </tr>
        <tr>
          <td class="Subtitle-Account"><b>109-110-000-1181</b></td>
          <td>April 23, 2026</td>
          <td>WILLIAMS TANGIE<br />1407 GREEN TRAIL DR<br />HOUSTON TX 77038-1744</td>
        </tr>
      </table>
      <table class="values">
        <tr>
          <td class="Subtitle">Property Description</td>
          <td class="Subtitle">Appraised Values</td>
        </tr>
        <tr>
          <td>1407 GREEN TRAIL DR 77038<br />LT 1181 BLK 24<br />FALLBROOK SEC 3</td>
          <td><table><tr><td>Total Market Value:</td><td>214,867</td></tr></table></td>
        </tr>
      </table>
      <table><tr><td>Total Amount Due for April 2026</td><td>$0.00</td></tr></table>
      <span>Account is Paid</span>
    </body></html>
    """

    result = HarrisTaxStatementParser().parse(html, account="1091100001181")

    assert result.owner_name == "WILLIAMS TANGIE"
    assert result.property_address == "1407 GREEN TRAIL DR"
    assert result.status == TaxOverlayStatus.VERIFIED_CURRENT
    assert result.tax_value == 214867


def test_harris_parser_marks_delinquent_when_prior_year_due_exists() -> None:
    html = """
    <html><body>
      <table>
        <tr><td>Assessed Owner</td><td>ESTATE OF JANE DOE</td></tr>
        <tr><td>Total Market Value</td><td>$200,000.00</td></tr>
        <tr><td>Total Current Taxes Due</td><td>$1,250.50</td></tr>
        <tr><td>Prior year taxes due</td><td>$4,000.25</td></tr>
        <tr><td>Total Amount Due</td><td>$5,250.75</td></tr>
      </table>
      <strong>Delinquent Taxes Exist</strong>
    </body></html>
    """

    result = HarrisTaxStatementParser().parse(html, account="0000000000001")

    assert result.status == TaxOverlayStatus.VERIFIED_DELINQUENT
    assert result.is_delinquent is True
    assert result.amount_owed == 5250.75
    assert result.current_year_owed == 1250.50
    assert result.prior_years_owed == 4000.25
    assert result.tax_to_value_pct == 2.63


def test_harris_parser_uses_ambiguous_status_when_required_fields_are_missing() -> None:
    html = "<html><body><p>No Delinquent Taxes Exist</p></body></html>"

    result = HarrisTaxStatementParser().parse(html, account="1091100001181")

    assert result.status == TaxOverlayStatus.AMBIGUOUS
    assert result.is_delinquent is False
    assert "missing_owner_name" in result.parser_warnings
    assert "missing_tax_value" in result.parser_warnings


def test_travis_adapter_posts_quick_search_and_parses_result_cards() -> None:
    calls: list[tuple[str, dict[str, str]]] = []
    html = """
    <html><body>
      <div class="result">
        <a href="/cart/responsive/accountDetail.do?account=01150409100000">01150409100000</a>
        <span>DOE JANE ESTATE</span>
        <span>123 MAIN ST</span>
        <span>Total Due: $3,210.45</span>
      </div>
    </body></html>
    """

    def post(url: str, data: dict[str, str]) -> str:
        calls.append((url, data))
        return html

    adapter = TravisTaxSearchAdapter(post=post)
    results = adapter.quick_search("DOE JANE")

    assert calls == [
        (
            "https://travis.go2gov.net/cart/responsive/quickSearch.do",
            {
                "formViewMode": "responsive",
                "criteria.searchStatus": "1",
                "pager.pageSize": "10",
                "pager.pageNumber": "1",
                "criteria.heuristicSearch": "DOE JANE",
            },
        )
    ]
    assert len(results) == 1
    result = results[0]
    assert result.county == AresCounty.TRAVIS
    assert result.account == "01150409100000"
    assert result.owner_name == "DOE JANE ESTATE"
    assert result.property_address == "123 MAIN ST"
    assert result.amount_owed == 3210.45
    assert result.status == TaxOverlayStatus.SOFT_SIGNAL
    assert result.is_delinquent is None
    assert result.source_url == "https://travis.go2gov.net/cart/responsive/accountDetail.do?account=01150409100000"


def test_travis_parser_handles_official_results_table_row() -> None:
    from app.services.tax_overlay_service import TravisTaxSearchParser

    html = """
    <table id="searchResultsTable">
      <tbody>
        <tr>
          <td>
            <div><a href="/showPropertyInfo.do?account=01150409100000"><span>01150409100000</span></a></div>
            <div>BARRY ALEX T</div>
            <div class="mobile-view"><span class="color-green-dark">$0.00</span></div>
            <div class="mobile-view">1901 VISTA LN</div>
          </td>
          <td class="mobile-hide-td">
            <div><span class="color-green-dark">$0.00</span></div>
            <div>1901 VISTA LN</div>
          </td>
        </tr>
      </tbody>
    </table>
    """

    results = TravisTaxSearchParser().parse(html)

    assert len(results) == 1
    assert results[0].account == "01150409100000"
    assert results[0].owner_name == "BARRY ALEX T"
    assert results[0].property_address == "1901 VISTA LN"
    assert results[0].amount_owed == 0


def test_act_web_parser_extracts_dallas_or_montgomery_detail_page() -> None:
    html = """
    <html><body>
      <table>
        <tr><td>Account No.</td><td>00000799731740000</td></tr>
        <tr><td>Owner Name</td><td>ESTATE OF SAMPLE OWNER</td></tr>
        <tr><td>Property Site Address</td><td>500 ELM ST</td></tr>
        <tr><td>Base Tax</td><td>$1,000.00</td></tr>
        <tr><td>Penalty & Interest</td><td>$250.00</td></tr>
        <tr><td>Total Due</td><td>$1,250.00</td></tr>
      </table>
    </body></html>
    """

    result = ActWebTaxDetailParser(county=AresCounty.DALLAS).parse(
        html,
        source_url="https://www.dallasact.com/act_webdev/dallas/showdetail2.jsp?can=00000799731740000&ownerno=0",
    )

    assert result.county == AresCounty.DALLAS
    assert result.account == "00000799731740000"
    assert result.owner_name == "ESTATE OF SAMPLE OWNER"
    assert result.property_address == "500 ELM ST"
    assert result.status == TaxOverlayStatus.VERIFIED_DELINQUENT
    assert result.is_delinquent is True
    assert result.amount_owed == 1250
    assert result.confidence == "high"
