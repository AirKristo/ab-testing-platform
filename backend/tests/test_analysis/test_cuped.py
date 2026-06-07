"""
Tests for the CUPED variance reduction module.
"""

import numpy as np
import pytest

from app.analysis.cuped import (
    cuped_adjustment,
    calculate_variance_reduction,
    get_pre_experiment_covariate,
    analyze_experiment_with_cuped,
    SUPPORTED_COVARIATES,
)
from app.models.event import Assignment, Event
from app.models.experiment import Experiment
from app.models.order import Order
from app.models.user import User


class TestCupedAdjustmentMath:
    """Property-based tests for the CUPED math (no database)."""

    def test_zero_correlation_yields_no_reduction(self):
        """
        When X and Y are uncorrelated, CUPED provides no benefit.
        """
        np.random.seed(42)
        outcomes = np.random.normal(0, 1, 1000)
        covariates = np.random.normal(0, 1, 1000)  # independent of outcomes

        adjusted, theta = cuped_adjustment(outcomes, covariates)
        reduction = calculate_variance_reduction(outcomes, covariates)

        assert abs(theta) < 0.1  # Very small slope when uncorrelated
        assert reduction < 0.05  # Less than 5% reduction

    def test_perfect_positive_correlation_high_reduction(self):
        """
        When Y = a*X + noise (high correlation), variance reduction approaches 1.
        """
        np.random.seed(42)
        covariates = np.random.normal(0, 1, 1000)
        outcomes = 2 * covariates + np.random.normal(0, 0.01, 1000)  # very low noise

        reduction = calculate_variance_reduction(outcomes, covariates)
        assert reduction > 0.99  # Near-perfect prediction

    def test_partial_correlation_matches_formula(self):
        """
        Variance reduction should equal ρ² exactly.

        Construct data with known correlation, verify the reduction matches.
        """
        np.random.seed(42)
        n = 10000
        covariates = np.random.normal(0, 1, n)

        # Generate Y with target correlation ρ = 0.6
        # Y = ρ*X + sqrt(1-ρ²)*noise  → corr(X,Y) = ρ
        target_rho = 0.6
        noise = np.random.normal(0, 1, n)
        outcomes = target_rho * covariates + np.sqrt(1 - target_rho ** 2) * noise

        reduction = calculate_variance_reduction(outcomes, covariates)
        expected = target_rho ** 2  # 0.36

        # Should be close to 0.36 with some sample variability
        assert abs(reduction - expected) < 0.02

    def test_variance_actually_reduced(self):
        """
        Var(Y_cuped) should be < Var(Y) when correlation is non-zero.
        """
        np.random.seed(42)
        n = 1000
        covariates = np.random.normal(50, 20, n)  # e.g., historical spend
        # Outcome positively correlated with covariate
        outcomes = 0.5 * covariates + np.random.normal(0, 10, n)

        adjusted, theta = cuped_adjustment(outcomes, covariates)

        var_raw = float(outcomes.var(ddof=1))
        var_cuped = float(adjusted.var(ddof=1))

        assert var_cuped < var_raw

    def test_means_preserved_in_expectation(self):
        """
        CUPED should preserve the mean of Y within each group (in expectation).
        """
        np.random.seed(42)
        n = 500

        # Control and treatment have same X distribution (balanced)
        covariates_c = np.random.normal(50, 10, n)
        covariates_t = np.random.normal(50, 10, n)
        outcomes_c = 0.5 * covariates_c + np.random.normal(20, 5, n)
        outcomes_t = 0.5 * covariates_t + np.random.normal(22, 5, n)  # +2 effect

        all_outcomes = np.concatenate([outcomes_c, outcomes_t])
        all_covariates = np.concatenate([covariates_c, covariates_t])

        adjusted, theta = cuped_adjustment(all_outcomes, all_covariates)

        adjusted_c = adjusted[:n]
        adjusted_t = adjusted[n:]

        raw_diff = outcomes_t.mean() - outcomes_c.mean()
        cuped_diff = adjusted_t.mean() - adjusted_c.mean()

        # The treatment effect estimate should be preserved (within sampling noise)
        assert abs(raw_diff - cuped_diff) < 0.5

    def test_zero_variance_covariate_returns_unchanged(self):
        """If everyone has the same covariate, CUPED is a no-op."""
        outcomes = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        covariates = np.array([10.0, 10.0, 10.0, 10.0, 10.0])  # all the same

        adjusted, theta = cuped_adjustment(outcomes, covariates)

        assert theta == 0.0
        np.testing.assert_array_equal(adjusted, outcomes)

    def test_mismatched_lengths_raises(self):
        """Arrays of different lengths raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            cuped_adjustment(np.array([1.0, 2.0]), np.array([1.0, 2.0, 3.0]))

    def test_too_few_samples_raises(self):
        """Fewer than 2 samples raises ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            cuped_adjustment(np.array([1.0]), np.array([1.0]))


