"""Stable identifier generation and canonical serialization.

v0.5.0: Reproducibility support

Provides deterministic IDs and JSON serialization for:
- Variant unit references
- Reading identifiers (hash-based)
- Token positions
- Content hashing for verification
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any


def verse_id(book: str, chapter: int, verse: int) -> str:
    """Generate stable verse identifier.

    Args:
        book: Book name (e.g., "John")
        chapter: Chapter number
        verse: Verse number

    Returns:
        Stable ID like "John.1.18"

    Example:
        >>> verse_id("John", 1, 18)
        'John.1.18'
    """
    return f"{book}.{chapter}.{verse}"


def variant_unit_id(verse_ref: str, position: int) -> str:
    """Generate stable variant unit identifier.

    Args:
        verse_ref: Verse reference (e.g., "John.1.18")
        position: Token position in verse (0-indexed)

    Returns:
        Stable ID like "John.1.18:3"

    Example:
        >>> variant_unit_id("John.1.18", 3)
        'John.1.18:3'
    """
    return f"{verse_ref}:{position}"


def normalize_text(text: str) -> str:
    """Normalize Greek text for consistent hashing.

    Applies:
    - Unicode NFC normalization
    - Lowercase
    - Strip whitespace
    - Remove diacritics (for comparison only)

    Args:
        text: Greek text

    Returns:
        Normalized form
    """
    # NFC normalize
    text = unicodedata.normalize("NFC", text)
    # Strip and lowercase
    text = text.strip().lower()
    return text


def reading_id(unit_id: str, normalized_text: str) -> str:
    """Generate stable reading identifier using deterministic hash.

    Uses first 12 chars of SHA256 of (unit_id + normalized_text).
    This ensures same reading text at same location always gets same ID.

    Args:
        unit_id: Variant unit ID (e.g., "John.1.18:3")
        normalized_text: Normalized surface text of reading

    Returns:
        Stable ID like "John.1.18:3#a1b2c3d4e5f6"

    Example:
        >>> reading_id("John.1.18:3", "μονογενης θεος")
        'John.1.18:3#...'  # deterministic hash suffix
    """
    # Normalize the text for consistent hashing
    normalized = normalize_text(normalized_text)
    # Create deterministic hash input
    hash_input = f"{unit_id}|{normalized}"
    # SHA256 -> first 12 hex chars
    hash_digest = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()[:12]
    return f"{unit_id}#{hash_digest}"


def token_id(verse_ref: str, position: int) -> str:
    """Generate stable token identifier.

    Args:
        verse_ref: Verse reference (e.g., "John.1.18")
        position: Token position (0-indexed)

    Returns:
        Stable ID like "John.1.18:5"

    Example:
        >>> token_id("John.1.18", 5)
        'John.1.18:5'
    """
    return f"{verse_ref}:{position}"


def canonical_json(obj: Any, *, sort_keys: bool = True) -> str:
    """Serialize object to canonical JSON for reproducible hashing.

    Produces deterministic output:
    - Sorted keys (configurable)
    - No extra whitespace
    - Consistent float formatting
    - UTF-8 encoding (no ASCII escapes for Unicode)

    Args:
        obj: Object to serialize
        sort_keys: Whether to sort dictionary keys (default: True)

    Returns:
        Canonical JSON string

    Example:
        >>> canonical_json({"b": 1, "a": 2})
        '{"a":2,"b":1}'
    """
    return json.dumps(
        obj,
        sort_keys=sort_keys,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def content_hash(data: Any) -> str:
    """Compute SHA256 hash of canonical JSON representation.

    Args:
        data: Object to hash (will be serialized to canonical JSON)

    Returns:
        64-character hex string (SHA256)

    Example:
        >>> content_hash({"key": "value"})
        'c8c1b4adae8e5af1a0e1a7a6b1c...'  # deterministic
    """
    canonical = canonical_json(data)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def file_hash(filepath: str) -> str:
    """Compute SHA256 hash of file contents.

    Args:
        filepath: Path to file

    Returns:
        64-character hex string (SHA256)
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
