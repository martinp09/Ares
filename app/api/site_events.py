from fastapi import APIRouter, Response, status

from app.domains.site_events.service import SiteEventIngestResponse, ingest_site_event
from app.models.site_events import SiteEventRecord

router = APIRouter(tags=["site-events"])


@router.post("/site-events", response_model=SiteEventIngestResponse, status_code=status.HTTP_202_ACCEPTED)
def create_site_event(request: SiteEventRecord, response: Response) -> SiteEventIngestResponse:
    response.status_code = status.HTTP_202_ACCEPTED
    return ingest_site_event(request)
