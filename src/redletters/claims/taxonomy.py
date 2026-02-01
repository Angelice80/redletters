"""Claim taxonomy: Types, dependencies, and data structures.

Implements ADR-009 claim type hierarchy ordered by epistemic distance from text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Literal


class ClaimType(IntEnum):
    """Claim types ordered by epistemic distance from the text.

    Lower numbers = closer to direct observation.
    Higher numbers = more inference required.
    """

    TYPE0_DESCRIPTIVE = 0
    """Observable facts about the text: 'This word is a verb.'
    No interpretation required. Pure linguistic description.
    """

    TYPE1_LEXICAL_RANGE = 1
    """Semantic field of a lemma: 'basileia can mean kingdom, reign, or royal power.'
    Bounded by lexicon entries. No single gloss selection.
    """

    TYPE2_GRAMMATICAL = 2
    """Interpretation based on morpho-syntax: 'This genitive is subjective.'
    Requires choosing among grammatically valid parses.
    """

    TYPE3_CONTEXTUAL = 3
    """Inference from literary/historical context: 'This refers to the Babylonian exile.'
    Requires assumptions about author intent, audience, background.
    """

    TYPE4_THEOLOGICAL = 4
    """Doctrinal interpretation: 'This teaches the divinity of Christ.'
    Requires theological framework and tradition.
    """

    TYPE5_MORAL = 5
    """Ethical universalization: 'This commands all Christians to...'
    Requires hermeneutical bridge from ancient to modern.
    """

    TYPE6_METAPHYSICAL = 6
    """Claims about ultimate reality: 'This proves the Trinity.'
    Maximum inference distance from text.
    """

    TYPE7_HARMONIZED = 7
    """Synthesis across multiple passages: 'When read with Romans 8, this means...'
    Requires assuming coherent authorial intent across corpus.
    """

    @property
    def label(self) -> str:
        """Human-readable label."""
        labels = {
            0: "Descriptive",
            1: "Lexical Range",
            2: "Grammatical",
            3: "Contextual",
            4: "Theological",
            5: "Moral",
            6: "Metaphysical",
            7: "Harmonized",
        }
        return labels.get(self.value, "Unknown")

    @property
    def description(self) -> str:
        """Full description of this claim type."""
        descriptions = {
            0: "Observable facts about the text requiring no interpretation",
            1: "Semantic range of a word without selecting a single meaning",
            2: "Interpretation based on grammatical analysis",
            3: "Inference from literary or historical context",
            4: "Interpretation within a theological framework",
            5: "Ethical claims applied to modern contexts",
            6: "Claims about metaphysical or ultimate reality",
            7: "Synthesis requiring harmony across multiple passages",
        }
        return descriptions.get(self.value, "Unknown claim type")

    @property
    def base_confidence(self) -> float:
        """Default interpretive confidence for this claim type.

        Used in ADR-010 layered confidence scoring.
        """
        confidences = {
            0: 1.0,  # Descriptive: direct observation
            1: 0.9,  # Lexical range: bounded by lexicons
            2: 0.75,  # Grammatical: parse ambiguity
            3: 0.6,  # Contextual: inference required
            4: 0.45,  # Theological: framework dependent
            5: 0.3,  # Moral: hermeneutical bridge
            6: 0.2,  # Metaphysical: maximum inference
            7: 0.25,  # Harmonized: cross-reference synthesis
        }
        return confidences.get(self.value, 0.1)


@dataclass
class TextSpan:
    """A span of text that a claim is about."""

    book: str
    chapter: int
    verse_start: int
    verse_end: int | None = None
    position_start: int | None = None
    position_end: int | None = None

    @property
    def ref(self) -> str:
        """Canonical reference string."""
        if self.verse_end and self.verse_end != self.verse_start:
            return f"{self.book}.{self.chapter}.{self.verse_start}-{self.verse_end}"
        return f"{self.book}.{self.chapter}.{self.verse_start}"


@dataclass
class VariantDependency:
    """Dependency on a textual variant reading."""

    variant_unit_ref: str
    reading_chosen: int
    rationale: str
    witnesses: list[str] = field(default_factory=list)


@dataclass
class GrammarDependency:
    """Dependency on a grammatical parse choice."""

    token_ref: str
    parse_choice: str
    alternatives: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class LexiconDependency:
    """Dependency on a lexical sense selection."""

    lemma: str
    sense_chosen: str
    sense_range: list[str] = field(default_factory=list)
    rationale: str = ""


@dataclass
class ContextDependency:
    """Dependency on contextual/historical assumption."""

    assumption: str
    evidence: str
    alternatives: list[str] = field(default_factory=list)


@dataclass
class ClaimDependency:
    """Aggregated dependencies for a claim."""

    variants: list[VariantDependency] = field(default_factory=list)
    grammar: list[GrammarDependency] = field(default_factory=list)
    lexicon: list[LexiconDependency] = field(default_factory=list)
    context: list[ContextDependency] = field(default_factory=list)

    @property
    def has_dependencies(self) -> bool:
        """True if any dependencies exist."""
        return bool(self.variants or self.grammar or self.lexicon or self.context)

    @property
    def variant_count(self) -> int:
        """Number of variant dependencies."""
        return len(self.variants)

    @property
    def total_count(self) -> int:
        """Total number of all dependencies."""
        return (
            len(self.variants)
            + len(self.grammar)
            + len(self.lexicon)
            + len(self.context)
        )


@dataclass
class Claim:
    """A claim about the text with typed classification and dependencies.

    Every claim above TYPE0 must declare what it depends on:
    - Which variant readings it assumes
    - Which grammatical parses it chooses
    - Which lexical senses it selects
    - Which contextual assumptions it makes
    """

    claim_type: ClaimType
    text_span: TextSpan
    content: str
    confidence: float = 1.0

    # Dependencies
    dependencies: ClaimDependency = field(default_factory=ClaimDependency)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    mode: Literal["readable", "traceable"] = "traceable"
    acknowledgement_ids: list[str] = field(default_factory=list)

    # Classification metadata
    classification_confidence: float = 1.0
    classification_signals: list[str] = field(default_factory=list)
    epistemic_warnings: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate claim after creation."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")
        if self.claim_type.value > 1 and not self.dependencies.has_dependencies:
            # TYPE2+ claims should declare dependencies
            # This is a soft warning, not an error
            pass

    @property
    def inference_distance(self) -> int:
        """How many epistemic steps from direct observation."""
        return self.claim_type.value

    @property
    def requires_escalation(self) -> bool:
        """True if this claim type requires traceable mode."""
        return self.claim_type.value >= 5  # TYPE5+

    @property
    def requires_hypothesis_markers(self) -> bool:
        """True if this claim needs uncertainty markers in readable mode."""
        return 2 <= self.claim_type.value <= 3  # TYPE2-3

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "claim_type": self.claim_type.value,
            "claim_type_label": self.claim_type.label,
            "text_span": {
                "book": self.text_span.book,
                "chapter": self.text_span.chapter,
                "verse_start": self.text_span.verse_start,
                "verse_end": self.text_span.verse_end,
                "ref": self.text_span.ref,
            },
            "content": self.content,
            "confidence": self.confidence,
            "dependencies": {
                "variants": [
                    {
                        "ref": v.variant_unit_ref,
                        "reading": v.reading_chosen,
                        "rationale": v.rationale,
                    }
                    for v in self.dependencies.variants
                ],
                "grammar": [
                    {
                        "ref": g.token_ref,
                        "parse": g.parse_choice,
                        "alternatives": g.alternatives,
                    }
                    for g in self.dependencies.grammar
                ],
                "lexicon": [
                    {
                        "lemma": lex.lemma,
                        "sense": lex.sense_chosen,
                        "range": lex.sense_range,
                    }
                    for lex in self.dependencies.lexicon
                ],
                "context": [
                    {"assumption": c.assumption, "evidence": c.evidence}
                    for c in self.dependencies.context
                ],
            },
            "mode": self.mode,
            "created_at": self.created_at.isoformat(),
            "inference_distance": self.inference_distance,
            "epistemic_warnings": self.epistemic_warnings,
        }
