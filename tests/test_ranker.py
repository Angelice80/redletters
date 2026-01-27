"""Tests for rendering ranking."""

import pytest
import sqlite3
from redletters.engine.generator import CandidateGenerator
from redletters.engine.ranker import RenderingRanker
from redletters.db.connection import init_db
from redletters.ingest.loader import load_demo_data


@pytest.fixture
def test_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    load_demo_data(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_tokens(test_db):
    cursor = test_db.execute(
        """
        SELECT id, book, chapter, verse, position, surface, lemma, morph, is_red_letter
        FROM tokens
        WHERE book = 'Matthew' AND chapter = 3 AND verse = 2
        ORDER BY position
        """
    )
    return [dict(row) for row in cursor]


class TestRenderingRanker:
    """Tests for RenderingRanker."""

    def test_returns_sorted_by_score(self, test_db, sample_tokens):
        """Results should be sorted by score descending."""
        gen = CandidateGenerator(test_db)
        ranker = RenderingRanker(test_db)

        candidates = gen.generate_all(sample_tokens)
        ranked = ranker.rank(candidates, sample_tokens)

        scores = [r["score"] for r in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_includes_score_breakdown(self, test_db, sample_tokens):
        """Each result should have score breakdown."""
        gen = CandidateGenerator(test_db)
        ranker = RenderingRanker(test_db)

        candidates = gen.generate_all(sample_tokens)
        ranked = ranker.rank(candidates, sample_tokens)

        for r in ranked:
            assert "score_breakdown" in r
            breakdown = r["score_breakdown"]
            assert "morph_fit" in breakdown
            assert "sense_weight" in breakdown
            assert "weights_used" in breakdown

    def test_includes_receipts(self, test_db, sample_tokens):
        """Each result should have receipts."""
        gen = CandidateGenerator(test_db)
        ranker = RenderingRanker(test_db)

        candidates = gen.generate_all(sample_tokens)
        ranked = ranker.rank(candidates, sample_tokens)

        for r in ranked:
            assert "receipts" in r
            assert len(r["receipts"]) == len(sample_tokens)

    def test_receipts_completeness(self, test_db, sample_tokens):
        """Receipts should have all required fields."""
        gen = CandidateGenerator(test_db)
        ranker = RenderingRanker(test_db)

        candidates = gen.generate_all(sample_tokens)
        ranked = ranker.rank(candidates, sample_tokens)

        required_fields = [
            "surface",
            "lemma",
            "morph",
            "chosen_sense_id",
            "chosen_gloss",
            "sense_source",
            "rationale",
        ]

        for r in ranked:
            for receipt in r["receipts"]:
                for field in required_fields:
                    assert field in receipt, f"Missing field: {field}"

    def test_deterministic_ranking(self, test_db, sample_tokens):
        """Same input should produce same ranking."""
        gen = CandidateGenerator(test_db)
        ranker = RenderingRanker(test_db)

        candidates1 = gen.generate_all(sample_tokens)
        ranked1 = ranker.rank(candidates1, sample_tokens)

        candidates2 = gen.generate_all(sample_tokens)
        ranked2 = ranker.rank(candidates2, sample_tokens)

        for r1, r2 in zip(ranked1, ranked2):
            assert r1["style"] == r2["style"]
            assert r1["score"] == r2["score"]
            assert r1["text"] == r2["text"]
