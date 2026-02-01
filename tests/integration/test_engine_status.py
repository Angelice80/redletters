"""Integration tests for engine status endpoint per Sprint-1-DOD.

Verifies:
- /v1/engine/status returns version
- /v1/engine/status returns build_hash
- /v1/engine/status returns api_version
- /v1/engine/status returns capabilities
"""


class TestEngineStatus:
    """Tests for /v1/engine/status endpoint."""

    def test_status_returns_version(self, engine_test_client):
        """Status returns version field per Sprint-1-DOD."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_status_returns_build_hash(self, engine_test_client):
        """Status returns build_hash field per Sprint-1-DOD."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "build_hash" in data
        assert isinstance(data["build_hash"], str)

    def test_status_returns_api_version(self, engine_test_client):
        """Status returns api_version field per Sprint-1-DOD."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "api_version" in data
        assert data["api_version"] == "v1"

    def test_status_returns_capabilities(self, engine_test_client):
        """Status returns capabilities array per Sprint-1-DOD."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)
        # Should include core capabilities
        assert "sse_streaming" in data["capabilities"]
        assert "job_management" in data["capabilities"]

    def test_status_returns_mode(self, engine_test_client):
        """Status returns mode field."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert data["mode"] in ["normal", "safe"]

    def test_status_returns_health(self, engine_test_client):
        """Status returns health field."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "health" in data
        assert data["health"] in ["healthy", "degraded"]

    def test_status_requires_auth(self, engine_test_client):
        """Status endpoint requires authentication."""
        client, _ = engine_test_client
        response = client.get("/v1/engine/status")

        assert response.status_code == 401

    def test_status_rejects_invalid_token(self, engine_test_client):
        """Status endpoint rejects invalid token."""
        client, _ = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401


class TestSafeModeStatus:
    """Tests for safe mode status."""

    def test_safe_mode_status_returns_safe(self, safe_mode_test_client):
        """Safe mode returns mode: 'safe' per Sprint-1-DOD."""
        client, token = safe_mode_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "safe"

    def test_safe_mode_jobs_disabled(self, safe_mode_test_client):
        """Safe mode returns 503 for POST /v1/jobs per Sprint-1-DOD."""
        client, token = safe_mode_test_client
        response = client.post(
            "/v1/jobs",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "config": {
                    "input_paths": ["/some/path"],
                },
            },
        )

        assert response.status_code == 503
        data = response.json()
        assert "safe mode" in data.get("detail", {}).get("message", "").lower()
