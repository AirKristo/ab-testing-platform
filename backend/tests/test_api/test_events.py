"""
Tests for the Event tracking API.
"""

from app.models.event import Event
from app.models.experiment import Experiment
from app.models.user import User


def _setup(db_session):
    """Helper: Create a user and a running experiment."""
    user = User(email="event_test@test.com", name="Event Tester")
    experiment = Experiment(
        name="Event Test Experiment",
        status="running",
        variants=[
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ],
        metrics={"primary": "conversion_rate", "secondary": []},
    )
    db_session.add_all([user, experiment])
    db_session.commit()
    return user, experiment


class TestCreateEvent:
    """Tests for POST /events"""

    def test_track_event_with_assignment(self, client, db_session):
        """Events are recorded with the correct variant from assignment."""
        user, experiment = _setup(db_session)

        # First, create an assignment via the assignment endpoint
        assign_response = client.get(
            f"/assignments?user_id={user.id}&experiment_id={experiment.id}"
        )
        variant_name = assign_response.json()["variant_name"]

        # Now track an event
        response = client.post("/events", json={
            "user_id": user.id,
            "experiment_id": experiment.id,
            "event_type": "exposure",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["event_type"] == "exposure"
        # The variant should match the assignment (server-resolved)
        assert data["variant_name"] == variant_name

    def test_track_event_without_assignment_ignored(self, client, db_session):
        """Events for unassigned users are silently dropped."""
        user, experiment = _setup(db_session)

        # Track event WITHOUT first assigning the user
        response = client.post("/events", json={
            "user_id": user.id,
            "experiment_id": experiment.id,
            "event_type": "purchase",
            "event_value": 99.99,
        })

        # Should succeed at the HTTP level but indicate the event was ignored
        assert response.status_code == 201
        assert response.json()["status"] == "ignored"

        # Verify no event was created in the database
        count = db_session.query(Event).filter(Event.user_id == user.id).count()
        assert count == 0

    def test_track_event_with_value(self, client, db_session):
        """Events can carry a numeric value (e.g., purchase amount)."""
        user, experiment = _setup(db_session)
        client.get(f"/assignments?user_id={user.id}&experiment_id={experiment.id}")

        response = client.post("/events", json={
            "user_id": user.id,
            "experiment_id": experiment.id,
            "event_type": "purchase",
            "event_value": 49.99,
        })

        assert response.status_code == 201
        assert float(response.json()["event_value"]) == 49.99

    def test_track_event_with_metadata(self, client, db_session):
        """Events can carry arbitrary metadata."""
        user, experiment = _setup(db_session)
        client.get(f"/assignments?user_id={user.id}&experiment_id={experiment.id}")

        response = client.post("/events", json={
            "user_id": user.id,
            "experiment_id": experiment.id,
            "event_type": "click",
            "event_metadata": {"product_id": 42, "page": "home"},
        })

        assert response.status_code == 201
        data = response.json()
        assert data["event_metadata"]["product_id"] == 42
        assert data["event_metadata"]["page"] == "home"

    def test_track_event_invalid_user(self, client, db_session):
        """Nonexistent user returns 404."""
        _, experiment = _setup(db_session)

        response = client.post("/events", json={
            "user_id": 9999,
            "experiment_id": experiment.id,
            "event_type": "exposure",
        })

        assert response.status_code == 404

    def test_track_event_invalid_experiment(self, client, db_session):
        """Nonexistent experiment returns 404."""
        user, _ = _setup(db_session)

        response = client.post("/events", json={
            "user_id": user.id,
            "experiment_id": 9999,
            "event_type": "exposure",
        })

        assert response.status_code == 404

    def test_event_variant_matches_assignment(self, client, db_session):
        """
        Critical test: the event's variant is always taken from the assignment.
        """
        user, experiment = _setup(db_session)

        # Get the user's assigned variant
        assign_response = client.get(
            f"/assignments?user_id={user.id}&experiment_id={experiment.id}"
        )
        true_variant = assign_response.json()["variant_name"]

        # Fire multiple events
        for event_type in ["exposure", "click", "purchase"]:
            response = client.post("/events", json={
                "user_id": user.id,
                "experiment_id": experiment.id,
                "event_type": event_type,
            })
            # All events should have the same variant (from assignment)
            assert response.json()["variant_name"] == true_variant

    def test_multiple_events_for_same_user(self, client, db_session):
        """A user can have many events (one per action)."""
        user, experiment = _setup(db_session)
        client.get(f"/assignments?user_id={user.id}&experiment_id={experiment.id}")

        # Fire 5 events
        for i in range(5):
            client.post("/events", json={
                "user_id": user.id,
                "experiment_id": experiment.id,
                "event_type": "click",
            })

        # Verify all 5 are in the database
        count = db_session.query(Event).filter(Event.user_id == user.id).count()
        assert count == 5