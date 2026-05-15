from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from app.models.source_runs import NightlySourcePullRequest, SourceCounty, SourceRunKind


class ProbateSourceFileService:
    def load_rows(self, path: str | Path) -> list[dict[str, Any]]:
        source_path = Path(path)
        suffix = source_path.suffix.lower()
        if suffix == ".csv":
            return self._load_csv(source_path)
        if suffix == ".jsonl":
            return self._load_jsonl(source_path)
        if suffix == ".json":
            return self._load_json(source_path)
        raise ValueError(f"Unsupported probate source file extension: {suffix or '<none>'}")

    def build_nightly_payload(
        self,
        *,
        business_id: str,
        environment: str,
        source_file: str | Path,
        county: SourceCounty | None = None,
        expected_counties: Iterable[SourceCounty] | None = None,
        run_kind: SourceRunKind = "manual",
        idempotency_key: str | None = None,
        window_start: str | None = None,
        window_end: str | None = None,
    ) -> dict[str, Any]:
        rows = self.load_rows(source_file)
        grouped_rows = self._group_rows(rows, default_county=county)
        expected_county_scope = list(expected_counties or ("harris", "montgomery"))
        if not grouped_rows:
            raise ValueError("No Harris or Montgomery probate source rows were found")
        request = NightlySourcePullRequest(
            business_id=business_id,
            environment=environment,
            idempotency_key=idempotency_key,
            live_source_calls=False,
            metadata={
                "autopilot": "harris_montgomery_probate",
                "run_kind": run_kind,
                "county_scope": list(grouped_rows),
                "expected_counties": expected_county_scope,
                "source_rows": grouped_rows,
                "source_uri": str(Path(source_file)),
                "window_start": window_start,
                "window_end": window_end,
                "no_send": True,
                "provider_sends_enabled": False,
            },
        )
        return request.model_dump(mode="json", exclude_none=True)

    def _load_csv(self, path: Path) -> list[dict[str, Any]]:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError(f"JSONL row {line_number} must be an object")
            rows.append(item)
        return rows

    def _load_json(self, path: Path) -> list[dict[str, Any]]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return self._objects_from_list(payload, label="JSON root")
        if isinstance(payload, dict):
            rows = payload.get("rows") or payload.get("records")
            if isinstance(rows, list):
                return self._objects_from_list(rows, label="rows")
            source_rows = payload.get("source_rows")
            if isinstance(source_rows, list):
                return self._objects_from_list(source_rows, label="source_rows")
            if isinstance(source_rows, Mapping):
                return self._flatten_county_rows(source_rows)
            county_rows = self._flatten_county_rows(payload)
            if county_rows:
                return county_rows
        raise ValueError("JSON probate source file must contain a list or a rows/records/source_rows array")

    def _group_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        default_county: SourceCounty | None = None,
    ) -> dict[SourceCounty, list[dict[str, Any]]]:
        grouped: dict[SourceCounty, list[dict[str, Any]]] = {}
        invalid_rows: list[int] = []
        for index, row in enumerate(rows, start=1):
            county = _normalize_county(row.get("county") or default_county)
            if county is None:
                invalid_rows.append(index)
                continue
            grouped.setdefault(county, []).append(row)
        if invalid_rows:
            raise ValueError(
                "Probate source rows missing supported county at row(s): " + ", ".join(str(item) for item in invalid_rows)
            )
        return grouped

    @staticmethod
    def _objects_from_list(rows: list[Any], *, label: str) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []
        for index, item in enumerate(rows, start=1):
            if not isinstance(item, Mapping):
                raise ValueError(f"{label} row {index} must be an object")
            objects.append(dict(item))
        return objects

    @staticmethod
    def _flatten_county_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
        county_rows: list[dict[str, Any]] = []
        for county in ("harris", "montgomery"):
            value = payload.get(county)
            if isinstance(value, list):
                county_rows.extend({**dict(item), "county": county} for item in value if isinstance(item, Mapping))
        return county_rows


def _normalize_county(value: Any) -> SourceCounty | None:
    normalized = str(value or "").strip().lower().replace("_county", "").replace(" county", "")
    if normalized in {"harris", "montgomery"}:
        return normalized  # type: ignore[return-value]
    return None
