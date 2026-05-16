from __future__ import annotations

import json

import pytest

from app.core.config import Settings
from app.db.source_runs import SourceRunsRepository
from app.models.source_runs import NightlySourcePullRequest
from app.services.nightly_lead_machine_service import NightlyLeadMachineService
from app.services.probate_source_file_service import ProbateSourceFileService


def test_csv_source_file_builds_no_send_payload_grouped_by_county(tmp_path):
    source_file = tmp_path / "probate.csv"
    source_file.write_text(
        "county,case_number,filing_type,style\n"
        "Harris County,543678,App for Independent Administration with an Heirship,Estate of Harris Seller\n"
        "Montgomery,24-CP-001,Independent Administration,Estate of Montgomery Seller\n",
        encoding="utf-8",
    )

    payload = ProbateSourceFileService().build_nightly_payload(
        business_id="limitless",
        environment="prod",
        source_file=source_file,
        run_kind="morning_catchup",
        idempotency_key="file-drop-2026-05-15-0710",
        window_end="2026-05-15T07:10:00Z",
    )

    assert payload["business_id"] == "limitless"
    assert payload["environment"] == "prod"
    assert payload["live_source_calls"] is False
    assert payload["idempotency_key"] == "file-drop-2026-05-15-0710"
    assert payload["metadata"]["county_scope"] == ["harris", "montgomery"]
    assert payload["metadata"]["expected_counties"] == ["harris", "montgomery"]
    assert payload["metadata"]["no_send"] is True
    assert payload["metadata"]["provider_sends_enabled"] is False
    assert payload["metadata"]["source_rows"]["harris"][0]["case_number"] == "543678"
    assert payload["metadata"]["source_rows"]["harris"][0]["source_adapter"] == "harris_probate_export_v1"
    assert payload["metadata"]["source_rows"]["montgomery"][0]["case_number"] == "24-CP-001"
    assert payload["metadata"]["source_rows"]["montgomery"][0]["source_adapter"] == "montgomery_probate_export_v1"
    assert payload["metadata"]["source_adapter_contract"] == "probate_export_adapter_v1"


def test_json_source_file_supports_county_keyed_payloads(tmp_path):
    source_file = tmp_path / "probate.json"
    source_file.write_text(
        json.dumps(
            {
                "harris": [{"case_number": "543678", "filing_type": "Independent Administration"}],
                "montgomery": [{"case_number": "24-CP-001", "filing_type": "Small Estate"}],
            }
        ),
        encoding="utf-8",
    )

    payload = ProbateSourceFileService().build_nightly_payload(
        business_id="biz",
        environment="test",
        source_file=source_file,
    )

    assert payload["metadata"]["county_scope"] == ["harris", "montgomery"]
    assert payload["metadata"]["source_rows"]["harris"][0]["county"] == "harris"
    assert payload["metadata"]["source_rows"]["montgomery"][0]["county"] == "montgomery"


def test_json_source_file_supports_nested_source_rows_payload(tmp_path):
    source_file = tmp_path / "probate.json"
    source_file.write_text(
        json.dumps(
            {
                "source_rows": {
                    "harris": [{"case_number": "543678", "filing_type": "Independent Administration"}],
                }
            }
        ),
        encoding="utf-8",
    )

    payload = ProbateSourceFileService().build_nightly_payload(
        business_id="biz",
        environment="test",
        source_file=source_file,
    )

    assert payload["metadata"]["county_scope"] == ["harris"]
    assert payload["metadata"]["expected_counties"] == ["harris", "montgomery"]
    assert payload["metadata"]["source_rows"]["harris"][0]["case_number"] == "543678"


