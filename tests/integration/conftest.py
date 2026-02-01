"""Shared fixtures for integration tests."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from redletters.engine_spine.app import create_engine_app
from redletters.engine_spine.auth import generate_auth_token
from redletters.engine_spine.middleware import reset_rate_limiter
from redletters.engine_spine.status import EngineState


@pytest.fixture(autouse=True)
def reset_engine_state():
    """Reset engine state singleton and rate limiter between tests."""
    # Reset rate limiter before each test
    reset_rate_limiter()
    yield
    EngineState.get_instance().reset()
    reset_rate_limiter()


@pytest.fixture
def patched_auth(tmp_path):
    """Create a test token with patched file storage.

    Patches multiple locations to ensure consistent token storage.
    """
    token = generate_auth_token()
    token_path = tmp_path / ".auth_token"

    # Create the token file manually
    token_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    token_path.write_text(token)
    token_path.chmod(0o600)

    # Patch the auth module's TOKEN_FILE_PATH
    with patch.object(
        __import__("redletters.engine_spine.auth", fromlist=["TOKEN_FILE_PATH"]),
        "TOKEN_FILE_PATH",
        token_path,
    ):
        # Also patch keyring to be unavailable
        with patch(
            "redletters.engine_spine.auth._keyring_available",
            return_value=False,
        ):
            # Clear the cached token
            import redletters.engine_spine.auth as auth_module

            auth_module._token_storage.clear_cache()

            yield (tmp_path, token)


@pytest.fixture
def engine_test_client(tmp_path, patched_auth):
    """Create test client with temporary database and patched auth."""
    _, token = patched_auth
    db_path = tmp_path / "engine.db"
    workspace_base = tmp_path / "workspaces"
    token_path = tmp_path / ".auth_token"

    # Re-apply patches within the test client context
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


@pytest.fixture
def safe_mode_test_client(tmp_path, patched_auth):
    """Create test client in safe mode with patched auth."""
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
                safe_mode=True,
            )

            with TestClient(app) as client:
                yield client, token
