from __future__ import annotations

import argparse
import json
import os
import re
from datetime import date
from pathlib import Path
from typing import Any

ARCHIVE_ROOT_ENV = "SMS_AGENT_OBSIDIAN_ARCHIVE_ROOT"

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}(?!\w)")


def redact_entry(entry: dict[str, object]) -> dict[str, object]:
    return _redact_value(entry)


def write_archive(root: Path, date_key: str, entries: list[dict[str, object]]) -> None:
    archive_date = _parse_date_key(date_key)
    redacted_entries = [redact_entry(entry) for entry in entries]
    archive_dir = root / f"{archive_date:%Y}" / f"{archive_date:%m}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = archive_dir / f"{date_key}.md"
    jsonl_path = archive_dir / f"{date_key}.sms-agent-corpus.jsonl"

    markdown_path.write_text(_render_markdown(date_key, redacted_entries), encoding="utf-8")
    jsonl_path.write_text(
        "".join(f"{json.dumps(entry, sort_keys=True, separators=(',', ':'))}\n" for entry in redacted_entries),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export redacted SMS reply-agent archive/eval files to an explicit local root."
    )
    parser.add_argument("--root", help=f"Archive root. Defaults to {ARCHIVE_ROOT_ENV} when set.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Archive date as YYYY-MM-DD.")
    parser.add_argument("--business-id", help="Optional business id filter for future data-source wiring.")
    parser.add_argument("--environment", help="Optional environment filter for future data-source wiring.")
    parser.add_argument("--dry-run", action="store_true", help="Report intended output paths without writing files.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root_value = args.root or os.environ.get(ARCHIVE_ROOT_ENV)
    if not root_value:
        parser.error(f"explicit --root or {ARCHIVE_ROOT_ENV} is required")

    archive_date = _parse_date_key(args.date)
    root = Path(root_value).expanduser()
    archive_dir = root / f"{archive_date:%Y}" / f"{archive_date:%m}"
    report = {
        "root": str(root),
        "date": args.date,
        "business_id": args.business_id,
        "environment": args.environment,
        "dry_run": args.dry_run,
        "entries": 0,
        "markdown_path": str(archive_dir / f"{args.date}.md"),
        "jsonl_path": str(archive_dir / f"{args.date}.sms-agent-corpus.jsonl"),
    }

    if not args.dry_run:
        write_archive(root=root, date_key=args.date, entries=[])

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def _redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redact_value_by_key(key, child) for key, child in value.items()}
    if isinstance(value, list):
        return [_redact_value(child) for child in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(child) for child in value)
    if isinstance(value, str):
        return _redact_string(value)
    return value


def _redact_value_by_key(key: str, value: Any) -> Any:
    normalized_key = key.lower()
    if isinstance(value, str):
        if "email" in normalized_key:
            return "[email]" if value else value
        if "phone" in normalized_key or normalized_key.endswith("_number") or normalized_key in {"from", "to"}:
            return "[phone]" if value else value
    return _redact_value(value)


def _redact_string(value: str) -> str:
    return PHONE_RE.sub("[phone]", EMAIL_RE.sub("[email]", value))


def _parse_date_key(date_key: str) -> date:
    try:
        return date.fromisoformat(date_key)
    except ValueError as exc:
        raise SystemExit(f"Invalid --date {date_key!r}; expected YYYY-MM-DD") from exc


def _render_markdown(date_key: str, entries: list[dict[str, object]]) -> str:
    lines = [
        f"# SMS Reply Agent Archive - {date_key}",
        "",
        "Redacted cold archive/eval corpus. Supabase remains the live runtime source of truth.",
        "",
        f"Entry count: {len(entries)}",
        "",
    ]
    for index, entry in enumerate(entries, start=1):
        decision_id = entry.get("decision_id", "unknown")
        intent = entry.get("intent", "unknown")
        lines.extend(
            [
                f"## {index}. {decision_id}",
                "",
                f"- Intent: {intent}",
                "",
                "```json",
                json.dumps(entry, indent=2, sort_keys=True),
                "```",
                "",
            ]
        )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
