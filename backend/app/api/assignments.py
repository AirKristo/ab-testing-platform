"""
Assignment API endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.assignment import AssignmentResponse
from app.services.assignment_service import assign_user_to_variant
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/assignments",
    tags=["assignments"],
)


@router.get("", response_model=AssignmentResponse)
def get_or_create_assignment(
    user_id: int = Query(..., gt=0, description="User ID"),
    experiment_id: int = Query(..., gt=0, description="Experiment ID"),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    """
    Get the user's variant assignment for an experiment.
    """
    logger.info(
        f"Assignment request: user_id={user_id}, experiment_id={experiment_id}"
    )

    try:
        assignment = assign_user_to_variant(db, user_id, experiment_id)
    except ValueError as e:
        error_message = str(e)
        # Different errors warrant different HTTP statuses
        if "not found" in error_message:
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=error_message)

    return AssignmentResponse.model_validate(assignment)