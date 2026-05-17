"""
Tests for the assignment service — the core of the experimentation platform.
"""

import pytest
from collections import Counter

from app.models.event import Assignment
from app.models.experiment import Experiment
from app.models.user import User
from app.services.assignment_service import (
    _hash_to_bucket,
    _bucket_to_variant,
    assign_user_to_variant,
    get_assignment,
)


def _create_running_experiment(db_session, variants=None) -> Experiment:
    """Helper: Create a running experiment for tests."""
    if variants is None:
        variants = [
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ]

    experiment = Experiment(
        name="Test Experiment",
        status="running",
        variants=variants,
        metrics={"primary": "conversion_rate", "secondary": []},
    )
    db_session.add(experiment)
    db_session.commit()
    return experiment


def _create_user(db_session, user_id_hint: int | None = None) -> User:
    """Helper: Create a user. Uses unique email per call."""
    import uuid
    email = f"user_{uuid.uuid4().hex[:8]}@test.com"
    user = User(email=email, name="Test User")
    db_session.add(user)
    db_session.commit()
    return user


class TestHashFunction:
    """
    Test the underlying hash function properties.
    """

    def test_hash_is_deterministic(self):
        """Same input always produces same output."""
        bucket1 = _hash_to_bucket(user_id=1, experiment_id=1)
        bucket2 = _hash_to_bucket(user_id=1, experiment_id=1)
        assert bucket1 == bucket2

    def test_hash_in_valid_range(self):
        """Output is always in [0.0, 1.0)."""
        for user_id in range(1, 100):
            for exp_id in range(1, 10):
                bucket = _hash_to_bucket(user_id, exp_id)
                assert 0.0 <= bucket < 1.0

    def test_different_users_get_different_buckets(self):
        """Different users typically get different buckets (not a hard requirement, but a sanity check)."""
        buckets = [_hash_to_bucket(uid, 1) for uid in range(1, 100)]
        # With 99 users and a uniform distribution, we should see many unique values
        assert len(set(buckets)) > 90

    def test_different_experiments_independent(self):
        """
        Same user, different experiments → different buckets.
        """
        # Test with 100 users and 2 experiments
        # Count how often experiment_1 and experiment_2 give the same bucket
        matches = 0
        for uid in range(1, 101):
            b1 = _hash_to_bucket(uid, 1)
            b2 = _hash_to_bucket(uid, 2)
            if abs(b1 - b2) < 0.01:
                matches += 1

        # Should be very rare (less than 5%) for buckets to be similar
        assert matches < 5

    def test_distribution_is_approximately_uniform(self):
        """
        Over many users, hash values should be uniformly distributed in [0,1).

        Test: bucket 1000 users into 10 deciles, expect ~100 per decile.
        With proper hashing, no decile should be wildly over/under-represented.
        """
        buckets = [_hash_to_bucket(uid, 1) for uid in range(1, 1001)]

        # Count how many fall in each decile
        deciles = [0] * 10
        for b in buckets:
            decile_idx = min(int(b * 10), 9)
            deciles[decile_idx] += 1

        # With 1000 samples in 10 buckets, expected count is 100
        # Allow generous tolerance (±40 = ±40%) since hash isn't perfectly uniform on small samples
        for count in deciles:
            assert 60 <= count <= 140, f"Decile counts: {deciles}"


class TestBucketToVariant:
    """Test the bucket → variant mapping logic."""

    def test_two_variant_50_50_split(self):
        """50/50 split: bucket < 0.5 → control, bucket >= 0.5 → treatment."""
        variants = [
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ]
        assert _bucket_to_variant(0.0, variants) == "control"
        assert _bucket_to_variant(0.25, variants) == "control"
        assert _bucket_to_variant(0.4999, variants) == "control"
        assert _bucket_to_variant(0.5, variants) == "treatment"
        assert _bucket_to_variant(0.75, variants) == "treatment"
        assert _bucket_to_variant(0.999, variants) == "treatment"

    def test_uneven_split(self):
        """90/10 split: bucket < 0.9 → control, bucket >= 0.9 → treatment."""
        variants = [
            {"name": "control", "allocation": 0.9},
            {"name": "treatment", "allocation": 0.1},
        ]
        assert _bucket_to_variant(0.0, variants) == "control"
        assert _bucket_to_variant(0.89, variants) == "control"
        assert _bucket_to_variant(0.9, variants) == "treatment"
        assert _bucket_to_variant(0.95, variants) == "treatment"

    def test_three_variants(self):
        """Three-way split with explicit thresholds."""
        variants = [
            {"name": "a", "allocation": 0.33},
            {"name": "b", "allocation": 0.33},
            {"name": "c", "allocation": 0.34},
        ]
        assert _bucket_to_variant(0.0, variants) == "a"
        assert _bucket_to_variant(0.32, variants) == "a"
        assert _bucket_to_variant(0.33, variants) == "b"
        assert _bucket_to_variant(0.65, variants) == "b"
        assert _bucket_to_variant(0.67, variants) == "c"
        assert _bucket_to_variant(0.99, variants) == "c"


