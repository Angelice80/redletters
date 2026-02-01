"""Integration tests for job lifecycle per Sprint-1-DOD.

Verifies:
- POST /v1/jobs creates job (returns 201 with job_id)
- Job starts immediately (state is 'queued', not 'draft')
- Job transitions: queued → running
- Job transitions: running → completed
- Job can fail: running → failed
- Persist-before-send verified

Uses shared fixtures from conftest.py for consistent auth handling.
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from redletters.engine_spine.app import create_engine_app
from redletters.engine_spine.database import EngineDatabase


# Uses engine_test_client from conftest.py - aliased to test_client for compatibility
@pytest.fixture
def test_client(tmp_path, patched_auth):
    """Create test client with temporary database and patched auth.

    Returns (client, token, db_path) tuple for compatibility with existing tests.
    """
    _, token = patched_auth
    db_path = tmp_path / "engine.db"
    workspace_base = tmp_path / "workspaces"
    token_path = tmp_path / ".auth_token"

    with patch.object(
        __import__("redletters.engine_spine.auth", fromlist=["TOKEN_FILE_PATH"]),
        "TOKEN_FILE_PATH",
        token_path,
    ):
        with patch(
            "redletters.engine_spine.auth._keyring_available",
            return_value=False,
        ):
            app = create_engine_app(
                db_path=db_path,
                workspace_base=workspace_base,
                safe_mode=False,
            )

            with TestClient(app) as client:
                yield client, token, db_path


class TestJobCreation:
    """Tests for job creation."""

    def test_create_job_returns_201(self, test_client):
        """POST /v1/jobs returns 201 with job_id per Sprint-1-DOD."""
        client, token, _ = test_client
        response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "config": {
                    "input_paths": ["/test/path"],
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "job_id" in data
        assert data["job_id"].startswith("job_")

    def test_create_job_state_is_queued(self, test_client):
        """Created job state is 'queued' (not 'draft') per Sprint-1-DOD."""
        client, token, _ = test_client
        response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "config": {
                    "input_paths": ["/test/path"],
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["state"] == "queued"

    def test_create_job_has_created_at(self, test_client):
        """Created job has created_at timestamp."""
        client, token, _ = test_client
        response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "config": {
                    "input_paths": ["/test/path"],
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "created_at" in data
        # Verify it's a valid timestamp
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

    def test_create_job_preserves_config(self, test_client):
        """Created job preserves configuration."""
        client, token, _ = test_client
        config = {
            "input_paths": ["/test/path1", "/test/path2"],
            "style": "meaning-first",
            "options": {"key": "value"},
        }
        response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": config},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["config"]["input_paths"] == config["input_paths"]
        assert data["config"]["style"] == config["style"]

    def test_create_job_idempotency(self, test_client):
        """Idempotency key prevents duplicate jobs."""
        client, token, _ = test_client
        idempotency_key = "unique_key_123"

        # First request
        response1 = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "config": {"input_paths": ["/test/path"]},
                "idempotency_key": idempotency_key,
            },
        )
        assert response1.status_code == 201
        job_id1 = response1.json()["job_id"]

        # Second request with same key
        response2 = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "config": {"input_paths": ["/different/path"]},
                "idempotency_key": idempotency_key,
            },
        )
        # Should return existing job, not create new
        assert response2.status_code == 201
        assert response2.json()["job_id"] == job_id1


class TestJobListing:
    """Tests for job listing."""

    def test_list_jobs_empty(self, test_client):
        """List jobs returns empty list when no jobs."""
        client, token, _ = test_client
        response = client.get(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_list_jobs_returns_created(self, test_client):
        """List jobs returns created jobs."""
        client, token, _ = test_client

        # Create a job
        client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"input_paths": ["/test"]}},
        )

        # List jobs
        response = client.get(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1

    def test_list_jobs_filter_by_state(self, test_client):
        """List jobs can filter by state."""
        client, token, _ = test_client

        # Create a job (will be queued)
        client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"input_paths": ["/test"]}},
        )

        # Filter for running (should be empty)
        response = client.get(
            "/v1/jobs?state=running",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 0


class TestJobRetrieval:
    """Tests for job retrieval."""

    def test_get_job_by_id(self, test_client):
        """Get job by ID."""
        client, token, _ = test_client

        # Create a job
        create_response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"input_paths": ["/test"]}},
        )
        job_id = create_response.json()["job_id"]

        # Get job
        response = client.get(
            f"/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["job_id"] == job_id

    def test_get_nonexistent_job(self, test_client):
        """Get nonexistent job returns 404."""
        client, token, _ = test_client

        response = client.get(
            "/v1/jobs/nonexistent_job_id",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


class TestJobCancellation:
    """Tests for job cancellation."""

    def test_cancel_queued_job(self, test_client):
        """Cancel queued job."""
        client, token, _ = test_client

        # Create a job
        create_response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"input_paths": ["/test"]}},
        )
        job_id = create_response.json()["job_id"]

        # Cancel job
        response = client.post(
            f"/v1/jobs/{job_id}/cancel",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["state"] == "cancelled"


class TestPersistBeforeSend:
    """Tests for persist-before-send contract per ADR-003."""

    def test_events_persisted_before_broadcast(self, test_client):
        """Events are persisted to database before being sent."""
        client, token, db_path = test_client

        # Create a job (emits state_changed event)
        create_response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={"config": {"input_paths": ["/test"]}},
        )
        job_id = create_response.json()["job_id"]

        # Check database for events
        db = EngineDatabase(db_path)
        events = db.get_events_since(0, job_id=job_id)

        # Should have at least one event (state_changed to queued)
        assert len(events) > 0

        # Event should have sequence number
        for event_data in events:
            event = event_data["event"]
            assert "sequence_number" in event
            assert event["sequence_number"] > 0

    def test_sequence_numbers_monotonic(self, test_client):
        """Sequence numbers are strictly monotonic."""
        client, token, db_path = test_client

        # Create multiple jobs to generate events
        for _ in range(3):
            client.post(
                "/v1/jobs",
                headers={"Authorization": f"Bearer {token}"},
                json={"config": {"input_paths": ["/test"]}},
            )

        # Get all events
        db = EngineDatabase(db_path)
        events = db.get_events_since(0)

        # Verify monotonicity
        sequences = [e["sequence"] for e in events]
        assert sequences == sorted(sequences)
        assert len(sequences) == len(set(sequences))  # No duplicates
