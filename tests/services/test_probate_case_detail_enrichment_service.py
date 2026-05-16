import pytest

from app.core.config import Settings
from app.services.probate_case_detail_enrichment_service import ProbateCaseDetailEnrichmentService


CASE_DETAIL_HTML = """
<html>
  <body>
    <h1>Case 2026-H-10001</h1>
    <table id="party-table">
      <tr><th>Party Type</th><th>Name</th><th>Address</th><th>Attorney</th></tr>
      <tr><td>Decedent</td><td>Jane Example</td><td>100 Estate Ave, Houston, TX</td><td></td></tr>
      <tr><td>Applicant / Proposed Independent Administrator</td><td>Alex Example</td><td>200 Living Contact Rd, Houston, TX</td><td>Pat Probate</td></tr>
      <tr><td>Heir</td><td>Blake Example</td><td>300 Heir Lane, Houston, TX</td><td></td></tr>
      <tr><td>Interested Party</td><td>Casey Example</td><td>400 Interested St, Houston, TX</td><td></td></tr>
    </table>
    <table id="event-table">
      <tr><th>Date</th><th>Event</th><th>Result</th></tr>
      <tr><td>05/20/2026</td><td>Hearing on Application</td><td>Scheduled</td></tr>
      <tr><td>05/21/2026</td><td>Publication Issued</td><td>Notice</td></tr>
    </table>
    <table id="documents">
      <tr><th>Filed</th><th>Document Type</th><th>Document Number</th></tr>
      <tr><td>05/15/2026</td><td>Application to Determine Heirship</td><td>D-1</td></tr>
      <tr><td>05/16/2026</td><td>Order Setting Hearing</td><td>D-2</td></tr>
    </table>
  </body>
</html>
"""


def test_case_detail_enrichment_extracts_evidence_and_caps_primary_contacts():
    service = ProbateCaseDetailEnrichmentService()

    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "county": "harris",
                "case_number": "2026-H-10001",
                "filing_type": "APP TO DETERMINE HEIRSHIP",
                "estate_name": "Estate of Jane Example",
                "decedent_name": "Jane Example",
                "keep_now": True,
            }
        ],
        case_details_by_case={
            "2026-H-10001": {
                "html": CASE_DETAIL_HTML,
                "source_url": "https://example.test/harris/CaseDetail.aspx?CaseID=10001",
            }
        },
    )

    assert result["no_send"] is True
    assert result["provider_sends_enabled"] is False
    assert result["outbound_allowed"] is False
    assert result["received_count"] == 1
    assert result["detail_completed_count"] == 1
    assert result["detail_incomplete_count"] == 0
    assert result["party_count"] == 4
    assert result["event_count"] == 2
    assert result["document_reference_count"] == 2
    assert result["contact_candidate_count"] == 3
    assert result["primary_contact_candidate_count"] == 2
    assert result["attorney_count"] == 1
    assert result["live_case_detail_calls_attempted"] is False

    record = result["records"][0]
    detail = record["case_detail"]
    assert detail["status"] == "completed"
    assert detail["source_url"] == "https://example.test/harris/CaseDetail.aspx?CaseID=10001"
    assert detail["parties"][0]["role"] == "decedent"
    assert detail["events"][0]["event_type"] == "Hearing on Application"
    assert detail["document_references"][0]["document_type"] == "Application to Determine Heirship"
    assert detail["hearing_clue_count"] == 2
    assert detail["publication_clue_count"] == 1

    primary_contacts = detail["primary_contact_candidates"]
    assert [candidate["name"] for candidate in primary_contacts] == ["Alex Example", "Blake Example"]
    assert all(candidate["is_confirmed_seller"] is False for candidate in primary_contacts)
    assert all(candidate["seller_authority_verified"] is False for candidate in primary_contacts)
    assert "Jane Example" not in [candidate["name"] for candidate in detail["contact_candidates"]]
    assert record["pain_stack"]["case_detail"]["status"] == "completed"


