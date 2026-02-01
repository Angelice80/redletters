"""Gate trigger detection.

Detects conditions that require acknowledgement gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redletters.claims.taxonomy import Claim
    from redletters.variants.store import VariantStore


class GateTrigger(Enum):
    """Types of conditions that trigger gates."""

    VARIANT_DEPENDENCY = "variant_dependency"
    """Claim depends on a textual variant reading."""

    GRAMMAR_AMBIGUITY = "grammar_ambiguity"
    """Claim depends on resolving grammatical ambiguity."""

    LEXICAL_SELECTION = "lexical_selection"
    """Claim depends on selecting from broad semantic range."""

    CLAIM_ESCALATION = "claim_escalation"
    """Claim type requires escalation to traceable mode."""

    EXPORT_WITH_VARIANTS = "export_with_variants"
    """Exporting content that depends on variant readings."""


@dataclass
class DetectionResult:
    """Result of gate trigger detection."""

    triggers: list[GateTrigger]
    variant_refs: list[str]
    grammar_refs: list[str]
    escalation_required: bool
    target_mode: str | None

    @property
    def gate_required(self) -> bool:
        """True if any gate triggers were detected."""
        return bool(self.triggers)

    def to_dict(self) -> dict:
        """Serialize for API response."""
        return {
            "gate_required": self.gate_required,
            "triggers": [t.value for t in self.triggers],
            "variant_refs": self.variant_refs,
            "grammar_refs": self.grammar_refs,
            "escalation_required": self.escalation_required,
            "target_mode": self.target_mode,
        }


class GateDetector:
    """Detects conditions requiring acknowledgement gates."""

    def __init__(self, variant_store: "VariantStore | None" = None):
        """Initialize detector with optional variant store."""
        self._variant_store = variant_store

    def detect_for_claim(
        self,
        claim: "Claim",
        current_mode: str = "readable",
    ) -> DetectionResult:
        """Detect gate triggers for a claim."""
        triggers: list[GateTrigger] = []
        variant_refs: list[str] = []
        grammar_refs: list[str] = []
        escalation_required = False
        target_mode: str | None = None

        # Check variant dependencies
        if claim.dependencies.variants:
            triggers.append(GateTrigger.VARIANT_DEPENDENCY)
            variant_refs = [v.variant_unit_ref for v in claim.dependencies.variants]

        # Check grammar dependencies
        if claim.dependencies.grammar:
            for g in claim.dependencies.grammar:
                if g.alternatives:
                    triggers.append(GateTrigger.GRAMMAR_AMBIGUITY)
                    grammar_refs.append(g.token_ref)
                    break

        # Check lexical selection
        if claim.dependencies.lexicon:
            for lex in claim.dependencies.lexicon:
                if len(lex.sense_range) > 3:
                    triggers.append(GateTrigger.LEXICAL_SELECTION)
                    break

        # Check escalation requirement
        if claim.requires_escalation and current_mode == "readable":
            triggers.append(GateTrigger.CLAIM_ESCALATION)
            escalation_required = True
            target_mode = "traceable"

        return DetectionResult(
            triggers=triggers,
            variant_refs=variant_refs,
            grammar_refs=grammar_refs,
            escalation_required=escalation_required,
            target_mode=target_mode,
        )

    def detect_for_ref(self, ref: str) -> DetectionResult:
        """Detect gate triggers for a scripture reference."""
        triggers: list[GateTrigger] = []
        variant_refs: list[str] = []

        if self._variant_store:
            variants = self._variant_store.get_variants_for_verse(ref)
            significant = [v for v in variants if v.is_significant]
            if significant:
                triggers.append(GateTrigger.VARIANT_DEPENDENCY)
                variant_refs = [v.ref for v in significant]

        return DetectionResult(
            triggers=triggers,
            variant_refs=variant_refs,
            grammar_refs=[],
            escalation_required=False,
            target_mode=None,
        )
