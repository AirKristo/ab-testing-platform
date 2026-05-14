"""
Experiment Management API endpoints.

Full CRUD for experiments plus status management (start/stop/pause).

STATUS LIFECYCLE:
    draft → running → completed
              ↕
            paused

Rules:
- Can only START a draft experiment
- Can only PAUSE a running experiment
- Can only RESUME (start) a paused experiment
- Can COMPLETE a running or paused experiment
- Cannot modify variants/metrics of a running experiment
- Cannot delete a running experiment
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.experiment import Experiment
from app.schemas.experiment import (
    ExperimentCreate,
    ExperimentUpdate,
    ExperimentResponse,
    ExperimentListResponse,
    VariantConfig,
    MetricsConfig,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/experiments",
    tags=["experiments"],
)


def _experiment_to_response(experiment: Experiment) -> ExperimentResponse:
    """
    Convert a SQLAlchemy Experiment to a Pydantic ExperimentResponse.
    """
    return ExperimentResponse(
        id=experiment.id,
        name=experiment.name,
        description=experiment.description,
        status=experiment.status,
        variants=[VariantConfig(**v) for v in experiment.variants],
        metrics=MetricsConfig(**experiment.metrics),
        start_date=experiment.start_date,
        end_date=experiment.end_date,
        created_at=experiment.created_at,
        updated_at=experiment.updated_at,
    )


@router.post("", response_model=ExperimentResponse, status_code=201)
def create_experiment(
    request: ExperimentCreate,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """
    Create a new experiment in DRAFT status.
    """
    logger.info(f"Creating experiment: name='{request.name}'")

    experiment = Experiment(
        name=request.name,
        description=request.description,
        status="draft",
        # Convert Pydantic models to dicts for JSONB storage
        variants=[v.model_dump() for v in request.variants],
        metrics=request.metrics.model_dump(),
    )

    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    logger.info(f"Created experiment: id={experiment.id}, name='{experiment.name}'")
    return _experiment_to_response(experiment)


@router.get("", response_model=ExperimentListResponse)
def list_experiments(
    status: str | None = None,
    db: Session = Depends(get_db),
) -> ExperimentListResponse:
    """
    List all experiments, optionally filtered by status.
    """
    logger.info(f"Listing experiments: status={status}")

    query = db.query(Experiment)

    if status:
        valid_statuses = {"draft", "running", "paused", "completed"}
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}",
            )
        query = query.filter(Experiment.status == status)

    experiments = query.order_by(Experiment.created_at.desc()).all()

    return ExperimentListResponse(
        experiments=[_experiment_to_response(e) for e in experiments],
        total=len(experiments),
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """Get a single experiment by ID."""
    logger.info(f"Fetching experiment: id={experiment_id}")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return _experiment_to_response(experiment)


@router.put("/{experiment_id}", response_model=ExperimentResponse)
def update_experiment(
    experiment_id: int,
    request: ExperimentUpdate,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """
    Update an experiment's configuration.
    """
    logger.info(f"Updating experiment: id={experiment_id}")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Restrict variant/metric changes on non-draft experiments
    if experiment.status != "draft":
        if request.variants is not None or request.metrics is not None:
            raise HTTPException(
                status_code=400,
                detail="Cannot modify variants or metrics of a non-draft experiment. "
                       "Only name and description can be updated.",
            )

    # Apply updates (only for fields that were provided)
    if request.name is not None:
        experiment.name = request.name
    if request.description is not None:
        experiment.description = request.description
    if request.variants is not None:
        experiment.variants = [v.model_dump() for v in request.variants]
    if request.metrics is not None:
        experiment.metrics = request.metrics.model_dump()

    db.commit()
    db.refresh(experiment)

    logger.info(f"Updated experiment: id={experiment.id}")
    return _experiment_to_response(experiment)


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
) -> None:
    """
    Delete an experiment.
    """
    logger.info(f"Deleting experiment: id={experiment_id}")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running experiment. Stop it first.",
        )

    db.delete(experiment)
    db.commit()

    logger.info(f"Deleted experiment: id={experiment_id}")


# ---- Status Management Endpoints ----

@router.post("/{experiment_id}/start", response_model=ExperimentResponse)
def start_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """
    Start an experiment (draft/paused → running).

    Sets start_date on first start. Subsequent starts (from paused) don't
    change start_date — the experiment's total runtime includes paused time.
    """
    logger.info(f"Starting experiment: id={experiment_id}")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    valid_from = {"draft", "paused"}
    if experiment.status not in valid_from:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start experiment with status '{experiment.status}'. "
                   f"Must be one of: {', '.join(valid_from)}.",
        )

    experiment.status = "running"
    if experiment.start_date is None:
        experiment.start_date = datetime.now(timezone.utc)

    db.commit()
    db.refresh(experiment)

    logger.info(f"Experiment started: id={experiment.id}")
    return _experiment_to_response(experiment)


@router.post("/{experiment_id}/pause", response_model=ExperimentResponse)
def pause_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """
    Pause a running experiment.
    """
    logger.info(f"Pausing experiment: id={experiment_id}")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.status != "running":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause experiment with status '{experiment.status}'. Must be 'running'.",
        )

    experiment.status = "paused"
    db.commit()
    db.refresh(experiment)

    logger.info(f"Experiment paused: id={experiment.id}")
    return _experiment_to_response(experiment)


@router.post("/{experiment_id}/complete", response_model=ExperimentResponse)
def complete_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
) -> ExperimentResponse:
    """
    Complete an experiment (running/paused → completed).

    This is permanent — sets end_date and no new assignments will be made.
    Existing data is preserved for analysis.
    """
    logger.info(f"Completing experiment: id={experiment_id}")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    valid_from = {"running", "paused"}
    if experiment.status not in valid_from:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot complete experiment with status '{experiment.status}'. "
                   f"Must be one of: {', '.join(valid_from)}.",
        )

    experiment.status = "completed"
    experiment.end_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(experiment)

    logger.info(f"Experiment completed: id={experiment.id}")
    return _experiment_to_response(experiment)