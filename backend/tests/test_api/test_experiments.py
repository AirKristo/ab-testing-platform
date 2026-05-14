"""
Tests for the Experiment Management API.
"""

import pytest


# ---- Test Data Helpers ----

def _valid_experiment_payload(**overrides) -> dict:
    """
    Build a valid experiment creation payload.
    """
    payload = {
        "name": "Test Experiment",
        "description": "A test experiment",
        "variants": [
            {"name": "control", "allocation": 0.5},
            {"name": "treatment", "allocation": 0.5},
        ],
        "metrics": {
            "primary": "conversion_rate",
            "secondary": ["revenue_per_user"],
        },
    }
    payload.update(overrides)
    return payload


def _create_experiment(client, **overrides) -> dict:
    """Helper: Create an experiment and return the response data."""
    response = client.post("/experiments", json=_valid_experiment_payload(**overrides))
    assert response.status_code == 201
    return response.json()


class TestCreateExperiment:
    """Tests for POST /experiments"""

    def test_create_basic_experiment(self, client, db_session):
        """Create a simple A/B test with 50/50 split."""
        response = client.post("/experiments", json=_valid_experiment_payload())

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Experiment"
        assert data["status"] == "draft"
        assert len(data["variants"]) == 2
        assert data["metrics"]["primary"] == "conversion_rate"
        assert data["start_date"] is None
        assert data["end_date"] is None

    def test_create_three_variant_experiment(self, client, db_session):
        """Create an A/B/C test with three variants."""
        data = _create_experiment(client, variants=[
            {"name": "control", "allocation": 0.34},
            {"name": "treatment_a", "allocation": 0.33},
            {"name": "treatment_b", "allocation": 0.33},
        ])

        assert len(data["variants"]) == 3

    def test_create_experiment_allocations_must_sum_to_one(self, client, db_session):
        """Reject variants that don't sum to 1.0."""
        response = client.post("/experiments", json=_valid_experiment_payload(
            variants=[
                {"name": "control", "allocation": 0.3},
                {"name": "treatment", "allocation": 0.3},
            ]
        ))

        assert response.status_code == 422

    def test_create_experiment_duplicate_variant_names(self, client, db_session):
        """Reject duplicate variant names."""
        response = client.post("/experiments", json=_valid_experiment_payload(
            variants=[
                {"name": "control", "allocation": 0.5},
                {"name": "control", "allocation": 0.5},
            ]
        ))

        assert response.status_code == 422

    def test_create_experiment_minimum_two_variants(self, client, db_session):
        """Reject experiments with fewer than 2 variants."""
        response = client.post("/experiments", json=_valid_experiment_payload(
            variants=[
                {"name": "control", "allocation": 1.0},
            ]
        ))

        assert response.status_code == 422

    def test_create_experiment_allocation_must_be_positive(self, client, db_session):
        """Reject variants with zero or negative allocation."""
        response = client.post("/experiments", json=_valid_experiment_payload(
            variants=[
                {"name": "control", "allocation": 0},
                {"name": "treatment", "allocation": 1.0},
            ]
        ))

        assert response.status_code == 422


class TestListExperiments:
    """Tests for GET /experiments"""

    def test_list_all_experiments(self, client, db_session):
        """Returns all experiments."""
        _create_experiment(client, name="Experiment A")
        _create_experiment(client, name="Experiment B")

        response = client.get("/experiments")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_list_experiments_filter_by_status(self, client, db_session):
        """Filter returns only matching status."""
        exp = _create_experiment(client, name="Draft Experiment")
        _create_experiment(client, name="Another Draft")

        # Start one experiment
        client.post(f"/experiments/{exp['id']}/start")

        # Filter for running
        response = client.get("/experiments?status=running")
        data = response.json()
        assert data["total"] == 1
        assert data["experiments"][0]["name"] == "Draft Experiment"

    def test_list_experiments_empty(self, client, db_session):
        """Empty database returns empty list."""
        response = client.get("/experiments")

        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_list_experiments_invalid_status(self, client, db_session):
        """Invalid status filter returns 400."""
        response = client.get("/experiments?status=invalid")
        assert response.status_code == 400


class TestGetExperiment:
    """Tests for GET /experiments/{id}"""

    def test_get_experiment(self, client, db_session):
        """Returns correct experiment by ID."""
        exp = _create_experiment(client, name="My Experiment")

        response = client.get(f"/experiments/{exp['id']}")

        assert response.status_code == 200
        assert response.json()["name"] == "My Experiment"

    def test_get_experiment_not_found(self, client, db_session):
        """Nonexistent experiment returns 404."""
        response = client.get("/experiments/9999")
        assert response.status_code == 404


