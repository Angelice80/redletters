"""Tests for confidence bucketing (v0.8.0).

Tests the bucket_confidence() function and integration with LayeredConfidence.
"""

from redletters.confidence import (
    bucket_confidence,
    CONFIDENCE_BUCKET_HIGH,
    CONFIDENCE_BUCKET_MEDIUM,
    LayeredConfidence,
    TextualConfidence,
    GrammaticalConfidence,
    LexicalConfidence,
    InterpretiveConfidence,
)


class TestBucketConfidenceThresholds:
    """Test bucket_confidence() threshold behavior."""

    def test_high_at_exactly_threshold(self):
        """Score exactly at HIGH threshold returns 'high'."""
        assert bucket_confidence(0.8) == "high"

    def test_high_above_threshold(self):
        """Score above HIGH threshold returns 'high'."""
        assert bucket_confidence(0.9) == "high"
        assert bucket_confidence(1.0) == "high"
        assert bucket_confidence(0.85) == "high"

    def test_medium_at_exactly_threshold(self):
        """Score exactly at MEDIUM threshold returns 'medium'."""
        assert bucket_confidence(0.6) == "medium"

    def test_medium_above_threshold_below_high(self):
        """Score between MEDIUM and HIGH thresholds returns 'medium'."""
        assert bucket_confidence(0.7) == "medium"
        assert bucket_confidence(0.79) == "medium"
        assert bucket_confidence(0.65) == "medium"

    def test_low_below_medium_threshold(self):
        """Score below MEDIUM threshold returns 'low'."""
        assert bucket_confidence(0.5) == "low"
        assert bucket_confidence(0.59) == "low"
        assert bucket_confidence(0.0) == "low"
        assert bucket_confidence(0.3) == "low"


class TestBucketConfidenceEdgeCases:
    """Test edge cases for bucket_confidence()."""

    def test_score_at_zero(self):
        """Score of 0.0 returns 'low'."""
        assert bucket_confidence(0.0) == "low"

    def test_score_at_one(self):
        """Score of 1.0 returns 'high'."""
        assert bucket_confidence(1.0) == "high"

    def test_threshold_boundary_high_minus_epsilon(self):
        """Score just below HIGH threshold returns 'medium'."""
        assert bucket_confidence(0.7999999) == "medium"

    def test_threshold_boundary_medium_minus_epsilon(self):
        """Score just below MEDIUM threshold returns 'low'."""
        assert bucket_confidence(0.5999999) == "low"


class TestBucketConfidenceConstants:
    """Test that constants have expected values."""

    def test_high_threshold_value(self):
        """HIGH threshold is 0.8."""
        assert CONFIDENCE_BUCKET_HIGH == 0.8

    def test_medium_threshold_value(self):
        """MEDIUM threshold is 0.6."""
        assert CONFIDENCE_BUCKET_MEDIUM == 0.6


class TestLayeredConfidenceBucket:
    """Test bucket property on LayeredConfidence."""

    def test_high_bucket_all_high_scores(self):
        """LayeredConfidence with all high scores returns 'high' bucket."""
        lc = LayeredConfidence(
            textual=TextualConfidence(score=1.0),
            grammatical=GrammaticalConfidence(score=1.0),
            lexical=LexicalConfidence(score=1.0),
            interpretive=InterpretiveConfidence(score=1.0),
        )
        # Composite = 1.0, bucket = "high"
        assert lc.bucket == "high"

    def test_medium_bucket_mixed_scores(self):
        """LayeredConfidence with mixed scores returns 'medium' bucket."""
        lc = LayeredConfidence(
            textual=TextualConfidence(score=0.7),
            grammatical=GrammaticalConfidence(score=0.7),
            lexical=LexicalConfidence(score=0.7),
            interpretive=InterpretiveConfidence(score=0.7),
        )
        # Composite = 0.7, bucket = "medium"
        assert lc.bucket == "medium"

    def test_low_bucket_all_low_scores(self):
        """LayeredConfidence with all low scores returns 'low' bucket."""
        lc = LayeredConfidence(
            textual=TextualConfidence(score=0.3),
            grammatical=GrammaticalConfidence(score=0.3),
            lexical=LexicalConfidence(score=0.3),
            interpretive=InterpretiveConfidence(score=0.3),
        )
        # Composite = 0.3, bucket = "low"
        assert lc.bucket == "low"

    def test_bucket_in_to_dict(self):
        """LayeredConfidence.to_dict() includes bucket field."""
        lc = LayeredConfidence(
            textual=TextualConfidence(score=0.9),
            grammatical=GrammaticalConfidence(score=0.9),
            lexical=LexicalConfidence(score=0.9),
            interpretive=InterpretiveConfidence(score=0.9),
        )
        result = lc.to_dict()
        assert "bucket" in result
        assert result["bucket"] == "high"

    def test_bucket_matches_composite(self):
        """Bucket always matches the bucketed composite score."""
        # Test a few combinations
        test_cases = [
            (0.9, 0.9, 0.9, 0.9, "high"),
            (0.8, 0.8, 0.8, 0.8, "high"),
            (0.7, 0.7, 0.7, 0.7, "medium"),
            (0.6, 0.6, 0.6, 0.6, "medium"),
            (0.5, 0.5, 0.5, 0.5, "low"),
        ]
        for t, g, lex, i, expected_bucket in test_cases:
            lc = LayeredConfidence(
                textual=TextualConfidence(score=t),
                grammatical=GrammaticalConfidence(score=g),
                lexical=LexicalConfidence(score=lex),
                interpretive=InterpretiveConfidence(score=i),
            )
            assert lc.bucket == expected_bucket, f"Failed for scores {t},{g},{lex},{i}"


class TestBucketDeterminism:
    """Test that bucketing is deterministic."""

    def test_bucket_is_deterministic(self):
        """Same score always produces same bucket."""
        for _ in range(100):
            assert bucket_confidence(0.79) == "medium"
            assert bucket_confidence(0.80) == "high"
            assert bucket_confidence(0.59) == "low"
            assert bucket_confidence(0.60) == "medium"

    def test_layered_confidence_bucket_deterministic(self):
        """LayeredConfidence bucket is deterministic across calls."""
        lc = LayeredConfidence(
            textual=TextualConfidence(score=0.75),
            grammatical=GrammaticalConfidence(score=0.75),
            lexical=LexicalConfidence(score=0.75),
            interpretive=InterpretiveConfidence(score=0.75),
        )
        # Call bucket multiple times
        buckets = [lc.bucket for _ in range(50)]
        assert all(b == "medium" for b in buckets)
