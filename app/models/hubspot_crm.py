from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.crm_records import CrmRecord

HubSpotObjectType = Literal["contacts", "companies", "deals"]
HubSpotActionStatus = Literal["skipped", "applied", "synced"]


class HubSpotPropertyOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    value: str = Field(min_length=1)
    displayOrder: int = 0
    hidden: bool = False


class HubSpotPropertyDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_type: HubSpotObjectType
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    type: Literal["string", "number", "bool", "enumeration"]
    fieldType: Literal["text", "textarea", "number", "checkbox", "select", "booleancheckbox"]
    groupName: str = Field(min_length=1)
    description: str = Field(min_length=1)
    displayOrder: int = 0
    options: list[HubSpotPropertyOption] = Field(default_factory=list)

    def hubspot_payload(self) -> dict[str, Any]:
        payload = self.model_dump(exclude={"object_type"}, exclude_none=True)
        if not self.options:
            payload.pop("options", None)
        return payload


class HubSpotPipelineStageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    stage_id: str = Field(min_length=1)
    displayOrder: int
    probability: float = Field(ge=0, le=1)
    closed_won: bool = False
    closed_lost: bool = False

    def hubspot_payload(self) -> dict[str, Any]:
        metadata: dict[str, str] = {"probability": str(self.probability)}
        if self.closed_won:
            metadata["closedWon"] = "true"
        if self.closed_lost:
            metadata["closedLost"] = "true"
        return {
            "label": self.label,
            "displayOrder": self.displayOrder,
            "metadata": metadata,
        }


class HubSpotPipelineSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    object_type: Literal["deals"] = "deals"
    label: str = "Ares Acquisition Pipeline"
    pipeline_id_suggestion: str = "ares_acquisitions"
    displayOrder: int = 0
    stages: list[HubSpotPipelineStageSpec]

    def hubspot_payload(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "displayOrder": self.displayOrder,
            "stages": [stage.hubspot_payload() for stage in self.stages],
        }


class HubSpotCustomizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    business_id: str = "limitless"
    environment: str = "prod"
    dry_run_only: bool = True
    include_properties: bool = True
    include_deal_pipeline: bool = True


class HubSpotRecordSyncRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record: CrmRecord
    dry_run_only: bool = True
    create_contact: bool = True
    create_deal: bool = True
    deal_name: str | None = None
    deal_stage: str | None = None
    pipeline_id: str | None = None
    owner_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HubSpotProviderActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    status: HubSpotActionStatus
    dry_run: bool
    request_payload: dict[str, Any]
    provider_response: dict[str, Any] | None = None
    missing_config: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
