"""Lexicon Provider module for gloss lookup.

Sprint 10: Provides license-aware lexicon lookup with provenance tracking.
"""

from redletters.lexicon.provider import (
    BasicGlossProvider,
    GlossResult,
    LexiconProvider,
    normalize_greek,
)

__all__ = [
    "BasicGlossProvider",
    "GlossResult",
    "LexiconProvider",
    "normalize_greek",
]
