from pathlib import Path
from typing import Any

import pytest

from app.core.config import Settings
from app.db.source_runs import SourceRunsPersistenceError, SourceRunsRepository
from app.models.slack_notifications import SlackNotificationAttempt
from app.models.source_runs import MorningBriefRequest, NightlySourcePullRequest, SourceRunArtifact, SourceRunManifest, SourceRunStatus
from app.services.nightly_lead_machine_service import NightlyLeadMachineService
from app.services.probate_autopilot_manifest_service import probate_source_identity_key


class StubSlackNotifier:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def notify(self, **kwargs: Any) -> SlackNotificationAttempt:
        self.calls.append(kwargs)
        return SlackNotificationAttempt(
            business_id=kwargs["business_id"],
            environment=kwargs["environment"],
            route=kwargs["route"],
            dedupe_key=kwargs["dedupe_key"],
            channel_id=f"C-{kwargs['route']}",
            status="sent",
            slack_message_ts=f"ts-{len(self.calls)}",
            payload=kwargs.get("payload") or {},
        )


class StubEnrichmentService:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result

    def run_enrichment(self, **_kwargs: Any) -> dict[str, Any]:
        return self.result


def _visible_block_text(call: dict[str, Any]) -> str:
    parts: list[str] = []
    for block in call["blocks"]:
        text = block.get("text") if isinstance(block, dict) else None
        if isinstance(text, dict):
            parts.append(str(text.get("text") or ""))
        fields = block.get("fields") if isinstance(block, dict) else None
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, dict):
                    parts.append(str(field.get("text") or ""))
    return "\n".join(parts)


@pytest.fixture(autouse=True)
def stub_default_slack_notifier(monkeypatch: pytest.MonkeyPatch) -> StubSlackNotifier:
    stub = StubSlackNotifier()
    monkeypatch.setattr("app.services.nightly_lead_machine_service.slack_notification_service", stub)
    return stub


@pytest.fixture
def service() -> NightlyLeadMachineService:
    return NightlyLeadMachineService(repository=SourceRunsRepository())


def _hot_enrichment_payload(idempotency_key: str = "slack-hot-run", hot_count: int = 1) -> NightlySourcePullRequest:
    source_rows = []
    case_details_by_case: dict[str, Any] = {}
    hcad_candidates_by_case: dict[str, Any] = {}
    tax_overlays_by_account: dict[str, Any] = {}
    land_record_rows_by_case: dict[str, Any] = {}
    for index in range(hot_count):
        case_number = f"5437{index:02d}"
        decedent_name = "Jane Hot" if index == 0 else f"Jane Hot {index}"
        owner_name = decedent_name
        mailing_address = f"{100 + index} Contact Rd, Houston, TX"
        property_address = (
            "900 Probate Property St, Houston, TX"
            if index == 0
            else f"{900 + index} Probate Property St, Houston, TX"
        )
        account = f"1234000{index + 3:03d}"
        source_rows.append(
            {
                "case_number": case_number,
                "filing_type": "APP TO DETERMINE HEIRSHIP",
                "style": f"Estate of {decedent_name}",
                "decedent_name": decedent_name,
                "owner_name": owner_name,
                "mailing_address": mailing_address,
                "property_address": property_address,
            }
        )
        case_details_by_case[case_number] = {
            "parties": [
                {"role": "Applicant", "name": "Alex Hot", "address": mailing_address},
                {"role": "Decedent", "name": decedent_name},
            ],
        }
        hcad_candidates_by_case[case_number] = [
            {
                "acct": f"000{account}",
                "owner_name": owner_name,
                "mailing_address": mailing_address,
                "property_address": property_address,
            }
        ]
        tax_overlays_by_account[account] = {
            "status": "tax_overlay_verified_delinquent",
            "is_delinquent": True,
            "amount_owed": 5250,
            "account": account,
            "confidence": "high",
        }
        land_record_rows_by_case[case_number] = [
            {
                "instrument_number": f"RP-2026-{index + 1}",
                "instrument_type": "Affidavit of Heirship",
                "grantor": decedent_name,
                "grantee": "Hot Heirs",
            }
        ]
    return NightlySourcePullRequest(
        business_id="biz",
        environment="prod",
        idempotency_key=idempotency_key,
        metadata={
            "autopilot": "harris_montgomery_probate",
            "run_kind": "morning_catchup",
            "window_end": "2026-05-15T07:10:00+00:00",
            "county_scope": ["harris"],
            "source_rows": {"harris": source_rows},
            "case_detail_enrichment": {"case_details_by_case": case_details_by_case},
            "property_tax_title_enrichment": {
                "hcad_candidates_by_case": hcad_candidates_by_case,
                "tax_overlays_by_account": tax_overlays_by_account,
                "land_record_rows_by_case": land_record_rows_by_case,
            },
        },
    )


def test_manifest_backed_run_creates_source_runs_artifacts_and_brief(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz-1",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="probate-2026-05-14",
                    source_label="Harris probate fixture",
                    source_lane="harris_county_probate",
                    artifacts=[
                        SourceRunArtifact(
                            path="artifacts/probate.jsonl",
                            artifact_type="fixture_jsonl",
                            record_count=3,
                            checksum="abc123",
                            metadata={"hot_lead_count": 1, "warm_lead_count": 2, "approval_required_count": 1},
                        )
                    ],
                )
            ],
        )
    )

    assert result.would_call_external_sources is False
    assert result.live_source_calls_enabled is False
    assert len(result.source_runs) == 1
    run = result.source_runs[0]
    assert run.status == SourceRunStatus.COMPLETED
    assert run.artifact_count == 1
    assert run.record_count == 3
    assert run.artifacts[0].path == "artifacts/probate.jsonl"
    assert result.morning_brief.new_record_count == 3
    assert result.morning_brief.hot_lead_count == 1
    assert result.morning_brief.warm_lead_count == 2
    assert result.morning_brief.approval_required_count == 1


