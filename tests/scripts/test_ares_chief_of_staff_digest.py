from __future__ import annotations

import json

from scripts import ares_chief_of_staff_digest


def test_cli_dry_run_prints_json_without_writing_or_posting(capsys, monkeypatch, tmp_path) -> None:
    artifact_root = tmp_path / "configured-artifacts"
    monkeypatch.setenv("ARES_CHIEF_OF_STAFF_ARTIFACT_ROOT", str(artifact_root))

    exit_code = ares_chief_of_staff_digest.main(
        [
            "--business-id",
            "limitless",
            "--environment",
            "dev",
            "--limit",
            "3",
            "--dry-run",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["brief"]["kind"] == "ares_chief_of_staff_brief_v0"
    assert payload["brief"]["business_id"] == "limitless"
    assert payload["brief"]["environment"] == "dev"
    assert payload["artifacts"] == {}
    assert not artifact_root.exists()
    assert payload["slack_notification"] == {"status": "not_requested"}
    assert "@" not in captured.out
