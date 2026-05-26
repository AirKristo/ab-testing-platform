"""
Tests for the basic statistical analysis module.
"""

import math
import pytest
import numpy as np

from app.analysis.basic_stats import (
    calculate_metrics,
    two_sample_ttest,
    analyze_experiment,
    _get_user_metric_values,
)
from app.models.event import Assignment, Event
from app.models.experiment import Experiment
from app.models.user import User


def _create_experiment_with_data(
    db_session,
    variants: list[dict] | None = None,
):
    """
    Helper: Create an experiment in a runnable state.
    """
    if variants is None:
        variants = [
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ]

    experiment = Experiment(
        name="Stats Test Experiment",
        status="running",
        variants=variants,
        metrics={"primary": "conversion_rate", "secondary": []},
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _add_assigned_user(
    db_session,
    experiment_id: int,
    variant_name: str,
    purchase_value: float | None = None,
) -> User:
    """
    Helper: Create a user, assign them to a variant, optionally add a purchase event.
    """
    import uuid
    user = User(email=f"u_{uuid.uuid4().hex[:8]}@t.com", name="T")
    db_session.add(user)
    db_session.flush()

    assignment = Assignment(
        experiment_id=experiment_id,
        user_id=user.id,
        variant_name=variant_name,
    )
    db_session.add(assignment)

    if purchase_value is not None:
        event = Event(
            experiment_id=experiment_id,
            user_id=user.id,
            variant_name=variant_name,
            event_type="purchase",
            event_value=purchase_value,
        )
        db_session.add(event)

    db_session.commit()
    return user


class TestTTestMath:
    """
    Tests for the t-test computation using direct value lists.
    """

    def test_identical_groups_p_value_is_one(self):
        """When two groups are identical, p-value should be 1.0 (no difference)."""
        control = [10.0, 20.0, 30.0, 40.0, 50.0]
        treatment = [10.0, 20.0, 30.0, 40.0, 50.0]

        result = two_sample_ttest(control, treatment)

        assert result.p_value == pytest.approx(1.0)
        assert result.absolute_effect == pytest.approx(0.0)
        assert result.t_statistic == pytest.approx(0.0)

    def test_clear_difference_low_p_value(self):
        """When groups are very different, p-value should be small."""
        # Big effect: treatment is 10x higher
        control = [1.0] * 30
        treatment = [10.0] * 30

        result = two_sample_ttest(control, treatment)

        # Different means → significant
        assert result.p_value < 0.001
        assert result.absolute_effect == pytest.approx(9.0)
        assert result.relative_effect == pytest.approx(9.0)  # 900% increase

    def test_treatment_higher_positive_effect(self):
        """Treatment > control → positive absolute_effect."""
        control = [10.0, 11.0, 9.0, 10.0, 12.0]
        treatment = [15.0, 16.0, 14.0, 15.0, 17.0]

        result = two_sample_ttest(control, treatment)

        assert result.absolute_effect > 0
        assert result.absolute_effect == pytest.approx(5.0)

    def test_treatment_lower_negative_effect(self):
        """Treatment < control → negative absolute_effect."""
        control = [15.0, 16.0, 14.0, 15.0, 17.0]
        treatment = [10.0, 11.0, 9.0, 10.0, 12.0]

        result = two_sample_ttest(control, treatment)

        assert result.absolute_effect < 0

    def test_ci_excludes_zero_when_significant(self):
        """For a significant result, the CI for the effect should exclude 0."""
        control = [1.0] * 50
        treatment = [2.0] * 50

        result = two_sample_ttest(control, treatment)

        # Both bounds should be positive (CI doesn't cross zero)
        assert result.ci_lower > 0
        assert result.ci_upper > 0

    def test_ci_includes_zero_when_not_significant(self):
        """When there's no effect, CI should include 0."""
        np.random.seed(42)
        control = list(np.random.normal(10, 2, 50))
        treatment = list(np.random.normal(10, 2, 50))

        result = two_sample_ttest(control, treatment)

        # CI should include zero (no significant effect)
        assert result.ci_lower <= 0 <= result.ci_upper
        assert result.p_value > 0.05

    def test_relative_effect_zero_control_mean(self):
        """If control mean is 0, relative_effect defaults to 0 (no division by zero)."""
        control = [0.0, 0.0, 0.0, 0.0, 0.0]
        treatment = [1.0, 2.0, 3.0, 4.0, 5.0]

        result = two_sample_ttest(control, treatment)

        # No crash, returns 0
        assert result.relative_effect == 0.0

    def test_requires_minimum_sample_size(self):
        """T-test requires at least 2 observations per group."""
        with pytest.raises(ValueError, match="at least 2"):
            two_sample_ttest([1.0], [2.0])

    def test_matches_scipy(self):
        """
        Verify our t-test result matches scipy's direct call.
        """
        from scipy import stats as scipy_stats
        np.random.seed(123)
        control = list(np.random.normal(10, 2, 100))
        treatment = list(np.random.normal(11, 2.5, 100))

        result = two_sample_ttest(control, treatment)

        # Compare to scipy directly
        t_expected, p_expected = scipy_stats.ttest_ind(treatment, control, equal_var=False)

        assert result.t_statistic == pytest.approx(t_expected)
        assert result.p_value == pytest.approx(p_expected)


class TestCalculateMetrics:
    """Tests for calculate_metrics using a real database."""

    def test_binary_metric_conversion_rate(self, db_session):
        """
        Conversion rate = (users with purchase) / (total assigned users).
        """
        exp = _create_experiment_with_data(db_session)

        # Control: 5 users, 2 with purchases → 40% conversion
        for _ in range(2):
            _add_assigned_user(db_session, exp.id, "control", purchase_value=50.0)
        for _ in range(3):
            _add_assigned_user(db_session, exp.id, "control")  # no purchase

        # Treatment: 5 users, 4 with purchases → 80% conversion
        for _ in range(4):
            _add_assigned_user(db_session, exp.id, "treatment", purchase_value=50.0)
        for _ in range(1):
            _add_assigned_user(db_session, exp.id, "treatment")

        results = calculate_metrics(db_session, exp.id, "conversion_rate")

        control = next(r for r in results if r.variant_name == "control")
        treatment = next(r for r in results if r.variant_name == "treatment")

        assert control.sample_size == 5
        assert control.mean == pytest.approx(0.4)

        assert treatment.sample_size == 5
        assert treatment.mean == pytest.approx(0.8)

    def test_continuous_metric_revenue(self, db_session):
        """
        Revenue per user = sum of purchase values / total users.
        Non-purchasers contribute 0 (intent-to-treat).
        """
        exp = _create_experiment_with_data(db_session)

        # Control: 4 users, total revenue $40 → $10/user average
        _add_assigned_user(db_session, exp.id, "control", purchase_value=10.0)
        _add_assigned_user(db_session, exp.id, "control", purchase_value=30.0)
        _add_assigned_user(db_session, exp.id, "control")  # 0
        _add_assigned_user(db_session, exp.id, "control")  # 0

        results = calculate_metrics(db_session, exp.id, "revenue_per_user")

        control = next(r for r in results if r.variant_name == "control")
        assert control.sample_size == 4
        assert control.mean == pytest.approx(10.0)

    def test_empty_variant_returns_zeros(self, db_session):
        """A variant with no assigned users gets zero metrics (no crash)."""
        exp = _create_experiment_with_data(db_session)

        # Only add users to control
        _add_assigned_user(db_session, exp.id, "control", purchase_value=10.0)
        _add_assigned_user(db_session, exp.id, "control")

        results = calculate_metrics(db_session, exp.id, "conversion_rate")

        treatment = next(r for r in results if r.variant_name == "treatment")
        assert treatment.sample_size == 0
        assert treatment.mean == 0.0

    def test_confidence_interval_bounds_mean(self, db_session):
        """The CI should bracket the mean (lower ≤ mean ≤ upper)."""
        exp = _create_experiment_with_data(db_session)

        # Enough samples to compute a meaningful CI
        for _ in range(20):
            _add_assigned_user(db_session, exp.id, "control", purchase_value=10.0)
        for _ in range(20):
            _add_assigned_user(db_session, exp.id, "control", purchase_value=20.0)

        results = calculate_metrics(db_session, exp.id, "revenue_per_user")
        control = next(r for r in results if r.variant_name == "control")

        assert control.ci_lower <= control.mean <= control.ci_upper

    def test_invalid_experiment(self, db_session):
        """Nonexistent experiment raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            calculate_metrics(db_session, 9999, "conversion_rate")

    def test_invalid_metric(self, db_session):
        """Unknown metric name raises ValueError."""
        exp = _create_experiment_with_data(db_session)
        with pytest.raises(ValueError, match="Unknown metric"):
            calculate_metrics(db_session, exp.id, "totally_made_up")


class TestAnalyzeExperiment:
    """End-to-end test of the full analysis pipeline."""

    def test_full_analysis(self, db_session):
        """analyze_experiment returns both metrics and t-test results."""
        exp = _create_experiment_with_data(db_session)

        # Control: 50% conversion at $20 average
        for _ in range(10):
            _add_assigned_user(db_session, exp.id, "control", purchase_value=20.0)
        for _ in range(10):
            _add_assigned_user(db_session, exp.id, "control")

        # Treatment: 70% conversion at $25 average (higher!)
        for _ in range(14):
            _add_assigned_user(db_session, exp.id, "treatment", purchase_value=25.0)
        for _ in range(6):
            _add_assigned_user(db_session, exp.id, "treatment")

        result = analyze_experiment(db_session, exp.id, "conversion_rate")

        assert len(result["metrics"]) == 2
        assert len(result["tests"]) == 1  # Treatment vs control

        # Treatment should have higher mean
        control = next(m for m in result["metrics"] if m.variant_name == "control")
        treatment = next(m for m in result["metrics"] if m.variant_name == "treatment")
        assert treatment.mean > control.mean

        # T-test should reflect a positive effect
        test = result["tests"][0]
        assert test.control_variant == "control"
        assert test.treatment_variant == "treatment"
        assert test.absolute_effect > 0

    def test_three_variant_experiment(self, db_session):
        """Each treatment is compared to control."""
        exp = _create_experiment_with_data(db_session, variants=[
            {"name": "control", "allocation": 0.34},
            {"name": "treatment_a", "allocation": 0.33},
            {"name": "treatment_b", "allocation": 0.33},
        ])

        for _ in range(10):
            _add_assigned_user(db_session, exp.id, "control", purchase_value=10.0)
        for _ in range(10):
            _add_assigned_user(db_session, exp.id, "treatment_a", purchase_value=15.0)
        for _ in range(10):
            _add_assigned_user(db_session, exp.id, "treatment_b", purchase_value=20.0)

        result = analyze_experiment(db_session, exp.id, "revenue_per_user")

        assert len(result["metrics"]) == 3
        assert len(result["tests"]) == 2  # Two pairwise comparisons vs control