def test_default_service_fixture_uses_stubbed_slack_notifier(stub_default_slack_notifier: StubSlackNotifier):
    service = NightlyLeadMachineService(repository=SourceRunsRepository())

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="safe-default",
                    source_label="Safe default",
                    source_lane="harris_county_probate",
                    record_count=1,
                )
            ],
        )
    )

    assert [call["route"] for call in stub_default_slack_notifier.calls] == ["lead_runs"]
    assert result.notifications[0]["channel_id"] == "C-lead_runs"


def test_nightly_source_pull_posts_lead_run_digest_and_hot_lead_notification():
    notifier = StubSlackNotifier()
    service = NightlyLeadMachineService(repository=SourceRunsRepository(), slack_notifier=notifier)

    result = service.run_nightly_source_pull(_hot_enrichment_payload())

    assert [call["route"] for call in notifier.calls] == ["lead_runs", "hot_leads"]
    assert [notice["route"] for notice in result.notifications] == ["lead_runs", "hot_leads"]
    assert all(notice["status"] == "sent" for notice in result.notifications)
    lead_digest = notifier.calls[0]["payload"]
    assert lead_digest["run_counts"]["total"] == len(result.source_runs)
    assert lead_digest["run_counts"]["failed"] == 0
    assert lead_digest["new_record_count"] == 1
    assert lead_digest["hot_lead_count"] == 1
    assert lead_digest["warm_lead_count"] == 0
    assert lead_digest["source_summary"]["counties"] == [{"county": "harris", "run_count": 5, "record_count": 1}]
    lead_blocks = _visible_block_text(notifier.calls[0])
    assert "Lane summary" in lead_blocks
    assert "harris_county_probate" in lead_blocks
    assert "County summary" in lead_blocks
    assert "harris: 1 records" in lead_blocks
    hot_payload = notifier.calls[1]["payload"]
    assert hot_payload["hot_leads"][0]["score"] >= 70
    assert hot_payload["hot_leads"][0]["case_number"] == "543700"
    assert hot_payload["hot_leads"][0]["property_address"] == "900 Probate Property St, Houston, TX"
    assert hot_payload["hot_leads"][0]["owner_name"] == "Jane Hot"
    assert hot_payload["hot_leads"][0]["decedent_name"] == "Jane Hot"
    assert hot_payload["hot_leads"][0]["contact_hint"] == "Alex Hot"
    assert hot_payload["next_action"] == "Review enriched probate lead before any outreach approval."
    hot_blocks = _visible_block_text(notifier.calls[1])
    assert "Decedent: Jane Hot" in hot_blocks
    assert "Next action: Review enriched probate lead before any outreach approval." in hot_blocks


def test_temperature_hot_record_with_low_score_still_posts_hot_leads_notification():
    notifier = StubSlackNotifier()
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        slack_notifier=notifier,
        enrichment_service=StubEnrichmentService(
            {
                "records": [
                    {
                        "case_number": "TEMP-HOT-1",
                        "filing_type": "Small Estate",
                        "lead_score": 30,
                        "temperature": "hot",
                        "county": "harris",
                        "owner_name": "Low Score Owner",
                        "decedent_name": "Low Score Decedent",
                        "property_address": "1 Low Score St, Houston, TX",
                        "raw_payload": {"source_row": {"county": "harris"}},
                    }
                ]
            }
        ),
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="temperature-hot-low-score",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {
                            "case_number": "TEMP-HOT-1",
                            "filing_type": "APP TO DETERMINE HEIRSHIP",
                            "style": "Estate of Low Score Decedent",
                        }
                    ]
                },
            },
        )
    )

    assert [call["route"] for call in notifier.calls] == ["lead_runs", "hot_leads"]
    assert [notice["route"] for notice in result.notifications] == ["lead_runs", "hot_leads"]
    assert notifier.calls[1]["payload"]["hot_leads"][0]["case_number"] == "TEMP-HOT-1"


def test_hot_lead_payload_and_visible_blocks_include_phone_and_email():
    notifier = StubSlackNotifier()
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        slack_notifier=notifier,
        enrichment_service=StubEnrichmentService(
            {
                "records": [
                    {
                        "case_number": "CONTACT-HOT-1",
                        "filing_type": "APP TO DETERMINE HEIRSHIP",
                        "lead_score": 92,
                        "county": "harris",
                        "owner_name": "Contact Owner",
                        "decedent_name": "Contact Decedent",
                        "property_address": "2 Contact St, Houston, TX",
                        "phone": "+17135550123",
                        "raw_payload": {
                            "source_row": {
                                "county": "harris",
                                "email": "source-owner@example.com",
                                "contact_candidates": [
                                    {
                                        "name": "Contact Applicant",
                                        "phone": "+17135559876",
                                        "email": "candidate@example.com",
                                    }
                                ],
                            }
                        },
                    }
                ]
            }
        ),
    )

    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="contact-hot-run",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {
                            "case_number": "CONTACT-HOT-1",
                            "filing_type": "APP TO DETERMINE HEIRSHIP",
                            "style": "Estate of Contact Decedent",
                        }
                    ]
                },
            },
        )
    )

    hot_lead = notifier.calls[1]["payload"]["hot_leads"][0]
    assert hot_lead["phone"] == "+17135550123"
    assert hot_lead["email"] == "source-owner@example.com"
    assert hot_lead["contact_hint"] == "Contact Applicant"
    visible = _visible_block_text(notifier.calls[1])
    assert "Phone: +17135550123" in visible
    assert "Email: source-owner@example.com" in visible


