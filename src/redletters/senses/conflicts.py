"""Cross-pack sense conflict detection for v0.7.0.

Finds all matching senses for a lemma across installed packs,
showing where packs agree or disagree on glosses/senses.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from redletters.senses import SENSES_SCHEMA_VERSION, normalize_lemma
from redletters.sources.sense_db import InstalledSensePack, SensePackDB


@dataclass
class SenseConflictEntry:
    """A sense entry from a specific pack."""

    pack_id: str
    """Pack identifier."""

    pack_version: str
    """Pack version."""

    sense_id: str
    """Sense identifier within pack."""

    gloss: str
    """English gloss."""

    definition: str
    """Fuller definition (may be empty)."""

    domain: str
    """Semantic domain (may be empty)."""

    weight: float
    """Sense weight (0.0-1.0)."""

    # Citation fields
    source_id: str
    """Citation key."""

    source_title: str
    """Full bibliographic title."""

    edition: str = ""
    """Edition string."""

    publisher: str = ""
    """Publisher name."""

    year: int | None = None
    """Publication year."""

    license: str = ""
    """License identifier."""

    license_url: str = ""
    """License URL."""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result = {
            "pack_id": self.pack_id,
            "pack_version": self.pack_version,
            "pack_ref": f"{self.pack_id}@{self.pack_version}",
            "sense_id": self.sense_id,
            "gloss": self.gloss,
            "definition": self.definition,
            "domain": self.domain,
            "weight": self.weight,
            "source_id": self.source_id,
            "source_title": self.source_title,
        }
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license:
            result["license"] = self.license
        if self.license_url:
            result["license_url"] = self.license_url
        return result

    def citation_string(self) -> str:
        """Format as citation string."""
        parts = [f"{self.pack_id}@{self.pack_version}"]
        details = [self.source_id]
        if self.source_title:
            details.append(self.source_title)
        parts.append(f"({', '.join(details)})")
        if self.license:
            parts.append(f"[{self.license}]")
        return " ".join(parts)


@dataclass
class ConflictsResult:
    """Result of cross-pack conflict detection."""

    lemma_input: str
    """Original lemma as provided."""

    lemma_normalized: str
    """Normalized lemma used for lookup."""

    packs_checked: list[str]
    """Pack IDs checked in precedence order."""

    entries: list[SenseConflictEntry]
    """All sense entries across all packs."""

    unique_glosses: list[str]
    """Deduplicated list of unique glosses found."""

    packs_with_matches: list[str]
    """Pack IDs that have this lemma."""

    has_conflict: bool
    """True if different packs have different primary glosses."""

    conflict_summary: str
    """Human-readable conflict summary."""

    schema_version: str = SENSES_SCHEMA_VERSION
    """Schema version."""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "lemma_input": self.lemma_input,
            "lemma_normalized": self.lemma_normalized,
            "packs_checked": self.packs_checked,
            "packs_checked_count": len(self.packs_checked),
            "entries": [e.to_dict() for e in self.entries],
            "entries_count": len(self.entries),
            "unique_glosses": self.unique_glosses,
            "packs_with_matches": self.packs_with_matches,
            "has_conflict": self.has_conflict,
            "conflict_summary": self.conflict_summary,
            "schema_version": self.schema_version,
        }


class SenseConflictDetector:
    """Detects sense conflicts across installed packs.

    Shows all matching senses for a lemma, highlighting where
    packs agree or disagree.

    Usage:
        detector = SenseConflictDetector(conn)
        result = detector.detect("λόγος")
        for entry in result.entries:
            print(f"{entry.pack_id}: {entry.gloss}")
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize detector.

        Args:
            conn: Database connection
        """
        self._conn = conn
        self._db = SensePackDB(conn)
        self._db.ensure_schema()

    def detect(self, lemma: str) -> ConflictsResult:
        """Detect sense conflicts for a lemma across all installed packs.

        Args:
            lemma: Greek lemma (with or without diacriticals)

        Returns:
            ConflictsResult with all matches and conflict analysis
        """
        # Normalize the lemma
        normalized = normalize_lemma(lemma)

        # Get all installed packs in precedence order
        packs = self._db.get_all_installed_packs()
        pack_ids = [p.pack_id for p in packs]

        # Build pack lookup for metadata
        pack_lookup: dict[str, InstalledSensePack] = {p.pack_id: p for p in packs}

        # Collect all entries
        entries: list[SenseConflictEntry] = []
        packs_with_matches: list[str] = []
        primary_glosses: dict[str, str] = {}  # pack_id -> primary gloss

        for pack_id in pack_ids:
            # Query senses for this lemma from this pack
            cursor = self._conn.execute(
                """
                SELECT ps.sense_id, ps.gloss, ps.definition, ps.domain, ps.weight
                FROM pack_senses ps
                WHERE ps.pack_id = ? AND (ps.lemma = ? OR ps.lemma = ?)
                ORDER BY ps.weight DESC
                """,
                (pack_id, normalized, lemma),
            )

            pack_entries = []
            for row in cursor:
                pack = pack_lookup.get(pack_id)
                if not pack:
                    continue

                entry = SenseConflictEntry(
                    pack_id=pack_id,
                    pack_version=pack.version,
                    sense_id=row[0],
                    gloss=row[1],
                    definition=row[2] or "",
                    domain=row[3] or "",
                    weight=row[4],
                    source_id=pack.source_id,
                    source_title=pack.source_title,
                    edition=pack.edition,
                    publisher=pack.publisher,
                    year=pack.year,
                    license=pack.license,
                    license_url=pack.license_url,
                )
                pack_entries.append(entry)
                entries.append(entry)

            if pack_entries:
                packs_with_matches.append(pack_id)
                # Track primary gloss (highest weight)
                primary_glosses[pack_id] = pack_entries[0].gloss

        # Analyze for conflicts
        unique_glosses = list(dict.fromkeys(e.gloss for e in entries))
        unique_primary_glosses = set(primary_glosses.values())
        has_conflict = len(unique_primary_glosses) > 1

        # Generate conflict summary
        if not entries:
            conflict_summary = f"No matches found for '{lemma}'"
        elif not has_conflict:
            if len(packs_with_matches) == 1:
                conflict_summary = (
                    f"Found in 1 pack ({packs_with_matches[0]}): {unique_glosses[0]}"
                )
            else:
                conflict_summary = (
                    f"Agreement across {len(packs_with_matches)} packs: "
                    f"'{unique_glosses[0]}'"
                )
        else:
            gloss_sources = []
            for pack_id, gloss in primary_glosses.items():
                gloss_sources.append(f"{pack_id}='{gloss}'")
            conflict_summary = (
                f"CONFLICT: {len(unique_primary_glosses)} different primary glosses "
                f"across {len(packs_with_matches)} packs: {', '.join(gloss_sources)}"
            )

        return ConflictsResult(
            lemma_input=lemma,
            lemma_normalized=normalized,
            packs_checked=pack_ids,
            entries=entries,
            unique_glosses=unique_glosses,
            packs_with_matches=packs_with_matches,
            has_conflict=has_conflict,
            conflict_summary=conflict_summary,
        )

    def list_packs(self) -> list[dict]:
        """List installed sense packs in precedence order.

        Returns:
            List of pack info dicts
        """
        packs = self._db.get_all_installed_packs()
        return [
            {
                "pack_id": p.pack_id,
                "version": p.version,
                "priority": p.priority,
                "source_id": p.source_id,
                "source_title": p.source_title,
                "license": p.license,
                "sense_count": p.sense_count,
            }
            for p in packs
        ]
