"""Sense resolution explainer for v0.7.0.

Shows deterministic audit trail for sense selection:
- Which packs were consulted (in order)
- What matched in each pack
- What was chosen and why
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from redletters.senses import SENSES_SCHEMA_VERSION, normalize_lemma
from redletters.sources.sense_db import InstalledSensePack, SensePackDB


@dataclass
class PackMatch:
    """A match from a single sense pack."""

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
        parts = [self.source_id]
        details = []
        if self.source_title:
            details.append(self.source_title)
        if self.edition:
            details.append(f"{self.edition} ed.")
        if self.publisher:
            details.append(self.publisher)
        if self.year:
            details.append(str(self.year))
        if details:
            parts.append(f"({', '.join(details)})")
        if self.license:
            parts.append(f"[{self.license}]")
        return " ".join(parts)


@dataclass
class ExplainResult:
    """Result of sense resolution explanation."""

    lemma_input: str
    """Original lemma as provided."""

    lemma_normalized: str
    """Normalized lemma used for lookup."""

    packs_consulted: list[str]
    """Pack IDs consulted in precedence order."""

    matches: list[PackMatch]
    """All matches found across packs (in order found)."""

    chosen: PackMatch | None
    """The sense that would be selected (first match by precedence)."""

    reason: str
    """Why this sense was chosen."""

    schema_version: str = SENSES_SCHEMA_VERSION
    """Schema version."""

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "lemma_input": self.lemma_input,
            "lemma_normalized": self.lemma_normalized,
            "packs_consulted": self.packs_consulted,
            "packs_consulted_count": len(self.packs_consulted),
            "matches": [m.to_dict() for m in self.matches],
            "matches_count": len(self.matches),
            "chosen": self.chosen.to_dict() if self.chosen else None,
            "reason": self.reason,
            "schema_version": self.schema_version,
        }

    @property
    def has_matches(self) -> bool:
        """True if any matches were found."""
        return len(self.matches) > 0


class SenseExplainer:
    """Explains sense resolution for a lemma.

    Shows deterministic audit trail:
    - Packs consulted in precedence order
    - All matches found
    - Which sense would be chosen and why

    Usage:
        explainer = SenseExplainer(conn)
        result = explainer.explain("μετανοέω")
        print(result.chosen.gloss)  # "repent"
    """

    def __init__(self, conn: sqlite3.Connection):
        """Initialize explainer.

        Args:
            conn: Database connection
        """
        self._conn = conn
        self._db = SensePackDB(conn)
        self._db.ensure_schema()

    def explain(self, lemma: str) -> ExplainResult:
        """Explain sense resolution for a lemma.

        Args:
            lemma: Greek lemma (with or without diacriticals)

        Returns:
            ExplainResult with full audit trail
        """
        # Normalize the lemma
        normalized = normalize_lemma(lemma)

        # Get all installed packs in precedence order
        packs = self._db.get_all_installed_packs()
        pack_ids = [p.pack_id for p in packs]

        # Build pack lookup for metadata
        pack_lookup: dict[str, InstalledSensePack] = {p.pack_id: p for p in packs}

        # Collect all matches
        matches: list[PackMatch] = []
        chosen: PackMatch | None = None

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

            for row in cursor:
                pack = pack_lookup.get(pack_id)
                if not pack:
                    continue

                match = PackMatch(
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
                matches.append(match)

                # First match by precedence is the chosen one
                if chosen is None:
                    chosen = match

        # Determine reason
        if chosen is None:
            reason = f"No matches found for '{lemma}' in any installed sense pack"
        elif len(matches) == 1:
            reason = f"Single match from {chosen.pack_id} (only pack with this lemma)"
        else:
            pack_with_matches = list(dict.fromkeys(m.pack_id for m in matches))
            if len(pack_with_matches) == 1:
                reason = (
                    f"Selected highest-weight sense from {chosen.pack_id} "
                    f"(weight={chosen.weight:.2f})"
                )
            else:
                reason = (
                    f"Selected from {chosen.pack_id} by precedence order "
                    f"(priority over {', '.join(pack_with_matches[1:])})"
                )

        return ExplainResult(
            lemma_input=lemma,
            lemma_normalized=normalized,
            packs_consulted=pack_ids,
            matches=matches,
            chosen=chosen,
            reason=reason,
        )

    def get_installed_packs(self) -> list[dict]:
        """Get list of installed sense packs for reference.

        Returns:
            List of pack info dicts
        """
        return self._db.get_pack_status()
