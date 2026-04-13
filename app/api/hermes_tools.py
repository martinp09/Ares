from fastapi import APIRouter, HTTPException, Response, status

from app.models.commands import CommandIngestResponse
from app.services.hermes_tools_service import (
    HermesToolInvokeRequest,
    HermesToolListResponse,
    hermes_tools_service,
)

router = APIRouter(prefix="/hermes", tags=["hermes-tools"])


@router.get("/tools", response_model=HermesToolListResponse)
def list_tools() -> HermesToolListResponse:
    return hermes_tools_service.list_tools()


@router.post("/tools/{tool_name}/invoke", response_model=CommandIngestResponse)
def invoke_tool(tool_name: str, request: HermesToolInvokeRequest, response: Response) -> CommandIngestResponse:
    try:
        command_response, status_code = hermes_tools_service.invoke_tool(tool_name, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    response.status_code = status_code
    return command_response
