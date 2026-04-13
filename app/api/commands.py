from fastapi import APIRouter, HTTPException, Response, status

from app.models.commands import CommandCreateRequest, CommandIngestResponse
from app.services.command_service import command_service

router = APIRouter(tags=["commands"])


@router.post("/commands", response_model=CommandIngestResponse)
def create_command(request: CommandCreateRequest, response: Response) -> CommandIngestResponse:
    try:
        command_response, status_code = command_service.create_command(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    response.status_code = status_code
    return command_response
