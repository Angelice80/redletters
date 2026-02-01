# ADR-010: Explainable Layered Confidence Scoring

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Project maintainers
**Depends on**: ADR-007 (canonical spine), ADR-008 (variants), ADR-009 (claims)

## Context

Confidence scores in NLP and translation systems are often:

1. **Opaque**: A single number (0.87) with no explanation of components
2. **Misleading**: High confidence in the model ≠ high confidence in the interpretation
3. **Uncomparable**: Scores from different subsystems on different scales

For forensic linguistics, confidence must be:

- **Decomposed**: Show which layer contributes what uncertainty
- **Explainable**: Each component has a human-readable rationale
- **Auditable**: The inputs to confidence calculation are traceable

## Decision

### Four-Layer Confidence Model

Confidence is calculated as four independent components, then aggregated:

```python
@dataclass
class LayeredConfidence:
    """Confidence decomposed into traceable components."""

    textual: TextualConfidence      # Manuscript/variant agreement
    grammatical: GrammarConfidence  # Parse ambiguity level
    lexical: LexicalConfidence      # Sense range breadth
    interpretive: InterpretiveConfidence  # Inference distance

    @property
    def composite(self) -> float:
        """Weighted aggregate. Always show components alongside."""
        return (
            self.textual.score * 0.30 +
            self.grammatical.score * 0.25 +
            self.lexical.score * 0.25 +
            self.interpretive.score * 0.20
        )
```

### Layer 1: Textual Confidence

Measures agreement among manuscript witnesses for the text being interpreted.

```python
@dataclass
class TextualConfidence:
    score: float  # 0.0 to 1.0

    # Inputs (for explainability)
    variant_exists: bool
    witness_agreement: float      # % of witnesses supporting chosen reading
    earliest_witness_century: int
    papyri_support: bool
    primary_uncial_support: list[str]  # e.g., ["א", "B", "A"]

    # Explanation
    rationale: str  # e.g., "Strong support from P66, P75, א, B (2nd-4th century)"

    @classmethod
    def calculate(cls, ref: str, reading_index: int, variant_data: VariantUnit) -> "TextualConfidence":
        """
        Calculate textual confidence based on:
        - Number and age of witnesses
        - Papyri support (highest weight)
        - Agreement among primary uncials
        - Geographic distribution
        """
```

**Scoring Heuristic**:
| Condition | Score Contribution |
|-----------|-------------------|
| No variant at this position | +0.40 |
| Papyri support (P66, P75, etc.) | +0.25 |
| Primary uncials agree (א, B, A) | +0.20 |
| >80% witness agreement | +0.15 |
| Reading is SBLGNT default | +0.10 |

### Layer 2: Grammatical Confidence

Measures ambiguity in morphological parsing and syntactic analysis.

```python
@dataclass
class GrammarConfidence:
    score: float  # 0.0 to 1.0

    # Inputs
    parse_ambiguity_count: int    # How many valid parses exist
    chosen_parse: str             # e.g., "genitive.subjective"
    alternative_parses: list[str]
    syntax_ambiguity: bool        # Clause structure unclear

    # Explanation
    rationale: str  # e.g., "Genitive could be subjective or objective; context suggests subjective"

    @classmethod
    def calculate(cls, token_ref: str, morphology: MorphologyData) -> "GrammarConfidence":
        """
        Calculate grammatical confidence based on:
        - Number of valid morphological parses
        - Distinctiveness of chosen parse
        - Syntactic role clarity
        """
```

**Scoring Heuristic**:
| Condition | Score |
|-----------|-------|
| Single valid parse, no ambiguity | 1.0 |
| 2 parses, one clearly preferred | 0.8 |
| 2-3 parses, contextually disambiguated | 0.6 |
| Multiple parses, disputed | 0.4 |
| Syntactically ambiguous construction | 0.2 |

### Layer 3: Lexical Confidence

Measures breadth of semantic range and certainty of sense selection.

```python
@dataclass
class LexicalConfidence:
    score: float  # 0.0 to 1.0

    # Inputs
    lemma: str
    sense_count: int              # How many senses in lexicon
    sense_range_breadth: float    # Semantic distance between senses
    chosen_sense: str
    sense_attestation: int        # Frequency in corpus
    collocational_support: bool   # Does context support this sense?

    # Explanation
    rationale: str  # e.g., "λόγος has 12 senses; 'word/message' strongly supported by κηρύσσω collocation"

    @classmethod
    def calculate(cls, lemma: str, chosen_sense: str, context: TokenContext) -> "LexicalConfidence":
        """
        Calculate lexical confidence based on:
        - Number of senses (more = less confident)
        - Semantic breadth of range
        - Collocational evidence
        - Corpus frequency of sense
        """
```

**Scoring Heuristic**:
| Condition | Score |
|-----------|-------|
| Single sense in all lexicons | 1.0 |
| 2-3 senses, one dominant (>70% usage) | 0.85 |
| Multiple senses, collocationally supported | 0.7 |
| Multiple senses, context-dependent | 0.5 |
| Broad semantic range, disputed selection | 0.3 |
| Hapax or rare word | 0.2 |

### Layer 4: Interpretive Confidence

Measures inference distance from text to claim. Directly tied to ClaimType.

```python
@dataclass
class InterpretiveConfidence:
    score: float  # 0.0 to 1.0

    # Inputs
    claim_type: ClaimType
    inference_steps: int          # How many reasoning steps from text
    assumption_count: int         # Unstated assumptions required
    tradition_dependency: bool    # Does claim require tradition?
    cross_reference_count: int    # How many other passages invoked

    # Explanation
    rationale: str  # e.g., "Type4 theological claim requires Nicene framework assumption"

    @classmethod
    def calculate(cls, claim: Claim) -> "InterpretiveConfidence":
        """
        Calculate interpretive confidence based on:
        - Claim type (higher type = lower base confidence)
        - Number of inference steps
        - Assumption transparency
        - Dependency chain length
        """
```

**Scoring by Claim Type**:
| Claim Type | Base Score | Adjustments |
|------------|------------|-------------|
| TYPE0 Descriptive | 1.0 | None |
| TYPE1 Lexical Range | 0.9 | -0.1 if range not shown |
| TYPE2 Grammatical | 0.75 | -0.15 if alternatives not shown |
| TYPE3 Contextual | 0.6 | -0.1 per unstated assumption |
| TYPE4 Theological | 0.45 | -0.1 if tradition not attributed |
| TYPE5 Moral | 0.3 | -0.1 if bridge not explicit |
| TYPE6 Metaphysical | 0.2 | -0.1 per inference step |
| TYPE7 Harmonized | 0.25 | -0.05 per cross-reference |

## Aggregation and Display

### Composite Score Calculation

```python
def calculate_composite(self) -> float:
    """
    Weighted average with traceable weights.

    Weights reflect epistemic priority:
    - Textual: 30% (what does the text say?)
    - Grammatical: 25% (how is it structured?)
    - Lexical: 25% (what do the words mean?)
    - Interpretive: 20% (what does it imply?)
    """
    return (
        self.textual.score * 0.30 +
        self.grammatical.score * 0.25 +
        self.lexical.score * 0.25 +
        self.interpretive.score * 0.20
    )
```

### Display Format

Confidence is **never shown as a single number alone**. Always show components:

```
┌─────────────────────────────────────────────────────────────────┐
│  Confidence: 0.68                                               │
├─────────────────────────────────────────────────────────────────┤
│  📜 Textual:      0.95  Strong P66/P75/א/B support              │
│  📐 Grammatical:  0.60  Genitive ambiguity (subjective chosen)  │
│  📖 Lexical:      0.70  3 senses; collocation supports "word"   │
│  🔍 Interpretive: 0.45  Type4 claim, Nicene framework assumed   │
├─────────────────────────────────────────────────────────────────┤
│  [View full rationale]                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

1. **Transparency**: Users see why confidence is high or low
2. **Actionable**: Low scores indicate where more work is needed
3. **Honest Uncertainty**: High textual + low interpretive = "text is clear, interpretation is not"
4. **Comparable**: Same scale across all layers

### Negative

1. **Complexity**: Four numbers instead of one
2. **Heuristic Weights**: The 30/25/25/20 split is somewhat arbitrary
3. **Calibration**: Scores need empirical calibration to match human intuition

### Mitigations

- **Progressive Disclosure**: Show composite first, components on expand
- **Configurable Weights**: Allow research mode to adjust weights
- **Feedback Loop**: Log user corrections to calibrate over time

## Implementation

```python
# src/redletters/confidence/scoring.py

class ConfidenceCalculator:
    def calculate(
        self,
        ref: str,
        claim: Optional[Claim] = None
    ) -> LayeredConfidence:
        """
        Calculate layered confidence for a text reference and optional claim.

        If no claim provided, interpretive layer is neutral (1.0).
        """

    def explain(self, confidence: LayeredConfidence) -> ConfidenceExplanation:
        """Generate human-readable explanation of all components."""

    def compare(
        self,
        conf_a: LayeredConfidence,
        conf_b: LayeredConfidence
    ) -> ConfidenceComparison:
        """Compare two confidence scores, highlighting differences."""
```

## Alternatives Considered

### Alternative 1: Single Confidence Score

**Rejected because**: Opaque. A score of 0.65 doesn't tell the user whether the problem is textual (manuscript disagreement) or interpretive (high inference).

### Alternative 2: Binary Certain/Uncertain

**Rejected because**: Too coarse. Most interesting cases are in the middle, and users need to know *where* the uncertainty lies.

### Alternative 3: Unbounded Scores (Log-Odds, etc.)

**Rejected because**: Hard for non-technical users to interpret. 0-1 scale is intuitive.

## References

- Tversky, Amos, and Daniel Kahneman. "Judgment under Uncertainty: Heuristics and Biases." *Science* 185, no. 4157 (1974): 1124-1131.
- Pearl, Judea. *Probabilistic Reasoning in Intelligent Systems*. Morgan Kaufmann, 1988.
- ADR-001: Architecture (scoring foundation)
- ADR-009: Claim Taxonomy (interpretive layer basis)
