"""
Pydantic schemas for the Events API.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class EventCreate(BaseModel):
    """
    Request to track an event for a user in an experiment.
    """
    user_id: int = Field(..., gt=0)
    experiment_id: int = Field(..., gt=0)
    event_type: str = Field(..., min_length=1, max_length=100, examples=["purchase"])
    event_value: Decimal | None = Field(None, examples=[29.99])
    event_metadata: dict | None = Field(
        None,
        examples=[{"product_id": 42, "page": "checkout"}],
        description="Optional structured context for the event.",
    )


class EventResponse(BaseModel):
    """Event record returned after creation."""
    id: int
    user_id: int
    experiment_id: int
    variant_name: str
    event_type: str
    event_value: Decimal | None
    event_metadata: dict | None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)