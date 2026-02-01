# ADR-009: Claim Taxonomy Enforcement Rules

**Status**: Accepted
**Date**: 2026-01-30
**Deciders**: Project maintainers
**Depends on**: ADR-007 (canonical spine), ADR-008 (variant gating)

## Context

A forensic linguistics tool must distinguish between different **epistemic categories** of claims. The following failure modes are common in biblical interpretation tools:

1. **Category Collapse**: Treating lexical definitions as if they were theological conclusions
2. **Epistemic Laundering**: Presenting high-inference claims as if they were direct readings
3. **Unearned Certainty**: Using confident language ("clearly", "obviously") for disputed interpretations

The system must enforce a **claim taxonomy** that:
- Classifies claims by their epistemic status
- Restricts certain claim types to appropriate modes (readable vs. traceable)
- Detects and flags "epistemic pressure language"
- Requires explicit dependencies (what variants, grammar choices, or lexical selections a claim relies on)

## Decision

### Claim Type Taxonomy

```python
class ClaimType(Enum):
    """Ordered by epistemic distance from the text."""

    TYPE0_DESCRIPTIVE = 0
    # Observable facts about the text: "This word is a verb"
    # No interpretation required

    TYPE1_LEXICAL_RANGE = 1
    # Semantic field of a lemma: "βασιλεία can mean 'kingdom', 'reign', 'royal power'"
    # Bounded by lexicon entries; no single gloss selection

    TYPE2_GRAMMATICAL = 2
    # Interpretation based on morpho-syntax: "This genitive is subjective"
    # Requires choosing among grammatically valid parses

    TYPE3_CONTEXTUAL = 3
    # Inference from literary/historical context: "This refers to the Babylonian exile"
    # Requires assumptions about author intent, audience, background

    TYPE4_THEOLOGICAL = 4
    # Doctrinal interpretation: "This teaches the divinity of Christ"
    # Requires theological framework and tradition

    TYPE5_MORAL = 5
    # Ethical universalization: "This commands all Christians to..."
    # Requires hermeneutical bridge from ancient to modern

    TYPE6_METAPHYSICAL = 6
    # Claims about ultimate reality: "This proves the Trinity"
    # Maximum inference distance from text

    TYPE7_HARMONIZED = 7
    # Synthesis across multiple passages: "When read with Romans 8, this means..."
    # Requires assuming coherent authorial intent across corpus
```

### Enforcement Rules by Mode

| Claim Type | Readable Mode | Traceable Mode |
|------------|---------------|----------------|
| TYPE0 Descriptive | ✅ Allowed | ✅ Allowed |
| TYPE1 Lexical Range | ✅ Ranges only (no single selection) | ✅ Full with selection rationale |
| TYPE2 Grammatical | ⚠️ Hypothesis markers required | ✅ With parse justification |
| TYPE3 Contextual | ⚠️ Hypothesis markers required | ✅ With context citation |
| TYPE4 Theological | 👁️ Preview only ("traditions interpret...") | ✅ With tradition attribution |
| TYPE5 Moral | ❌ Forbidden → escalate | ✅ With hermeneutical bridge |
| TYPE6 Metaphysical | ❌ Forbidden → escalate | ✅ With full dependency chain |
| TYPE7 Harmonized | ❌ Forbidden → escalate | ✅ With cross-reference justification |

### Epistemic Pressure Language Detection

The following patterns trigger warnings or blocks:

```python
EPISTEMIC_PRESSURE_PATTERNS = [
    # Certainty markers (forbidden in readable mode for Type2+)
    r"\bclearly\b",
    r"\bobviously\b",
    r"\bplainly\b",
    r"\bundoubtedly\b",
    r"\bcertainly\b",
    r"\bself-evident\b",

    # False objectivity markers
    r"\bthe text says\b",          # Text doesn't "say"; it's interpreted
    r"\bthe Greek means\b",         # Greek has ranges, not singular meanings
    r"\bthe original meaning\b",    # Original meaning is reconstructed, not accessed

    # Suppressed agency
    r"\bit is clear that\b",
    r"\bwe can see that\b",
    r"\bthe passage teaches\b",
]
```

When detected:
- **Readable mode**: Block claim, show rewrite suggestions
- **Traceable mode**: Allow but flag with warning annotation

### Claim Dependencies

Every Type2+ claim must declare its dependencies:

