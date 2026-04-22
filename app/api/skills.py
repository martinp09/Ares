from fastapi import APIRouter, HTTPException

from app.models.skills import SkillCreateRequest, SkillRecord
from app.services.skill_registry_service import skill_registry_service

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("", response_model=SkillRecord)
def create_skill(request: SkillCreateRequest) -> SkillRecord:
    try:
        return skill_registry_service.register_skill(
            name=request.name,
            description=request.description,
            input_schema=request.input_schema,
            output_schema=request.output_schema,
            required_tools=request.required_tools,
            permission_requirements=request.permission_requirements,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("", response_model=list[SkillRecord])
def list_skills() -> list[SkillRecord]:
    return skill_registry_service.list_skills()


@router.get("/{skill_id}", response_model=SkillRecord)
def get_skill(skill_id: str) -> SkillRecord:
    skill = skill_registry_service.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill
