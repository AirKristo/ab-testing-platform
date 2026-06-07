"""
CUPED (Controlled-experiment Using Pre-Experiment Data) implementation.

Variance reduction technique for A/B tests. See docs/cuped-implementation.md
for the full methodology and motivation.
"""

from collections import defaultdict
from typing import Literal

import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analysis.basic_stats import (
    VariantMetrics,
    TTestResult,
    two_sample_ttest,
    _get_user_outcomes_by_user,
)
from app.models.event import Assignment
from app.models.experiment import Experiment
from app.models.order import Order
from app.utils.logging import get_logger

logger = get_logger(__name__)


# Supported covariate types
SUPPORTED_COVARIATES = {
    "historical_spend",      # Total order amount before assignment
    "order_count",           # Number of orders before assignment
    "days_since_signup",     # Account age at time of assignment
}

CovariateType = Literal["historical_spend", "order_count", "days_since_signup"]


def get_pre_experiment_covariate(
    db: Session,
    experiment_id: int,
    covariate_type: CovariateType = "historical_spend",
) -> dict[int, float]:
    """
    Compute pre-experiment covariate for each user assigned to the experiment.

    Example:
        covariates = get_pre_experiment_covariate(db, exp_id, "historical_spend")
        # {1: 152.50, 2: 0.0, 3: 87.30, ...}
    """
    if covariate_type not in SUPPORTED_COVARIATES:
        raise ValueError(
            f"Unsupported covariate '{covariate_type}'. "
            f"Choose from: {sorted(SUPPORTED_COVARIATES)}"
        )

    assignments = (
        db.query(Assignment)
        .filter(Assignment.experiment_id == experiment_id)
        .all()
    )

    logger.info(
        f"Computing covariate '{covariate_type}' for "
        f"{len(assignments)} assigned users"
    )

    covariates: dict[int, float] = {}

    for assignment in assignments:
        user_id = assignment.user_id
        assigned_at = assignment.assigned_at

        if covariate_type == "historical_spend":
            total = db.query(func.sum(Order.total_amount)).filter(
                Order.user_id == user_id,
                Order.created_at < assigned_at,
            ).scalar()
            covariates[user_id] = float(total) if total is not None else 0.0

        elif covariate_type == "order_count":
            count = db.query(func.count(Order.id)).filter(
                Order.user_id == user_id,
                Order.created_at < assigned_at,
            ).scalar()
            covariates[user_id] = float(count) if count is not None else 0.0

        elif covariate_type == "days_since_signup":
            # Get the user's created_at, compute days between then and assignment
            from app.models.user import User
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.created_at:
                delta = assigned_at - user.created_at
                covariates[user_id] = float(delta.total_seconds() / 86400)
            else:
                covariates[user_id] = 0.0

    return covariates


def cuped_adjustment(
    outcomes: np.ndarray,
    covariates: np.ndarray,
) -> tuple[np.ndarray, float]:
    """
    Apply the CUPED adjustment formula.
    """
    if len(outcomes) != len(covariates):
        raise ValueError(
            f"outcomes and covariates must be same length, "
            f"got {len(outcomes)} and {len(covariates)}"
        )

    if len(outcomes) < 2:
        raise ValueError("Need at least 2 observations for CUPED adjustment")

    # Use sample (ddof=1) statistics — we're working with samples, not populations
    var_x = float(np.var(covariates, ddof=1))

    if var_x == 0:
        # Covariate is constant — no variance to exploit
        logger.warning("Covariate has zero variance — CUPED adjustment skipped")
        return outcomes.copy(), 0.0

    cov_xy = float(np.cov(covariates, outcomes, ddof=1)[0, 1])
    theta = cov_xy / var_x

    x_mean = float(covariates.mean())
    adjusted = outcomes - theta * (covariates - x_mean)

    logger.info(f"CUPED adjustment: theta={theta:.4f}, n={len(outcomes)}")

    return adjusted, theta


def calculate_variance_reduction(
    outcomes: np.ndarray,
    covariates: np.ndarray,
) -> float:
    """
    Calculate the proportion of variance reduced by CUPED.
    """
    if len(outcomes) != len(covariates):
        raise ValueError("outcomes and covariates must be same length")

    if len(outcomes) < 2:
        return 0.0

    # Correlation coefficient
    # Use np.corrcoef which handles edge cases (returns NaN if either has zero variance)
    correlation_matrix = np.corrcoef(covariates, outcomes)
    correlation = correlation_matrix[0, 1]

    if np.isnan(correlation):
        # Happens when one array has zero variance
        return 0.0

    return float(correlation ** 2)


def analyze_experiment_with_cuped(
    db: Session,
    experiment_id: int,
    metric_name: str,
    covariate_type: CovariateType = "historical_spend",
    confidence_level: float = 0.95,
) -> dict:
    """
    Full experiment analysis with CUPED adjustment.
    """
    # 1. Get per-user outcomes
    user_outcomes = _get_user_outcomes_by_user(db, experiment_id, metric_name)

    # 2. Get per-user covariates
    user_covariates = get_pre_experiment_covariate(db, experiment_id, covariate_type)

    # 3. Align: users present in both
    aligned_user_ids = sorted(set(user_outcomes.keys()) & set(user_covariates.keys()))

    if len(aligned_user_ids) < 2:
        raise ValueError(
            f"Not enough users for CUPED analysis (got {len(aligned_user_ids)})"
        )

    outcomes_arr = np.array([user_outcomes[uid][1] for uid in aligned_user_ids])
    covariates_arr = np.array([user_covariates[uid] for uid in aligned_user_ids])
    variant_names = [user_outcomes[uid][0] for uid in aligned_user_ids]

    # 4. CUPED adjustment (using POOLED theta)
    adjusted_arr, theta = cuped_adjustment(outcomes_arr, covariates_arr)

    # 5. Variance reduction metric
    variance_reduction = calculate_variance_reduction(outcomes_arr, covariates_arr)

    # Signed correlation (useful diagnostic)
    if len(outcomes_arr) >= 2 and covariates_arr.var() > 0:
        correlation = float(np.corrcoef(covariates_arr, outcomes_arr)[0, 1])
        if np.isnan(correlation):
            correlation = 0.0
    else:
        correlation = 0.0

    # 6. Group by variant for both raw and adjusted analyses
    by_variant_raw = defaultdict(list)
    by_variant_cuped = defaultdict(list)
    for variant, raw_val, adj_val in zip(variant_names, outcomes_arr, adjusted_arr):
        by_variant_raw[variant].append(float(raw_val))
        by_variant_cuped[variant].append(float(adj_val))

    # 7. Compute per-variant metrics — both raw and CUPED
    from scipy import stats as sp_stats
    alpha = 1 - confidence_level
    z = sp_stats.norm.ppf(1 - alpha / 2)

    def _compute_variant_metrics(values_dict: dict, experiment_variants: list) -> list[VariantMetrics]:
        """Inner helper: compute VariantMetrics from a variant→values dict."""
        results = []
        for variant_config in experiment_variants:
            variant_name = variant_config["name"]
            values = values_dict.get(variant_name, [])
            n = len(values)
            if n == 0:
                results.append(VariantMetrics(
                    variant_name=variant_name, sample_size=0, mean=0.0,
                    std_dev=0.0, ci_lower=0.0, ci_upper=0.0,
                ))
                continue
            arr = np.array(values)
            mean = float(arr.mean())
            std_dev = float(arr.std(ddof=1)) if n > 1 else 0.0
            margin = z * std_dev / np.sqrt(n) if n > 1 else 0.0
            results.append(VariantMetrics(
                variant_name=variant_name, sample_size=n, mean=mean,
                std_dev=std_dev, ci_lower=mean - margin, ci_upper=mean + margin,
            ))
        return results

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    metrics_raw = _compute_variant_metrics(by_variant_raw, experiment.variants)
    metrics_cuped = _compute_variant_metrics(by_variant_cuped, experiment.variants)

    # 8. Run t-tests on both raw and CUPED
    control_name = next(
        (m.variant_name for m in metrics_raw if m.variant_name == "control"),
        metrics_raw[0].variant_name if metrics_raw else None,
    )

    def _run_tests(by_variant: dict) -> list[TTestResult]:
        if control_name is None or control_name not in by_variant:
            return []
        tests = []
        for variant in by_variant:
            if variant == control_name:
                continue
            if len(by_variant[control_name]) < 2 or len(by_variant[variant]) < 2:
                continue
            tests.append(two_sample_ttest(
                control_values=by_variant[control_name],
                treatment_values=by_variant[variant],
                control_name=control_name,
                treatment_name=variant,
                confidence_level=confidence_level,
            ))
        return tests

    tests_raw = _run_tests(by_variant_raw)
    tests_cuped = _run_tests(by_variant_cuped)

    return {
        "metrics_raw": metrics_raw,
        "metrics_cuped": metrics_cuped,
        "tests_raw": tests_raw,
        "tests_cuped": tests_cuped,
        "theta": theta,
        "variance_reduction": variance_reduction,
        "covariate_correlation": correlation,
    }