def test_lead_run_digest_visible_blocks_include_warning_details():
    notifier = StubSlackNotifier()
    service = NightlyLeadMachineService(repository=SourceRunsRepository(), slack_notifier=notifier)

    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            source_runs=[
                SourceRunManifest(
                    source_key="harris-warning",
                    source_label="Harris warning",
                    source_lane="harris_county_probate",
                    county="harris",
                    record_count=2,
                    warnings=["harris parse warning"],
                ),
                SourceRunManifest(
                    source_key="montgomery-warning",
                    source_label="Montgomery warning",
                    source_lane="montgomery_county_probate",
                    county="montgomery",
                    record_count=3,
                ),
            ],
        )
    )

    visible = _visible_block_text(notifier.calls[0])
    assert "Lane summary" in visible
    assert "harris_county_probate: 2 records" in visible
    assert "montgomery_county_probate: 3 records" in visible
    assert "County summary" in visible
    assert "harris: 2 records" in visible
    assert "montgomery: 3 records" in visible
    assert "Warnings" in visible
    assert "harris parse warning" in visible


def test_hot_lead_digest_caps_visible_rows_and_reports_remaining_count():
    notifier = StubSlackNotifier()
    service = NightlyLeadMachineService(repository=SourceRunsRepository(), slack_notifier=notifier)

    result = service.run_nightly_source_pull(_hot_enrichment_payload(idempotency_key="slack-hot-capped-run", hot_count=12))

    assert [call["route"] for call in notifier.calls] == ["lead_runs", "hot_leads"]
    assert [notice["route"] for notice in result.notifications] == ["lead_runs", "hot_leads"]
    hot_payload = notifier.calls[1]["payload"]
    assert hot_payload["total_hot_lead_count"] == 12
    assert len(hot_payload["hot_leads"]) == 10
    assert hot_payload["remaining_count"] == 2
    visible = _visible_block_text(notifier.calls[1])
    assert visible.count("Case ") == 10
    assert "2 additional hot lead(s) hidden by Slack digest cap." in visible


def test_nightly_source_pull_idempotency_replay_does_not_post_slack_notifications():
    notifier = StubSlackNotifier()
    service = NightlyLeadMachineService(repository=SourceRunsRepository(), slack_notifier=notifier)
    request = _hot_enrichment_payload(idempotency_key="slack-idempotent-run")

    first = service.run_nightly_source_pull(request)
    second = service.run_nightly_source_pull(request)

    assert [call["route"] for call in notifier.calls] == ["lead_runs", "hot_leads"]
    assert [notice["route"] for notice in first.notifications] == ["lead_runs", "hot_leads"]
    assert second.duplicate is True
    assert second.replayed is True
    assert [notice["route"] for notice in second.notifications] == ["lead_runs", "hot_leads"]


def test_nightly_source_pull_without_hot_records_posts_digest_only():
    notifier = StubSlackNotifier()
    service = NightlyLeadMachineService(repository=SourceRunsRepository(), slack_notifier=notifier)

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="slack-no-hot-run",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {
                            "case_number": "543701",
                            "filing_type": "Small Estate",
                            "style": "Estate of Warm Only",
                        }
                    ]
                },
            },
        )
    )

    assert [call["route"] for call in notifier.calls] == ["lead_runs"]
    assert [notice["route"] for notice in result.notifications] == ["lead_runs"]


def test_tenant_scoping(service: NightlyLeadMachineService):
    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz-a",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="a",
                    source_label="A",
                    source_lane="hcad_estate_of",
                    record_count=1,
                )
            ],
        )
    )
    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz-b",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="b",
                    source_label="B",
                    source_lane="hcad_estate_of",
                    record_count=2,
                )
            ],
        )
    )

    assert [run.source_key for run in service.list_source_runs(business_id="biz-a", environment="test")] == ["a"]
    assert service.get_latest_morning_brief(business_id="biz-a", environment="test").new_record_count == 1
    assert service.get_latest_morning_brief(business_id="biz-b", environment="test").new_record_count == 2


def test_missing_manifests_records_fixture_warnings_without_external_calls(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(NightlySourcePullRequest(business_id="biz", environment="test"))

    assert len(result.source_runs) == 4
    assert {run.source_lane for run in result.source_runs} == {
        "harris_county_probate",
        "hcad_estate_of",
        "hctax_delinquency_overlay",
        "harris_land_records",
    }
    assert all(run.record_count == 0 for run in result.source_runs)
    assert result.would_call_external_sources is False
    assert result.live_source_calls_enabled is False
    assert "no source artifacts supplied; fixture source definitions recorded with zero counts" in result.warnings
    assert "no source artifacts supplied" in result.morning_brief.warnings


def test_live_source_calls_request_rejected_when_disabled_before_work():
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_live_source_calls_enabled=False),
    )
    with pytest.raises(RuntimeError, match="live source calls are disabled"):
        service.run_nightly_source_pull(
            NightlySourcePullRequest(business_id="biz", environment="test", live_source_calls=True)
        )
    assert service.list_source_runs(business_id="biz", environment="test") == []


