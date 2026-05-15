from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "probate_source_file_payload.py"


def test_probate_source_file_payload_script_writes_no_send_payload(tmp_path):
    source_file = tmp_path / "probate.csv"
    output_file = tmp_path / "payload.json"
    source_file.write_text(
        "case_number,filing_type,style\n"
        "543678,Independent Administration,Estate of Script Seller\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--business-id",
            "biz",
            "--environment",
            "prod",
            "--source-file",
            str(source_file),
            "--county",
            "harris",
            "--run-kind",
            "midday",
            "--idempotency-key",
            "script-payload",
            "--output",
            str(output_file),
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout == ""
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["business_id"] == "biz"
    assert payload["live_source_calls"] is False
    assert payload["metadata"]["county_scope"] == ["harris"]
    assert payload["metadata"]["expected_counties"] == ["harris", "montgomery"]
    assert payload["metadata"]["source_rows"]["harris"][0]["case_number"] == "543678"
    assert payload["metadata"]["provider_sends_enabled"] is False


def test_probate_source_file_payload_script_can_emit_stdout_from_any_cwd(tmp_path):
    source_file = tmp_path / "probate.csv"
    source_file.write_text(
        "case_number,filing_type,style\n"
        "543678,Independent Administration,Estate of Stdout Seller\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--business-id",
            "biz",
            "--environment",
            "prod",
            "--source-file",
            str(source_file),
            "--county",
            "harris",
            "--run-kind",
            "manual",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert payload["metadata"]["county_scope"] == ["harris"]
    assert payload["metadata"]["expected_counties"] == ["harris", "montgomery"]


def test_probate_source_file_payload_script_rejects_invalid_run_kind(tmp_path):
    source_file = tmp_path / "probate.csv"
    source_file.write_text("case_number,filing_type\n543678,Independent Administration\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--business-id",
            "biz",
            "--environment",
            "prod",
            "--source-file",
            str(source_file),
            "--county",
            "harris",
            "--run-kind",
            "not-a-run-kind",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "invalid choice" in result.stderr