class TestGetPreExperimentCovariate:
    """Tests for fetching pre-experiment covariates from the database."""

    def test_invalid_covariate_type_raises(self, db_session):
        """Unsupported covariate type raises ValueError."""
        # Create a minimal experiment so the function gets that far
        exp = Experiment(
            name="x", status="running",
            variants=[{"name": "control", "allocation": 0.5},
                      {"name": "treatment", "allocation": 0.5}],
            metrics={"primary": "conversion_rate", "secondary": []},
        )
        db_session.add(exp)
        db_session.commit()

        with pytest.raises(ValueError, match="Unsupported covariate"):
            get_pre_experiment_covariate(db_session, exp.id, "made_up_thing")

    def test_returns_zero_for_no_prior_orders(self, db_session):
        """Users with no prior orders get covariate value 0."""
        from datetime import datetime, timezone, timedelta

        # Set up: user, experiment, assignment
        user = User(email="newuser@t.com", name="N")
        exp = Experiment(
            name="x", status="running",
            variants=[{"name": "control", "allocation": 0.5},
                      {"name": "treatment", "allocation": 0.5}],
            metrics={"primary": "conversion_rate", "secondary": []},
        )
        db_session.add_all([user, exp])
        db_session.commit()

        # Assign — but user has no orders
        assignment = Assignment(
            experiment_id=exp.id, user_id=user.id, variant_name="control",
            assigned_at=datetime.now(timezone.utc),
        )
        db_session.add(assignment)
        db_session.commit()

        covariates = get_pre_experiment_covariate(db_session, exp.id, "historical_spend")

        assert covariates[user.id] == 0.0

    def test_only_counts_orders_before_assignment(self, db_session):
        """
        Critical test: orders AFTER assignment must NOT count toward the covariate.
        """
        from datetime import datetime, timezone, timedelta

        # Pick a fixed assignment time so we can put orders before and after
        assigned_at = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        user = User(email="u@t.com", name="U")
        exp = Experiment(
            name="x", status="running",
            variants=[{"name": "control", "allocation": 0.5},
                      {"name": "treatment", "allocation": 0.5}],
            metrics={"primary": "revenue_per_user", "secondary": []},
        )
        db_session.add_all([user, exp])
        db_session.commit()

        # Two orders BEFORE assignment ($50 + $30 = $80)
        order_before_1 = Order(
            user_id=user.id, total_amount=50.0,
            created_at=assigned_at - timedelta(days=10),
        )
        order_before_2 = Order(
            user_id=user.id, total_amount=30.0,
            created_at=assigned_at - timedelta(days=5),
        )

        # Two orders AFTER assignment (should NOT count)
        order_after_1 = Order(
            user_id=user.id, total_amount=999.0,
            created_at=assigned_at + timedelta(days=1),
        )
        order_after_2 = Order(
            user_id=user.id, total_amount=999.0,
            created_at=assigned_at + timedelta(days=5),
        )

        db_session.add_all([order_before_1, order_before_2, order_after_1, order_after_2])

        assignment = Assignment(
            experiment_id=exp.id, user_id=user.id, variant_name="control",
            assigned_at=assigned_at,
        )
        db_session.add(assignment)
        db_session.commit()

        covariates = get_pre_experiment_covariate(db_session, exp.id, "historical_spend")

        # Should only include the $80 of pre-assignment orders
        assert covariates[user.id] == pytest.approx(80.0)

    def test_order_count_covariate(self, db_session):
        """Order count covariate counts only orders before assignment."""
        from datetime import datetime, timezone, timedelta

        assigned_at = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        user = User(email="u@t.com", name="U")
        exp = Experiment(
            name="x", status="running",
            variants=[{"name": "control", "allocation": 0.5},
                      {"name": "treatment", "allocation": 0.5}],
            metrics={"primary": "conversion_rate", "secondary": []},
        )
        db_session.add_all([user, exp])
        db_session.commit()

        # 3 orders before
        for i in range(3):
            db_session.add(Order(
                user_id=user.id, total_amount=10.0,
                created_at=assigned_at - timedelta(days=i + 1),
            ))
        # 5 orders after (shouldn't count)
        for i in range(5):
            db_session.add(Order(
                user_id=user.id, total_amount=10.0,
                created_at=assigned_at + timedelta(days=i + 1),
            ))

        db_session.add(Assignment(
            experiment_id=exp.id, user_id=user.id, variant_name="control",
            assigned_at=assigned_at,
        ))
        db_session.commit()

        covariates = get_pre_experiment_covariate(db_session, exp.id, "order_count")

        assert covariates[user.id] == 3.0