def test_failed_manifest_recorded_but_brief_still_produced(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="hctax-failed",
                    source_label="HCTax fixture",
                    source_lane="hctax_delinquency_overlay",
                    failed=True,
                    error_message="fixture parse failed",
                    warnings=["bad fixture row"],
                    artifacts=[
                        SourceRunArtifact(
                            path="artifacts/hctax.csv",
                            artifact_type="fixture_csv",
                            record_count=4,
                            warnings=["artifact warning"],
                        )
                    ],
                )
            ],
        )
    )

    assert result.source_runs[0].status == SourceRunStatus.FAILED
    assert result.source_runs[0].error_message == "fixture parse failed"
    assert result.morning_brief.new_record_count == 0
    assert "hctax-failed failed: fixture parse failed" in result.morning_brief.warnings
    assert "bad fixture row" in result.morning_brief.warnings


def test_source_lanes_remain_separate(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="probate",
                    source_label="Probate",
                    source_lane="harris_county_probate",
                    record_count=1,
                ),
                SourceRunManifest(
                    source_key="land",
                    source_label="Land records",
                    source_lane="harris_land_records",
                    record_count=2,
                ),
            ],
        )
    )

    lanes = result.morning_brief.sections["source_health"]["lanes"]
    assert {lane["source_lane"]: lane["record_count"] for lane in lanes} == {
        "harris_county_probate": 1,
        "harris_land_records": 2,
    }
    assert service.list_source_runs(business_id="biz", environment="test", source_lane="harris_land_records")[0].source_key == "land"



def test_nightly_source_pull_idempotency_key_replays_without_duplicate_runs(service: NightlyLeadMachineService):
    request = NightlySourcePullRequest(
        business_id="biz",
        environment="test",
        idempotency_key="nightly-key-1",
        source_runs=[
            SourceRunManifest(
                source_key="probate",
                source_label="Probate",
                source_lane="harris_county_probate",
                record_count=2,
            )
        ],
    )

    first = service.run_nightly_source_pull(request)
    second = service.run_nightly_source_pull(request)

    assert first.duplicate is False
    assert second.duplicate is True
    assert second.replayed is True
    assert [run.id for run in second.source_runs] == [run.id for run in first.source_runs]
    assert len(service.list_source_runs(business_id="biz", environment="test")) == 1
    assert service.get_latest_morning_brief(business_id="biz", environment="test").new_record_count == 2


def test_morning_brief_idempotency_key_replays_stable_counts(service: NightlyLeadMachineService):
    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="probate",
                    source_label="Probate",
                    source_lane="harris_county_probate",
                    record_count=3,
                )
            ],
        )
    )

    first = service.create_morning_brief(
        MorningBriefRequest(business_id="biz", environment="test", idempotency_key="brief-key-1")
    )
    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="land",
                    source_label="Land",
                    source_lane="harris_land_records",
                    record_count=99,
                )
            ],
        )
    )
    second = service.create_morning_brief(
        MorningBriefRequest(business_id="biz", environment="test", idempotency_key="brief-key-1")
    )

    assert second.id == first.id
    assert second.new_record_count == 3


def test_manifest_warnings_are_not_double_counted(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="probate",
                    source_label="Probate",
                    source_lane="harris_county_probate",
                    record_count=1,
                    warnings=["manifest warning"],
                    artifacts=[
                        SourceRunArtifact(path="a.jsonl", artifact_type="fixture", record_count=1, warnings=["artifact warning"])
                    ],
                )
            ],
        )
    )

    assert result.source_runs[0].warning_count == 2
    assert result.morning_brief.sections["source_health"]["lanes"][0]["warning_count"] == 2
    assert result.morning_brief.warnings.count("manifest warning") == 1


def test_probate_autopilot_builds_harris_and_montgomery_no_send_manifests(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="probate-auto-2026-05-15-0710",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "run_kind": "morning_catchup",
                "county_scope": ["harris", "montgomery"],
                "record_counts": {
                    "harris": {"raw_count": 4, "parsed_count": 4, "keep_now_count": 2, "record_count": 4},
                    "montgomery": {"raw_count": 3, "parsed_count": 2, "keep_now_count": 1, "record_count": 2, "source_reported_count": 3},
                },
            },
        )
    )

    assert {run.source_lane for run in result.source_runs} == {"harris_county_probate", "montgomery_county_probate"}
    assert {run.county for run in result.source_runs} == {"harris", "montgomery"}
    assert all(run.run_kind == "morning_catchup" for run in result.source_runs)
    assert all(run.metadata["no_send"] is True for run in result.source_runs)
    assert all(run.metadata["provider_sends_enabled"] is False for run in result.source_runs)
    assert all(run.idempotency_key for run in result.source_runs)

    sections = result.morning_brief.sections
    assert sections["no_send_confirmation"]["no_send"] is True
    assert sections["no_send_confirmation"]["instantly_enrollment_enabled"] is False
    assert sections["keep_now"]["keep_now_count"] == 3
    assert {item["county"]: item["keep_now_count"] for item in sections["county_counts"]} == {
        "harris": 2,
        "montgomery": 1,
    }
    assert sections["source_count_mismatches"] == [
        {
            "source_key": "montgomery_county_probate:morning_catchup:unspecified-window",
            "source_lane": "montgomery_county_probate",
            "county": "montgomery",
            "source_reported_count": 3,
            "parsed_count": 2,
        }
    ]


