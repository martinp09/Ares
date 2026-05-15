import pytest

from app.core.config import Settings
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
    with pytest.raises(ValueError, match="only supports mode=local_export_files or mode=adapter_preview"):
        bridge.hydrate_request(
            NightlySourcePullRequest(
                business_id="biz",
                environment="test",
                metadata={"source_provider_bridge": {"mode": "live_browser", "exports": ["/tmp/nope.csv"]}},
            )
        )


def test_source_provider_adapter_preview_rejects_when_preview_gate_disabled():
    bridge = ProbateSourceProviderBridgeService(settings=Settings(_env_file=None))

    with pytest.raises(RuntimeError, match="source adapter preview is disabled"):
        bridge.hydrate_request(
            NightlySourcePullRequest(
                business_id="biz",
                environment="test",
                metadata={
                    "source_provider_approval": {"approved": True, "approved_by": "operator"},
                    "source_provider_bridge": {"mode": "adapter_preview", "expected_counties": ["harris"]},
                },
            )
        )


def test_source_provider_adapter_preview_requires_explicit_approval():
    bridge = ProbateSourceProviderBridgeService(
        settings=Settings(_env_file=None, lead_machine_source_adapter_preview_enabled=True)
    )

    with pytest.raises(RuntimeError, match="source_provider_approval.approved=true"):
        bridge.hydrate_request(
            NightlySourcePullRequest(
                business_id="biz",
                environment="test",
                metadata={"source_provider_bridge": {"mode": "adapter_preview", "expected_counties": ["harris"]}},
            )
        )


def test_source_provider_adapter_preview_hydrates_dry_run_metadata_without_network_calls():
    bridge = ProbateSourceProviderBridgeService(
        settings=Settings(_env_file=None, lead_machine_source_adapter_preview_enabled=True)
    )

    request = bridge.hydrate_request(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            metadata={
                "source_provider_approval": {"approved": True, "approved_by": "operator", "scope": "dry_run_preview"},
                "source_provider_bridge": {"mode": "adapter_preview", "expected_counties": ["harris", "montgomery"]},
            },
        )
    )

    bridge_metadata = request.metadata["source_provider_bridge"]
    assert request.live_source_calls is False
    assert request.metadata["source_rows"] == {"harris": [], "montgomery": []}
    assert bridge_metadata["mode"] == "adapter_preview"
    assert bridge_metadata["dry_run"] is True
    assert bridge_metadata["would_call_live_sources"] is False
    assert bridge_metadata["network_calls_attempted"] is False
    assert bridge_metadata["browser_calls_attempted"] is False
    assert bridge_metadata["provider_adapters"] == ["harris_county_probate_live_v1", "montgomery_county_probate_live_v1"]
    assert "raw" not in bridge_metadata
    assert "case_number" not in str(bridge_metadata).lower()


def test_nightly_service_runs_adapter_preview_as_placeholder_manifests_without_live_calls():
    settings = Settings(_env_file=None, lead_machine_source_adapter_preview_enabled=True)
    bridge = ProbateSourceProviderBridgeService(settings=settings)
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=settings,
        source_provider_bridge=bridge,
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            metadata={
                "source_provider_approval": {"approved": True, "approved_by": "operator", "scope": "dry_run_preview"},
                "source_provider_bridge": {"mode": "adapter_preview", "expected_counties": ["harris", "montgomery"]},
            },
        )
    )

    assert result.would_call_external_sources is False
    assert result.live_source_calls_enabled is False
    assert {run.county for run in result.source_runs} == {"harris", "montgomery"}
    assert all(run.record_count == 0 for run in result.source_runs)
    assert all(run.metadata["source_provider_bridge"]["dry_run"] is True for run in result.source_runs)
    assert all(run.metadata["source_provider_bridge"]["network_calls_attempted"] is False for run in result.source_runs)
    assert result.morning_brief.sections["no_send_confirmation"]["no_send"] is True
