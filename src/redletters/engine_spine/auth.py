"""Authentication token management per ADR-005.

Primary storage: OS keychain (macOS Keychain Services, Windows Credential Manager)
Fallback: ~/.greek2english/.auth_token with 0600 permissions
"""

from __future__ import annotations

import logging
import re
import secrets
from pathlib import Path

logger = logging.getLogger(__name__)

SERVICE_NAME = "com.redletters.engine"
TOKEN_ACCOUNT = "auth_token"
TOKEN_PREFIX = "rl_"
TOKEN_FILE_PATH = Path("~/.greek2english/.auth_token").expanduser()

# Regex for detecting tokens in logs/output (for scrubbing)
TOKEN_PATTERN = re.compile(r"rl_[A-Za-z0-9_-]{20,}")


class AuthError(Exception):
    """Authentication error."""

    pass


class SecurityError(Exception):
    """Security violation."""

    pass


def generate_auth_token() -> str:
    """Generate a new 256-bit auth token.

    Returns:
        Token string prefixed with 'rl_' (43 chars total)
    """
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


def _keyring_available() -> bool:
    """Check if keyring is available."""
    try:
        import keyring
        from keyring.errors import NoKeyringError

        # Try to detect if a backend is available
        try:
            keyring.get_keyring()
            return True
        except NoKeyringError:
            return False
    except ImportError:
        return False


def store_token(token: str) -> str:
    """Store auth token, preferring keychain.

    Args:
        token: The token to store

    Returns:
        Storage location ("keychain" or "file")

    Raises:
        SecurityError: If storage fails
    """
    if _keyring_available():
        try:
            import keyring

            keyring.set_password(SERVICE_NAME, TOKEN_ACCOUNT, token)
            logger.info("Token stored in OS keychain")
            return "keychain"
        except Exception as e:
            logger.warning(f"Keychain storage failed: {e}, falling back to file")

    # Fallback to file
    return _store_token_file(token)


def _store_token_file(token: str) -> str:
    """Store token in file with restricted permissions."""
    TOKEN_FILE_PATH.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    TOKEN_FILE_PATH.write_text(token)
    TOKEN_FILE_PATH.chmod(0o600)
    logger.warning(
        f"Token stored in file (keychain unavailable). Location: {TOKEN_FILE_PATH}"
    )
    return "file"


def get_stored_token() -> str | None:
    """Retrieve stored token, checking keychain first.

    Returns:
        Token string or None if not found

    Raises:
        SecurityError: If token file has unsafe permissions
    """
    # Try keychain first
    if _keyring_available():
        try:
            import keyring

            token = keyring.get_password(SERVICE_NAME, TOKEN_ACCOUNT)
            if token:
                return token
        except Exception as e:
            logger.debug(f"Keychain retrieval failed: {e}")

    # Fallback to file
    if TOKEN_FILE_PATH.exists():
        # Verify permissions before reading
        mode = TOKEN_FILE_PATH.stat().st_mode & 0o777
        if mode != 0o600:
            raise SecurityError(
                f"Token file has unsafe permissions: {oct(mode)}. "
                f"Expected 0600. Please fix: chmod 600 {TOKEN_FILE_PATH}"
            )
        return TOKEN_FILE_PATH.read_text().strip()

    return None


def delete_token() -> bool:
    """Delete stored token from all storage locations.

    Returns:
        True if any token was deleted
    """
    deleted = False

    # Try keychain
    if _keyring_available():
        try:
            import keyring

            keyring.delete_password(SERVICE_NAME, TOKEN_ACCOUNT)
            deleted = True
            logger.info("Token deleted from keychain")
        except Exception:
            pass

    # Try file
    if TOKEN_FILE_PATH.exists():
        TOKEN_FILE_PATH.unlink()
        deleted = True
        logger.info(f"Token file deleted: {TOKEN_FILE_PATH}")

    return deleted


def ensure_token_exists() -> str:
    """Ensure a token exists, creating one if necessary.

    Returns:
        The auth token (existing or newly generated)
    """
    token = get_stored_token()
    if token:
        return token

    # Generate and store new token
    token = generate_auth_token()
    store_token(token)
    logger.info("Generated new auth token")
    return token


def validate_token(provided: str, expected: str) -> bool:
    """Validate token with constant-time comparison.

    Args:
        provided: Token from request
        expected: Expected token

    Returns:
        True if tokens match
    """
    return secrets.compare_digest(provided, expected)


def mask_token(token: str) -> str:
    """Mask token for logging (show prefix only).

    Args:
        token: Full token string

    Returns:
        Masked token (e.g., "rl_a3f8****")
    """
    if len(token) < 10:
        return "****"
    return token[:7] + "****"


def scrub_secrets(text: str) -> str:
    """Scrub auth tokens from text for logging/diagnostics.

    Args:
        text: Text that may contain tokens

    Returns:
        Text with tokens replaced by mask
    """
    return TOKEN_PATTERN.sub("rl_****MASKED****", text)


class TokenStorage:
    """Token storage manager with caching."""

    def __init__(self):
        self._cached_token: str | None = None

    def get_token(self) -> str:
        """Get token, using cache if available."""
        if self._cached_token is None:
            self._cached_token = ensure_token_exists()
        return self._cached_token

    def rotate_token(self) -> str:
        """Generate and store a new token.

        Returns:
            The new token
        """
        new_token = generate_auth_token()
        store_token(new_token)
        self._cached_token = new_token
        logger.info("Auth token rotated")
        return new_token

    def reset_token(self) -> str:
        """Delete existing and create new token.

        Returns:
            The new token
        """
        delete_token()
        self._cached_token = None
        return self.get_token()

    def clear_cache(self) -> None:
        """Clear cached token (force re-read on next access)."""
        self._cached_token = None


# Global token storage instance
_token_storage = TokenStorage()


def get_auth_token() -> str:
    """Get the current auth token (convenience function)."""
    return _token_storage.get_token()


def rotate_auth_token() -> str:
    """Rotate the auth token (convenience function)."""
    return _token_storage.rotate_token()


def reset_auth_token() -> str:
    """Reset the auth token (convenience function)."""
    return _token_storage.reset_token()
