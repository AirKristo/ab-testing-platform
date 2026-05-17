"""
Pydantic schemas for the Assignment API.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AssignmentResponse(BaseModel):
    """
    User's variant assignment for a given experiment.
    """
    id: int
    user_id: int
    experiment_id: int
    variant_name: str
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)