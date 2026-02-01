"""Claims module: Claim taxonomy, classification, and enforcement.

This module implements ADR-009 (Claim Taxonomy Enforcement Rules).

The claim taxonomy distinguishes epistemic levels:
- TYPE0: Descriptive (observable facts about text)
- TYPE1: Lexical range (semantic field without selection)
- TYPE2: Grammatical (parse-based interpretation)
- TYPE3: Contextual (historical/literary inference)
- TYPE4: Theological (doctrinal interpretation)
- TYPE5: Moral (ethical universalization)
- TYPE6: Metaphysical (claims about reality)
- TYPE7: Harmonized (cross-passage synthesis)

Enforcement rules restrict claim types by mode:
- Readable mode: TYPE0-1 allowed, TYPE2-3 with markers, TYPE4 preview only, TYPE5-7 forbidden
- Traceable mode: All types allowed with explicit dependencies
"""

from redletters.claims.taxonomy import (
    ClaimType,
    Claim,
    ClaimDependency,
    VariantDependency,
    GrammarDependency,
    LexiconDependency,
    ContextDependency,
    TextSpan,
)
from redletters.claims.classifier import ClaimClassifier, ClassificationResult
from redletters.claims.enforcement import (
    EnforcementEngine,
    EnforcementResult,
    EnforcementMode,
)
from redletters.claims.epistemic_pressure import (
    EpistemicPressureDetector,
    EpistemicPressureWarning,
)

__all__ = [
    # Taxonomy
    "ClaimType",
    "Claim",
    "ClaimDependency",
    "VariantDependency",
    "GrammarDependency",
    "LexiconDependency",
    "ContextDependency",
    "TextSpan",
    # Classifier
    "ClaimClassifier",
    "ClassificationResult",
    # Enforcement
    "EnforcementEngine",
    "EnforcementResult",
    "EnforcementMode",
    # Epistemic Pressure
    "EpistemicPressureDetector",
    "EpistemicPressureWarning",
]