class TestUpdateExperiment:
    """Tests for PUT /experiments/{id}"""

    def test_update_name_and_description(self, client, db_session):
        """Update basic fields on a draft experiment."""
        exp = _create_experiment(client)

        response = client.put(f"/experiments/{exp['id']}", json={
            "name": "Updated Name",
            "description": "Updated description",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_update_variants_on_draft(self, client, db_session):
        """Can update variants while experiment is still draft."""
        exp = _create_experiment(client)

        response = client.put(f"/experiments/{exp['id']}", json={
            "variants": [
                {"name": "control", "allocation": 0.7},
                {"name": "treatment", "allocation": 0.3},
            ],
        })

        assert response.status_code == 200
        variants = response.json()["variants"]
        assert variants[0]["allocation"] == 0.7
        assert variants[1]["allocation"] == 0.3

    def test_cannot_update_variants_on_running(self, client, db_session):
        """Cannot change variants once experiment is running."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")

        response = client.put(f"/experiments/{exp['id']}", json={
            "variants": [
                {"name": "control", "allocation": 0.7},
                {"name": "treatment", "allocation": 0.3},
            ],
        })

        assert response.status_code == 400

    def test_can_update_name_on_running(self, client, db_session):
        """Name and description can be updated on running experiments."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")

        response = client.put(f"/experiments/{exp['id']}", json={
            "name": "Renamed Running Experiment",
        })

        assert response.status_code == 200
        assert response.json()["name"] == "Renamed Running Experiment"

    def test_update_not_found(self, client, db_session):
        """Update nonexistent experiment returns 404."""
        response = client.put("/experiments/9999", json={"name": "Nope"})
        assert response.status_code == 404


class TestDeleteExperiment:
    """Tests for DELETE /experiments/{id}"""

    def test_delete_draft_experiment(self, client, db_session):
        """Can delete a draft experiment."""
        exp = _create_experiment(client)

        response = client.delete(f"/experiments/{exp['id']}")
        assert response.status_code == 204

        # Verify it's gone
        get_response = client.get(f"/experiments/{exp['id']}")
        assert get_response.status_code == 404

    def test_cannot_delete_running_experiment(self, client, db_session):
        """Cannot delete a running experiment."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")

        response = client.delete(f"/experiments/{exp['id']}")
        assert response.status_code == 400

    def test_delete_completed_experiment(self, client, db_session):
        """Can delete a completed experiment."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")
        client.post(f"/experiments/{exp['id']}/complete")

        response = client.delete(f"/experiments/{exp['id']}")
        assert response.status_code == 204

    def test_delete_not_found(self, client, db_session):
        """Delete nonexistent experiment returns 404."""
        response = client.delete("/experiments/9999")
        assert response.status_code == 404


class TestExperimentStatusManagement:
    """
    Tests for the experiment status lifecycle.
    """

    def test_start_draft_experiment(self, client, db_session):
        """draft → running: sets status and start_date."""
        exp = _create_experiment(client)

        response = client.post(f"/experiments/{exp['id']}/start")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["start_date"] is not None

    def test_pause_running_experiment(self, client, db_session):
        """running → paused."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")

        response = client.post(f"/experiments/{exp['id']}/pause")

        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    def test_resume_paused_experiment(self, client, db_session):
        """paused → running (via start)."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")
        client.post(f"/experiments/{exp['id']}/pause")

        response = client.post(f"/experiments/{exp['id']}/start")

        assert response.status_code == 200
        assert response.json()["status"] == "running"

    def test_complete_running_experiment(self, client, db_session):
        """running → completed: sets end_date."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")

        response = client.post(f"/experiments/{exp['id']}/complete")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["end_date"] is not None

    def test_complete_paused_experiment(self, client, db_session):
        """paused → completed."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")
        client.post(f"/experiments/{exp['id']}/pause")

        response = client.post(f"/experiments/{exp['id']}/complete")

        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    def test_cannot_pause_draft(self, client, db_session):
        """draft → paused is invalid."""
        exp = _create_experiment(client)

        response = client.post(f"/experiments/{exp['id']}/pause")
        assert response.status_code == 400

    def test_cannot_complete_draft(self, client, db_session):
        """draft → completed is invalid."""
        exp = _create_experiment(client)

        response = client.post(f"/experiments/{exp['id']}/complete")
        assert response.status_code == 400

    def test_cannot_start_completed(self, client, db_session):
        """completed → running is invalid."""
        exp = _create_experiment(client)
        client.post(f"/experiments/{exp['id']}/start")
        client.post(f"/experiments/{exp['id']}/complete")

        response = client.post(f"/experiments/{exp['id']}/start")
        assert response.status_code == 400

    def test_start_preserves_original_start_date(self, client, db_session):
        """Resuming from paused doesn't change the original start_date."""
        exp = _create_experiment(client)

        # Start, capture the start_date
        start_response = client.post(f"/experiments/{exp['id']}/start")
        original_start = start_response.json()["start_date"]

        # Pause and resume
        client.post(f"/experiments/{exp['id']}/pause")
        resume_response = client.post(f"/experiments/{exp['id']}/start")

        assert resume_response.json()["start_date"] == original_start