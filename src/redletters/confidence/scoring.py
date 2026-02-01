"""Layered confidence scoring implementation.

Implements ADR-010: Four-layer confidence model with explainability.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from redletters.claims.taxonomy import Claim, ClaimType


@dataclass
class TextualConfidence:
    """Layer 1: Confidence based on manuscript witness agreement.

    Measures how certain we are about what the text actually says,
    based on variant evidence and witness attestation.
    """

    score: float  # 0.0 to 1.0

    # Inputs for explainability
    variant_exists: bool = False
    witness_agreement: float = 1.0  # % of witnesses supporting chosen reading
    earliest_witness_century: int | None = None
    papyri_support: bool = False
    primary_uncial_support: list[str] = field(default_factory=list)

    # Human-readable explanation
    rationale: str = ""

    @classmethod
    def calculate(
        cls,
        variant_exists: bool = False,
        witness_agreement: float = 1.0,
        earliest_witness_century: int | None = None,
        papyri_support: bool = False,
        primary_uncials: list[str] | None = None,
    ) -> "TextualConfidence":
        """Calculate textual confidence from witness data.

        Scoring heuristic:
        - No variant: +0.40
        - Papyri support (P66, P75, etc.): +0.25
        - Primary uncials agree (aleph, B, A): +0.20
        - >80% witness agreement: +0.15
        - Reading is early (2nd-3rd century): +0.10
        """
        score = 0.0
        factors: list[str] = []

        if not variant_exists:
            score += 0.40
            factors.append("No variant at this position")
        else:
            factors.append("Variant exists")

        if papyri_support:
            score += 0.25
            factors.append("Papyri support")

        uncials = primary_uncials or []
        if len(uncials) >= 2:
            score += 0.20
            factors.append(f"Primary uncials: {', '.join(uncials)}")
        elif len(uncials) == 1:
            score += 0.10
            factors.append(f"Uncial support: {uncials[0]}")

        if witness_agreement > 0.80:
            score += 0.15
            factors.append(f"Witness agreement: {witness_agreement:.0%}")

        if earliest_witness_century and earliest_witness_century <= 3:
            score += 0.10
            factors.append(f"Early witness: {earliest_witness_century}th century")

        # Clamp to [0, 1]
        score = min(max(score, 0.0), 1.0)

        rationale = "; ".join(factors) if factors else "No textual data available"

        return cls(
            score=score,
            variant_exists=variant_exists,
            witness_agreement=witness_agreement,
            earliest_witness_century=earliest_witness_century,
            papyri_support=papyri_support,
            primary_uncial_support=uncials,
            rationale=rationale,
        )

    @classmethod
    def default_high(cls) -> "TextualConfidence":
        """Default high confidence (no variants)."""
        return cls.calculate(variant_exists=False, witness_agreement=1.0)

    @classmethod
    def default_uncertain(cls) -> "TextualConfidence":
        """Default uncertain (variant present, no witness data)."""
        return cls.calculate(variant_exists=True, witness_agreement=0.5)


@dataclass
class GrammaticalConfidence:
    """Layer 2: Confidence based on parse ambiguity.

    Measures certainty about grammatical analysis of the text,
    including morphological parsing and syntactic structure.
    """

    score: float  # 0.0 to 1.0

    # Inputs for explainability
    parse_ambiguity_count: int = 1  # How many valid parses exist
    chosen_parse: str = ""
    alternative_parses: list[str] = field(default_factory=list)
    syntax_ambiguity: bool = False

    # Human-readable explanation
    rationale: str = ""

    @classmethod
    def calculate(
        cls,
        parse_count: int = 1,
        chosen_parse: str = "",
        alternatives: list[str] | None = None,
        syntax_ambiguous: bool = False,
        context_disambiguates: bool = False,
    ) -> "GrammaticalConfidence":
        """Calculate grammatical confidence from parse data.

        Scoring heuristic:
        - Single valid parse: 1.0
        - 2 parses, one clearly preferred: 0.8
        - 2-3 parses, contextually disambiguated: 0.6
        - Multiple parses, disputed: 0.4
        - Syntactically ambiguous construction: 0.2
        """
        alts = alternatives or []
        factors: list[str] = []

        if parse_count == 1 and not syntax_ambiguous:
            score = 1.0
            factors.append("Single unambiguous parse")
        elif parse_count == 2 and context_disambiguates:
            score = 0.8
            factors.append("Two parses; context favors one")
        elif parse_count <= 3 and context_disambiguates:
            score = 0.6
            factors.append(f"{parse_count} parses; contextually disambiguated")
        elif syntax_ambiguous:
            score = 0.2
            factors.append("Syntactically ambiguous construction")
        elif parse_count > 1:
            score = 0.4
            factors.append(f"{parse_count} competing parses")
        else:
            score = 0.5
            factors.append("Parse analysis incomplete")

        if chosen_parse:
            factors.append(f"Chosen: {chosen_parse}")

        if alts:
            factors.append(f"Alternatives: {', '.join(alts[:3])}")

        rationale = "; ".join(factors)

        return cls(
            score=score,
            parse_ambiguity_count=parse_count,
            chosen_parse=chosen_parse,
            alternative_parses=alts,
            syntax_ambiguity=syntax_ambiguous,
            rationale=rationale,
        )

    @classmethod
    def default_high(cls) -> "GrammaticalConfidence":
        """Default high confidence (unambiguous parse)."""
        return cls.calculate(parse_count=1)

    @classmethod
    def default_ambiguous(cls) -> "GrammaticalConfidence":
        """Default ambiguous (multiple parses)."""
        return cls.calculate(parse_count=3)


@dataclass
class LexicalConfidence:
    """Layer 3: Confidence based on lexical sense selection.

    Measures certainty about word meaning selection,
    considering semantic range breadth and contextual support.
    """

    score: float  # 0.0 to 1.0

    # Inputs for explainability
    lemma: str = ""
    sense_count: int = 1
    sense_chosen: str = ""
    sense_range: list[str] = field(default_factory=list)
    collocational_support: bool = False
    corpus_frequency: float = 0.0  # How common is this sense in corpus

    # Human-readable explanation
    rationale: str = ""

    @classmethod
    def calculate(
        cls,
        lemma: str,
        sense_count: int = 1,
        sense_chosen: str = "",
        sense_range: list[str] | None = None,
        collocation_supported: bool = False,
        dominant_sense: bool = False,
        is_hapax: bool = False,
    ) -> "LexicalConfidence":
        """Calculate lexical confidence from sense data.

        Scoring heuristic:
        - Single sense: 1.0
        - 2-3 senses, one dominant (>70%): 0.85
        - Multiple senses, collocationally supported: 0.7
        - Multiple senses, context-dependent: 0.5
        - Broad range, disputed: 0.3
        - Hapax or rare: 0.2
        """
        senses = sense_range or []
        factors: list[str] = []

        if is_hapax:
            score = 0.2
            factors.append(f"Hapax legomenon: {lemma}")
        elif sense_count == 1:
            score = 1.0
            factors.append("Single sense in lexicons")
        elif sense_count <= 3 and dominant_sense:
            score = 0.85
            factors.append(f"{sense_count} senses; one dominant")
        elif collocation_supported:
            score = 0.7
            factors.append(
                f"{sense_count} senses; collocation supports '{sense_chosen}'"
            )
        elif sense_count <= 5:
            score = 0.5
            factors.append(f"{sense_count} senses; context-dependent")
        else:
            score = 0.3
            factors.append(f"Broad semantic range ({sense_count} senses)")

        if sense_chosen:
            factors.append(f"Selected: {sense_chosen}")

        if senses and len(senses) > 1:
            factors.append(f"Range: {', '.join(senses[:4])}")

        rationale = "; ".join(factors)

        return cls(
            score=score,
            lemma=lemma,
            sense_count=sense_count,
            sense_chosen=sense_chosen,
            sense_range=senses,
            collocational_support=collocation_supported,
            rationale=rationale,
        )

    @classmethod
    def default_high(cls, lemma: str = "") -> "LexicalConfidence":
        """Default high confidence (single sense)."""
        return cls.calculate(lemma=lemma, sense_count=1)

    @classmethod
    def default_broad(cls, lemma: str = "") -> "LexicalConfidence":
        """Default broad range (many senses)."""
        return cls.calculate(lemma=lemma, sense_count=8)


@dataclass
class InterpretiveConfidence:
    """Layer 4: Confidence based on inference distance.

    Measures certainty about the interpretation itself,
    directly tied to ClaimType (higher type = lower confidence).
    """

    score: float  # 0.0 to 1.0

    # Inputs for explainability
    claim_type: ClaimType | None = None
    inference_steps: int = 0
    assumption_count: int = 0
    tradition_dependency: bool = False
    cross_reference_count: int = 0

    # Human-readable explanation
    rationale: str = ""

    @classmethod
    def calculate(
        cls,
        claim: Claim | None = None,
        claim_type: ClaimType | None = None,
        inference_steps: int = 0,
        assumptions: int = 0,
        tradition_dependent: bool = False,
        cross_references: int = 0,
    ) -> "InterpretiveConfidence":
        """Calculate interpretive confidence from claim data.

        Base score by claim type, adjusted for:
        - Inference steps (-0.05 per step beyond base)
        - Unstated assumptions (-0.10 per assumption)
        - Tradition dependency (-0.10 if not attributed)
        - Cross-references (-0.05 per reference in TYPE7)
        """
        factors: list[str] = []

        # Get claim type from claim or parameter
        if claim:
            ctype = claim.claim_type
            inference_steps = claim.dependencies.total_count
            assumptions = len(claim.dependencies.context)
            cross_references = len(
                [
                    d
                    for d in claim.dependencies.context
                    if "cross" in d.assumption.lower()
                    or "reference" in d.assumption.lower()
                ]
            )
        else:
            ctype = claim_type or ClaimType.TYPE0_DESCRIPTIVE

        # Base score from claim type
        base_score = ctype.base_confidence
        factors.append(f"{ctype.label} claim (base: {base_score:.2f})")

        score = base_score

        # Adjustments
        if inference_steps > 1:
            penalty = 0.05 * (inference_steps - 1)
            score -= penalty
            factors.append(f"Inference steps: -{penalty:.2f}")

        if assumptions > 0:
            penalty = 0.10 * assumptions
            score -= penalty
            factors.append(f"Assumptions: -{penalty:.2f}")

        if tradition_dependent:
            factors.append("Tradition-dependent")

        if cross_references > 0 and ctype == ClaimType.TYPE7_HARMONIZED:
            penalty = 0.05 * cross_references
            score -= penalty
            factors.append(f"Cross-refs: -{penalty:.2f}")

        # Clamp to [0, 1]
        score = min(max(score, 0.0), 1.0)

        rationale = "; ".join(factors)

        return cls(
            score=score,
            claim_type=ctype,
            inference_steps=inference_steps,
            assumption_count=assumptions,
            tradition_dependency=tradition_dependent,
            cross_reference_count=cross_references,
            rationale=rationale,
        )

    @classmethod
    def from_claim_type(cls, claim_type: ClaimType) -> "InterpretiveConfidence":
        """Create confidence from claim type alone."""
        return cls.calculate(claim_type=claim_type)

    @classmethod
    def default_descriptive(cls) -> "InterpretiveConfidence":
        """Default for descriptive claims (highest)."""
        return cls.calculate(claim_type=ClaimType.TYPE0_DESCRIPTIVE)


@dataclass
class LayeredConfidence:
    """Aggregated confidence from all four layers.

    Composite score is a weighted average, but components
    should always be shown alongside the aggregate.
    """

    textual: TextualConfidence
    grammatical: GrammaticalConfidence
    lexical: LexicalConfidence
    interpretive: InterpretiveConfidence

    # Configurable weights (default per ADR-010)
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "textual": 0.30,
            "grammatical": 0.25,
            "lexical": 0.25,
            "interpretive": 0.20,
        }
    )

    @property
    def composite(self) -> float:
        """Weighted composite score."""
        return (
            self.textual.score * self.weights["textual"]
            + self.grammatical.score * self.weights["grammatical"]
            + self.lexical.score * self.weights["lexical"]
            + self.interpretive.score * self.weights["interpretive"]
        )

    @property
    def components(self) -> dict[str, float]:
        """All component scores."""
        return {
            "textual": self.textual.score,
            "grammatical": self.grammatical.score,
            "lexical": self.lexical.score,
            "interpretive": self.interpretive.score,
            "composite": self.composite,
        }

    @property
    def weakest_layer(self) -> str:
        """Name of the lowest-scoring layer."""
        scores = {
            "textual": self.textual.score,
            "grammatical": self.grammatical.score,
            "lexical": self.lexical.score,
            "interpretive": self.interpretive.score,
        }
        return min(scores, key=lambda k: scores[k])

    def to_dict(self) -> dict:
        """Serialize to dictionary for API responses."""
        return {
            "composite": round(self.composite, 3),
            "layers": {
                "textual": {
                    "score": round(self.textual.score, 3),
                    "rationale": self.textual.rationale,
                    "variant_exists": self.textual.variant_exists,
                },
                "grammatical": {
                    "score": round(self.grammatical.score, 3),
                    "rationale": self.grammatical.rationale,
                    "parse_count": self.grammatical.parse_ambiguity_count,
                },
                "lexical": {
                    "score": round(self.lexical.score, 3),
                    "rationale": self.lexical.rationale,
                    "sense_count": self.lexical.sense_count,
                },
                "interpretive": {
                    "score": round(self.interpretive.score, 3),
                    "rationale": self.interpretive.rationale,
                    "claim_type": (
                        self.interpretive.claim_type.label
                        if self.interpretive.claim_type
                        else None
                    ),
                },
            },
            "weakest_layer": self.weakest_layer,
            "weights": self.weights,
        }


@dataclass
class ConfidenceExplanation:
    """Human-readable explanation of confidence score."""

    summary: str
    layer_explanations: dict[str, str]
    improvement_suggestions: list[str]

    def __str__(self) -> str:
        lines = [self.summary, ""]
        for layer, explanation in self.layer_explanations.items():
            lines.append(f"  {layer}: {explanation}")
        if self.improvement_suggestions:
            lines.append("")
            lines.append("Suggestions:")
            for s in self.improvement_suggestions:
                lines.append(f"  - {s}")
        return "\n".join(lines)


class ConfidenceCalculator:
    """Calculator for layered confidence scores.

    Usage:
        calc = ConfidenceCalculator()
        confidence = calc.calculate(claim=my_claim)
        print(confidence.composite)
        print(confidence.to_dict())
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
    ):
        """Initialize calculator with optional custom weights.

        Args:
            weights: Custom layer weights (must sum to 1.0)
        """
        self._weights = weights or {
            "textual": 0.30,
            "grammatical": 0.25,
            "lexical": 0.25,
            "interpretive": 0.20,
        }

    def calculate(
        self,
        claim: Claim | None = None,
        textual: TextualConfidence | None = None,
        grammatical: GrammaticalConfidence | None = None,
        lexical: LexicalConfidence | None = None,
    ) -> LayeredConfidence:
        """Calculate layered confidence.

        Args:
            claim: Optional claim for interpretive layer
            textual: Pre-calculated textual confidence (or default high)
            grammatical: Pre-calculated grammatical confidence (or default high)
            lexical: Pre-calculated lexical confidence (or default high)

        Returns:
            LayeredConfidence with all layers populated
        """
        # Use provided layers or defaults
        text_conf = textual or TextualConfidence.default_high()
        gram_conf = grammatical or GrammaticalConfidence.default_high()
        lex_conf = lexical or LexicalConfidence.default_high()

        # Calculate interpretive from claim or default
        if claim:
            interp_conf = InterpretiveConfidence.calculate(claim=claim)
        else:
            interp_conf = InterpretiveConfidence.default_descriptive()

        return LayeredConfidence(
            textual=text_conf,
            grammatical=gram_conf,
            lexical=lex_conf,
            interpretive=interp_conf,
            weights=self._weights,
        )

    def explain(self, confidence: LayeredConfidence) -> ConfidenceExplanation:
        """Generate human-readable explanation.

        Args:
            confidence: The layered confidence to explain

        Returns:
            ConfidenceExplanation with summary and suggestions
        """
        composite = confidence.composite
        weakest = confidence.weakest_layer

        if composite >= 0.8:
            summary = (
                f"High confidence ({composite:.2f}): Strong support across all layers"
            )
        elif composite >= 0.6:
            summary = f"Moderate confidence ({composite:.2f}): Some uncertainty in {weakest} layer"
        elif composite >= 0.4:
            summary = f"Low confidence ({composite:.2f}): Significant uncertainty, especially {weakest}"
        else:
            summary = f"Very low confidence ({composite:.2f}): Multiple sources of uncertainty"

        layer_explanations = {
            "Textual": confidence.textual.rationale,
            "Grammatical": confidence.grammatical.rationale,
            "Lexical": confidence.lexical.rationale,
            "Interpretive": confidence.interpretive.rationale,
        }

        suggestions = []
        if confidence.textual.score < 0.5:
            suggestions.append("Consult additional manuscript witnesses")
        if confidence.grammatical.score < 0.5:
            suggestions.append("Consider alternative grammatical parses")
        if confidence.lexical.score < 0.5:
            suggestions.append("Present full lexical range, not single gloss")
        if confidence.interpretive.score < 0.5:
            suggestions.append("Lower claim type or add explicit dependencies")

        return ConfidenceExplanation(
            summary=summary,
            layer_explanations=layer_explanations,
            improvement_suggestions=suggestions,
        )

    def compare(
        self,
        conf_a: LayeredConfidence,
        conf_b: LayeredConfidence,
    ) -> dict[str, tuple[float, float, float]]:
        """Compare two confidence scores.

        Args:
            conf_a: First confidence
            conf_b: Second confidence

        Returns:
            Dict mapping layer name to (score_a, score_b, difference)
        """
        return {
            "textual": (
                conf_a.textual.score,
                conf_b.textual.score,
                conf_a.textual.score - conf_b.textual.score,
            ),
            "grammatical": (
                conf_a.grammatical.score,
                conf_b.grammatical.score,
                conf_a.grammatical.score - conf_b.grammatical.score,
            ),
            "lexical": (
                conf_a.lexical.score,
                conf_b.lexical.score,
                conf_a.lexical.score - conf_b.lexical.score,
            ),
            "interpretive": (
                conf_a.interpretive.score,
                conf_b.interpretive.score,
                conf_a.interpretive.score - conf_b.interpretive.score,
            ),
            "composite": (
                conf_a.composite,
                conf_b.composite,
                conf_a.composite - conf_b.composite,
            ),
        }