def test_montgomery_probate_manifest_is_accepted_and_summarized(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            source_runs=[
                SourceRunManifest(
                    source_key="montgomery-probate",
                    source_label="Montgomery probate fixture",
                    source_lane="montgomery_county_probate",
                    county="montgomery",
                    run_kind="midday",
                    raw_count=6,
                    parsed_count=6,
                    keep_now_count=2,
                    record_count=6,
                )
            ],
        )
    )

    run = result.source_runs[0]
    assert run.county == "montgomery"
    assert run.run_kind == "midday"
    assert run.keep_now_count == 2
    assert result.morning_brief.sections["county_counts"][0]["raw_count"] == 6
    assert result.morning_brief.sections["keep_now"]["keep_now_count"] == 2


def test_probate_autopilot_boolean_counts_are_ignored(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "record_counts": {
                    "harris": {
                        "raw_count": True,
                        "parsed_count": True,
                        "keep_now_count": True,
                        "source_reported_count": True,
                    }
                },
            },
        )
    )

    run = result.source_runs[0]
    assert run.raw_count == 0
    assert run.parsed_count == 0
    assert run.keep_now_count == 0
    assert run.source_reported_count is None
    assert result.morning_brief.sections["source_count_mismatches"] == []


def test_probate_autopilot_source_rows_create_artifacts_and_keep_now_counts(tmp_path):
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(tmp_path)),
    )
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="source-rows-0710",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "run_kind": "morning_catchup",
                "window_end": "2026-05-15T07:10:00+00:00",
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {
                            "case_number": "543678",
                            "filing_type": "App for Independent Administration with an Heirship",
                            "style": "Estate of Test Seller",
                        },
                        {"case_number": "543679", "filing_type": "Small Estate", "style": "Estate of Skip Seller"},
                        {"case_number": "", "filing_type": "Independent Administration"},
                    ]
                },
            },
        )
    )

    run = result.source_runs[0]
    assert run.raw_count == 3
    assert run.parsed_count == 2
    assert run.keep_now_count == 1
    assert run.record_count == 2
    assert run.metadata["invalid_row_count"] == 1
    assert {artifact.artifact_type for artifact in run.artifacts} == {
        "raw_source_rows",
        "normalized_source_rows",
        "keep_now_rows",
        "invalid_source_rows",
    }
    assert all(artifact.checksum for artifact in run.artifacts)
    assert all(tmp_path.as_posix() in artifact.path for artifact in run.artifacts)
    keep_now_artifact = next(artifact for artifact in run.artifacts if artifact.artifact_type == "keep_now_rows")
    assert "543678" in Path(keep_now_artifact.path).read_text(encoding="utf-8")
    assert result.morning_brief.sections["keep_now"]["keep_now_count"] == 1
    assert result.morning_brief.sections["county_counts"][0]["parsed_count"] == 2
    assert result.morning_brief.sections["source_quality"]["invalid_row_count"] == 1
    assert result.morning_brief.sections["enrichment_backlog"] == {
        "status": "partial",
        "case_detail_status": "incomplete",
        "case_detail_completed_count": 0,
        "case_detail_pending_count": 1,
        "case_detail_blocked_count": 0,
        "case_detail_incomplete_count": 1,
        "contact_candidate_count": 0,
        "primary_contact_candidate_count": 0,
        "live_case_detail_calls_attempted": False,
        "enriched_count": 1,
        "property_match_completed_count": 0,
        "property_match_pending_count": 1,
        "property_match_unmatched_count": 1,
        "tax_overlay_completed_count": 0,
        "tax_overlay_pending_count": 1,
        "tax_overlay_ambiguous_count": 0,
        "title_friction_completed_count": 0,
        "title_friction_pending_count": 1,
        "title_friction_review_count": 1,
        "hubspot_mirror_blocked_until_approval_count": 1,
        "outbound_blocked_until_explicit_approval_count": 1,
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
        "live_cad_calls_attempted": False,
        "live_tax_calls_attempted": False,
        "live_land_record_calls_attempted": False,
    }
    assert [action["action"] for action in result.morning_brief.sections["operator_next_actions"]] == [
        "reconcile_source_count_mismatches",
        "inspect_invalid_source_rows",
        "complete_case_detail_enrichment",
        "complete_property_tax_title_enrichment",
        "keep_outbound_blocked",
    ]