def test_case_detail_enrichment_marks_list_view_only_rows_incomplete_without_inventing_contacts():
    service = ProbateCaseDetailEnrichmentService()

    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "county": "montgomery",
                "case_number": "2026-M-10002-P",
                "filing_type": "Independent Administration",
                "style": "Estate of List View Only",
                "keep_now": True,
            }
        ],
    )

    assert result["detail_completed_count"] == 0
    assert result["detail_incomplete_count"] == 1
    assert result["contact_candidate_count"] == 0
    detail = result["records"][0]["case_detail"]
    assert detail["status"] == "incomplete"
    assert detail["incomplete_reason"] == "case_detail_not_available"
    assert detail["primary_contact_candidates"] == []
    assert detail["contact_candidates"] == []
    assert detail["no_send"] is True
    assert detail["provider_sends_enabled"] is False


class FakeCaseDetailClient:
    def __init__(self) -> None:
        self.calls = []

    def fetch_case_detail(self, *, source_row):
        self.calls.append(source_row["case_number"])
        return {"html": CASE_DETAIL_HTML, "source_url": source_row["case_detail_url"]}


def test_case_detail_enrichment_requires_no_send_approval_before_live_client_call():
    client = FakeCaseDetailClient()
    service = ProbateCaseDetailEnrichmentService(
        settings=Settings(_env_file=None, lead_machine_live_case_detail_calls_enabled=True),
        case_detail_client=client,
    )

    with pytest.raises(RuntimeError, match="case_detail_approval.approved=true"):
        service.run_enrichment(
            business_id="limitless",
            environment="test",
            keep_now_rows=[
                {
                    "county": "harris",
                    "case_number": "2026-H-10003",
                    "filing_type": "Independent Administration",
                    "case_detail_url": "https://www.cclerk.hctx.net/Applications/WebSearch/CaseDetail.aspx?CaseID=10003",
                    "keep_now": True,
                }
            ],
            live_case_detail_calls=True,
        )

    assert client.calls == []


def test_case_detail_enrichment_blocks_unapproved_live_detail_urls_before_client_call():
    client = FakeCaseDetailClient()
    service = ProbateCaseDetailEnrichmentService(
        settings=Settings(_env_file=None, lead_machine_live_case_detail_calls_enabled=True),
        case_detail_client=client,
    )

    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "county": "harris",
                "case_number": "2026-H-10005",
                "filing_type": "Independent Administration",
                "case_detail_url": "http://169.254.169.254/latest/meta-data/",
                "keep_now": True,
            }
        ],
        live_case_detail_calls=True,
        case_detail_approval={
            "approved": True,
            "approved_by": "operator",
            "no_send": True,
            "provider_sends_enabled": False,
        },
    )

    assert client.calls == []
    assert result["detail_blocked_count"] == 1
    assert result["records"][0]["case_detail"]["status"] == "blocked"
    assert result["records"][0]["case_detail"]["warnings"] == ["case_detail_url_not_allowed"]


def test_case_detail_enrichment_uses_live_client_with_explicit_no_send_approval():
    client = FakeCaseDetailClient()
    service = ProbateCaseDetailEnrichmentService(
        settings=Settings(_env_file=None, lead_machine_live_case_detail_calls_enabled=True),
        case_detail_client=client,
    )

    result = service.run_enrichment(
        business_id="limitless",
        environment="test",
        keep_now_rows=[
            {
                "county": "harris",
                "case_number": "2026-H-10004",
                "filing_type": "Independent Administration",
                "case_detail_url": "https://www.cclerk.hctx.net/Applications/WebSearch/CaseDetail.aspx?CaseID=10004",
                "keep_now": True,
            }
        ],
        live_case_detail_calls=True,
        case_detail_approval={
            "approved": True,
            "approved_by": "operator",
            "no_send": True,
            "provider_sends_enabled": False,
        },
    )

    assert client.calls == ["2026-H-10004"]
    assert result["live_case_detail_calls_attempted"] is True
    assert result["detail_completed_count"] == 1
    assert result["records"][0]["case_detail"]["status"] == "completed"
