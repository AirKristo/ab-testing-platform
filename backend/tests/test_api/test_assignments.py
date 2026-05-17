"""
Tests for the Assignment API endpoint.
"""

from app.models.experiment import Experiment
from app.models.user import User


def _create_user_and_experiment(db_session, exp_status="running"):
    """Helper: Create a user and experiment for tests."""
    user = User(email="assign_test@test.com", name="Test User")
    experiment = Experiment(
        name="Assignment Test Experiment",
        status=exp_status,
        variants=[
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ],
        metrics={"primary": "conversion_rate", "secondary": []},
    )
    db_session.add_all([user, experiment])
    db_session.commit()
    return user, experiment


class TestGetAssignment:
    """Tests for GET /assignments"""

    def test_creates_assignment_on_first_call(self, client, db_session):
        """First call creates and returns assignment."""
        user, experiment = _create_user_and_experiment(db_session)

        response = client.get(
            f"/assignments?user_id={user.id}&experiment_id={experiment.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user.id
        assert data["experiment_id"] == experiment.id
        assert data["variant_name"] in {"control", "treatment"}

    def test_returns_same_assignment_on_repeated_calls(self, client, db_session):
        """Idempotency: multiple calls return the same variant."""
        user, experiment = _create_user_and_experiment(db_session)

        response1 = client.get(
            f"/assignments?user_id={user.id}&experiment_id={experiment.id}"
        )
        response2 = client.get(
            f"/assignments?user_id={user.id}&experiment_id={experiment.id}"
        )
        response3 = client.get(
            f"/assignments?user_id={user.id}&experiment_id={experiment.id}"
        )

        assert response1.json()["variant_name"] == response2.json()["variant_name"]
        assert response2.json()["variant_name"] == response3.json()["variant_name"]
        assert response1.json()["id"] == response2.json()["id"]

    def test_assignment_user_not_found(self, client, db_session):
        """Nonexistent user returns 404."""
        _, experiment = _create_user_and_experiment(db_session)

        response = client.get(
            f"/assignments?user_id=9999&experiment_id={experiment.id}"
        )

        assert response.status_code == 404

    def test_assignment_experiment_not_found(self, client, db_session):
        """Nonexistent experiment returns 404."""
        user, _ = _create_user_and_experiment(db_session)

        response = client.get(
            f"/assignments?user_id={user.id}&experiment_id=9999"
        )

        assert response.status_code == 404

    def test_assignment_to_draft_experiment_fails(self, client, db_session):
        """Cannot assign to a non-running experiment."""
        user, experiment = _create_user_and_experiment(db_session, exp_status="draft")

        response = client.get(
            f"/assignments?user_id={user.id}&experiment_id={experiment.id}"
        )

        assert response.status_code == 400

    def test_assignment_missing_params(self, client, db_session):
        """Missing query parameters return 422 validation error."""
        response = client.get("/assignments")
        assert response.status_code == 422