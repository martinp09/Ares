import pytest

from app.core.config import Settings
from app.db.source_runs import SourceRunsRepository
from app.models.source_runs import NightlySourcePullRequest
from app.services.nightly_lead_machine_service import NightlyLeadMachineService
from app.services.probate_live_source_adapter_service import CountyProbateSourceFetch
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


def test_source_provider_bridge_rejects_live_calls_when_disabled_before_work():
    bridge = ProbateSourceProviderBridgeService(settings=Settings(_env_file=None, lead_machine_live_source_calls_enabled=False))
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


class FakeLiveSourceAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_window(self, **kwargs):
        self.calls.append(kwargs)
        assert kwargs["live_source_calls_enabled"] is True
        assert kwargs["source_provider_approval"]["approved"] is True
        assert kwargs["source_provider_approval"]["no_send"] is True
        assert kwargs["source_provider_approval"]["provider_sends_enabled"] is False
        return {
            "harris": CountyProbateSourceFetch(
                county="harris",
                source_url="https://example.test/harris-probate",
                rows=[
                    {
                        "county": "harris",
                        "case_number": "H-LIVE-1",
                        "filing_type": "APP FOR INDEPENDENT ADMINISTRATION",
                        "style": "ESTATE OF HARRIS LIVE",
                        "file_date": "05/14/2026",
                    }
                ],
                source_reported_count=1,
                raw_count=1,
                metadata={"fixture": "harris"},
            ),
            "montgomery": CountyProbateSourceFetch(
                county="montgomery",
                source_url="https://example.test/montgomery-probate",
                rows=[
                    {
                        "county": "montgomery",
                        "case_number": "M-LIVE-1",
                        "filing_type": "MUNIMENT OF TITLE",
                        "style": "Estate of: Montgomery Live",
                        "file_date": "05/14/2026",
                    }
                ],
                source_reported_count=1,
                raw_count=1,
                metadata={"fixture": "montgomery"},
            ),
        }


def test_source_provider_bridge_hydrates_live_source_adapters_only_with_gate_and_approval():
    settings = Settings(_env_file=None, lead_machine_live_source_calls_enabled=True)
    adapter = FakeLiveSourceAdapter()
    bridge = ProbateSourceProviderBridgeService(settings=settings, live_source_adapter=adapter)

    request = bridge.hydrate_request(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            live_source_calls=True,
            metadata={
                "window_start": "2026-05-14T00:00:00+00:00",
                "window_end": "2026-05-15T00:00:00+00:00",
                "source_provider_approval": {
                    "approved": True,
                    "approved_by": "operator",
                    "scope": "public_probate_sources",
                    "no_send": True,
                    "provider_sends_enabled": False,
                },
                "source_provider_bridge": {
                    "mode": "live_source_adapters",
                    "expected_counties": ["harris", "montgomery"],
                },
            },
        )
    )

    assert adapter.calls
    assert request.live_source_calls is False
    assert request.metadata["no_send"] is True
    assert request.metadata["provider_sends_enabled"] is False
    assert request.metadata["source_rows"]["harris"][0]["case_number"] == "H-LIVE-1"
    assert request.metadata["source_rows"]["montgomery"][0]["case_number"] == "M-LIVE-1"
    bridge_metadata = request.metadata["source_provider_bridge"]
    assert bridge_metadata["mode"] == "live_source_adapters"
    assert bridge_metadata["would_call_live_sources"] is True
    assert bridge_metadata["network_calls_attempted"] is True
    assert bridge_metadata["browser_calls_attempted"] is False
    assert bridge_metadata["no_send"] is True
    assert bridge_metadata["provider_sends_enabled"] is False
    assert "raw" not in bridge_metadata


def test_source_provider_bridge_requires_explicit_no_send_approval_for_live_adapters():
    settings = Settings(_env_file=None, lead_machine_live_source_calls_enabled=True)
    bridge = ProbateSourceProviderBridgeService(settings=settings, live_source_adapter=FakeLiveSourceAdapter())

    with pytest.raises(RuntimeError, match="source_provider_approval.no_send=true"):
        bridge.hydrate_request(
            NightlySourcePullRequest(
                business_id="biz",
                environment="test",
                live_source_calls=True,
                metadata={
                    "source_provider_approval": {"approved": True, "approved_by": "operator"},
                    "source_provider_bridge": {"mode": "live_source_adapters", "expected_counties": ["harris"]},
                },
            )
        )


def test_source_provider_bridge_rejects_live_source_adapters_without_live_flag():
    settings = Settings(_env_file=None, lead_machine_live_source_calls_enabled=True)
    bridge = ProbateSourceProviderBridgeService(settings=settings, live_source_adapter=FakeLiveSourceAdapter())

    with pytest.raises(RuntimeError, match="requires live_source_calls=true"):
        bridge.hydrate_request(
            NightlySourcePullRequest(
                business_id="biz",
                environment="test",
                metadata={
                    "source_provider_approval": {"approved": True, "approved_by": "operator"},
                    "source_provider_bridge": {"mode": "live_source_adapters", "expected_counties": ["harris"]},
                },
            )
        )


def test_nightly_service_runs_live_source_adapters_as_no_send_source_runs():
    settings = Settings(_env_file=None, lead_machine_live_source_calls_enabled=True)
    bridge = ProbateSourceProviderBridgeService(settings=settings, live_source_adapter=FakeLiveSourceAdapter())
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=settings,
        source_provider_bridge=bridge,
    )

    result = service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="test",
            live_source_calls=True,
            metadata={
                "window_start": "2026-05-14T00:00:00+00:00",
                "window_end": "2026-05-15T00:00:00+00:00",
                "source_provider_approval": {
                    "approved": True,
                    "approved_by": "operator",
                    "scope": "public_probate_sources",
                    "no_send": True,
                    "provider_sends_enabled": False,
                },
                "source_provider_bridge": {
                    "mode": "live_source_adapters",
                    "expected_counties": ["harris", "montgomery"],
                },
            },
        )
    )

    assert result.would_call_external_sources is True
    assert result.live_source_calls_enabled is True
    assert {run.county for run in result.source_runs} == {"harris", "montgomery"}
    assert all(run.record_count == 1 for run in result.source_runs)
    assert all(run.metadata["source_provider_bridge"]["mode"] == "live_source_adapters" for run in result.source_runs)
    assert all(run.metadata["source_provider_bridge"]["network_calls_attempted"] is True for run in result.source_runs)
    assert result.morning_brief.sections["no_send_confirmation"]["no_send"] is True