def test_source_file_adapter_normalizes_county_export_column_aliases(tmp_path):
    harris_file = tmp_path / "harris.csv"
    harris_file.write_text(
        "county,Case Number,Case Type,Style of Case,Date Filed,Court\n"
        "Harris,543678,Independent Administration,Estate of Harris Seller,05/01/2026,Probate Court 4\n",
        encoding="utf-8",
    )
    montgomery_file = tmp_path / "montgomery.csv"
    montgomery_file.write_text(
        "county,Cause No.,Case Style,Type Description,Filing Date,Court Number\n"
        "Montgomery,24-CP-001,Estate of Montgomery Seller,App To Determine Heirship,2026-05-02,County Court 2\n",
        encoding="utf-8",
    )

    payload = ProbateSourceFileService().build_nightly_payload_from_files(
        business_id="biz",
        environment="prod",
        source_files=[harris_file, montgomery_file],
        run_kind="daily_reconciliation",
    )

    harris = payload["metadata"]["source_rows"]["harris"][0]
    montgomery = payload["metadata"]["source_rows"]["montgomery"][0]
    assert harris["case_number"] == "543678"
    assert harris["filing_type"] == "Independent Administration"
    assert harris["style"] == "Estate of Harris Seller"
    assert harris["source_row_id"].startswith("harris:543678:")
    assert montgomery["case_number"] == "24-CP-001"
    assert montgomery["filing_type"] == "App To Determine Heirship"
    assert montgomery["source_row_id"].startswith("montgomery:24-cp-001:")
    assert payload["metadata"]["source_files"] == [
        {"path": str(harris_file), "row_count": 1, "county_scope": ["harris"]},
        {"path": str(montgomery_file), "row_count": 1, "county_scope": ["montgomery"]},
    ]


def test_json_source_file_rejects_non_object_rows(tmp_path):
    source_file = tmp_path / "probate.json"
    source_file.write_text(json.dumps({"rows": [[]]}), encoding="utf-8")

    with pytest.raises(ValueError, match="rows row 1 must be an object"):
        ProbateSourceFileService().load_rows(source_file)


def test_source_file_payload_requires_supported_county_without_default(tmp_path):
    source_file = tmp_path / "probate.csv"
    source_file.write_text(
        "county,case_number,filing_type\n"
        "Fort Bend,123,Independent Administration\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"missing supported county at row\(s\): 1"):
        ProbateSourceFileService().build_nightly_payload(
            business_id="biz",
            environment="test",
            source_file=source_file,
        )


def test_jsonl_source_file_requires_object_rows(tmp_path):
    source_file = tmp_path / "probate.jsonl"
    source_file.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ValueError, match="JSONL row 1 must be an object"):
        ProbateSourceFileService().load_rows(source_file)


def test_source_file_payload_runs_through_nightly_service_without_provider_side_effects(tmp_path):
    source_file = tmp_path / "probate.csv"
    artifact_root = tmp_path / "artifacts"
    source_file.write_text(
        "county,case_number,filing_type,style\n"
        "Harris,543678,Independent Administration,Estate of Harris Seller\n"
        "Montgomery,24-CP-001,Small Estate,Estate of Montgomery Seller\n",
        encoding="utf-8",
    )
    payload = ProbateSourceFileService().build_nightly_payload(
        business_id="biz",
        environment="prod",
        source_file=source_file,
        run_kind="midday",
        idempotency_key="local-file-midday",
    )
    service = NightlyLeadMachineService(
        repository=SourceRunsRepository(),
        settings=Settings(_env_file=None, lead_machine_artifact_root=str(artifact_root)),
    )
    result = service.run_nightly_source_pull(NightlySourcePullRequest(**payload))

    assert result.would_call_external_sources is False
    assert result.live_source_calls_enabled is False
    no_send = result.morning_brief.sections["no_send_confirmation"]
    assert no_send["no_send"] is True
    assert no_send["provider_sends_enabled"] is False
    assert no_send["instantly_enrollment_enabled"] is False
    assert {run.county for run in result.source_runs} == {"harris", "montgomery"}
    assert sum(run.keep_now_count or 0 for run in result.source_runs) == 1


def test_source_file_payload_marks_missing_expected_county_in_brief(tmp_path):
    source_file = tmp_path / "probate.csv"
    source_file.write_text(
        "county,case_number,filing_type,style\n"
        "Harris,543678,Independent Administration,Estate of Harris Seller\n",
        encoding="utf-8",
    )
    payload = ProbateSourceFileService().build_nightly_payload(
        business_id="biz",
        environment="prod",
        source_file=source_file,
        run_kind="midday",
        idempotency_key="harris-only-file",
    )
    result = NightlyLeadMachineService(repository=SourceRunsRepository()).run_nightly_source_pull(
        NightlySourcePullRequest(**payload)
    )

    assert result.morning_brief.sections["sla_health"]["status"] == "blocked"
    assert result.morning_brief.sections["sla_health"]["missing_counties"] == ["montgomery"]
    assert result.morning_brief.sections["source_anomalies"][0]["type"] == "missing_expected_county"


