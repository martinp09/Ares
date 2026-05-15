from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.db.source_runs import SourceRunsRepository
from app.models.source_runs import NightlySourcePullRequest
from app.services.nightly_lead_machine_service import NightlyLeadMachineService
from scripts.probate_autopilot_doctor import apply_freshness_gate


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "probate_autopilot_doctor.py"


def test_probate_autopilot_doctor_reports_latest_blocked_sla(tmp_path):
    state_path = tmp_path / "source-runs.json"
    service = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))
    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            metadata={
                "autopilot": "harris_montgomery_probate",
                "expected_counties": ["harris", "montgomery"],
                "county_scope": ["harris"],
                "source_rows": {"harris": [{"case_number": "543678", "filing_type": "Independent Administration"}]},
            },
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--state-path",
            str(state_path),
            "--business-id",
            "biz",
            "--environment",
            "prod",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["status"] == "blocked"
    assert report["no_send_ok"] is True
    assert report["outbound_allowed"] is False
    assert report["sla_health"]["missing_counties"] == ["montgomery"]
    assert report["anomalies"][0]["type"] == "missing_expected_county"


def test_probate_autopilot_doctor_can_fail_on_blocked(tmp_path):
    state_path = tmp_path / "source-runs.json"
    service = NightlyLeadMachineService(repository=SourceRunsRepository(state_path=state_path))
    service.run_nightly_source_pull(
        NightlySourcePullRequest(
            business_id="biz",
            environment="prod",
            source_runs=[],
            metadata={
                "autopilot": "harris_montgomery_probate",
                "expected_counties": ["harris", "montgomery"],
                "county_scope": ["harris"],
            },
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--state-path",
            str(state_path),
            "--business-id",
            "biz",
            "--environment",
            "prod",
            "--fail-on-blocked",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert json.loads(result.stdout)["status"] == "blocked"


def test_probate_autopilot_doctor_reports_no_data(tmp_path):
    state_path = tmp_path / "source-runs.json"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--state-path",
            str(state_path),
            "--business-id",
            "biz",
            "--environment",
            "prod",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["status"] == "no_data"
    assert report["outbound_allowed"] is False


def test_probate_autopilot_doctor_freshness_gate_blocks_stale_brief():
    report = {"status": "healthy", "operator_next_actions": []}

    result = apply_freshness_gate(
        report,
        generated_at=datetime(2026, 5, 15, 7, 0, tzinfo=timezone.utc),
        max_age_hours=2,
        now=datetime(2026, 5, 15, 10, 30, tzinfo=timezone.utc),
    )

    assert result["status"] == "blocked"
    assert result["freshness_ok"] is False
    assert result["stale_brief"] is True
    assert result["operator_next_actions"][0]["action"] == "run_or_repair_probate_autopilot_source_pull"
