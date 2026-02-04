"""Confidence module: Layered explainable confidence scoring.

This module implements ADR-010 (Explainable Layered Confidence Scoring).

Confidence is decomposed into four layers:
- Textual: Manuscript/variant witness agreement
- Grammatical: Parse ambiguity level
- Lexical: Sense range breadth and selection certainty
- Interpretive: Inference distance from text (tied to ClaimType)

Each layer provides:
- A score (0.0-1.0)
- A rationale explaining the score
- Input factors for auditability

v0.8.0: Added confidence bucketing (high/medium/low) for uncertainty propagation.
"""

from redletters.confidence.scoring import (
    LayeredConfidence,
    TextualConfidence,
    GrammaticalConfidence,
    LexicalConfidence,
    InterpretiveConfidence,
    ConfidenceCalculator,
    ConfidenceExplanation,
    # v0.8.0: Confidence bucketing
    bucket_confidence,
    ConfidenceBucket,
    CONFIDENCE_BUCKET_HIGH,
    CONFIDENCE_BUCKET_MEDIUM,
)

__all__ = [
    "LayeredConfidence",
    "TextualConfidence",
    "GrammaticalConfidence",
    "LexicalConfidence",
    "InterpretiveConfidence",
    "ConfidenceCalculator",
    "ConfidenceExplanation",
    # v0.8.0: Confidence bucketing
    "bucket_confidence",
    "ConfidenceBucket",
    "CONFIDENCE_BUCKET_HIGH",
    "CONFIDENCE_BUCKET_MEDIUM",
]