def _probate_autopilot_request(*, rows, idempotency_key, run_kind="midday", scope="autonomous"):
    return NightlySourcePullRequest(
        business_id="biz",
        environment="prod",
        idempotency_key=idempotency_key,
        metadata={
            "autopilot": "harris_montgomery_probate",
            "county_scope": ["harris"],
            "expected_counties": ["harris"],
            "source_rows": {"harris": rows},
            "run_kind": run_kind,
            "source_run_scope": scope,
            "window_start": "2026-05-15T00:00:00+00:00",
            "window_end": "2026-05-15T23:59:59+00:00",
            "no_send": True,
            "provider_sends_enabled": False,
        },
    )


def _probate_service(tmp_path):
    return NightlyLeadMachineService(
        repository=SourceRunsRepository(state_path=tmp_path / "source-runs.json"),
        settings=Settings(lead_machine_artifact_root=str(tmp_path / "artifacts")),
    )


def test_probate_autopilot_dedupes_source_rows_seen_in_prior_autonomous_run(tmp_path):
    service = _probate_service(tmp_path)
    first = service.run_nightly_source_pull(
        _probate_autopilot_request(
            idempotency_key="autonomous-first",
            rows=[
                {"case_number": "H-100", "filing_type": "Independent Administration", "style": "Estate of A"},
                {"case_number": "H-200", "filing_type": "Independent Administration", "style": "Estate of B"},
            ],
        )
    )
    assert first.morning_brief.new_record_count >= 2

    second = service.run_nightly_source_pull(
        _probate_autopilot_request(
            idempotency_key="autonomous-second",
            rows=[
                {"case_number": "H-100", "filing_type": "Independent Administration", "style": "Estate of A duplicate"},
                {"case_number": "H-300", "filing_type": "Independent Administration", "style": "Estate of C"},
            ],
        )
    )

    source_run = next(run for run in second.source_runs if run.source_lane == "harris_county_probate")
    assert source_run.parsed_count == 2
    assert source_run.record_count == 1
    assert source_run.metadata["duplicate_prior_run_count"] == 1
    assert source_run.metadata["new_unique_record_count"] == 1
    assert second.morning_brief.sections["source_quality"]["duplicate_prior_run_count"] == 1
    assert second.morning_brief.sections["source_quality"]["deduped_existing_record_count"] == 1
    assert any(artifact.artifact_type == "duplicate_prior_run_rows" for artifact in source_run.artifacts)


def test_probate_autopilot_dedupes_repeated_rows_inside_same_source_packet(tmp_path):
    service = _probate_service(tmp_path)
    result = service.run_nightly_source_pull(
        _probate_autopilot_request(
            idempotency_key="autonomous-current-packet-dupe",
            rows=[
                {"case_number": "H-400", "filing_type": "Independent Administration", "style": "Estate of D"},
                {"case_number": "h 400", "filing_type": "Independent Administration", "style": "Estate of D duplicate"},
            ],
        )
    )

    source_run = next(run for run in result.source_runs if run.source_lane == "harris_county_probate")
    assert source_run.parsed_count == 2
    assert source_run.record_count == 1
    assert source_run.metadata["duplicate_current_run_count"] == 1
    assert result.morning_brief.sections["source_quality"]["duplicate_current_run_count"] == 1


def test_probate_autopilot_manual_scope_does_not_pollute_autonomous_dedupe(tmp_path):
    service = _probate_service(tmp_path)
    service.run_nightly_source_pull(
        _probate_autopilot_request(
            idempotency_key="manual-first",
            scope="manual",
            run_kind="manual",
            rows=[{"case_number": "H-500", "filing_type": "Independent Administration", "style": "Estate of Manual"}],
        )
    )

    autonomous = service.run_nightly_source_pull(
        _probate_autopilot_request(
            idempotency_key="autonomous-after-manual",
            rows=[{"case_number": "H-500", "filing_type": "Independent Administration", "style": "Estate of Autonomous"}],
        )
    )

    source_run = next(run for run in autonomous.source_runs if run.source_lane == "harris_county_probate")
    assert source_run.record_count == 1
    assert source_run.metadata["duplicate_prior_run_count"] == 0
    assert autonomous.morning_brief.sections["source_request"]["source_run_scope"] == "autonomous"
