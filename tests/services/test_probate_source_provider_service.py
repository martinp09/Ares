import pytest

from app.db.source_runs import SourceRunsRepository
from app.models.source_runs import NightlySourcePullRequest
from app.services.nightly_lead_machine_service import NightlyLeadMachineService
from app.services.probate_source_provider_service import (
    PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION,
    ProbateSourceProviderBridgeService,
)


def test_source_provider_bridge_hydrates_local_export_files(tmp_path):
    harris_file = tmp_path / "harris.csv"
    harris_file.write_text(
        "case_number,filing_type,style\n"
        "H-1,APP FOR INDEPENDENT ADMINISTRATION,ESTATE OF HARRIS\n",
        encoding="utf-8",
    )
    montgomery_file = tmp_path / "montgomery.csv"
    montgomery_file.write_text(
        "case_number,filing_type,style\n"
        "M-1,APPLICATION TO DETERMINE HEIRSHIP,ESTATE OF MONTGOMERY\n",
        encoding="utf-8",
    )

    bridge = ProbateSourceProviderBridgeService()
    request = bridge.hydrate_request(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            metadata={
                "source_provider_bridge": {
                    "mode": "local_export_files",
                    "exports": [
                        {"path": str(harris_file), "county": "harris"},
                        {"path": str(montgomery_file), "county": "montgomery"},
                    ],
                    "expected_counties": ["harris", "montgomery"],
                }
            },
        )
    )

    assert request.live_source_calls is False
    assert request.metadata["autopilot"] == "harris_montgomery_probate"
    assert request.metadata["no_send"] is True
    assert request.metadata["provider_sends_enabled"] is False
    assert request.metadata["source_provider_bridge"]["version"] == PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION
    assert request.metadata["source_provider_bridge"]["would_call_live_sources"] is False
    assert request.metadata["source_rows"]["harris"][0]["case_number"] == "H-1"
    assert request.metadata["source_rows"]["montgomery"][0]["case_number"] == "M-1"
    assert request.metadata["record_counts"]["harris"]["source_reported_count"] == 1
    assert request.metadata["record_counts"]["montgomery"]["source_reported_count"] == 1


def test_source_provider_bridge_rejects_live_calls_before_work():
    bridge = ProbateSourceProviderBridgeService()
    with pytest.raises(RuntimeError, match="live source calls are disabled"):
        bridge.reject_live_source_calls(
            NightlySourcePullRequest(business_id="biz", environment="test", live_source_calls=True)
        )


def test_nightly_service_runs_local_export_provider_bridge_without_live_calls(tmp_path):
    source_file = tmp_path / "harris.csv"
    source_file.write_text(
        "case_number,filing_type,style\n"
        "H-2,APP FOR INDEPENDENT ADMINISTRATION,ESTATE OF EXPORT\n",
        encoding="utf-8",
    )
    service = NightlyLeadMachineService(repository=SourceRunsRepository())

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            metadata={
                "source_provider_bridge": {
                    "mode": "local_export_files",
                    "exports": [{"path": str(source_file), "county": "harris"}],
                    "expected_counties": ["harris", "montgomery"],
                }
            },
        )
    )

    assert result.would_call_external_sources is False
    assert result.live_source_calls_enabled is False
    assert {run.county for run in result.source_runs} == {"harris"}
    harris_run = next(run for run in result.source_runs if run.county == "harris")
    assert harris_run.record_count == 1
    assert harris_run.metadata["source_provider_bridge"]["version"] == PROBATE_SOURCE_PROVIDER_BRIDGE_VERSION
    assert result.morning_brief.sections["sla_health"]["missing_counties"] == ["montgomery"]
    assert result.morning_brief.sections["source_anomalies"][0]["type"] == "missing_expected_county"
    assert result.morning_brief.sections["no_send_confirmation"]["no_send"] is True


def test_source_provider_bridge_rejects_unsupported_mode():
    bridge = ProbateSourceProviderBridgeService()
    with pytest.raises(ValueError, match="only supports mode=local_export_files"):
        bridge.hydrate_request(
            NightlySourcePullRequest(
                business_id="biz",
                environment="test",
                metadata={"source_provider_bridge": {"mode": "live_browser", "exports": ["/tmp/nope.csv"]}},
            )
        )
