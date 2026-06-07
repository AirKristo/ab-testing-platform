"""
Pydantic schemas for the Experiment Results API.
"""

from pydantic import BaseModel, Field, ConfigDict


class VariantMetricsResponse(BaseModel):
    """Per-variant metrics in API responses."""
    variant_name: str
    sample_size: int
    mean: float
    std_dev: float
    ci_lower: float
    ci_upper: float

    model_config = ConfigDict(from_attributes=True)


class TTestResultResponse(BaseModel):
    """T-test comparison in API responses."""
    control_variant: str
    treatment_variant: str
    t_statistic: float
    p_value: float
    absolute_effect: float
    relative_effect: float
    ci_lower: float
    ci_upper: float
    is_significant: bool = Field(
        ...,
        description="True if p_value < 0.05 (statistical significance at α=0.05)",
    )

    model_config = ConfigDict(from_attributes=True)


class ExperimentResultsResponse(BaseModel):
    """
    Full experiment analysis response.

    Contains per-variant metrics and pairwise statistical comparisons.
    """
    experiment_id: int
    experiment_name: str
    metric_name: str
    confidence_level: float
    metrics: list[VariantMetricsResponse]
    tests: list[TTestResultResponse]

class CupedDiagnostics(BaseModel):
    """
    Diagnostic info about the CUPED adjustment.

    Useful for debugging and understanding why CUPED helped (or didn't).
    """
    covariate_type: str
    theta: float = Field(..., description="The regression slope used in the adjustment")
    covariate_correlation: float = Field(
        ...,
        description="Correlation between covariate and outcome (signed)",
    )
    variance_reduction: float = Field(
        ...,
        description="Proportion of variance reduced (rho^2). 0 to 1.",
    )


class CupedResultsResponse(BaseModel):
    """
    Experiment results with both raw and CUPED-adjusted analysis.

    Lets the frontend show a before/after comparison.
    """
    experiment_id: int
    experiment_name: str
    metric_name: str
    confidence_level: float

    # Raw (unadjusted) analysis
    metrics_raw: list[VariantMetricsResponse]
    tests_raw: list[TTestResultResponse]

    # CUPED-adjusted analysis
    metrics_cuped: list[VariantMetricsResponse]
    tests_cuped: list[TTestResultResponse]

    # CUPED diagnostics
    cuped: CupedDiagnostics