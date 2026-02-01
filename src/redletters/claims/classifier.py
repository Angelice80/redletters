"""Claim classifier: Analyzes text to determine claim type.

Uses heuristic pattern matching to classify claims by epistemic level.
The classifier is intentionally conservative - when uncertain, it
classifies higher (requiring more justification).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from redletters.claims.taxonomy import ClaimType, TextSpan
from redletters.claims.epistemic_pressure import (
    EpistemicPressureDetector,
    EpistemicPressureWarning,
)


@dataclass
class ClaimContext:
    """Context for claim classification."""

    text_span: TextSpan
    has_variant_at_span: bool = False
    has_grammar_ambiguity: bool = False
    has_lexical_ambiguity: bool = False
    cross_references: list[str] = field(default_factory=list)


@dataclass
class ClassificationResult:
    """Result of claim classification."""

    claim_type: ClaimType
    confidence: float  # Classifier confidence (not claim confidence)
    signals: list[str]  # Patterns/features that influenced classification
    warnings: list[EpistemicPressureWarning]
    suggested_type: ClaimType | None = None  # If override recommended

    @property
    def type_label(self) -> str:
        """Human-readable type label."""
        return self.claim_type.label


# Classification patterns: (regex, claim_type, signal_description)
CLASSIFICATION_PATTERNS: list[tuple[str, ClaimType, str]] = [
    # TYPE0: Descriptive patterns
    (
        r"\bis a (noun|verb|adjective|adverb|participle|infinitive)\b",
        ClaimType.TYPE0_DESCRIPTIVE,
        "POS identification",
    ),
    (
        r"\b(appears|occurs) \d+ times?\b",
        ClaimType.TYPE0_DESCRIPTIVE,
        "frequency count",
    ),
    (r"\bthis word is\b", ClaimType.TYPE0_DESCRIPTIVE, "word identification"),
    (r"\bthe lemma is\b", ClaimType.TYPE0_DESCRIPTIVE, "lemma identification"),
    (
        r"\b(nominative|genitive|dative|accusative|vocative)\b",
        ClaimType.TYPE0_DESCRIPTIVE,
        "case identification",
    ),
    (
        r"\b(singular|plural|dual)\b",
        ClaimType.TYPE0_DESCRIPTIVE,
        "number identification",
    ),
    (
        r"\b(active|middle|passive)\b",
        ClaimType.TYPE0_DESCRIPTIVE,
        "voice identification",
    ),
    # TYPE1: Lexical range patterns
    (r"\bcan mean\b", ClaimType.TYPE1_LEXICAL_RANGE, "semantic range indicator"),
    (
        r"\bsemantic (range|field|domain)\b",
        ClaimType.TYPE1_LEXICAL_RANGE,
        "explicit range reference",
    ),
    (
        r"\bpossible meanings include\b",
        ClaimType.TYPE1_LEXICAL_RANGE,
        "meaning enumeration",
    ),
    (
        r"\bgloss(es)? (include|are)\b",
        ClaimType.TYPE1_LEXICAL_RANGE,
        "gloss enumeration",
    ),
    (r"\blexicon entries\b", ClaimType.TYPE1_LEXICAL_RANGE, "lexicon reference"),
    (r"\bLSJ|BDAG|Louw-Nida\b", ClaimType.TYPE1_LEXICAL_RANGE, "lexicon citation"),
    # TYPE2: Grammatical patterns
    (
        r"\b(subjective|objective|possessive|partitive|epexegetical) genitive\b",
        ClaimType.TYPE2_GRAMMATICAL,
        "genitive classification",
    ),
    (
        r"\b(dative of |indirect object|locative|instrumental)\b",
        ClaimType.TYPE2_GRAMMATICAL,
        "dative classification",
    ),
    (r"\bclause (structure|type)\b", ClaimType.TYPE2_GRAMMATICAL, "syntax analysis"),
    (r"\bmodifies\b", ClaimType.TYPE2_GRAMMATICAL, "modification analysis"),
    (
        r"\bthe syntax (suggests|indicates)\b",
        ClaimType.TYPE2_GRAMMATICAL,
        "syntax interpretation",
    ),
    (r"\bgrammatically\b", ClaimType.TYPE2_GRAMMATICAL, "grammar-based reasoning"),
    (r"\bparse[ds]? as\b", ClaimType.TYPE2_GRAMMATICAL, "parse classification"),
    # Grammatical "should/must" - translation/parsing recommendations (must precede TYPE5)
    # "should be parsed/translated" and "must be understood" are grammar, not morals
    (
        r"\b(should|must) be (parsed|read|translated|understood|taken|rendered)\b",
        ClaimType.TYPE2_GRAMMATICAL,
        "grammatical recommendation",
    ),
    (
        r"\b(must|should) (parse|read|translate|understand|take|render)\b",
        ClaimType.TYPE2_GRAMMATICAL,
        "grammatical directive",
    ),
    # TYPE3: Contextual patterns
    (r"\bin (this|that) context\b", ClaimType.TYPE3_CONTEXTUAL, "contextual framing"),
    (r"\b(first|second) century\b", ClaimType.TYPE3_CONTEXTUAL, "historical reference"),
    (
        r"\b(jewish|roman|hellenistic|greco-roman) (context|background|culture)\b",
        ClaimType.TYPE3_CONTEXTUAL,
        "cultural context",
    ),
    (
        r"\baudience (would have|understood)\b",
        ClaimType.TYPE3_CONTEXTUAL,
        "audience inference",
    ),
    (r"\bauthor (intended|meant)\b", ClaimType.TYPE3_CONTEXTUAL, "authorial intent"),
    (
        r"\bliterary (context|genre|convention)\b",
        ClaimType.TYPE3_CONTEXTUAL,
        "literary analysis",
    ),
    (r"\bintertextual\b", ClaimType.TYPE3_CONTEXTUAL, "intertextual reference"),
    (r"\ballud(es?|ing) to\b", ClaimType.TYPE3_CONTEXTUAL, "allusion identification"),
    (r"\bbackground\b", ClaimType.TYPE3_CONTEXTUAL, "background knowledge"),
    # TYPE4: Theological patterns
    (
        r"\b(doctrine|doctrinal|theology|theological)\b",
        ClaimType.TYPE4_THEOLOGICAL,
        "explicit theological language",
    ),
    (
        r"\b(divinity|deity|incarnation|trinity|atonement|salvation|redemption)\b",
        ClaimType.TYPE4_THEOLOGICAL,
        "doctrinal term",
    ),
    (
        r"\b(christ|christological|messianic|eschatological)\b",
        ClaimType.TYPE4_THEOLOGICAL,
        "christological/eschatological",
    ),
    (r"\bteaches (that|us)\b", ClaimType.TYPE4_THEOLOGICAL, "didactic framing"),
    (
        r"\bthe (church|tradition) (has |)interpret\b",
        ClaimType.TYPE4_THEOLOGICAL,
        "tradition reference",
    ),
    (
        r"\b(reformed|catholic|orthodox|lutheran|calvinist) (reading|interpretation)\b",
        ClaimType.TYPE4_THEOLOGICAL,
        "tradition attribution",
    ),
    (
        r"\bsoteriology|ecclesiology|pneumatology\b",
        ClaimType.TYPE4_THEOLOGICAL,
        "systematic theology term",
    ),
    # TYPE5: Moral patterns (require moral framing, not generic "should")
    # Subject-based moral prescriptions
    (
        r"\b(christians|believers|disciples|we|you) (should|must|ought to|are called to)\b",
        ClaimType.TYPE5_MORAL,
        "moral application to persons",
    ),
    # Moral vocabulary signals
    (
        r"\b(sin|sinful|sinning|immoral|wrong|righteous|ethical|obey|obedience|disobey)\b",
        ClaimType.TYPE5_MORAL,
        "moral vocabulary",
    ),
    # Explicit commands
    (
        r"\b(commanded to|forbidden to|obligated to)\b",
        ClaimType.TYPE5_MORAL,
        "explicit moral command",
    ),
    (
        r"\bappl(y|ies|ication) (to|for) (us|today|modern)\b",
        ClaimType.TYPE5_MORAL,
        "modern application",
    ),
    (
        r"\bethical (implication|application|command)\b",
        ClaimType.TYPE5_MORAL,
        "ethical framing",
    ),
    (
        r"\buniversal (command|principle|truth)\b",
        ClaimType.TYPE5_MORAL,
        "universal claim",
    ),
    (r"\bfor all time\b", ClaimType.TYPE5_MORAL, "timeless claim"),
    # TYPE6: Metaphysical patterns
    (r"\bproves? (that|the existence)\b", ClaimType.TYPE6_METAPHYSICAL, "proof claim"),
    (
        r"\bdemonstrates? (that|the reality)\b",
        ClaimType.TYPE6_METAPHYSICAL,
        "demonstration claim",
    ),
    (
        r"\bestablishes? (that|the truth)\b",
        ClaimType.TYPE6_METAPHYSICAL,
        "establishment claim",
    ),
    (
        r"\b(ultimate|absolute|eternal) (truth|reality)\b",
        ClaimType.TYPE6_METAPHYSICAL,
        "metaphysical language",
    ),
    (r"\bontological\b", ClaimType.TYPE6_METAPHYSICAL, "ontological term"),
    (
        r"\bthe nature of (god|reality|being)\b",
        ClaimType.TYPE6_METAPHYSICAL,
        "nature-of claim",
    ),
    # TYPE7: Harmonized patterns
    (
        r"\bwhen read (with|alongside|together with)\b",
        ClaimType.TYPE7_HARMONIZED,
        "cross-reference synthesis",
    ),
    (
        r"\b(cf\.|compare|see also)\b",
        ClaimType.TYPE7_HARMONIZED,
        "cross-reference marker",
    ),
    (r"\btaken together (with|,)\b", ClaimType.TYPE7_HARMONIZED, "synthesis marker"),
    (
        r"\bin light of (romans|galatians|matthew|john|hebrews)\b",
        ClaimType.TYPE7_HARMONIZED,
        "book cross-reference",
    ),
    (
        r"\bpaul (also|elsewhere) (says|writes)\b",
        ClaimType.TYPE7_HARMONIZED,
        "author harmonization",
    ),
    (r"\bscripture as a whole\b", ClaimType.TYPE7_HARMONIZED, "canonical synthesis"),
    (
        r"\bbiblical (theology|witness)\b",
        ClaimType.TYPE7_HARMONIZED,
        "canonical framing",
    ),
]


class ClaimClassifier:
    """Classifies claims by epistemic level.

    The classifier uses pattern matching to identify signals that
    indicate claim type. When multiple patterns match, the highest
    (most epistemically distant) type is chosen.

    This is intentionally conservative: uncertain classifications
    default to higher types (requiring more justification).

    Usage:
        classifier = ClaimClassifier()
        result = classifier.classify("This clearly teaches the Trinity")
        print(result.claim_type)  # TYPE4_THEOLOGICAL or TYPE6_METAPHYSICAL
    """

    def __init__(self):
        """Initialize classifier with compiled patterns."""
        self._patterns = [
            (re.compile(p, re.IGNORECASE), claim_type, signal)
            for p, claim_type, signal in CLASSIFICATION_PATTERNS
        ]
        self._pressure_detector = EpistemicPressureDetector()

    def classify(
        self,
        claim_text: str,
        context: ClaimContext | None = None,
    ) -> ClassificationResult:
        """Classify a claim by its epistemic level.

        Args:
            claim_text: The claim text to classify
            context: Optional context (variants, ambiguities, cross-refs)

        Returns:
            ClassificationResult with type, confidence, and signals
        """
        signals: list[str] = []
        type_votes: dict[ClaimType, int] = {t: 0 for t in ClaimType}

        # Pattern matching
        for pattern, claim_type, signal in self._patterns:
            if pattern.search(claim_text):
                signals.append(f"{claim_type.label}: {signal}")
                type_votes[claim_type] += 1

        # Context adjustments
        if context:
            if context.cross_references:
                type_votes[ClaimType.TYPE7_HARMONIZED] += len(context.cross_references)
                signals.append(f"Cross-references: {len(context.cross_references)}")

            if context.has_variant_at_span:
                # Variants increase uncertainty
                signals.append("Variant present at span")

            if context.has_grammar_ambiguity:
                # Grammar ambiguity suggests TYPE2 minimum
                if type_votes[ClaimType.TYPE0_DESCRIPTIVE] > 0:
                    type_votes[ClaimType.TYPE0_DESCRIPTIVE] -= 1
                type_votes[ClaimType.TYPE2_GRAMMATICAL] += 1
                signals.append("Grammar ambiguity present")

            if context.has_lexical_ambiguity:
                # Lexical ambiguity suggests TYPE1 minimum
                type_votes[ClaimType.TYPE1_LEXICAL_RANGE] += 1
                signals.append("Lexical ambiguity present")

        # Epistemic pressure detection
        warnings = self._pressure_detector.detect(claim_text)
        if warnings:
            signals.append(f"Epistemic pressure: {len(warnings)} pattern(s)")
            # Pressure language often correlates with higher inference
            for w in warnings:
                if w.severity == "block":
                    # Blocking patterns suggest the claim is making
                    # stronger assertions than warranted
                    type_votes[ClaimType.TYPE4_THEOLOGICAL] += 1

        # Determine final type (highest with votes, or TYPE0 if none)
        final_type = ClaimType.TYPE0_DESCRIPTIVE
        max_votes = 0
        for claim_type in reversed(list(ClaimType)):
            if type_votes[claim_type] > 0:
                final_type = claim_type
                max_votes = type_votes[claim_type]
                break

        # Calculate confidence in classification
        total_signals = sum(type_votes.values())
        if total_signals == 0:
            confidence = 0.5  # No signals = uncertain
        elif max_votes == total_signals:
            confidence = 0.95  # All signals agree
        else:
            # Mixed signals reduce confidence
            confidence = 0.6 + (0.3 * max_votes / total_signals)

        return ClassificationResult(
            claim_type=final_type,
            confidence=min(confidence, 0.99),
            signals=signals,
            warnings=warnings,
        )

    def detect_epistemic_pressure(self, text: str) -> list[EpistemicPressureWarning]:
        """Detect epistemic pressure language in text.

        Args:
            text: The claim text to analyze

        Returns:
            List of warnings
        """
        return self._pressure_detector.detect(text)

    def suggest_lower_type(
        self,
        claim_text: str,
        current_type: ClaimType,
    ) -> list[str]:
        """Suggest rewrites to lower the claim's epistemic level.

        Args:
            claim_text: The original claim text
            current_type: Current classification

        Returns:
            List of rewrite suggestions
        """
        suggestions: list[str] = []

        if current_type >= ClaimType.TYPE4_THEOLOGICAL:
            suggestions.append(
                "Add tradition attribution: 'In the Reformed tradition, this is read as...'"
            )
            suggestions.append(
                "Reframe as hypothesis: 'One theological interpretation suggests...'"
            )

        if current_type >= ClaimType.TYPE5_MORAL:
            suggestions.append(
                "Remove prescriptive language ('should', 'must') for TYPE4 or lower"
            )
            suggestions.append(
                "Specify the ethical framework: 'Within virtue ethics, this suggests...'"
            )

        if current_type == ClaimType.TYPE7_HARMONIZED:
            suggestions.append("Analyze passages independently before synthesizing")
            suggestions.append("Note tensions as well as harmonies across passages")

        # Epistemic pressure suggestions
        pressure_suggestions = self._pressure_detector.suggest_rewrites(claim_text)
        for original, category, suggestion in pressure_suggestions:
            suggestions.append(f"'{original}' -> {suggestion}")

        return suggestions

    def get_minimum_required_type(self, context: ClaimContext) -> ClaimType:
        """Get minimum claim type based on context.

        Some contexts require a minimum epistemic level:
        - Variants present -> TYPE2 minimum (grammar-dependent)
        - Cross-references -> TYPE7 minimum (harmonized)

        Args:
            context: The claim context

        Returns:
            Minimum required ClaimType
        """
        minimum = ClaimType.TYPE0_DESCRIPTIVE

        if context.has_variant_at_span and minimum < ClaimType.TYPE2_GRAMMATICAL:
            minimum = ClaimType.TYPE2_GRAMMATICAL

        if context.cross_references and minimum < ClaimType.TYPE7_HARMONIZED:
            minimum = ClaimType.TYPE7_HARMONIZED

        return minimum
