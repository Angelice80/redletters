"""Provenance-gate loader for external data sources.

This loader acts as an EPISTEMIC BOUNDARY: it verifies provenance,
enforces integrity, and refuses to load data that fails validation.

Responsibilities (and nothing else):
1. Open DB, ensure schema v2 applied
2. For each source: verify local file exists
3. Compute SHA256 and match recorded SHA256 (or record if first load)
4. Insert/update sources row
5. Ingest records into tokens (MorphGNT) / lexicon_entries (Strong's)

Fail fast if:
- Source metadata missing
- SHA mismatch (tamper or drift)
- Parser emits rows without required fields
"""

import hashlib
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from redletters.db.schema_v2 import (
    SCHEMA_VERSION,
    get_schema_version,
    init_schema_v2,
    register_source,
)
from redletters.ingest.demo_data import (
    DEMO_COLLOCATIONS,
    DEMO_SENSES,
    DEMO_SPEECH_SPANS,
    DEMO_TOKENS,
)
from redletters.ingest.fetch import get_source_path, SOURCES
from redletters.ingest.morphgnt_parser import parse_directory as parse_morphgnt
from redletters.ingest.strongs_parser import parse_strongs_directory


@dataclass
class LoadReport:
    """Receipt for a data load operation.

    This is the provenance record - what was loaded, from where,
    and whether it matched expectations.
    """

    source_key: str
    source_id: int
    sha256_expected: str | None
    sha256_actual: str
    counts_inserted: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    success: bool = True
    error: str | None = None


class LoaderError(Exception):
    """Raised when loader cannot proceed due to provenance violation."""

    pass


class SHAMismatchError(LoaderError):
    """Raised when computed SHA256 doesn't match expected value."""

    def __init__(self, source_key: str, expected: str, actual: str):
        self.source_key = source_key
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"SHA256 mismatch for {source_key}: "
            f"expected {expected[:16]}..., got {actual[:16]}..."
        )


class MissingSourceError(LoaderError):
    """Raised when source data is not available locally."""

    pass


class MissingFieldError(LoaderError):
    """Raised when parser output is missing required fields."""

    pass


def _normalize(text: str) -> str:
    """Normalize text to NFC form (no other transformations)."""
    return unicodedata.normalize("NFC", text)


def _whitespace_normalize(text: str) -> str:
    """Normalize whitespace (collapse runs of whitespace to single space)."""
    return " ".join(text.split())


