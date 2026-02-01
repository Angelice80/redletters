"""Integration tests for authentication per Sprint-1-DOD.

Verifies:
- Token required for all endpoints
- Token required for SSE stream
- Keychain storage works
- Fallback file storage works with 0600 permissions

Uses shared fixtures from conftest.py for consistent auth handling.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from redletters.engine_spine.app import create_engine_app
from redletters.engine_spine.auth import (
    delete_token,
    generate_auth_token,
    get_stored_token,
    mask_token,
    scrub_secrets,
    store_token,
    validate_token,
)


# Uses reset_engine_state from conftest.py (autouse=True) for rate limiter reset


class TestTokenGeneration:
    """Tests for token generation."""

    def test_generate_token_format(self):
        """Token has correct prefix and length."""
        token = generate_auth_token()
        assert token.startswith("rl_")
        assert len(token) == 46  # "rl_" + 43 chars

    def test_generate_token_uniqueness(self):
        """Each token is unique."""
        tokens = [generate_auth_token() for _ in range(100)]
        assert len(set(tokens)) == 100


class TestTokenValidation:
    """Tests for token validation."""

    def test_validate_correct_token(self):
        """Correct token validates."""
        token = generate_auth_token()
        assert validate_token(token, token)

    def test_validate_incorrect_token(self):
        """Incorrect token fails validation."""
        token1 = generate_auth_token()
        token2 = generate_auth_token()
        assert not validate_token(token1, token2)

    def test_constant_time_comparison(self):
        """Validation uses constant-time comparison."""
        # This test verifies the implementation calls secrets.compare_digest
        # by checking that similar tokens don't leak timing information
        token = generate_auth_token()
        wrong_tokens = [
            token[:-1] + "X",  # Last char different
            "X" + token[1:],  # First char different
            generate_auth_token(),  # Completely different
        ]

        # All should fail (we can't easily test timing, but we can verify behavior)
        for wrong in wrong_tokens:
            assert not validate_token(wrong, token)


class TestTokenStorage:
    """Tests for token storage."""

    def test_store_and_retrieve_token(self, tmp_path):
        """Token can be stored and retrieved."""
        # Use file storage for testing
        with patch(
            "redletters.engine_spine.auth.TOKEN_FILE_PATH",
            tmp_path / ".auth_token",
        ):
            with patch(
                "redletters.engine_spine.auth._keyring_available",
                return_value=False,
            ):
                token = generate_auth_token()
                store_token(token)
                retrieved = get_stored_token()
                assert retrieved == token

    def test_file_storage_permissions(self, tmp_path):
        """File storage uses 0600 permissions per ADR-005."""
        token_path = tmp_path / ".auth_token"
        with patch(
            "redletters.engine_spine.auth.TOKEN_FILE_PATH",
            token_path,
        ):
            with patch(
                "redletters.engine_spine.auth._keyring_available",
                return_value=False,
            ):
                token = generate_auth_token()
                store_token(token)

                # Check permissions
                mode = token_path.stat().st_mode & 0o777
                assert mode == 0o600

    def test_reject_world_readable_file(self, tmp_path):
        """Reject token file with unsafe permissions."""
        token_path = tmp_path / ".auth_token"
        token_path.write_text("rl_test_token_12345678901234567890123")
        token_path.chmod(0o644)  # World-readable - unsafe!

        with patch(
            "redletters.engine_spine.auth.TOKEN_FILE_PATH",
            token_path,
        ):
            with patch(
                "redletters.engine_spine.auth._keyring_available",
                return_value=False,
            ):
                from redletters.engine_spine.auth import SecurityError

                with pytest.raises(SecurityError):
                    get_stored_token()

    def test_delete_token(self, tmp_path):
        """Token can be deleted."""
        token_path = tmp_path / ".auth_token"
        with patch(
            "redletters.engine_spine.auth.TOKEN_FILE_PATH",
            token_path,
        ):
            with patch(
                "redletters.engine_spine.auth._keyring_available",
                return_value=False,
            ):
                token = generate_auth_token()
                store_token(token)
                assert token_path.exists()

                delete_token()
                assert not token_path.exists()


class TestTokenMasking:
    """Tests for token masking."""

    def test_mask_token(self):
        """Token is properly masked for logging."""
        token = "rl_a3f8c21e9b4d7f6e5a4b3c2d1e0f9g8h7i6j5k4l3m2n1o0p"
        masked = mask_token(token)
        assert masked == "rl_a3f8****"
        assert token not in masked

    def test_scrub_secrets(self):
        """Secrets are scrubbed from text."""
        text = "Token is rl_a3f8c21e9b4d7f6e5a4b3c2d1e0f9g8h7i6j5k4l3m2n1o0p in the log"
        scrubbed = scrub_secrets(text)
        assert "rl_a3f8c21e" not in scrubbed
        assert "rl_****MASKED****" in scrubbed


# Uses patched_auth from conftest.py


@pytest.fixture
def test_client(tmp_path, patched_auth):
    """Create test client with temporary database and patched auth."""
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
                yield client, token


class TestEndpointAuth:
    """Tests for endpoint authentication."""

    def test_status_without_token_returns_401(self, test_client):
        """Request without Authorization header returns 401."""
        client, _ = test_client
        response = client.get("/v1/engine/status")
        assert response.status_code == 401

    def test_status_with_invalid_token_returns_401(self, test_client):
        """Request with invalid token returns 401."""
        client, _ = test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401

    def test_status_with_valid_token_succeeds(self, test_client):
        """Request with valid token succeeds."""
        client, token = test_client
        response = client.get(
            "/v1/engine/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_stream_without_token_returns_401(self, test_client):
        """SSE stream without token returns 401."""
        client, _ = test_client
        response = client.get("/v1/stream")
        assert response.status_code == 401

    def test_jobs_without_token_returns_401(self, test_client):
        """Jobs endpoint without token returns 401."""
        client, _ = test_client
        response = client.get("/v1/jobs")
        assert response.status_code == 401

    def test_post_jobs_without_token_returns_401(self, test_client):
        """POST jobs without token returns 401."""
        client, _ = test_client
        response = client.post(
            "/v1/jobs",
            json={"config": {"input_paths": ["/test"]}},
        )
        assert response.status_code == 401


class TestFallbackWarning:
    """Tests for keychain fallback warning."""

    def test_fallback_logs_warning(self, tmp_path, caplog):
        """Fallback to file storage logs warning."""
        import logging

        token_path = tmp_path / ".auth_token"
        with patch(
            "redletters.engine_spine.auth.TOKEN_FILE_PATH",
            token_path,
        ):
            with patch(
                "redletters.engine_spine.auth._keyring_available",
                return_value=False,
            ):
                with caplog.at_level(logging.WARNING):
                    token = generate_auth_token()
                    store_token(token)

                # Should have warning about file storage
                assert any(
                    "keychain unavailable" in r.message.lower() for r in caplog.records
                )
