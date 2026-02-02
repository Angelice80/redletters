"""Variant storage and persistence.

Implements ADR-008 database schema for variants.
Sprint 9: Enhanced with reading_support table for multi-pack aggregation.
"""

from __future__ import annotations

import sqlite3

from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessType,
    WitnessSupportType,
    WitnessSupport,
    VariantClassification,
    SignificanceLevel,
)


# Schema extension for variants (extends schema_v2)
VARIANT_SCHEMA_SQL = """
-- Minimal sources table if not present (needed for FK constraints)
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    version TEXT,
    license TEXT,
    url TEXT,
    retrieved_at TEXT,
    sha256 TEXT,
    git_commit TEXT,
    git_tag TEXT,
    notes TEXT
);

-- variant_units: Points of textual variation
CREATE TABLE IF NOT EXISTS variant_units (
    id INTEGER PRIMARY KEY,
    ref TEXT NOT NULL,
    position INTEGER NOT NULL,
    classification TEXT NOT NULL,
    significance TEXT NOT NULL,
    sblgnt_reading_index INTEGER DEFAULT 0,
    source_id INTEGER REFERENCES sources(id),
    notes TEXT,
    -- Sprint 7: Reason classification (B4)
    reason_code TEXT DEFAULT '',
    reason_summary TEXT DEFAULT '',
    reason_detail TEXT,
    UNIQUE(ref, position)
);

-- witness_readings: Individual readings with witness support
CREATE TABLE IF NOT EXISTS witness_readings (
    id INTEGER PRIMARY KEY,
    variant_unit_id INTEGER NOT NULL REFERENCES variant_units(id) ON DELETE CASCADE,
    reading_index INTEGER NOT NULL,
    surface_text TEXT NOT NULL,
    normalized_text TEXT,
    notes TEXT,
    source_id INTEGER REFERENCES sources(id),
    source_pack_id TEXT,  -- Sprint 8: Pack provenance tracking
    UNIQUE(variant_unit_id, reading_index)
);

-- reading_witnesses: Witnesses supporting each reading (legacy, retained for backward compat)
CREATE TABLE IF NOT EXISTS reading_witnesses (
    id INTEGER PRIMARY KEY,
    reading_id INTEGER NOT NULL REFERENCES witness_readings(id) ON DELETE CASCADE,
    witness_siglum TEXT NOT NULL,
    witness_type TEXT NOT NULL,
    century_earliest INTEGER,
    century_latest INTEGER,
    source_id INTEGER REFERENCES sources(id),
    UNIQUE(reading_id, witness_siglum)
);

-- Sprint 9: reading_support - structured witness support with provenance (B1)
CREATE TABLE IF NOT EXISTS reading_support (
    id INTEGER PRIMARY KEY,
    reading_id INTEGER NOT NULL REFERENCES witness_readings(id) ON DELETE CASCADE,
    witness_siglum TEXT NOT NULL,
    witness_type TEXT NOT NULL,  -- 'edition', 'manuscript', 'tradition', 'other'
    century_earliest INTEGER,
    century_latest INTEGER,
    source_pack_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    -- Dedupe: same witness can't support same reading twice from same pack
    UNIQUE(reading_id, witness_siglum, source_pack_id)
);

-- Indexes for variant queries
CREATE INDEX IF NOT EXISTS idx_variant_units_ref ON variant_units(ref);
CREATE INDEX IF NOT EXISTS idx_variant_units_significance ON variant_units(significance);
CREATE INDEX IF NOT EXISTS idx_witness_readings_unit ON witness_readings(variant_unit_id);
CREATE INDEX IF NOT EXISTS idx_reading_witnesses_reading ON reading_witnesses(reading_id);
CREATE INDEX IF NOT EXISTS idx_reading_support_reading ON reading_support(reading_id);
CREATE INDEX IF NOT EXISTS idx_reading_support_siglum ON reading_support(witness_siglum);
CREATE INDEX IF NOT EXISTS idx_reading_support_type ON reading_support(witness_type);
"""