def test_probate_autopilot_runs_enrichment_stages_inside_nightly_pull(tmp_path):
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(tmp_path)),
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="enriched-source-0710",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "run_kind": "morning_catchup",
                "window_end": "2026-05-15T07:10:00+00:00",
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {
                            "case_number": "543680",
                            "filing_type": "App to Determine Heirship",
                            "style": "Estate of Jane Example",
                            "decedent_name": "Jane Example",
                        }
                    ]
                },
                "property_tax_title_enrichment": {
                    "hcad_candidates_by_case": {
                        "543680": [
                            {
                                "acct": "000123400001",
                                "owner_name": "Jane Example",
                                "mailing_address": "123 MAIN ST, HOUSTON, TX 77002",
                                "property_address": "456 OAK ST, HOUSTON, TX 77008",
                            }
                        ]
                    },
                    "tax_overlays_by_account": {
                        "123400001": {
                            "status": "tax_overlay_verified_delinquent",
                            "is_delinquent": True,
                            "amount_owed": 5250.75,
                            "account": "123400001",
                            "confidence": "high",
                            "search_method": "local_harris_tax_statement_snapshot",
                        }
                    },
                    "land_record_rows_by_case": {
                        "543680": [
                            {
                                "instrument_number": "RP-2026-1",
                                "instrument_type": "Affidavit of Heirship",
                                "grantor": "Jane Example",
                                "grantee": "Example Heirs",
                            }
                        ]
                    },
                },
            },
        )
    )

    lanes = {run.source_lane for run in result.source_runs}
    assert {
        "harris_county_probate",
        "harris_hcad_property_match",
        "harris_hctax_overlay",
        "harris_land_records",
    }.issubset(lanes)
    assert result.morning_brief.new_record_count == 1
    assert result.morning_brief.sections["enrichment_backlog"] == {
        "status": "partial",
        "case_detail_status": "incomplete",
        "case_detail_completed_count": 0,
        "case_detail_pending_count": 1,
        "case_detail_blocked_count": 0,
        "case_detail_incomplete_count": 1,
        "contact_candidate_count": 0,
        "primary_contact_candidate_count": 0,
        "live_case_detail_calls_attempted": False,
        "enriched_count": 1,
        "property_match_completed_count": 1,
        "property_match_pending_count": 0,
        "property_match_unmatched_count": 0,
        "tax_overlay_completed_count": 1,
        "tax_overlay_pending_count": 0,
        "tax_overlay_ambiguous_count": 0,
        "title_friction_completed_count": 1,
        "title_friction_pending_count": 0,
        "title_friction_review_count": 1,
        "hubspot_mirror_blocked_until_approval_count": 1,
        "outbound_blocked_until_explicit_approval_count": 1,
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
        "live_cad_calls_attempted": False,
        "live_tax_calls_attempted": False,
        "live_land_record_calls_attempted": False,
    }
    assert [action["action"] for action in result.morning_brief.sections["operator_next_actions"]] == [
        "complete_case_detail_enrichment",
        "keep_outbound_blocked",
    ]
    enrichment_artifacts = [
        artifact
        for run in result.source_runs
        for artifact in run.artifacts
        if artifact.artifact_type.endswith("_enrichment")
    ]
    assert {artifact.artifact_type for artifact in enrichment_artifacts} == {
        "case_detail_enrichment",
        "property_match_enrichment",
        "tax_overlay_enrichment",
        "title_friction_enrichment",
    }
    assert all(Path(artifact.path).exists() for artifact in enrichment_artifacts)
    assert "Jane Example" in Path(enrichment_artifacts[0].path).read_text(encoding="utf-8")


def test_probate_autopilot_runs_case_detail_enrichment_before_property_stages(tmp_path):
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(tmp_path)),
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="case-detail-source-0710",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "run_kind": "morning_catchup",
                "window_end": "2026-05-15T07:10:00+00:00",
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {
                            "case_number": "543681",
                            "filing_type": "App for Independent Administration with an Heirship",
                            "style": "Estate of Jane Detail",
                            "decedent_name": "Jane Detail",
                        }
                    ]
                },
                "case_detail_enrichment": {
                    "case_details_by_case": {
                        "543681": {
                            "source_url": "https://example.test/harris/detail/543681",
                            "parties": [
                                {"role": "Applicant", "name": "Alex Detail", "address": "100 Contact Rd, Houston, TX"},
                                {"role": "Decedent", "name": "Jane Detail"},
                            ],
                            "events": [{"date": "2026-05-20", "event_type": "Hearing on Application"}],
                            "documents": [{"document_type": "Application to Determine Heirship", "document_number": "D-1"}],
                        }
                    }
                },
                "property_tax_title_enrichment": {
                    "hcad_candidates_by_case": {
                        "543681": [
                            {
                                "acct": "000123400002",
                                "owner_name": "Jane Detail",
                                "mailing_address": "100 Contact Rd, Houston, TX",
                                "property_address": "900 Probate Property St, Houston, TX",
                            }
                        ]
                    },
                    "tax_overlays_by_account": {
                        "123400002": {
                            "status": "tax_overlay_verified_current",
                            "is_delinquent": False,
                            "account": "123400002",
                            "confidence": "high",
                        }
                    },
                },
            },
        )
    )

    lanes = {run.source_lane for run in result.source_runs}
    assert "harris_probate_case_detail" in lanes
    assert "harris_hcad_property_match" in lanes
    assert result.morning_brief.sections["case_detail"] == {
        "status": "completed",
        "received_count": 1,
        "detail_completed_count": 1,
        "detail_incomplete_count": 0,
        "detail_blocked_count": 0,
        "party_count": 2,
        "event_count": 1,
        "document_reference_count": 1,
        "contact_candidate_count": 1,
        "primary_contact_candidate_count": 1,
        "attorney_count": 0,
        "hearing_clue_count": 1,
        "publication_clue_count": 0,
        "no_send": True,
        "provider_sends_enabled": False,
        "outbound_allowed": False,
        "live_case_detail_calls_attempted": False,
    }
    assert result.morning_brief.sections["enrichment_backlog"]["case_detail_pending_count"] == 0
    case_detail_run = next(run for run in result.source_runs if run.source_lane == "harris_probate_case_detail")
    assert case_detail_run.metadata["contact_candidate_count"] == 1
    assert case_detail_run.metadata["provider_sends_enabled"] is False
    case_detail_artifact = case_detail_run.artifacts[0]
    assert case_detail_artifact.artifact_type == "case_detail_enrichment"
    artifact_payload = Path(case_detail_artifact.path).read_text(encoding="utf-8")
    assert "Alex Detail" in artifact_payload
    assert '"is_confirmed_seller": false' in artifact_payload
    property_artifact = next(
        artifact
        for run in result.source_runs
        for artifact in run.artifacts
        if artifact.artifact_type == "property_match_enrichment"
    )
    assert '"case_detail"' in Path(property_artifact.path).read_text(encoding="utf-8")


