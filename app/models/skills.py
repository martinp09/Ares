from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_metadata_entries(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = value.strip()
        if not item:
            raise ValueError("Skill metadata entries must not be blank")
        if item in seen:
            continue
        seen.add(item)
        normalized.append(item)
    return normalized


class SkillMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str | None = None
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    required_tools: list[str] = Field(default_factory=list)
    permission_requirements: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Skill name must not be blank")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("required_tools", "permission_requirements")
    @classmethod
    def normalize_metadata_lists(cls, values: list[str]) -> list[str]:
        return _normalize_metadata_entries(values)


class SkillCreateRequest(SkillMetadata):
    pass


class SkillRecord(SkillMetadata):
    id: str
    created_at: datetime
    updated_at: datetime