class VariantStore:
    """Database storage for textual variants.

    Provides CRUD operations for variant units and their readings,
    with provenance tracking via source_id foreign keys.

    Usage:
        store = VariantStore(connection)
        store.init_schema()
        store.save_variant(variant_unit)
        variants = store.get_variants_for_verse("John.1.18")
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize store with database connection.

        Args:
            conn: SQLite connection

        Note:
            Enables foreign key enforcement. SQLite requires this pragma
            per-connection for ON DELETE CASCADE to function.
        """
        self._conn = conn
        # Enable FK enforcement so ON DELETE CASCADE works
        self._conn.execute("PRAGMA foreign_keys = ON")

    def init_schema(self) -> None:
        """Initialize variant tables."""
        self._conn.executescript(VARIANT_SCHEMA_SQL)
        self._conn.commit()

    def save_variant(self, variant: VariantUnit, source_id: int | None = None) -> int:
        """Save a variant unit with its readings.

        Args:
            variant: The variant unit to save
            source_id: Optional source ID for provenance

        Returns:
            The variant unit ID
        """
        cursor = self._conn.execute(
            """
            INSERT INTO variant_units (ref, position, classification, significance,
                                       sblgnt_reading_index, source_id, notes,
                                       reason_code, reason_summary, reason_detail)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ref, position) DO UPDATE SET
                classification = excluded.classification,
                significance = excluded.significance,
                sblgnt_reading_index = excluded.sblgnt_reading_index,
                source_id = excluded.source_id,
                notes = excluded.notes,
                reason_code = excluded.reason_code,
                reason_summary = excluded.reason_summary,
                reason_detail = excluded.reason_detail
            RETURNING id
            """,
            (
                variant.ref,
                variant.position,
                variant.classification.value,
                variant.significance.value,
                variant.sblgnt_reading_index,
                source_id or variant.source_id,
                variant.notes,
                variant.reason_code,
                variant.reason_summary,
                variant.reason_detail,
            ),
        )
        unit_id = cursor.fetchone()[0]

        # Delete existing readings (cascade will remove witnesses via FK)
        # Manual delete ensures clean slate even if cascade isn't honored
        self._conn.execute(
            """
            DELETE FROM reading_witnesses
            WHERE reading_id IN (
                SELECT id FROM witness_readings WHERE variant_unit_id = ?
            )
            """,
            (unit_id,),
        )
        # Then delete readings
        self._conn.execute(
            "DELETE FROM witness_readings WHERE variant_unit_id = ?", (unit_id,)
        )

        # Insert readings
        for idx, reading in enumerate(variant.readings):
            self._save_reading(unit_id, idx, reading, source_id)

        self._conn.commit()
        return unit_id

    def _save_reading(
        self,
        unit_id: int,
        index: int,
        reading: WitnessReading,
        source_id: int | None,
    ) -> int:
        """Save a witness reading."""
        cursor = self._conn.execute(
            """
            INSERT INTO witness_readings (variant_unit_id, reading_index, surface_text,
                                         normalized_text, notes, source_id, source_pack_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """,
            (
                unit_id,
                index,
                reading.surface_text,
                reading.normalized_text,
                reading.notes,
                source_id,
                reading.source_pack_id,
            ),
        )
        reading_id = cursor.fetchone()[0]

        # Insert witnesses (deduplicate by siglum to avoid UNIQUE violations) - legacy
        seen_sigla: set[str] = set()
        for witness, wtype in zip(reading.witnesses, reading.witness_types):
            if witness in seen_sigla:
                continue  # Skip duplicate witness sigla
            seen_sigla.add(witness)

            self._conn.execute(
                """
                INSERT INTO reading_witnesses (reading_id, witness_siglum, witness_type,
                                              century_earliest, century_latest, source_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    reading_id,
                    witness,
                    wtype.value,
                    reading.date_range[0] if reading.date_range else None,
                    reading.date_range[1] if reading.date_range else None,
                    source_id,
                ),
            )

        # Sprint 9: Insert support_set entries (B1)
        for support in reading.support_set:
            self._save_support(reading_id, support)

        return reading_id

    def _save_support(self, reading_id: int, support: WitnessSupport) -> None:
        """Save a witness support entry (Sprint 9: B1).

        Uses INSERT OR IGNORE to handle duplicates idempotently.
        """
        self._conn.execute(
            """
            INSERT OR IGNORE INTO reading_support (
                reading_id, witness_siglum, witness_type,
                century_earliest, century_latest, source_pack_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                reading_id,
                support.witness_siglum,
                support.witness_type.value,
                support.century_range[0] if support.century_range else None,
                support.century_range[1] if support.century_range else None,
                support.source_pack_id,
            ),
        )

    def add_support_to_reading(self, reading_id: int, support: WitnessSupport) -> bool:
        """Add a support entry to an existing reading (Sprint 9: B2).

        Returns True if support was added, False if already exists.
        Used for idempotent multi-pack aggregation.
        """
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO reading_support (
                reading_id, witness_siglum, witness_type,
                century_earliest, century_latest, source_pack_id
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                reading_id,
                support.witness_siglum,
                support.witness_type.value,
                support.century_range[0] if support.century_range else None,
                support.century_range[1] if support.century_range else None,
                support.source_pack_id,
            ),
        )
        return cursor.rowcount > 0

    def get_variant(self, ref: str, position: int) -> VariantUnit | None:
        """Get a variant unit by reference and position.

        Args:
            ref: Scripture reference (e.g., "John.1.18")
            position: Word position in verse

        Returns:
            VariantUnit or None if not found
        """
        cursor = self._conn.execute(
            """
            SELECT id, ref, position, classification, significance,
                   sblgnt_reading_index, source_id, notes,
                   reason_code, reason_summary, reason_detail
            FROM variant_units
            WHERE ref = ? AND position = ?
            """,
            (ref, position),
        )
        row = cursor.fetchone()
        if not row:
            return None

        return self._load_variant_from_row(row)

    def get_variants_for_verse(self, ref: str) -> list[VariantUnit]:
        """Get all variants in a verse.

        Args:
            ref: Scripture reference (e.g., "John.1.18")

        Returns:
            List of VariantUnit objects
        """
        cursor = self._conn.execute(
            """
            SELECT id, ref, position, classification, significance,
                   sblgnt_reading_index, source_id, notes,
                   reason_code, reason_summary, reason_detail
            FROM variant_units
            WHERE ref = ?
            ORDER BY position
            """,
            (ref,),
        )

        return [self._load_variant_from_row(row) for row in cursor]

    def get_significant_variants(
        self, book: str | None = None, chapter: int | None = None
    ) -> list[VariantUnit]:
        """Get all significant/major variants.

        Args:
            book: Optional book filter
            chapter: Optional chapter filter (requires book)

        Returns:
            List of significant VariantUnit objects
        """
        query = """
            SELECT id, ref, position, classification, significance,
                   sblgnt_reading_index, source_id, notes,
                   reason_code, reason_summary, reason_detail
            FROM variant_units
            WHERE significance IN ('significant', 'major')
        """
        params: list = []

        if book:
            query += " AND ref LIKE ?"
            if chapter:
                params.append(f"{book}.{chapter}.%")
            else:
                params.append(f"{book}.%")

        query += " ORDER BY ref, position"

        cursor = self._conn.execute(query, params)
        return [self._load_variant_from_row(row) for row in cursor]

    def _load_variant_from_row(self, row) -> VariantUnit:
        """Load a VariantUnit from a database row."""
        (
            unit_id,
            ref,
            position,
            classification,
            significance,
            sblgnt_idx,
            source_id,
            notes,
            reason_code,
            reason_summary,
            reason_detail,
        ) = row

        # Load readings
        readings = self._load_readings(unit_id)

        return VariantUnit(
            ref=ref,
            position=position,
            readings=readings,
            sblgnt_reading_index=sblgnt_idx,
            classification=VariantClassification(classification),
            significance=SignificanceLevel(significance),
            notes=notes or "",
            source_id=source_id,
            reason_code=reason_code or "",
            reason_summary=reason_summary or "",
            reason_detail=reason_detail,
        )

    def _load_readings(self, unit_id: int) -> list[WitnessReading]:
        """Load all readings for a variant unit."""
        cursor = self._conn.execute(
            """
            SELECT id, reading_index, surface_text, normalized_text, notes, source_pack_id
            FROM witness_readings
            WHERE variant_unit_id = ?
            ORDER BY reading_index
            """,
            (unit_id,),
        )

        readings = []
        for row in cursor:
            reading_id, idx, surface, normalized, notes, source_pack_id = row
            witnesses, types, date_range = self._load_witnesses(reading_id)
            # Sprint 9: Load support_set
            support_set = self._load_support_set(reading_id)
            readings.append(
                WitnessReading(
                    surface_text=surface,
                    witnesses=witnesses,
                    witness_types=types,
                    date_range=date_range,
                    normalized_text=normalized,
                    notes=notes or "",
                    source_pack_id=source_pack_id,
                    support_set=support_set,
                )
            )

        return readings

    def _load_support_set(self, reading_id: int) -> list[WitnessSupport]:
        """Load support set entries for a reading (Sprint 9: B1)."""
        cursor = self._conn.execute(
            """
            SELECT witness_siglum, witness_type, century_earliest, century_latest, source_pack_id
            FROM reading_support
            WHERE reading_id = ?
            ORDER BY witness_siglum
            """,
            (reading_id,),
        )

        support_set = []
        for row in cursor:
            siglum, wtype, cent_early, cent_late, pack_id = row
            century_range = None
            if cent_early is not None and cent_late is not None:
                century_range = (cent_early, cent_late)
            elif cent_early is not None:
                century_range = (cent_early, cent_early)

            support_set.append(
                WitnessSupport(
                    witness_siglum=siglum,
                    witness_type=WitnessSupportType(wtype),
                    source_pack_id=pack_id,
                    century_range=century_range,
                )
            )

        return support_set

    def _load_witnesses(
        self, reading_id: int
    ) -> tuple[list[str], list[WitnessType], tuple[int, int] | None]:
        """Load witnesses for a reading."""
        cursor = self._conn.execute(
            """
            SELECT witness_siglum, witness_type, century_earliest, century_latest
            FROM reading_witnesses
            WHERE reading_id = ?
            ORDER BY century_earliest, witness_siglum
            """,
            (reading_id,),
        )

        witnesses = []
        types = []
        earliest = None
        latest = None

        for row in cursor:
            siglum, wtype, cent_early, cent_late = row
            witnesses.append(siglum)
            types.append(WitnessType(wtype))
            if cent_early:
                earliest = min(earliest, cent_early) if earliest else cent_early
            if cent_late:
                latest = max(latest, cent_late) if latest else cent_late

        date_range = (earliest, latest) if earliest and latest else None
        return witnesses, types, date_range

    def has_variant(self, ref: str, position: int) -> bool:
        """Check if a variant exists at a position.

        Args:
            ref: Scripture reference
            position: Word position

        Returns:
            True if variant exists
        """
        cursor = self._conn.execute(
            "SELECT 1 FROM variant_units WHERE ref = ? AND position = ?",
            (ref, position),
        )
        return cursor.fetchone() is not None

    def has_significant_variant(self, ref: str) -> bool:
        """Check if verse has any significant variants.

        Args:
            ref: Scripture reference

        Returns:
            True if significant variant exists
        """
        cursor = self._conn.execute(
            """
            SELECT 1 FROM variant_units
            WHERE ref = ? AND significance IN ('significant', 'major')
            """,
            (ref,),
        )
        return cursor.fetchone() is not None

    def delete_variant(self, ref: str, position: int) -> bool:
        """Delete a variant unit.

        Args:
            ref: Scripture reference
            position: Word position

        Returns:
            True if deleted, False if not found
        """
        cursor = self._conn.execute(
            "DELETE FROM variant_units WHERE ref = ? AND position = ?",
            (ref, position),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def count_variants(self, significance: SignificanceLevel | None = None) -> int:
        """Count variant units.

        Args:
            significance: Optional filter by significance

        Returns:
            Count of variants
        """
        if significance:
            cursor = self._conn.execute(
                "SELECT COUNT(*) FROM variant_units WHERE significance = ?",
                (significance.value,),
            )
        else:
            cursor = self._conn.execute("SELECT COUNT(*) FROM variant_units")

        return cursor.fetchone()[0]

    # Sprint 9: Methods for multi-pack aggregation (B2)

    def get_reading_id_by_normalized(
        self, variant_ref: str, position: int, normalized_text: str
    ) -> int | None:
        """Get reading ID by normalized text for merging (Sprint 9: B2).

        Used during multi-pack aggregation to find existing readings
        that match the normalized form.
        """
        cursor = self._conn.execute(
            """
            SELECT wr.id
            FROM witness_readings wr
            JOIN variant_units vu ON wr.variant_unit_id = vu.id
            WHERE vu.ref = ? AND vu.position = ? AND wr.normalized_text = ?
            """,
            (variant_ref, position, normalized_text),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def get_variant_id(self, ref: str, position: int) -> int | None:
        """Get variant unit ID by reference and position (Sprint 9: B2)."""
        cursor = self._conn.execute(
            "SELECT id FROM variant_units WHERE ref = ? AND position = ?",
            (ref, position),
        )
        row = cursor.fetchone()
        return row[0] if row else None

    def add_reading_to_variant(
        self,
        variant_id: int,
        reading: WitnessReading,
        source_id: int | None = None,
    ) -> int:
        """Add a new reading to an existing variant (Sprint 9: B2).

        Used during multi-pack aggregation when a new reading text is found.
        """
        # Get next reading index
        cursor = self._conn.execute(
            """
            SELECT COALESCE(MAX(reading_index), -1) + 1
            FROM witness_readings
            WHERE variant_unit_id = ?
            """,
            (variant_id,),
        )
        next_index = cursor.fetchone()[0]

        return self._save_reading(variant_id, next_index, reading, source_id)

    def count_support_entries(self, reading_id: int) -> int:
        """Count support entries for a reading (Sprint 9: B2)."""
        cursor = self._conn.execute(
            "SELECT COUNT(*) FROM reading_support WHERE reading_id = ?",
            (reading_id,),
        )
        return cursor.fetchone()[0]
