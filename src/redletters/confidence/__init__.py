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
"""

from redletters.confidence.scoring import (
    LayeredConfidence,
    TextualConfidence,
    GrammaticalConfidence,
    LexicalConfidence,
    InterpretiveConfidence,
    ConfidenceCalculator,
    ConfidenceExplanation,
)

__all__ = [
    "LayeredConfidence",
    "TextualConfidence",
    "GrammaticalConfidence",
    "LexicalConfidence",
    "InterpretiveConfidence",
    "ConfidenceCalculator",
    "ConfidenceExplanation",
]
