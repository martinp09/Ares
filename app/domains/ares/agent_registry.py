from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AresAgentRevisionSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision: str = Field(min_length=1)
    allowed_tools: tuple[str, ...] = Field(default_factory=tuple)
    risk_policy: str = Field(min_length=1)
    output_contract: str = Field(min_length=1)


class AresVersionedAgentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    revisions: tuple[AresAgentRevisionSpec, ...] = Field(default_factory=tuple)
    active_revision: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_revisions(self) -> "AresVersionedAgentRecord":
        revision_ids = [revision.revision for revision in self.revisions]
        if not revision_ids:
            raise ValueError("revisions must include at least one revision")
        if len(revision_ids) != len(set(revision_ids)):
            raise ValueError("revisions must be unique per agent")
        if self.active_revision not in revision_ids:
            raise ValueError("active_revision must reference an existing revision")
        return self

