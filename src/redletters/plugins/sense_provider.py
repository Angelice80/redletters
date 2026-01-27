"""Sense provider plugin implementations."""

from redletters.plugins.base import TokenContext
from redletters.engine.senses import LexemeSense


class DatabaseSenseProvider:
    """Default sense provider using the SQLite database."""

    def __init__(self, conn):
        self.conn = conn
        self._source_name = "redletters-db"

    def get_senses(self, lemma: str) -> list[LexemeSense]:
        """Return all senses from the database."""
        cursor = self.conn.execute(
            """
            SELECT lemma, sense_id, gloss, definition, source, weight, domain
            FROM lexeme_senses
            WHERE lemma = ?
            ORDER BY weight DESC
            """,
            (lemma,),
        )

        return [
            LexemeSense(
                lemma=row["lemma"],
                sense_id=row["sense_id"],
                gloss=row["gloss"],
                definition=row["definition"],
                source=row["source"],
                weight=row["weight"],
                domain=row["domain"],
            )
            for row in cursor
        ]

    def get_sense_weight(
        self, lemma: str, sense_id: str, context: TokenContext
    ) -> float:
        """Get base weight (no contextual adjustment in default provider)."""
        cursor = self.conn.execute(
            "SELECT weight FROM lexeme_senses WHERE lemma = ? AND sense_id = ?",
            (lemma, sense_id),
        )
        row = cursor.fetchone()
        return row["weight"] if row else 0.5

    @property
    def source_name(self) -> str:
        return self._source_name


class CompositeSenseProvider:
    """Combine multiple sense providers with priority ordering."""

    def __init__(self, providers: list):
        self.providers = providers

    def get_senses(self, lemma: str) -> list[LexemeSense]:
        """Get senses from all providers, deduplicated by sense_id."""
        seen_ids = set()
        all_senses = []

        for provider in self.providers:
            for sense in provider.get_senses(lemma):
                if sense.sense_id not in seen_ids:
                    seen_ids.add(sense.sense_id)
                    all_senses.append(sense)

        # Sort by weight
        all_senses.sort(key=lambda s: -s.weight)
        return all_senses

    def get_sense_weight(
        self, lemma: str, sense_id: str, context: TokenContext
    ) -> float:
        """Get highest weight from any provider."""
        weights = []
        for provider in self.providers:
            w = provider.get_sense_weight(lemma, sense_id, context)
            if w > 0:
                weights.append(w)
        return max(weights) if weights else 0.5

    @property
    def source_name(self) -> str:
        return "composite:" + "+".join(p.source_name for p in self.providers)
