"""Tests for candidate rendering generation."""

import pytest
import sqlite3
from redletters.engine.generator import CandidateGenerator, RenderingStyle
from redletters.db.connection import init_db
from redletters.ingest.loader import load_demo_data


@pytest.fixture
def test_db():
    """Create in-memory test database."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    load_demo_data(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_tokens(test_db):
    """Get sample tokens for Matthew 3:2."""
    cursor = test_db.execute(
        """
        SELECT id, book, chapter, verse, position, surface, lemma, morph, is_red_letter
        FROM tokens
        WHERE book = 'Matthew' AND chapter = 3 AND verse = 2
        ORDER BY position
        """
    )
    return [dict(row) for row in cursor]


class TestCandidateGenerator:
    """Tests for CandidateGenerator."""

    def test_generates_all_styles(self, test_db, sample_tokens):
        """Should generate one rendering per style."""
        gen = CandidateGenerator(test_db)
        candidates = gen.generate_all(sample_tokens)

        styles = {c.style for c in candidates}
        assert RenderingStyle.ULTRA_LITERAL in styles
        assert RenderingStyle.NATURAL in styles
        assert RenderingStyle.MEANING_FIRST in styles
        assert RenderingStyle.JEWISH_CONTEXT in styles

    def test_all_candidates_have_text(self, test_db, sample_tokens):
        """All candidates should have non-empty text."""
        gen = CandidateGenerator(test_db)
        candidates = gen.generate_all(sample_tokens)

        for c in candidates:
            assert c.text
            assert len(c.text) > 0

    def test_token_renderings_match_input(self, test_db, sample_tokens):
        """Each candidate should have one rendering per input token."""
        gen = CandidateGenerator(test_db)
        candidates = gen.generate_all(sample_tokens)

        for c in candidates:
            assert len(c.token_renderings) == len(sample_tokens)

    def test_renderings_have_senses(self, test_db, sample_tokens):
        """Each token rendering should have a chosen sense."""
        gen = CandidateGenerator(test_db)
        candidates = gen.generate_all(sample_tokens)

        for c in candidates:
            for tr in c.token_renderings:
                assert tr.chosen_sense is not None
                assert tr.chosen_sense.gloss

    def test_deterministic_output(self, test_db, sample_tokens):
        """Same input should produce same output."""
        gen = CandidateGenerator(test_db)

        result1 = gen.generate_all(sample_tokens)
        result2 = gen.generate_all(sample_tokens)

        for c1, c2 in zip(result1, result2):
            assert c1.text == c2.text
            assert c1.style == c2.style