```python
class Claim:
    claim_type: ClaimType
    text_span: TextSpan           # What portion of text this claim is about
    content: str                  # The claim statement
    confidence: float             # 0.0 to 1.0

    # Dependencies (what this claim relies on)
    variant_dependencies: list[VariantDependency]
    grammar_dependencies: list[GrammarDependency]
    lexicon_dependencies: list[LexiconDependency]
    context_dependencies: list[ContextDependency]

    # Traceability
    created_at: datetime
    mode: Literal["readable", "traceable"]
    acknowledgements: list[str]   # IDs of ack'd variants/choices

class VariantDependency:
    variant_unit_ref: str
    reading_chosen: int
    rationale: str

class GrammarDependency:
    token_ref: str
    parse_choice: str             # e.g., "subjective genitive"
    alternatives: list[str]       # e.g., ["objective genitive", "genitive of source"]
    rationale: str

class LexiconDependency:
    lemma: str
    sense_chosen: str
    sense_range: list[str]
    rationale: str
```

### Escalation Flow

When a claim requires escalation from readable to traceable mode:

```
┌─────────────────────────────────────────────────────────────────┐
│  ⬆️  CLAIM REQUIRES TRACEABLE MODE                              │
├─────────────────────────────────────────────────────────────────┤
│  Your claim is classified as: TYPE5_MORAL                       │
│                                                                 │
│  "This passage commands Christians to forgive unconditionally"  │
│                                                                 │
│  This claim type is not permitted in Readable mode because:     │
│  • Moral universalization requires hermeneutical assumptions    │
│  • The inference distance from text to claim is high            │
│  • Dependencies must be made explicit                           │
│                                                                 │
│  Options:                                                       │
│  [ ] Switch to Traceable Mode to make this claim                │
│  [ ] Rewrite as TYPE3 (contextual hypothesis)                   │
│  [ ] Cancel                                                     │
└─────────────────────────────────────────────────────────────────┘
```

## Consequences

### Positive

1. **Category Integrity**: Lexical ≠ grammatical ≠ theological claims stay distinct
2. **Honest Uncertainty**: High-inference claims cannot masquerade as low-inference
3. **Dependency Transparency**: Users see what choices underlie each claim
4. **Graduated Access**: Readable mode is safe; traceable mode is powerful but explicit

### Negative

1. **User Friction**: Claim classification may feel pedantic
2. **Subjectivity**: Borderline cases exist (is this Type3 or Type4?)
3. **Implementation Complexity**: NLP-based detection is imperfect

### Mitigations

- **User Override with Logging**: Users can override classification but it's logged
- **Conservative Defaults**: When uncertain, classify higher (safer)
- **Pattern Refinement**: Epistemic pressure patterns are configurable

## Implementation

### Classifier Module

```python
# src/redletters/claims/classifier.py

class ClaimClassifier:
    def classify(self, claim_text: str, context: ClaimContext) -> ClassificationResult:
        """
        Analyze claim text and context to determine claim type.

        Returns:
            ClassificationResult with:
            - claim_type: ClaimType enum value
            - confidence: float (classifier confidence)
            - signals: list of patterns/features that influenced classification
            - warnings: list of epistemic pressure detections
        """

    def detect_epistemic_pressure(self, text: str) -> list[EpistemicPressureWarning]:
        """Scan for certainty markers and false objectivity language."""

    def suggest_rewrite(self, claim: Claim, target_type: ClaimType) -> list[str]:
        """Suggest rewrites to lower the claim's epistemic level."""
```

### Enforcement Engine

```python
# src/redletters/claims/enforcement.py

class EnforcementEngine:
    def check_claim(self, claim: Claim, mode: Literal["readable", "traceable"]) -> EnforcementResult:
        """
        Check if claim is permitted in the given mode.

        Returns:
            EnforcementResult with:
            - allowed: bool
            - reason: str (if blocked)
            - required_escalation: ClaimType (if escalation needed)
            - missing_dependencies: list (if dependencies incomplete)
            - epistemic_warnings: list (pressure language found)
        """

    def get_dependency_requirements(self, claim_type: ClaimType) -> list[DependencyRequirement]:
        """Return what dependencies a claim type requires."""
```

## Alternatives Considered

### Alternative 1: No Claim Classification

**Rejected because**: Without classification, the system cannot enforce the readable/traceable distinction. All claims would be treated equivalently regardless of epistemic status.

### Alternative 2: Binary Classification (Fact/Opinion)

**Rejected because**: Too coarse. The difference between "this word is a verb" (fact), "this genitive is subjective" (grammar interpretation), and "this teaches the Trinity" (theological) cannot be captured in a binary.

### Alternative 3: User Self-Classification Only

**Rejected because**: Users tend to underestimate the epistemic level of their claims. Automated detection with user override provides guardrails while preserving autonomy.

## References

- EPISTEMIC-CONSTITUTION.md (project governing document)
- Vanhoozer, Kevin J. *Is There a Meaning in This Text?* Zondervan, 1998.
- Porter, Stanley E. "Linguistic Issues in New Testament Lexicography." In *Studies in the Greek New Testament*, 49-74. Peter Lang, 1996.
- ADR-002: Provenance-First Data Model (dependency tracking foundation)
