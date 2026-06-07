"""
Basic statistical analysis for A/B experiments.

Compute per-variant metrics (sample size, mean,
standard deviation, confidence interval) and run statistical tests
comparing variants.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import numpy as np
from scipy import stats
from sqlalchemy.orm import Session

from app.models.event import Assignment, Event
from app.models.experiment import Experiment
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Mapping of metric name → event_type that signals the metric
# We could make this configurable per-experiment, but defaults work for now
METRIC_EVENT_TYPES = {
    "conversion_rate": "purchase",        # User purchased anything
    "revenue_per_user": "purchase",       # Total revenue per user
    "add_to_cart_rate": "add_to_cart",   # User added to cart at least once
    "click_through_rate": "click",        # User clicked at least once
}

# Whether each metric is binary (rate) or continuous (mean value)
METRIC_KIND: dict[str, Literal["binary", "continuous"]] = {
    "conversion_rate": "binary",
    "add_to_cart_rate": "binary",
    "click_through_rate": "binary",
    "revenue_per_user": "continuous",
}


@dataclass
class VariantMetrics:
    """
    Computed metrics for a single variant.
    """
    variant_name: str
    sample_size: int
    mean: float
    std_dev: float
    ci_lower: float       # Lower bound of 95% CI
    ci_upper: float       # Upper bound of 95% CI


@dataclass
class TTestResult:
    """
    Result of comparing two variants with Welch's t-test.

    Includes the test statistic, p-value, and effect size estimates.
    """
    control_variant: str
    treatment_variant: str
    t_statistic: float
    p_value: float
    absolute_effect: float       # treatment_mean - control_mean
    relative_effect: float       # (treatment - control) / control
    ci_lower: float              # 95% CI lower for the absolute effect
    ci_upper: float              # 95% CI upper for the absolute effect


def _get_user_metric_values(
    db: Session,
    experiment_id: int,
    metric_name: str,
) -> dict[str, list[float]]:
    """
    For each variant, return a list of per-user metric values.

    Behavior by metric type:
    - Binary metrics: 1 if user has at least one matching event, else 0
    - Continuous metrics: sum of event_values across matching events, else 0
    """
    event_type = METRIC_EVENT_TYPES.get(metric_name)
    if event_type is None:
        raise ValueError(f"Unknown metric: '{metric_name}'")

    metric_kind = METRIC_KIND[metric_name]

    # Get all assignments for this experiment (intent-to-treat denominator)
    assignments = (
        db.query(Assignment)
        .filter(Assignment.experiment_id == experiment_id)
        .all()
    )

    # Initialize: every assigned user contributes a value of 0 by default
    user_values: dict[int, float] = {a.user_id: 0.0 for a in assignments}
    user_variants: dict[int, str] = {a.user_id: a.variant_name for a in assignments}

    # Aggregate events into per-user values
    events = (
        db.query(Event)
        .filter(
            Event.experiment_id == experiment_id,
            Event.event_type == event_type,
        )
        .all()
    )

    for event in events:
        if event.user_id not in user_values:
            # User had events but no assignment — skip
            continue

        if metric_kind == "binary":
            user_values[event.user_id] = 1.0
        else:
            value = float(event.event_value) if event.event_value is not None else 0.0
            user_values[event.user_id] += value

    # Group user values by variant
    by_variant: dict[str, list[float]] = defaultdict(list)
    for user_id, value in user_values.items():
        variant = user_variants[user_id]
        by_variant[variant].append(value)

    return dict(by_variant)


def _get_user_outcomes_by_user(
    db: Session,
    experiment_id: int,
    metric_name: str,
) -> dict[int, tuple[str, float]]:
    """
    Per-user outcome data with user_id keys.
    """
    event_type = METRIC_EVENT_TYPES.get(metric_name)
    if event_type is None:
        raise ValueError(f"Unknown metric: '{metric_name}'")

    metric_kind = METRIC_KIND[metric_name]

    assignments = (
        db.query(Assignment)
        .filter(Assignment.experiment_id == experiment_id)
        .all()
    )

    # Initialize: every assigned user starts at 0 (intent-to-treat)
    user_data: dict[int, list] = {a.user_id: [a.variant_name, 0.0] for a in assignments}

    events = (
        db.query(Event)
        .filter(
            Event.experiment_id == experiment_id,
            Event.event_type == event_type,
        )
        .all()
    )

    for event in events:
        if event.user_id not in user_data:
            continue
        if metric_kind == "binary":
            user_data[event.user_id][1] = 1.0
        else:
            value = float(event.event_value) if event.event_value is not None else 0.0
            user_data[event.user_id][1] += value

    return {uid: (data[0], data[1]) for uid, data in user_data.items()}


def calculate_metrics(
    db: Session,
    experiment_id: int,
    metric_name: str,
    confidence_level: float = 0.95,
) -> list[VariantMetrics]:
    """
    Calculate per-variant metrics for an experiment.
    """
    # Validate experiment exists
    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if experiment is None:
        raise ValueError(f"Experiment {experiment_id} not found")

    logger.info(
        f"Computing metrics: experiment_id={experiment_id}, "
        f"metric='{metric_name}', confidence={confidence_level}"
    )

    # Get per-user values, grouped by variant
    by_variant = _get_user_metric_values(db, experiment_id, metric_name)

    # Z-score for the given confidence level
    alpha = 1 - confidence_level
    z = stats.norm.ppf(1 - alpha / 2)

    results: list[VariantMetrics] = []

    # Process variants in the order defined in the experiment config
    for variant_config in experiment.variants:
        variant_name = variant_config["name"]
        values = by_variant.get(variant_name, [])
        n = len(values)

        if n == 0:
            # No users in this variant yet — return zeros
            results.append(VariantMetrics(
                variant_name=variant_name,
                sample_size=0,
                mean=0.0,
                std_dev=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
            ))
            continue

        values_arr = np.array(values)
        mean = float(values_arr.mean())

        if n == 1:
            # Can't compute std_dev with one sample
            std_dev = 0.0
            ci_lower = ci_upper = mean
        else:
            # ddof=1 for sample standard deviation (Bessel's correction)
            std_dev = float(values_arr.std(ddof=1))
            standard_error = std_dev / np.sqrt(n)
            margin = z * standard_error
            ci_lower = mean - margin
            ci_upper = mean + margin

        results.append(VariantMetrics(
            variant_name=variant_name,
            sample_size=n,
            mean=mean,
            std_dev=std_dev,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
        ))

    logger.info(f"Computed metrics for {len(results)} variants")
    return results


def two_sample_ttest(
    control_values: list[float],
    treatment_values: list[float],
    control_name: str = "control",
    treatment_name: str = "treatment",
    confidence_level: float = 0.95,
) -> TTestResult:
    """
    Welch's two-sample t-test comparing treatment to control.
    """
    if len(control_values) < 2 or len(treatment_values) < 2:
        raise ValueError(
            "Need at least 2 observations per variant for a t-test. "
            f"Got control={len(control_values)}, treatment={len(treatment_values)}"
        )

    control_arr = np.array(control_values)
    treatment_arr = np.array(treatment_values)

    # Welch's t-test (equal_var=False)
    t_stat, p_value = stats.ttest_ind(treatment_arr, control_arr, equal_var=False)

    # Compute effect size
    control_mean = float(control_arr.mean())
    treatment_mean = float(treatment_arr.mean())
    absolute_effect = treatment_mean - control_mean

    # Relative effect (% change). Guard against division by zero.
    if control_mean != 0:
        relative_effect = absolute_effect / control_mean
    else:
        relative_effect = 0.0

    # 95% CI for the absolute effect
    var_c = float(control_arr.var(ddof=1))
    var_t = float(treatment_arr.var(ddof=1))
    n_c = len(control_arr)
    n_t = len(treatment_arr)

    se_diff = np.sqrt(var_t / n_t + var_c / n_c)

    # Welch-Satterthwaite degrees of freedom
    if var_c > 0 or var_t > 0:
        df_numerator = (var_t / n_t + var_c / n_c) ** 2
        df_denominator = (
            (var_t / n_t) ** 2 / (n_t - 1) + (var_c / n_c) ** 2 / (n_c - 1)
        )
        df = df_numerator / df_denominator if df_denominator > 0 else min(n_c, n_t) - 1
    else:
        df = min(n_c, n_t) - 1

    alpha = 1 - confidence_level
    t_crit = stats.t.ppf(1 - alpha / 2, df)
    margin = t_crit * se_diff

    return TTestResult(
        control_variant=control_name,
        treatment_variant=treatment_name,
        t_statistic=float(t_stat),
        p_value=float(p_value),
        absolute_effect=absolute_effect,
        relative_effect=relative_effect,
        ci_lower=absolute_effect - margin,
        ci_upper=absolute_effect + margin,
    )


def analyze_experiment(
    db: Session,
    experiment_id: int,
    metric_name: str,
    confidence_level: float = 0.95,
) -> dict:
    """
    Full experiment analysis: per-variant metrics + pairwise t-tests vs control.
    """
    # Compute per-variant metrics
    metrics = calculate_metrics(db, experiment_id, metric_name, confidence_level)

    # Identify the control variant (convention: variant named "control" or first one)
    control_metric = next(
        (m for m in metrics if m.variant_name == "control"),
        metrics[0] if metrics else None,
    )

    if control_metric is None:
        return {"metrics": [], "tests": []}

    # Get per-user values to run t-tests
    by_variant = _get_user_metric_values(db, experiment_id, metric_name)
    control_values = by_variant.get(control_metric.variant_name, [])

    # Run pairwise t-tests: each treatment vs control
    tests: list[TTestResult] = []
    for variant_metric in metrics:
        if variant_metric.variant_name == control_metric.variant_name:
            continue

        treatment_values = by_variant.get(variant_metric.variant_name, [])

        # Skip if either side doesn't have enough data
        if len(control_values) < 2 or len(treatment_values) < 2:
            continue

        result = two_sample_ttest(
            control_values=control_values,
            treatment_values=treatment_values,
            control_name=control_metric.variant_name,
            treatment_name=variant_metric.variant_name,
            confidence_level=confidence_level,
        )
        tests.append(result)

    return {"metrics": metrics, "tests": tests}