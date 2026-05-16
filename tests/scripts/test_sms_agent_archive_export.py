from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.sms_agent_archive_export import redact_entry, write_archive

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sms_agent_archive_export.py"


def test_redact_entry_redacts_phone_numbers_and_emails_recursively() -> None:
    entry = {
        "decision_id": "smsdec_1",
        "from_number": "+15551234567",
        "email": "owner@example.com",
        "body": "Call me at 555-123-4567 or owner@example.com.",
        "intent": "interested",
        "context": {
            "lead": {
                "phone": "(555) 765-4321",
                "notes": ["Backup email: backup.owner@example.com", "Keep lane probate"],
            }
        },
    }

    redacted = redact_entry(entry)

    redacted_text = json.dumps(redacted, sort_keys=True)
    assert "+15551234567" not in redacted_text
    assert "555-123-4567" not in redacted_text
    assert "555) 765-4321" not in redacted_text
    assert "owner@example.com" not in redacted_text
    assert "backup.owner@example.com" not in redacted_text
    assert "[phone]" in redacted["body"]
    assert "[email]" in redacted["body"]
    assert redacted["intent"] == "interested"
    assert redacted["context"]["lead"]["notes"][1] == "Keep lane probate"


def test_write_archive_writes_markdown_and_jsonl_with_redacted_entries(tmp_path: Path) -> None:
    write_archive(
        root=tmp_path,
        date_key="2026-05-16",
        entries=[
            {
                "decision_id": "smsdec_1",
                "intent": "interested",
                "body": "Call me at +15551234567",
                "email": "owner@example.com",
            }
        ],
    )

    markdown_path = tmp_path / "2026" / "05" / "2026-05-16.md"
    jsonl_path = tmp_path / "2026" / "05" / "2026-05-16.sms-agent-corpus.jsonl"

    assert markdown_path.exists()
    assert jsonl_path.exists()
    assert "+15551234567" not in markdown_path.read_text(encoding="utf-8")
    assert "owner@example.com" not in jsonl_path.read_text(encoding="utf-8")

    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {
            "decision_id": "smsdec_1",
            "intent": "interested",
            "body": "Call me at [phone]",
            "email": "[email]",
        }
    ]


def test_cli_fails_closed_without_explicit_root(monkeypatch) -> None:
    monkeypatch.delenv("SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT", raising=False)

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--date", "2026-05-16", "--dry-run"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT" in result.stderr


def test_cli_uses_archive_root_env_for_dry_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT", str(tmp_path))

    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--date", "2026-05-16", "--dry-run"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)
    assert report["root"] == str(tmp_path)
    assert report["date"] == "2026-05-16"
    assert report["dry_run"] is True
    assert not (tmp_path / "2026").exists()
