"""
Event tracking service.

Events record what users do during experiments. Every event is associated with:
- A user (who did the thing)
- An experiment (which test they're in)
- A variant (which arm of the test) — looked up automatically
- An event type (what they did: exposure, add_to_cart, purchase, etc.)
- An optional value (e.g., revenue amount for purchase events)
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.event import Assignment, Event
from app.models.experiment import Experiment
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)


def track_event(
    db: Session,
    user_id: int,
    experiment_id: int,
    event_type: str,
    event_value: Decimal | None = None,
    event_metadata: dict | None = None,
) -> Event | None:
    """
    Record an event for a user in an experiment.

    Returns:
        Event record if tracking succeeded.
        None if the user has no assignment for this experiment (event ignored).
    """
    # Validate user exists
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError(f"User {user_id} not found")

    # Validate experiment exists
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise ValueError(f"Experiment {experiment_id} not found")

    # Look up the user's assignment
    assignment = (
        db.query(Assignment)
        .filter(
            Assignment.user_id == user_id,
            Assignment.experiment_id == experiment_id,
        )
        .first()
    )

    if assignment is None:
        # User isn't assigned — silently ignore the event
        # WHY: This can happen if the frontend fires events before assignment
        logger.warning(
            f"Event ignored: user_id={user_id} has no assignment for "
            f"experiment_id={experiment_id} (event_type='{event_type}')"
        )
        return None

    # Create the event with the variant from the assignment
    event = Event(
        user_id=user_id,
        experiment_id=experiment_id,
        variant_name=assignment.variant_name,
        event_type=event_type,
        event_value=event_value,
        event_metadata=event_metadata,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    logger.info(
        f"Event tracked: user_id={user_id}, experiment_id={experiment_id}, "
        f"variant='{assignment.variant_name}', event_type='{event_type}'"
    )

    return event