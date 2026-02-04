"""Sense pack-based lexicon provider for v0.6.0.

Provides glosses from installed sense packs with citation-grade provenance.
Deterministic: same installed packs = same results.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from redletters.lexicon.provider import GlossResult, normalize_greek
from redletters.sources.sense_db import SensePackDB


@dataclass
class CitationGlossResult(GlossResult):
    """Extended GlossResult with citation-grade provenance.

    Adds fields for scholarly citation beyond the basic GlossResult.
    """

    source_title: str = ""
    edition: str = ""
    publisher: str = ""
    year: int | None = None
    license_url: str = ""

    def to_dict(self) -> dict:
        """Serialize including citation fields."""
        result = super().to_dict()
        result["source_title"] = self.source_title
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license_url:
            result["license_url"] = self.license_url
        return result

    def citation_dict(self) -> dict:
        """Return just the citation-grade fields for receipts."""
        result = {
            "source_id": self.source,
        }
        if self.source_title:
            result["source_title"] = self.source_title
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license_url:
            result["license_url"] = self.license_url
        return result


class SensePackProvider:
    """Lexicon provider using installed sense packs.

    Provides glosses from installed sense packs with full citation provenance.
    Deterministic: queries packs in priority order.

    Usage:
        provider = SensePackProvider(conn)
        result = provider.lookup("λόγος")
        if result:
            print(result.gloss)  # "word"
            print(result.source)  # "LSJ" (citation key)
            print(result.source_title)  # "A Greek-English Lexicon"
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        pack_ids: list[str] | None = None,
    ):
        """Initialize provider.

        Args:
            conn: Database connection
            pack_ids: Optional list of pack IDs to use (in precedence order).
                     If None, uses all installed packs in priority order.
        """
        self._db = SensePackDB(conn)
        self._db.ensure_schema()
        self._pack_ids = pack_ids
        self._source_id = self._compute_source_id()

    def _compute_source_id(self) -> str:
        """Compute source_id based on installed packs."""
        if self._pack_ids:
            return f"sense_packs:{','.join(self._pack_ids)}"

        packs = self._db.get_all_installed_packs()
        if not packs:
            return "sense_packs:none"
        return f"sense_packs:{','.join(p.pack_id for p in packs)}"

    @property
    def source_id(self) -> str:
        """Unique identifier for provenance tracking."""
        return self._source_id

    @property
    def license_info(self) -> str:
        """Combined license information from all packs."""
        packs = self._db.get_all_installed_packs()
        if not packs:
            return "No sense packs installed"
        licenses = set(p.license for p in packs)
        return " | ".join(sorted(licenses))

    def lookup(self, key: str) -> CitationGlossResult | None:
        """Lookup gloss by lemma with citation provenance.

        Args:
            key: Greek lemma (with or without diacriticals)

        Returns:
            CitationGlossResult if found, None otherwise
        """
        # Normalize for lookup
        normalized = normalize_greek(key)
        lookup_key = normalized  # Track which key finds the sense

        # Try both normalized and original key
        sense = self._db.get_primary_gloss(normalized, self._pack_ids)
        if sense is None and normalized != key:
            sense = self._db.get_primary_gloss(key, self._pack_ids)
            lookup_key = key  # Original key worked

        if sense is None:
            return None

        # Get alternatives from same lemma using the key that worked
        all_senses = self._db.get_senses_for_lemma(lookup_key, self._pack_ids)
        alternatives = [s["gloss"] for s in all_senses if s["gloss"] != sense["gloss"]][
            :4
        ]

        return CitationGlossResult(
            gloss=sense["gloss"],
            source=sense["source_id"],
            confidence=min(sense.get("weight", 0.8), 1.0),
            alternatives=alternatives,
            source_title=sense.get("source_title", ""),
            edition=sense.get("edition", ""),
            publisher=sense.get("publisher", ""),
            year=sense.get("year"),
            license_url=sense.get("license_url", ""),
        )

    def lookup_all(self, key: str) -> list[CitationGlossResult]:
        """Lookup all senses for a lemma.

        Args:
            key: Greek lemma

        Returns:
            List of CitationGlossResult
        """
        # Try normalized first, fall back to original key
        normalized = normalize_greek(key)
        senses = self._db.get_senses_for_lemma(normalized, self._pack_ids)
        if not senses and normalized != key:
            senses = self._db.get_senses_for_lemma(key, self._pack_ids)

        results = []
        for sense in senses:
            # Get alternatives (other glosses for same lemma)
            alternatives = [s["gloss"] for s in senses if s["gloss"] != sense["gloss"]][
                :4
            ]

            results.append(
                CitationGlossResult(
                    gloss=sense["gloss"],
                    source=sense["source_id"],
                    confidence=min(sense.get("weight", 0.8), 1.0),
                    alternatives=alternatives,
                    source_title=sense.get("source_title", ""),
                    edition=sense.get("edition", ""),
                    publisher=sense.get("publisher", ""),
                    year=sense.get("year"),
                    license_url=sense.get("license_url", ""),
                )
            )

        return results

    def has_senses(self) -> bool:
        """Check if any sense packs are installed."""
        packs = self._db.get_all_installed_packs()
        return len(packs) > 0

    def get_installed_packs(self) -> list[dict]:
        """Get list of installed sense packs for provenance.

        Returns:
            List of pack info dicts
        """
        return self._db.get_pack_status()


