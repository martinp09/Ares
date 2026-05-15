import pytest

from app.db.source_runs import SourceRunsRepository
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


def test_live_source_calls_request_rejected_before_work(service: NightlyLeadMachineService):
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
