"""
User-to-variant assignment service.

When a user visits the site, we need to decide: which variant should they see?
"""

import hashlib

from sqlalchemy.orm import Session

from app.models.event import Assignment
from app.models.experiment import Experiment
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _hash_to_bucket(user_id: int, experiment_id: int) -> float:
    """
    Hash a (user_id, experiment_id) pair to a float in [0.0, 1.0).
    """
    key = f"{user_id}:{experiment_id}".encode("utf-8")
    digest = hashlib.md5(key).hexdigest()

    # Take first 8 hex chars = 32 bits
    bucket_int = int(digest[:8], 16)

    # Normalize to [0.0, 1.0)
    return bucket_int / 0x100000000  # 2^32


def _bucket_to_variant(bucket: float, variants: list[dict]) -> str:
    """
    Map a bucket value [0.0, 1.0) to a variant name based on allocations.
    """
    cumulative = 0.0
    for variant in variants:
        cumulative += variant["allocation"]
        if bucket < cumulative:
            return variant["name"]

    return variants[-1]["name"]


def assign_user_to_variant(
    db: Session,
    user_id: int,
    experiment_id: int,
) -> Assignment:
    """
    Assign a user to a variant for an experiment.
    """
    # Check for existing assignment (idempotency)
    existing = (
        db.query(Assignment)
        .filter(
            Assignment.user_id == user_id,
            Assignment.experiment_id == experiment_id,
        )
        .first()
    )

    if existing:
        logger.debug(
            f"Existing assignment found: user_id={user_id}, "
            f"experiment_id={experiment_id}, variant='{existing.variant_name}'"
        )
        return existing

    # Validate user and experiment exist
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise ValueError(f"User {user_id} not found")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise ValueError(f"Experiment {experiment_id} not found")

    # Only assign for running experiments
    if experiment.status != "running":
        raise ValueError(
            f"Cannot assign to experiment with status '{experiment.status}'. "
            f"Experiment must be 'running'."
        )

    # Compute the variant
    bucket = _hash_to_bucket(user_id, experiment_id)
    variant_name = _bucket_to_variant(bucket, experiment.variants)

    logger.info(
        f"Computing new assignment: user_id={user_id}, "
        f"experiment_id={experiment_id}, bucket={bucket:.4f}, variant='{variant_name}'"
    )

    # Create and persist the assignment
    assignment = Assignment(
        user_id=user_id,
        experiment_id=experiment_id,
        variant_name=variant_name,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def get_assignment(
    db: Session,
    user_id: int,
    experiment_id: int,
) -> Assignment | None:
    """
    Look up an existing assignment without creating one.

    Returns None if no assignment exists.
    """
    return (
        db.query(Assignment)
        .filter(
            Assignment.user_id == user_id,
            Assignment.experiment_id == experiment_id,
        )
        .first()
    )