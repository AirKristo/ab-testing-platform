"""
Event tracking API endpoint.

The frontend fires events here whenever something experiment-relevant happens:
- User views a page (exposure)
- User adds to cart
- User completes a purchase
- User clicks a CTA
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.event import EventCreate, EventResponse
from app.services.event_service import track_event
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/events",
    tags=["events"],
)


@router.post("", status_code=201)
def create_event(
    request: EventCreate,
    db: Session = Depends(get_db),
) -> dict:
    """
    Record an event.
    """
    logger.info(
        f"Event request: user_id={request.user_id}, "
        f"experiment_id={request.experiment_id}, event_type='{request.event_type}'"
    )

    try:
        event = track_event(
            db,
            user_id=request.user_id,
            experiment_id=request.experiment_id,
            event_type=request.event_type,
            event_value=request.event_value,
            event_metadata=request.event_metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if event is None:
        # User wasn't assigned — return 202 Accepted
        return {"status": "ignored", "reason": "no_assignment"}

    return EventResponse.model_validate(event).model_dump(mode="json")