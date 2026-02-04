"""Integration tests for unified API routes (Sprint 16).

Verifies that the engine app includes both:
- Engine spine routes (/v1/*)
- API routes (/translate, /sources/*, /health, etc.)

This ensures GUI can access translate and sources endpoints via the engine port.
"""


class TestUnifiedOpenAPI:
    """Tests that OpenAPI includes all expected routes."""

    def test_openapi_contains_translate(self, engine_test_client):
        """OpenAPI schema includes /translate endpoint."""
        client, token = engine_test_client
        response = client.get(
            "/openapi.json",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "/translate" in data["paths"], "Missing /translate in OpenAPI"

    def test_openapi_contains_sources_status(self, engine_test_client):
        """OpenAPI schema includes /sources/status endpoint."""
        client, token = engine_test_client
        response = client.get(
            "/openapi.json",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "/sources/status" in data["paths"], "Missing /sources/status in OpenAPI"

    def test_openapi_contains_sources_endpoints(self, engine_test_client):
        """OpenAPI schema includes all sources endpoints."""
        client, token = engine_test_client
        response = client.get(
            "/openapi.json",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        paths = response.json()["paths"]

        expected = [
            "/sources",
            "/sources/status",
            "/sources/install",
            "/sources/uninstall",
        ]
        for path in expected:
            assert path in paths, f"Missing {path} in OpenAPI"

    def test_openapi_contains_engine_routes(self, engine_test_client):
        """OpenAPI schema includes engine spine routes."""
        client, token = engine_test_client
        response = client.get(
            "/openapi.json",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        paths = response.json()["paths"]

        expected = ["/v1/engine/status", "/v1/jobs", "/v1/stream"]
        for path in expected:
            assert path in paths, f"Missing {path} in OpenAPI"


class TestTranslateEndpoint:
    """Tests for /translate endpoint availability."""

    def test_translate_exists_returns_405_for_get(self, engine_test_client):
        """GET /translate returns 405 (route exists, wrong method)."""
        client, token = engine_test_client
        response = client.get(
            "/translate",
            headers={"Authorization": f"Bearer {token}"},
        )

        # 405 means route exists but GET is not allowed (it's POST only)
        assert response.status_code == 405

    def test_translate_post_requires_body(self, engine_test_client):
        """POST /translate requires request body."""
        client, token = engine_test_client
        response = client.post(
            "/translate",
            headers={"Authorization": f"Bearer {token}"},
        )

        # 422 = validation error (missing body), means route exists
        assert response.status_code == 422


class TestSourcesStatusEndpoint:
    """Tests for /sources/status endpoint availability."""

    def test_sources_status_returns_200(self, engine_test_client):
        """GET /sources/status returns 200."""
        client, token = engine_test_client
        response = client.get(
            "/sources/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    def test_sources_status_has_required_fields(self, engine_test_client):
        """GET /sources/status returns expected structure."""
        client, token = engine_test_client
        response = client.get(
            "/sources/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "data_root" in data
        assert "spine_installed" in data
        assert "sources" in data
        assert isinstance(data["sources"], dict)


class TestHealthEndpoint:
    """Tests for /health endpoint (API router)."""

    def test_health_returns_200(self, engine_test_client):
        """GET /health returns 200."""
        client, token = engine_test_client
        response = client.get(
            "/health",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    def test_health_has_status_field(self, engine_test_client):
        """GET /health returns status field."""
        client, token = engine_test_client
        response = client.get(
            "/health",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "degraded"]


class TestBackendShape:
    """Tests for backend shape detection (Sprint 19).

    Verifies that /v1/engine/status includes shape info for GUI mismatch detection.
    """

    def test_engine_status_includes_shape(self, engine_test_client):
        """GET /v1/engine/status includes shape field."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "shape" in data, "Missing 'shape' field in engine status"

    def test_shape_has_backend_mode(self, engine_test_client):
        """Shape includes backend_mode field."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        shape = response.json().get("shape", {})
        assert "backend_mode" in shape, "Missing 'backend_mode' in shape"
        assert shape["backend_mode"] == "full", "Expected full mode for unified app"

    def test_shape_has_route_booleans(self, engine_test_client):
        """Shape includes route presence booleans."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        shape = response.json().get("shape", {})

        # All required route booleans should be present
        assert "has_translate" in shape, "Missing 'has_translate' in shape"
        assert "has_sources_status" in shape, "Missing 'has_sources_status' in shape"
        assert "has_acknowledge" in shape, "Missing 'has_acknowledge' in shape"
        assert "has_variants_dossier" in shape, (
            "Missing 'has_variants_dossier' in shape"
        )

    def test_shape_indicates_full_mode_routes(self, engine_test_client):
        """Full mode app has all required routes."""
        client, token = engine_test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        shape = response.json().get("shape", {})

        # Full mode should have all routes
        assert shape.get("has_translate") is True, "Full mode should have /translate"
        assert shape.get("has_sources_status") is True, (
            "Full mode should have /sources/status"
        )
        assert shape.get("has_acknowledge") is True, (
            "Full mode should have /acknowledge"
        )
        assert shape.get("has_variants_dossier") is True, (
            "Full mode should have /variants/dossier"
        )
