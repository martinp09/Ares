from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import json

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.ares_file_state import atomic_write_text, exclusive_file_lock, load_json_model


class AresEvalSample(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leads_reviewed: int = Field(ge=0)
    qualified_leads: int = Field(ge=0)
    responses_sent: int = Field(ge=0)
    quality_responses: int = Field(ge=0)
    conversion_opportunities: int = Field(ge=0)
    successful_conversions: int = Field(ge=0)
    false_positives: int = Field(ge=0)
    duplicate_work_items: int = Field(ge=0)
    operator_corrections: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_rates(self) -> "AresEvalSample":
        if self.qualified_leads > self.leads_reviewed:
            raise ValueError("qualified_leads cannot exceed leads_reviewed")
        if self.quality_responses > self.responses_sent:
            raise ValueError("quality_responses cannot exceed responses_sent")
        if self.successful_conversions > self.conversion_opportunities:
            raise ValueError("successful_conversions cannot exceed conversion_opportunities")
        if self.false_positives > self.leads_reviewed:
            raise ValueError("false_positives cannot exceed leads_reviewed")
        if self.duplicate_work_items > self.leads_reviewed:
            raise ValueError("duplicate_work_items cannot exceed leads_reviewed")
        if self.operator_corrections > self.leads_reviewed:
            raise ValueError("operator_corrections cannot exceed leads_reviewed")
        return self


class AresEvalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lead_quality: float = Field(ge=0.0, le=1.0)
    response_quality: float = Field(ge=0.0, le=1.0)
    conversion_quality: float = Field(ge=0.0, le=1.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0)
    duplicate_work_rate: float = Field(ge=0.0, le=1.0)
    operator_correction_rate: float = Field(ge=0.0, le=1.0)


class AresEvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    recorded_at: datetime
    sample: AresEvalSample
    metrics: AresEvalMetrics


class AresEvalLoopState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries: list[AresEvalResult] = Field(default_factory=list)


class AresEvalLoopService:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._state = AresEvalLoopState()
        self._loaded = False

    def load(self) -> AresEvalLoopState:
        self._state = load_json_model(
            self._storage_path,
            model_type=AresEvalLoopState,
            label="Ares eval loop state",
        )
        self._loaded = True
        return self.snapshot()

    def save(self) -> None:
        self._ensure_loaded()
        with exclusive_file_lock(self._storage_path):
            disk_state = load_json_model(
                self._storage_path,
                model_type=AresEvalLoopState,
                label="Ares eval loop state",
            )
            self._state = self._merge_states(disk_state=disk_state, pending_state=self._state)
            atomic_write_text(self._storage_path, self._state.model_dump_json(indent=2))

    def snapshot(self) -> AresEvalLoopState:
        return self._state.model_copy(deep=True)

    def evaluate_and_record(self, *, run_id: str, sample: AresEvalSample) -> AresEvalResult:
        self._ensure_loaded()

        result = AresEvalResult(
            run_id=run_id,
            recorded_at=datetime.now(UTC),
            sample=sample,
            metrics=AresEvalMetrics(
                lead_quality=self._rate(sample.qualified_leads, sample.leads_reviewed),
                response_quality=self._rate(sample.quality_responses, sample.responses_sent),
                conversion_quality=self._rate(
                    sample.successful_conversions, sample.conversion_opportunities
                ),
                false_positive_rate=self._rate(sample.false_positives, sample.leads_reviewed),
                duplicate_work_rate=self._rate(sample.duplicate_work_items, sample.leads_reviewed),
                operator_correction_rate=self._rate(
                    sample.operator_corrections, sample.leads_reviewed
                ),
            ),
        )
        self._state.entries.append(result)
        return result.model_copy(deep=True)

    def list_results(self) -> list[AresEvalResult]:
        self._ensure_loaded()
        return [entry.model_copy(deep=True) for entry in self._state.entries]

    @staticmethod
    def _rate(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return numerator / denominator

    def _merge_states(self, *, disk_state: AresEvalLoopState, pending_state: AresEvalLoopState) -> AresEvalLoopState:
        merged_entries = [entry.model_copy(deep=True) for entry in disk_state.entries]
        seen = {json.dumps(entry.model_dump(mode="json"), sort_keys=True) for entry in merged_entries}
        for entry in pending_state.entries:
            serialized = json.dumps(entry.model_dump(mode="json"), sort_keys=True)
            if serialized not in seen:
                merged_entries.append(entry.model_copy(deep=True))
                seen.add(serialized)
        return AresEvalLoopState(entries=merged_entries)

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
