from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from pydantic import BaseModel, ConfigDict, Field

from app.domains.ares import AresCounty
from app.services.ares_file_state import atomic_write_text, exclusive_file_lock, load_json_model


class AresMemoryState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market_preferences: dict[str, Any] = Field(default_factory=dict)
    county_defaults: dict[AresCounty, dict[str, Any]] = Field(default_factory=dict)
    lead_history: list[dict[str, Any]] = Field(default_factory=list)
    outreach_history: list[dict[str, Any]] = Field(default_factory=list)
    operator_decisions: list[dict[str, Any]] = Field(default_factory=list)
    outcomes: list[dict[str, Any]] = Field(default_factory=list)
    exceptions: list[dict[str, Any]] = Field(default_factory=list)


class AresMemoryService:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._state = AresMemoryState()
        self._loaded = False

    def load(self) -> AresMemoryState:
        self._state = load_json_model(
            self._storage_path,
            model_type=AresMemoryState,
            label="Ares memory state",
        )
        self._loaded = True
        return self.snapshot()

    def save(self) -> None:
        self._ensure_loaded()
        with exclusive_file_lock(self._storage_path):
            disk_state = load_json_model(
                self._storage_path,
                model_type=AresMemoryState,
                label="Ares memory state",
            )
            self._state = self._merge_states(disk_state=disk_state, pending_state=self._state)
            atomic_write_text(self._storage_path, self._state.model_dump_json(indent=2))

    def snapshot(self) -> AresMemoryState:
        return self._state.model_copy(deep=True)

    def set_market_preferences(self, preferences: dict[str, Any]) -> None:
        self._ensure_loaded()
        self._state.market_preferences = dict(preferences)

    def set_county_defaults(self, county: AresCounty, defaults: dict[str, Any]) -> None:
        self._ensure_loaded()
        self._state.county_defaults[county] = dict(defaults)

    def record_lead_history(self, entry: dict[str, Any]) -> None:
        self._ensure_loaded()
        self._append_entry(self._state.lead_history, entry)

    def record_outreach_history(self, entry: dict[str, Any]) -> None:
        self._ensure_loaded()
        self._append_entry(self._state.outreach_history, entry)

    def record_operator_decision(self, entry: dict[str, Any]) -> None:
        self._ensure_loaded()
        self._append_entry(self._state.operator_decisions, entry)

    def record_outcome(self, entry: dict[str, Any]) -> None:
        self._ensure_loaded()
        self._append_entry(self._state.outcomes, entry)

    def record_exception(self, entry: dict[str, Any]) -> None:
        self._ensure_loaded()
        self._append_entry(self._state.exceptions, entry)

    def _append_entry(self, bucket: list[dict[str, Any]], entry: dict[str, Any]) -> None:
        bucket.append(dict(entry))

    def _merge_states(self, *, disk_state: AresMemoryState, pending_state: AresMemoryState) -> AresMemoryState:
        merged = disk_state.model_copy(deep=True)
        merged.market_preferences.update(pending_state.market_preferences)
        for county, defaults in pending_state.county_defaults.items():
            combined_defaults = dict(merged.county_defaults.get(county, {}))
            combined_defaults.update(defaults)
            merged.county_defaults[county] = combined_defaults
        merged.lead_history = self._merge_entry_lists(disk_state.lead_history, pending_state.lead_history)
        merged.outreach_history = self._merge_entry_lists(disk_state.outreach_history, pending_state.outreach_history)
        merged.operator_decisions = self._merge_entry_lists(
            disk_state.operator_decisions,
            pending_state.operator_decisions,
        )
        merged.outcomes = self._merge_entry_lists(disk_state.outcomes, pending_state.outcomes)
        merged.exceptions = self._merge_entry_lists(disk_state.exceptions, pending_state.exceptions)
        return merged

    @staticmethod
    def _merge_entry_lists(
        disk_entries: list[dict[str, Any]],
        pending_entries: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        merged = [dict(entry) for entry in disk_entries]
        seen = {json.dumps(entry, sort_keys=True, default=str) for entry in merged}
        for entry in pending_entries:
            serialized = json.dumps(entry, sort_keys=True, default=str)
            if serialized not in seen:
                merged.append(dict(entry))
                seen.add(serialized)
        return merged

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