class ChainedSenseProvider:
    """Chain multiple providers with fallback.

    Tries SensePackProvider first, falls back to BasicGlossProvider.
    """

    def __init__(
        self,
        conn: sqlite3.Connection | None = None,
        include_basic: bool = True,
    ):
        """Initialize chained provider.

        Args:
            conn: Database connection for sense packs
            include_basic: Whether to include BasicGlossProvider as fallback
        """
        self._providers = []

        # Add sense pack provider if connection provided
        if conn is not None:
            try:
                pack_provider = SensePackProvider(conn)
                if pack_provider.has_senses():
                    self._providers.append(pack_provider)
            except Exception:
                pass  # Sense pack DB not available

        # Add basic provider as fallback
        if include_basic:
            from redletters.lexicon.provider import BasicGlossProvider

            self._providers.append(BasicGlossProvider())

    @property
    def source_id(self) -> str:
        """Combined source ID."""
        if not self._providers:
            return "none"
        return "chained:" + ",".join(
            getattr(p, "source_id", "unknown") for p in self._providers
        )

    @property
    def license_info(self) -> str:
        """Combined license info."""
        if not self._providers:
            return "No providers"
        return " | ".join(
            getattr(p, "license_info", "unknown") for p in self._providers
        )

    def lookup(self, key: str) -> GlossResult | None:
        """Lookup gloss from first provider that has it.

        Args:
            key: Greek lemma

        Returns:
            GlossResult or None
        """
        for provider in self._providers:
            result = provider.lookup(key)
            if result is not None:
                return result
        return None

    def lookup_with_citation(self, key: str) -> CitationGlossResult | None:
        """Lookup with full citation info if available.

        Args:
            key: Greek lemma

        Returns:
            CitationGlossResult or None
        """
        for provider in self._providers:
            result = provider.lookup(key)
            if result is not None:
                if isinstance(result, CitationGlossResult):
                    return result
                # Convert basic result to citation result
                return CitationGlossResult(
                    gloss=result.gloss,
                    source=result.source,
                    confidence=result.confidence,
                    alternatives=result.alternatives,
                )
        return None


def get_sense_provider(
    conn: sqlite3.Connection | None = None,
) -> ChainedSenseProvider:
    """Get the default sense provider.

    Returns ChainedSenseProvider that tries:
    1. Installed sense packs (if any)
    2. BasicGlossProvider as fallback

    Args:
        conn: Optional database connection

    Returns:
        ChainedSenseProvider instance
    """
    return ChainedSenseProvider(conn=conn, include_basic=True)