def compute_sha256(path: Path, exclude_marker: bool = True) -> str:
    """Compute SHA256 hash of a file or directory.

    For directories, hashes all files in sorted order.
    Excludes .fetched marker file by default (it contains the hash itself).
    """
    sha256 = hashlib.sha256()

    if path.is_file():
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
    elif path.is_dir():
        # Hash all files in sorted order for reproducibility
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                # Skip marker file to avoid circular dependency
                if exclude_marker and file_path.name == ".fetched":
                    continue
                sha256.update(file_path.name.encode("utf-8"))
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        sha256.update(chunk)

    return sha256.hexdigest()


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure schema v2 is applied."""
    current_version = get_schema_version(conn)
    if current_version is None or current_version < SCHEMA_VERSION:
        init_schema_v2(conn)


def get_expected_sha256(source_dir: Path) -> str | None:
    """Read expected SHA256 from .fetched marker file."""
    marker = source_dir / ".fetched"
    if not marker.exists():
        return None

    with open(marker) as f:
        for line in f:
            if line.startswith("sha256="):
                return line.strip().split("=", 1)[1]
    return None


def load_source(
    conn: sqlite3.Connection,
    source_key: str,
    data_dir: Path | None = None,
    skip_sha_check: bool = False,
) -> LoadReport:
    """
    Load a data source into the database with full provenance tracking.

    This is the main entry point - it:
    1. Verifies the source exists locally
    2. Validates SHA256 integrity
    3. Registers the source in the database
    4. Dispatches to the appropriate loader

    Args:
        conn: Database connection
        source_key: Key from SOURCES dict (e.g., "morphgnt-sblgnt")
        data_dir: Override data directory (default: ~/.redletters/data)
        skip_sha_check: Skip SHA validation (for testing only)

    Returns:
        LoadReport with results and any warnings

    Raises:
        MissingSourceError: If source not fetched
        SHAMismatchError: If SHA256 doesn't match
        LoaderError: If loading fails
    """
    # Ensure schema is ready
    ensure_schema(conn)

    # Get source spec
    if source_key not in SOURCES:
        raise LoaderError(f"Unknown source: {source_key}")
    spec = SOURCES[source_key]

    # Find source directory
    source_dir = get_source_path(source_key, data_dir)
    if source_dir is None:
        raise MissingSourceError(
            f"Source {source_key} not fetched. Run: redletters data fetch {source_key}"
        )

    # Compute and verify SHA256
    sha256_expected = get_expected_sha256(source_dir)
    sha256_actual = compute_sha256(source_dir)

    if not skip_sha_check and sha256_expected and sha256_actual != sha256_expected:
        raise SHAMismatchError(source_key, sha256_expected, sha256_actual)

    # Read metadata from marker file
    marker = source_dir / ".fetched"
    metadata = {}
    if marker.exists():
        with open(marker) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    metadata[k] = v

    # Register source in database
    retrieved_at = metadata.get("retrieved_at", datetime.now(timezone.utc).isoformat())
    source_id = register_source(
        conn,
        name=spec.name,
        version=spec.version,
        license_=spec.license,
        url=spec.url,
        retrieved_at=retrieved_at,
        sha256=sha256_actual,
        notes=spec.notes,
    )

    # Initialize report
    report = LoadReport(
        source_key=source_key,
        source_id=source_id,
        sha256_expected=sha256_expected,
        sha256_actual=sha256_actual,
    )

    # Dispatch to appropriate loader
    try:
        if source_key == "morphgnt-sblgnt":
            counts = load_morphgnt(conn, source_id, source_dir)
        elif source_key == "strongs-greek":
            counts = load_strongs(conn, source_id, source_dir)
        else:
            report.warnings.append(f"No loader implemented for {source_key}")
            counts = {}

        report.counts_inserted = counts
        conn.commit()

    except Exception as e:
        report.success = False
        report.error = str(e)
        conn.rollback()
        raise

    return report


def load_morphgnt(
    conn: sqlite3.Connection,
    source_id: int,
    source_dir: Path,
) -> dict[str, int]:
    """
    Load MorphGNT tokens into the database.

    Every token is validated for required fields before insertion.

    Returns:
        Dict with counts: {"tokens": N, "unique_lemmas": M}
    """
    # Find the actual data directory (may be nested in archive structure)
    morphgnt_dir = source_dir
    if (source_dir / "sblgnt-master").exists():
        morphgnt_dir = source_dir / "sblgnt-master"

    # Parse all files
    tokens = parse_morphgnt(morphgnt_dir)

    if not tokens:
        raise LoaderError(f"No tokens parsed from {morphgnt_dir}")

    # Validate required fields for each token
    required_fields = [
        "ref",
        "pos",
        "parse_code",
        "surface_text",
        "word",
        "normalized",
        "lemma",
    ]
    for token in tokens:
        for field_name in required_fields:
            value = getattr(token, field_name, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise MissingFieldError(
                    f"Token {token.ref} missing required field: {field_name}"
                )

    # Insert tokens
    cursor = conn.cursor()

    # Clear existing tokens from this source (idempotent reload)
    cursor.execute("DELETE FROM tokens WHERE source_id = ?", (source_id,))

    # Batch insert
    rows = [token.to_db_tuple(source_id) for token in tokens]
    cursor.executemany(
        """
        INSERT INTO tokens (ref, surface_text, word, normalized, lemma, pos, parse_code, source_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    unique_lemmas = {token.lemma for token in tokens}

    return {
        "tokens": len(tokens),
        "unique_lemmas": len(unique_lemmas),
    }


def load_strongs(
    conn: sqlite3.Connection,
    source_id: int,
    source_dir: Path,
) -> dict[str, int]:
    """
    Load Strong's Greek Dictionary entries into lexicon_entries.

    These are SENSE INVENTORIES, not authoritative meanings.

    Returns:
        Dict with counts: {"entries": N, "unique_lemmas": M}
    """
    # Parse XML
    entries = parse_strongs_directory(source_dir)

    if not entries:
        raise LoaderError(f"No entries parsed from {source_dir}")

    # Validate required fields
    for entry in entries:
        if not entry.lemma or not entry.lemma.strip():
            raise MissingFieldError(f"Strong's entry {entry.strongs_id} missing lemma")
        if not entry.gloss or not entry.gloss.strip():
            raise MissingFieldError(f"Strong's entry {entry.strongs_id} missing gloss")

    # Insert entries
    cursor = conn.cursor()

    # Clear existing entries from this source
    cursor.execute("DELETE FROM lexicon_entries WHERE source_id = ?", (source_id,))

    # Batch insert
    rows = [entry.to_db_tuple(source_id) for entry in entries]
    cursor.executemany(
        """
        INSERT INTO lexicon_entries (lemma, sense_id, gloss, definition, domain, source_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )

    unique_lemmas = {entry.lemma for entry in entries}

    return {
        "entries": len(entries),
        "unique_lemmas": len(unique_lemmas),
    }


def load_all(
    conn: sqlite3.Connection,
    data_dir: Path | None = None,
    skip_sha_check: bool = False,
) -> list[LoadReport]:
    """
    Load all available sources.

    Continues even if individual sources fail, collecting reports.
    """
    reports = []

    for source_key in SOURCES:
        try:
            # Skip UBS for now (requires additional handling)
            if source_key == "ubs-dictionary":
                continue

            source_dir = get_source_path(source_key, data_dir)
            if source_dir is None:
                # Source not fetched, skip
                continue

            report = load_source(conn, source_key, data_dir, skip_sha_check)
            reports.append(report)

        except Exception as e:
            reports.append(
                LoadReport(
                    source_key=source_key,
                    source_id=0,
                    sha256_expected=None,
                    sha256_actual="",
                    success=False,
                    error=str(e),
                )
            )

    return reports


# =============================================================================
# Demo data loader (preserved for offline testing)
# =============================================================================


def load_demo_data(conn: sqlite3.Connection) -> None:
    """Load all demo data into the database (for offline testing)."""
    load_tokens(conn)
    load_senses(conn)
    load_speech_spans(conn)
    load_collocations(conn)
    conn.commit()


def load_tokens(conn: sqlite3.Connection) -> None:
    """Load demo tokens with NFC-normalized Greek text."""
    # Normalize surface and lemma fields (indices 4 and 5)
    normalized_tokens = [
        (
            row[0],
            row[1],
            row[2],
            row[3],
            _normalize(row[4]),
            _normalize(row[5]),
            row[6],
            row[7],
        )
        for row in DEMO_TOKENS
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO tokens
        (book, chapter, verse, position, surface, lemma, morph, is_red_letter)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        normalized_tokens,
    )


def load_senses(conn: sqlite3.Connection) -> None:
    """Load demo lexeme senses with NFC-normalized lemmas."""
    # Normalize lemma field (index 0)
    normalized_senses = [
        (_normalize(row[0]), row[1], row[2], row[3], row[4], row[5], row[6])
        for row in DEMO_SENSES
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO lexeme_senses
        (lemma, sense_id, gloss, definition, source, weight, domain)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        normalized_senses,
    )


def load_speech_spans(conn: sqlite3.Connection) -> None:
    """Load demo speech spans."""
    conn.executemany(
        """
        INSERT OR REPLACE INTO speech_spans
        (book, chapter, verse_start, verse_end, speaker, confidence, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        DEMO_SPEECH_SPANS,
    )


def load_collocations(conn: sqlite3.Connection) -> None:
    """Load demo collocations with NFC-normalized lemmas."""
    # Normalize lemma1 and lemma2 fields (indices 0 and 1)
    normalized_collocations = [
        (_normalize(row[0]), _normalize(row[1]), row[2], row[3])
        for row in DEMO_COLLOCATIONS
    ]
    conn.executemany(
        """
        INSERT OR REPLACE INTO collocations
        (lemma1, lemma2, frequency, context_type)
        VALUES (?, ?, ?, ?)
        """,
        normalized_collocations,
    )
