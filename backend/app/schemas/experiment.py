"""
Pydantic schemas for the Experiment Management API.

This is the core of the platform — where experiments are defined and configured.

- Status lifecycle: draft → running → completed
  - draft: Experiment is being configured, not yet live
  - running: Experiment is actively assigning users and tracking events
  - paused: Temporarily stopped (can resume)
  - completed: Experiment is done, no new assignments
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator


class VariantConfig(BaseModel):
    """
    Configuration for a single experiment variant.

    Example:
        {"name": "control", "allocation": 0.5}
        {"name": "treatment", "allocation": 0.5}
    """
    name: str = Field(..., min_length=1, max_length=100, examples=["control"])
    allocation: float = Field(
        ...,
        gt=0,
        le=1.0,
        examples=[0.5],
        description="Traffic allocation (0-1). All variants must sum to 1.0.",
    )


class MetricsConfig(BaseModel):
    """
    Configuration for experiment metrics.

    Example:
        {"primary": "conversion_rate", "secondary": ["revenue_per_user", "cart_size"]}
    """
    primary: str = Field(
        ...,
        min_length=1,
        examples=["conversion_rate"],
        description="The primary metric for decision-making.",
    )
    secondary: list[str] = Field(
        default=[],
        examples=[["revenue_per_user", "cart_size"]],
        description="Additional metrics to monitor (not for decision-making).",
    )


class ExperimentCreate(BaseModel):
    """
    Schema for creating a new experiment.

    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["Free Shipping Threshold Test"],
    )
    description: str | None = Field(
        None,
        examples=["Test whether a $50 vs $75 free shipping threshold increases AOV"],
    )
    variants: list[VariantConfig] = Field(
        ...,
        min_length=2,
        examples=[[
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ]],
    )
    metrics: MetricsConfig

    @model_validator(mode="after")
    def validate_experiment(self):
        """
        Cross-field validation that runs after individual field validation.
        """
        # Check: allocations must sum to 1.0 (with small floating-point tolerance)
        total_allocation = sum(v.allocation for v in self.variants)
        if abs(total_allocation - 1.0) > 0.001:
            raise ValueError(
                f"Variant allocations must sum to 1.0, got {total_allocation:.3f}"
            )

        # Check: variant names must be unique
        names = [v.name for v in self.variants]
        if len(names) != len(set(names)):
            raise ValueError("Variant names must be unique")

        return self


class ExperimentUpdate(BaseModel):
    """
    Schema for updating an experiment.
    """
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    variants: list[VariantConfig] | None = Field(None, min_length=2)
    metrics: MetricsConfig | None = None

    @model_validator(mode="after")
    def validate_update(self):
        """Only validate allocations if variants are being updated."""
        if self.variants is not None:
            total_allocation = sum(v.allocation for v in self.variants)
            if abs(total_allocation - 1.0) > 0.001:
                raise ValueError(
                    f"Variant allocations must sum to 1.0, got {total_allocation:.3f}"
                )

            names = [v.name for v in self.variants]
            if len(names) != len(set(names)):
                raise ValueError("Variant names must be unique")

        return self


class ExperimentResponse(BaseModel):
    """
    Full experiment response returned from the API.

    Includes all configuration plus server-generated fields
    (id, status, timestamps).
    """
    id: int
    name: str
    description: str | None
    status: str
    variants: list[VariantConfig]
    metrics: MetricsConfig
    start_date: datetime | None
    end_date: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperimentListResponse(BaseModel):
    """List of experiments with total count."""
    experiments: list[ExperimentResponse]
    total: int