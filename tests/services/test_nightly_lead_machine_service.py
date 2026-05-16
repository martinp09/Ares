from pathlib import Path

import pytest

from app.core.config import Settings
from app.db.source_runs import SourceRunsPersistenceError, SourceRunsRepository
from app.models.source_runs import MorningBriefRequest, NightlySourcePullRequest, SourceRunArtifact, SourceRunManifest, SourceRunStatus
from app.services.nightly_lead_machine_service import NightlyLeadMachineService


@pytest.fixture
def service() -> NightlyLeadMachineService:
    return NightlyLeadMachineService(repository=SourceRunsRepository())


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