def test_probate_autopilot_source_rows_detect_source_report_mismatch(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["montgomery"],
                "source_rows": {
                    "montgomery": [
                        {"case_number": "24-CP-001", "filing_type": "Independent Administration"},
                    ]
                },
                "record_counts": {"montgomery": {"source_reported_count": 3}},
            },
        )
    )

    assert result.source_runs[0].source_reported_count == 3
    assert result.source_runs[0].parsed_count == 1
    assert result.morning_brief.sections["source_count_mismatches"] == [
        {
            "source_key": "montgomery_county_probate:manual:unspecified-window",
            "source_lane": "montgomery_county_probate",
            "county": "montgomery",
            "source_reported_count": 3,
            "parsed_count": 1,
        }
    ]
    assert result.morning_brief.sections["sla_health"]["status"] == "warning"
    assert result.morning_brief.sections["source_anomalies"][0]["type"] == "source_count_mismatch"


def test_probate_autopilot_source_rows_detect_duplicate_case_numbers(tmp_path):
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(tmp_path)),
    )
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {"case_number": "543678", "filing_type": "Independent Administration"},
                        {"case_number": "543678", "filing_type": "Independent Administration"},
                    ]
                },
            },
        )
    )

    run = result.source_runs[0]
    assert run.metadata["duplicate_case_count"] == 1
    assert run.metadata["duplicate_case_numbers"] == {"543678": 2}
    assert "duplicate_case_numbers" in {artifact.artifact_type for artifact in run.artifacts}
    assert result.morning_brief.sections["source_quality"]["duplicate_case_count"] == 1
    assert result.morning_brief.sections["source_quality"]["duplicate_case_count_by_county"] == {"harris": 1}
    assert result.morning_brief.sections["source_anomalies"][0]["type"] == "duplicate_case_numbers"
    assert result.morning_brief.sections["source_anomalies"][0]["duplicate_case_count_by_county"] == {"harris": 1}
    assert "543678" not in str(result.morning_brief.sections)
    assert "dedupe_duplicate_case_rows" in [
        action["action"] for action in result.morning_brief.sections["operator_next_actions"]
    ]


def test_probate_autopilot_sla_flags_missing_expected_county(service: NightlyLeadMachineService):
    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "expected_counties": ["harris", "montgomery"],
                "county_scope": ["harris"],
                "source_rows": {
                    "harris": [
                        {"case_number": "543678", "filing_type": "Independent Administration"},
                    ]
                },
            },
        )
    )

    assert result.morning_brief.sections["sla_health"]["status"] == "blocked"
    assert result.morning_brief.sections["sla_health"]["missing_counties"] == ["montgomery"]
    assert result.morning_brief.sections["source_anomalies"][0] == {
        "severity": "blocked",
        "type": "missing_expected_county",
        "county": "montgomery",
        "message": "Expected montgomery probate source lane was not present in this run",
    }


class _FakeProbateSourceIdentityRepository:
    def __init__(
        self,
        existing_keys_by_county: dict[str, set[str]] | None = None,
        record_error: Exception | None = None,
    ) -> None:
        self.existing_keys_by_county = existing_keys_by_county or {"harris": set(), "montgomery": set()}
        self.record_error = record_error
        self.list_error: Exception | None = None
        self.list_calls: list[dict[str, object]] = []
        self.recorded_run_ids: list[str] = []

    def list_identity_keys(self, *, business_id: str, environment: str, run_scope: str, counties):
        if self.list_error is not None:
            raise self.list_error
        self.list_calls.append(
            {
                "business_id": business_id,
                "environment": environment,
                "run_scope": run_scope,
                "counties": tuple(counties),
            }
        )
        return {county: set(self.existing_keys_by_county.get(county, set())) for county in counties}

    def record_source_run(self, run):
        if self.record_error is not None:
            raise self.record_error
        self.recorded_run_ids.append(run.id)
        return 0


def test_probate_autopilot_uses_remote_identity_ledger_before_file_ledger(tmp_path):
    duplicate_key = probate_source_identity_key({"case_number": "H-900"}, county="harris")
    assert duplicate_key is not None
    identity_repository = _FakeProbateSourceIdentityRepository({"harris": {duplicate_key}})
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(tmp_path)),
        source_identity_repository=identity_repository,
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="limitless",
            environment="prod",
            idempotency_key="remote-ledger-dedupe",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "expected_counties": ["harris"],
                "source_run_scope": "autonomous",
                "source_rows": {
                    "harris": [
                        {"case_number": "H-900", "filing_type": "Independent Administration", "style": "Estate of Existing"},
                        {"case_number": "H-901", "filing_type": "Independent Administration", "style": "Estate of New"},
                    ]
                },
                "no_send": True,
                "provider_sends_enabled": False,
            },
        )
    )

    source_run = next(run for run in result.source_runs if run.source_lane == "harris_county_probate")
    assert identity_repository.list_calls == [
        {
            "business_id": "limitless",
            "environment": "prod",
            "run_scope": "autonomous",
            "counties": ("harris", "montgomery"),
        }
    ]
    assert source_run.record_count == 1
    assert source_run.metadata["duplicate_prior_run_count"] == 1
    assert result.morning_brief.sections["source_quality"]["duplicate_prior_run_count"] == 1
    assert source_run.id in identity_repository.recorded_run_ids


