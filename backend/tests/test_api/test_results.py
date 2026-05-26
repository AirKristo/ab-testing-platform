"""
Tests for the Results API endpoint.
"""

from app.models.event import Assignment, Event
from app.models.experiment import Experiment
from app.models.user import User


def _setup_experiment_with_data(db_session):
    """
    Create a running experiment with a clear treatment effect.

    Control: 50% conversion
    Treatment: 80% conversion
    """
    experiment = Experiment(
        name="Results API Test",
        status="running",
        variants=[
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ],
        metrics={"primary": "conversion_rate", "secondary": ["revenue_per_user"]},
    )
    db_session.add(experiment)
    db_session.commit()

    import uuid

    # Control: 10 users, 5 with purchases (50% conversion)
    for i in range(10):
        user = User(email=f"c_{uuid.uuid4().hex[:8]}@t.com", name="C")
        db_session.add(user)
        db_session.flush()

        db_session.add(Assignment(
            experiment_id=experiment.id, user_id=user.id, variant_name="control"
        ))
        if i < 5:
            db_session.add(Event(
                experiment_id=experiment.id, user_id=user.id,
                variant_name="control", event_type="purchase", event_value=25.0,
            ))

    # Treatment: 10 users, 8 with purchases (80% conversion)
    for i in range(10):
        user = User(email=f"t_{uuid.uuid4().hex[:8]}@t.com", name="T")
        db_session.add(user)
        db_session.flush()

        db_session.add(Assignment(
            experiment_id=experiment.id, user_id=user.id, variant_name="treatment"
        ))
        if i < 8:
            db_session.add(Event(
                experiment_id=experiment.id, user_id=user.id,
                variant_name="treatment", event_type="purchase", event_value=30.0,
            ))

    db_session.commit()
    return experiment


class TestGetResults:
    """Tests for GET /experiments/{id}/results"""

    def test_get_results_default_metric(self, client, db_session):
        """Uses experiment's primary metric by default."""
        experiment = _setup_experiment_with_data(db_session)

        response = client.get(f"/experiments/{experiment.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["experiment_id"] == experiment.id
        assert data["metric_name"] == "conversion_rate"  # The primary metric
        assert data["confidence_level"] == 0.95
        assert len(data["metrics"]) == 2
        assert len(data["tests"]) == 1

    def test_get_results_override_metric(self, client, db_session):
        """Can override the metric via query param."""
        experiment = _setup_experiment_with_data(db_session)

        response = client.get(
            f"/experiments/{experiment.id}/results?metric=revenue_per_user"
        )

        assert response.status_code == 200
        assert response.json()["metric_name"] == "revenue_per_user"

    def test_get_results_includes_significance_flag(self, client, db_session):
        """Test results include is_significant boolean."""
        experiment = _setup_experiment_with_data(db_session)

        response = client.get(f"/experiments/{experiment.id}/results")

        data = response.json()
        test = data["tests"][0]
        assert "is_significant" in test
        assert isinstance(test["is_significant"], bool)
        # is_significant should match the p_value check
        assert test["is_significant"] == (test["p_value"] < 0.05)

    def test_get_results_correct_metric_values(self, client, db_session):
        """Verify the computed values are correct."""
        experiment = _setup_experiment_with_data(db_session)

        response = client.get(f"/experiments/{experiment.id}/results")

        data = response.json()
        control = next(m for m in data["metrics"] if m["variant_name"] == "control")
        treatment = next(m for m in data["metrics"] if m["variant_name"] == "treatment")

        # Control: 5/10 = 0.5, Treatment: 8/10 = 0.8
        assert control["mean"] == 0.5
        assert treatment["mean"] == 0.8
        assert control["sample_size"] == 10
        assert treatment["sample_size"] == 10

    def test_get_results_custom_confidence_level(self, client, db_session):
        """Can request a different confidence level."""
        experiment = _setup_experiment_with_data(db_session)

        response = client.get(
            f"/experiments/{experiment.id}/results?confidence_level=0.99"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["confidence_level"] == 0.99

    def test_get_results_experiment_not_found(self, client, db_session):
        """404 for nonexistent experiment."""
        response = client.get("/experiments/9999/results")
        assert response.status_code == 404

    def test_get_results_invalid_metric(self, client, db_session):
        """400 for unknown metric."""
        experiment = _setup_experiment_with_data(db_session)

        response = client.get(
            f"/experiments/{experiment.id}/results?metric=fake_metric"
        )

        assert response.status_code == 400

    def test_get_results_invalid_confidence_level(self, client, db_session):
        """422 for out-of-range confidence level."""
        experiment = _setup_experiment_with_data(db_session)

        response = client.get(
            f"/experiments/{experiment.id}/results?confidence_level=1.5"
        )

        assert response.status_code == 422