class TestAssignUserToVariant:
    """Test the full assignment flow with database persistence."""

    def test_assigns_user_to_variant(self, db_session):
        """First call creates an assignment."""
        user = _create_user(db_session)
        experiment = _create_running_experiment(db_session)

        assignment = assign_user_to_variant(db_session, user.id, experiment.id)

        assert assignment is not None
        assert assignment.user_id == user.id
        assert assignment.experiment_id == experiment.id
        assert assignment.variant_name in {"control", "treatment"}

    def test_assignment_is_idempotent(self, db_session):
        """Multiple calls return the same assignment."""
        user = _create_user(db_session)
        experiment = _create_running_experiment(db_session)

        assignment1 = assign_user_to_variant(db_session, user.id, experiment.id)
        assignment2 = assign_user_to_variant(db_session, user.id, experiment.id)
        assignment3 = assign_user_to_variant(db_session, user.id, experiment.id)

        assert assignment1.id == assignment2.id == assignment3.id
        assert assignment1.variant_name == assignment2.variant_name == assignment3.variant_name

    def test_assignment_persists_in_database(self, db_session):
        """Assignment is saved to the database."""
        user = _create_user(db_session)
        experiment = _create_running_experiment(db_session)

        assign_user_to_variant(db_session, user.id, experiment.id)

        # Query directly to verify it's in the DB
        count = db_session.query(Assignment).filter(
            Assignment.user_id == user.id,
            Assignment.experiment_id == experiment.id,
        ).count()
        assert count == 1

    def test_assignment_requires_running_experiment(self, db_session):
        """Cannot assign to draft, paused, or completed experiments."""
        user = _create_user(db_session)

        for status in ["draft", "paused", "completed"]:
            experiment = Experiment(
                name=f"{status} experiment",
                status=status,
                variants=[
                    {"name": "control", "allocation": 0.5},
                    {"name": "treatment", "allocation": 0.5},
                ],
                metrics={"primary": "conversion_rate", "secondary": []},
            )
            db_session.add(experiment)
            db_session.commit()

            with pytest.raises(ValueError, match="must be 'running'"):
                assign_user_to_variant(db_session, user.id, experiment.id)

    def test_assignment_invalid_user(self, db_session):
        """Nonexistent user raises ValueError."""
        experiment = _create_running_experiment(db_session)

        with pytest.raises(ValueError, match="User .* not found"):
            assign_user_to_variant(db_session, 9999, experiment.id)

    def test_assignment_invalid_experiment(self, db_session):
        """Nonexistent experiment raises ValueError."""
        user = _create_user(db_session)

        with pytest.raises(ValueError, match="Experiment .* not found"):
            assign_user_to_variant(db_session, user.id, 9999)

    def test_get_assignment_returns_none_if_missing(self, db_session):
        """get_assignment returns None if no assignment exists."""
        user = _create_user(db_session)
        experiment = _create_running_experiment(db_session)

        result = get_assignment(db_session, user.id, experiment.id)
        assert result is None

    def test_get_assignment_returns_existing(self, db_session):
        """get_assignment returns the existing assignment."""
        user = _create_user(db_session)
        experiment = _create_running_experiment(db_session)

        created = assign_user_to_variant(db_session, user.id, experiment.id)
        fetched = get_assignment(db_session, user.id, experiment.id)

        assert fetched is not None
        assert fetched.id == created.id


class TestAllocationDistribution:
    """
    Statistical tests: verify allocations are respected over many users.
    """

    def test_50_50_split_is_approximately_even(self, db_session):
        """
        With 500 users and a 50/50 split, we expect roughly 250 in each variant.

        Tolerance: ±50 (allow for natural variance in finite samples).
        """
        experiment = _create_running_experiment(db_session)

        # Create 500 users and assign each
        variants_assigned = []
        for i in range(500):
            user = _create_user(db_session)
            assignment = assign_user_to_variant(db_session, user.id, experiment.id)
            variants_assigned.append(assignment.variant_name)

        counts = Counter(variants_assigned)
        assert 200 <= counts["control"] <= 300, f"Control count: {counts['control']}"
        assert 200 <= counts["treatment"] <= 300, f"Treatment count: {counts['treatment']}"

    def test_uneven_allocation_is_respected(self, db_session):
        """
        With 500 users and a 90/10 split, we expect ~450 control and ~50 treatment.

        Tolerance: ±30 (10% allows more relative variance).
        """
        experiment = _create_running_experiment(db_session, variants=[
            {"name": "control", "allocation": 0.9},
            {"name": "treatment", "allocation": 0.1},
        ])

        variants_assigned = []
        for i in range(500):
            user = _create_user(db_session)
            assignment = assign_user_to_variant(db_session, user.id, experiment.id)
            variants_assigned.append(assignment.variant_name)

        counts = Counter(variants_assigned)
        assert 420 <= counts["control"] <= 480, f"Control count: {counts['control']}"
        assert 20 <= counts["treatment"] <= 80, f"Treatment count: {counts['treatment']}"