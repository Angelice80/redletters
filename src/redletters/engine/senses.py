"""Lexeme sense lookup and disambiguation."""

import math
import sqlite3
import unicodedata
from dataclasses import dataclass


def _normalize_lemma(lemma: str) -> str:
    """Normalize lemma to NFC form for consistent lookups."""
    return unicodedata.normalize("NFC", lemma)


@dataclass
class LexemeSense:
    """A single sense/meaning for a lemma."""

    lemma: str
    sense_id: str
    gloss: str
    definition: str | None
    source: str
    weight: float
    domain: str | None

    def to_dict(self) -> dict:
        return {
            "lemma": self.lemma,
            "sense_id": self.sense_id,
            "gloss": self.gloss,
            "definition": self.definition,
            "source": self.source,
            "weight": self.weight,
            "domain": self.domain,
        }


class SenseLookup:
    """Handles lexeme sense retrieval and contextual weighting."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._cache: dict[str, list[LexemeSense]] = {}

    def get_senses(self, lemma: str) -> list[LexemeSense]:
        """
        Get all senses for a lemma, ordered by default weight.

        Args:
            lemma: Greek lemma (dictionary form)

        Returns:
            List of LexemeSense objects
        """
        # Normalize lemma to NFC for consistent lookups
        lemma = _normalize_lemma(lemma)

        if lemma in self._cache:
            return self._cache[lemma]

        cursor = self.conn.execute(
            """
            SELECT lemma, sense_id, gloss, definition, source, weight, domain
            FROM lexeme_senses
            WHERE lemma = ?
            ORDER BY weight DESC
            """,
            (lemma,),
        )

        senses = []
        for row in cursor:
            senses.append(
                LexemeSense(
                    lemma=row["lemma"],
                    sense_id=row["sense_id"],
                    gloss=row["gloss"],
                    definition=row["definition"],
                    source=row["source"],
                    weight=row["weight"],
                    domain=row["domain"],
                )
            )

        # If no senses found, create a fallback
        if not senses:
            senses.append(
                LexemeSense(
                    lemma=lemma,
                    sense_id=f"{lemma}.unknown",
                    gloss=f"[{lemma}]",
                    definition="No lexical entry found",
                    source="fallback",
                    weight=0.1,
                    domain=None,
                )
            )

        self._cache[lemma] = senses
        return senses

    def get_primary_sense(self, lemma: str) -> LexemeSense | None:
        """Get the highest-weighted sense for a lemma."""
        senses = self.get_senses(lemma)
        return senses[0] if senses else None

    def get_senses_by_domain(self, lemma: str, domain: str) -> list[LexemeSense]:
        """Get senses filtered by semantic domain."""
        return [s for s in self.get_senses(lemma) if s.domain == domain]

    def get_contextual_weight(
        self,
        sense: LexemeSense,
        adjacent_lemmas: list[str],
        collocation_data: dict[tuple[str, str], int],
    ) -> float:
        """
        Calculate contextual weight for a sense given surrounding lemmas.

        Boosts weight if the sense's lemma frequently collocates with neighbors.

        Args:
            sense: The sense to evaluate
            adjacent_lemmas: Lemmas appearing near this token
            collocation_data: Dict mapping (lemma1, lemma2) to frequency

        Returns:
            Adjusted weight (base weight * collocation bonus)
        """
        base_weight = sense.weight
        collocation_bonus = 0.0

        for adj_lemma in adjacent_lemmas:
            # Check both orderings
            freq1 = collocation_data.get((sense.lemma, adj_lemma), 0)
            freq2 = collocation_data.get((adj_lemma, sense.lemma), 0)
            freq = max(freq1, freq2)

            if freq > 0:
                # Log-scaled bonus to prevent runaway values
                collocation_bonus += math.log1p(freq) * 0.05

        return base_weight * (1 + collocation_bonus)


def load_collocations(conn: sqlite3.Connection) -> dict[tuple[str, str], int]:
    """Load all collocations into a lookup dict."""
    cursor = conn.execute("SELECT lemma1, lemma2, frequency FROM collocations")
    return {(row["lemma1"], row["lemma2"]): row["frequency"] for row in cursor}
