"""
Experiment results API endpoint.

This is what the dashboard calls to display statistical analysis.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.analysis.basic_stats import analyze_experiment, METRIC_EVENT_TYPES
from app.database import get_db
from app.models.experiment import Experiment
from app.schemas.results import (
    ExperimentResultsResponse,
    VariantMetricsResponse,
    TTestResultResponse,
)
from app.utils.logging import get_logger
from app.analysis.cuped import (
    analyze_experiment_with_cuped,
    SUPPORTED_COVARIATES,
)
from app.schemas.results import (
    CupedResultsResponse,
    CupedDiagnostics,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/experiments",
    tags=["results"],
)


@router.get(
    "/{experiment_id}/results",
    response_model=ExperimentResultsResponse,
)
def get_experiment_results(
    experiment_id: int,
    metric: str | None = Query(
        None,
        description="Metric to analyze. Defaults to the experiment's primary metric.",
    ),
    confidence_level: float = Query(
        0.95,
        ge=0.5,
        lt=1.0,
        description="Confidence level for CIs (0.5 to 0.99, default 0.95).",
    ),
    db: Session = Depends(get_db),
) -> ExperimentResultsResponse:
    """
    Compute and return statistical results for an experiment.

    Returns per-variant metrics and pairwise t-tests vs control.
    """
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Use the primary metric if none specified
    metric_name = metric or experiment.metrics["primary"]

    # Validate the metric is supported
    if metric_name not in METRIC_EVENT_TYPES:
        supported = ", ".join(sorted(METRIC_EVENT_TYPES.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{metric_name}'. Supported metrics: {supported}",
        )

    logger.info(
        f"Computing results: experiment_id={experiment_id}, "
        f"metric='{metric_name}', confidence={confidence_level}"
    )

    # Run the analysis
    analysis = analyze_experiment(db, experiment_id, metric_name, confidence_level)

    # Convert dataclasses to Pydantic models
    metrics_response = [
        VariantMetricsResponse.model_validate(m) for m in analysis["metrics"]
    ]

    tests_response = [
        TTestResultResponse(
            control_variant=t.control_variant,
            treatment_variant=t.treatment_variant,
            t_statistic=t.t_statistic,
            p_value=t.p_value,
            absolute_effect=t.absolute_effect,
            relative_effect=t.relative_effect,
            ci_lower=t.ci_lower,
            ci_upper=t.ci_upper,
            is_significant=t.p_value < 0.05,
        )
        for t in analysis["tests"]
    ]

    return ExperimentResultsResponse(
        experiment_id=experiment_id,
        experiment_name=experiment.name,
        metric_name=metric_name,
        confidence_level=confidence_level,
        metrics=metrics_response,
        tests=tests_response,
    )

@router.get(
    "/{experiment_id}/results/cuped",
    response_model=CupedResultsResponse,
)

def get_experiment_results_cuped(
    experiment_id: int,
    metric: str | None = Query(
        None,
        description="Metric to analyze. Defaults to the experiment's primary metric.",
    ),
    covariate: str = Query(
        "historical_spend",
        description="Pre-experiment covariate for CUPED adjustment.",
    ),
    confidence_level: float = Query(
        0.95,
        ge=0.5,
        lt=1.0,
        description="Confidence level for CIs (0.5 to 0.99, default 0.95).",
    ),
    db: Session = Depends(get_db),
) -> CupedResultsResponse:
    """
    Compute CUPED-adjusted experiment results.

    Returns both raw and CUPED-adjusted analysis, plus diagnostic info
    (theta, correlation, variance reduction).
    """
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    metric_name = metric or experiment.metrics["primary"]

    if metric_name not in METRIC_EVENT_TYPES:
        supported_metrics = ", ".join(sorted(METRIC_EVENT_TYPES.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{metric_name}'. Supported: {supported_metrics}",
        )

    if covariate not in SUPPORTED_COVARIATES:
        supported_covs = ", ".join(sorted(SUPPORTED_COVARIATES))
        raise HTTPException(
            status_code=400,
            detail=f"Unknown covariate '{covariate}'. Supported: {supported_covs}",
        )

    logger.info(
        f"CUPED results: experiment_id={experiment_id}, "
        f"metric='{metric_name}', covariate='{covariate}'"
    )

    try:
        analysis = analyze_experiment_with_cuped(
            db, experiment_id, metric_name, covariate, confidence_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Helper to wrap a TTestResult in the response model (with is_significant)
    def _t_to_response(t):
        return TTestResultResponse(
            control_variant=t.control_variant,
            treatment_variant=t.treatment_variant,
            t_statistic=t.t_statistic,
            p_value=t.p_value,
            absolute_effect=t.absolute_effect,
            relative_effect=t.relative_effect,
            ci_lower=t.ci_lower,
            ci_upper=t.ci_upper,
            is_significant=t.p_value < 0.05,
        )

    return CupedResultsResponse(
        experiment_id=experiment_id,
        experiment_name=experiment.name,
        metric_name=metric_name,
        confidence_level=confidence_level,
        metrics_raw=[VariantMetricsResponse.model_validate(m) for m in analysis["metrics_raw"]],
        tests_raw=[_t_to_response(t) for t in analysis["tests_raw"]],
        metrics_cuped=[VariantMetricsResponse.model_validate(m) for m in analysis["metrics_cuped"]],
        tests_cuped=[_t_to_response(t) for t in analysis["tests_cuped"]],
        cuped=CupedDiagnostics(
            covariate_type=covariate,
            theta=analysis["theta"],
            covariate_correlation=analysis["covariate_correlation"],
            variance_reduction=analysis["variance_reduction"],
        ),
    )