def test_probate_autopilot_identity_ledger_write_failure_does_not_abort_nightly_pull(tmp_path):
    repository = SourceRunsRepository()
    identity_repository = _FakeProbateSourceIdentityRepository(record_error=RuntimeError("remote unavailable"))
    service = NightlyLeadMachineService(
        repository=repository,
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(tmp_path)),
        source_identity_repository=identity_repository,
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="limitless",
            environment="prod",
            idempotency_key="remote-ledger-write-fails",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "expected_counties": ["harris"],
                "source_run_scope": "autonomous",
                "source_rows": {
                    "harris": [
                        {"case_number": "H-902", "filing_type": "Independent Administration", "style": "Estate of New"},
                    ]
                },
                "no_send": True,
                "provider_sends_enabled": False,
            },
        )
    )

    source_run = next(run for run in result.source_runs if run.source_lane == "harris_county_probate")
    assert result.status == "completed"
    assert source_run.status == SourceRunStatus.COMPLETED
    assert source_run.warning_count >= 1
    assert any("probate source identity ledger write failed with RuntimeError" in item for item in source_run.metadata["warnings"])
    replay = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="limitless",
            environment="prod",
            idempotency_key="remote-ledger-write-fails",
            metadata={"autopilot": "harris_montgomery_probate", "county_scope": ["harris"]},
        )
    )
    assert replay.duplicate is True
    assert replay.replayed is True


def test_probate_autopilot_identity_ledger_read_failure_falls_back_to_file_dedupe(tmp_path):
    identity_repository = _FakeProbateSourceIdentityRepository()
    identity_repository.list_error = RuntimeError("remote unavailable")
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(tmp_path)),
        source_identity_repository=identity_repository,
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="limitless",
            environment="prod",
            idempotency_key="remote-ledger-read-fails",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "county_scope": ["harris"],
                "expected_counties": ["harris"],
                "source_run_scope": "autonomous",
                "source_rows": {
                    "harris": [
                        {"case_number": "H-903", "filing_type": "Independent Administration", "style": "Estate of New"},
                    ]
                },
                "no_send": True,
                "provider_sends_enabled": False,
            },
        )
    )

    source_run = next(run for run in result.source_runs if run.source_lane == "harris_county_probate")
    assert result.status == "completed"
    assert source_run.record_count == 1
    assert source_run.metadata["source_dedupe"]["remote_identity_ledger_status"] == "warning"
    assert any("probate source identity ledger read failed with RuntimeError" in item for item in source_run.metadata["warnings"])


def test_file_backed_repository_replays_nightly_idempotency_after_restart(tmp_path):
    state_path = tmp_path / "source-runs.json"
    first_service = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))
    first = first_service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="daily-probate-2026-05-15",
            metadata={"autopilot": "harris_montgomery_probate", "county_scope": ["harris"]},
        )
    )

    restarted_service = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))
    second = restarted_service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="daily-probate-2026-05-15",
            metadata={"autopilot": "harris_montgomery_probate", "county_scope": ["harris"]},
        )
    )

    assert second.duplicate is True
    assert second.replayed is True
    assert [run.id for run in second.source_runs] == [run.id for run in first.source_runs]
    assert len(restarted_service.list_source_runs(business_id="biz", environment="prod")) == 1


def test_file_backed_repository_reloads_before_save_to_preserve_other_writers(tmp_path):
    state_path = tmp_path / "source-runs.json"
    writer_a = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))
    writer_b = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))

    writer_a.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="harris-run",
            metadata={"autopilot": "harris_montgomery_probate", "county_scope": ["harris"]},
        )
    )
    writer_b.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            idempotency_key="montgomery-run",
            metadata={"autopilot": "harris_montgomery_probate", "county_scope": ["montgomery"]},
        )
    )

    reloaded = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))
    assert {run.county for run in reloaded.list_source_runs(business_id="biz", environment="prod")} == {
        "harris",
        "montgomery",
    }


def test_file_backed_repository_corrupt_state_raises_domain_error(tmp_path):
    state_path = tmp_path / "source-runs.json"
    state_path.write_text("{not-json", encoding="utf-8")
    repo = SourceRunsRepository(state_path=state_path)

    with pytest.raises(SourceRunsPersistenceError, match="Corrupted source-runs repository state"):
        repo.list_runs(business_id="biz", environment="prod")


def test_probate_autopilot_health_reports_blocked_when_state_file_is_corrupt(tmp_path):
    state_path = tmp_path / "source-runs.json"
    state_path.write_text("{not-json", encoding="utf-8")
    service = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))

    health = service.get_probate_autopilot_health(business_id="limitless", environment="prod")

    assert health.status == "blocked"
    assert health.freshness_ok is False
    assert health.no_send_ok is False
    assert health.outbound_allowed is False
    assert health.operator_next_actions[0]["action"] == "repair_probate_autopilot_state"
    assert "source-runs repository state is unreadable" in health.operator_next_actions[0]["reason"]
