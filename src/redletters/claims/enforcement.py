"""Claim enforcement: Mode-based gating and dependency validation.

Implements ADR-009 enforcement rules:
- Readable mode: TYPE0-1 allowed, TYPE2-3 with markers, TYPE4 preview, TYPE5-7 forbidden
- Traceable mode: All types allowed with explicit dependencies
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from redletters.claims.taxonomy import Claim, ClaimType
from redletters.claims.epistemic_pressure import EpistemicPressureWarning


class EnforcementMode(Enum):
    """Enforcement mode determines what claims are allowed."""

    READABLE = "readable"
    """User-friendly mode with restricted claim types.

    Allowed:
    - TYPE0: Descriptive (fully allowed)
    - TYPE1: Lexical range (ranges only, no single selection)
    - TYPE2-3: Grammatical/Contextual (with hypothesis markers)
    - TYPE4: Theological (preview only: "traditions interpret...")

    Forbidden (must escalate to traceable):
    - TYPE5-7: Moral/Metaphysical/Harmonized
    """

    TRACEABLE = "traceable"
    """Full mode with all claim types allowed.

    All claim types permitted, but dependencies must be explicit.
    """


class DependencyRequirement(Enum):
    """Types of dependencies that may be required."""

    VARIANT = "variant"
    """Must declare which textual variant reading is assumed."""

    GRAMMAR = "grammar"
    """Must declare which grammatical parse is chosen."""

    LEXICON = "lexicon"
    """Must declare which lexical sense is selected."""

    CONTEXT = "context"
    """Must declare contextual/historical assumptions."""

    TRADITION = "tradition"
    """Must attribute to a theological tradition."""

    HERMENEUTIC = "hermeneutic"
    """Must specify hermeneutical framework for moral claims."""

    CROSS_REF = "cross_ref"
    """Must list cross-referenced passages for harmonized claims."""


@dataclass
class EnforcementResult:
    """Result of enforcement check."""

    allowed: bool
    reason: str
    required_escalation: ClaimType | None = None
    missing_dependencies: list[DependencyRequirement] = field(default_factory=list)
    epistemic_warnings: list[EpistemicPressureWarning] = field(default_factory=list)
    rewrite_suggestions: list[str] = field(default_factory=list)
    hypothesis_markers_required: bool = False

    @property
    def can_proceed(self) -> bool:
        """True if claim can proceed (possibly with modifications)."""
        return self.allowed or (
            self.hypothesis_markers_required
            and not self.missing_dependencies
            and self.required_escalation is None
        )


# Dependency requirements by claim type
DEPENDENCY_REQUIREMENTS: dict[ClaimType, list[DependencyRequirement]] = {
    ClaimType.TYPE0_DESCRIPTIVE: [],
    ClaimType.TYPE1_LEXICAL_RANGE: [],
    ClaimType.TYPE2_GRAMMATICAL: [DependencyRequirement.GRAMMAR],
    ClaimType.TYPE3_CONTEXTUAL: [DependencyRequirement.CONTEXT],
    ClaimType.TYPE4_THEOLOGICAL: [DependencyRequirement.TRADITION],
    ClaimType.TYPE5_MORAL: [
        DependencyRequirement.TRADITION,
        DependencyRequirement.HERMENEUTIC,
    ],
    ClaimType.TYPE6_METAPHYSICAL: [
        DependencyRequirement.TRADITION,
        DependencyRequirement.CONTEXT,
    ],
    ClaimType.TYPE7_HARMONIZED: [DependencyRequirement.CROSS_REF],
}


class EnforcementEngine:
    """Enforces claim rules based on mode.

    The enforcement engine checks whether a claim is permitted in the
    current mode and whether its dependencies are complete.

    Usage:
        engine = EnforcementEngine()
        result = engine.check_claim(claim, mode="readable")
        if not result.allowed:
            print(result.reason)
            print(result.rewrite_suggestions)
    """

    def __init__(self):
        """Initialize enforcement engine."""
        from redletters.claims.epistemic_pressure import EpistemicPressureDetector

        self._pressure_detector = EpistemicPressureDetector()

    def check_claim(
        self,
        claim: Claim,
        mode: Literal["readable", "traceable"] | EnforcementMode,
    ) -> EnforcementResult:
        """Check if claim is permitted in the given mode.

        Args:
            claim: The claim to check
            mode: "readable" or "traceable" mode

        Returns:
            EnforcementResult with allowed status and details
        """
        if isinstance(mode, str):
            mode = EnforcementMode(mode)

        # Check epistemic pressure language
        warnings = self._pressure_detector.detect(claim.content)
        blocking_warnings = [w for w in warnings if w.severity == "block"]

        # Readable mode enforcement
        if mode == EnforcementMode.READABLE:
            return self._check_readable_mode(claim, warnings, blocking_warnings)

        # Traceable mode enforcement
        return self._check_traceable_mode(claim, warnings)

    def _check_readable_mode(
        self,
        claim: Claim,
        warnings: list[EpistemicPressureWarning],
        blocking_warnings: list[EpistemicPressureWarning],
    ) -> EnforcementResult:
        """Check claim against readable mode rules."""
        claim_type = claim.claim_type

        # TYPE5-7: Forbidden in readable mode
        if claim_type >= ClaimType.TYPE5_MORAL:
            return EnforcementResult(
                allowed=False,
                reason=f"{claim_type.label} claims require Traceable mode",
                required_escalation=claim_type,
                epistemic_warnings=warnings,
                rewrite_suggestions=[
                    f"Switch to Traceable mode to make {claim_type.label} claims",
                    f"Rewrite as {ClaimType.TYPE4_THEOLOGICAL.label} (preview: 'traditions interpret...')",
                ],
            )

        # TYPE4: Preview only in readable mode
        if claim_type == ClaimType.TYPE4_THEOLOGICAL:
            if not self._has_tradition_framing(claim.content):
                return EnforcementResult(
                    allowed=False,
                    reason="Theological claims in Readable mode require tradition attribution",
                    rewrite_suggestions=[
                        "Reframe as: 'In [tradition], this is interpreted as...'",
                        "Add: 'Historically, this has been read as...'",
                        "Switch to Traceable mode for full theological claims",
                    ],
                    epistemic_warnings=warnings,
                )

        # TYPE2-3: Require hypothesis markers
        if claim_type in (ClaimType.TYPE2_GRAMMATICAL, ClaimType.TYPE3_CONTEXTUAL):
            if not self._has_hypothesis_markers(claim.content):
                return EnforcementResult(
                    allowed=True,  # Allowed but with requirement
                    reason="Grammatical/Contextual claims should use hypothesis markers",
                    hypothesis_markers_required=True,
                    rewrite_suggestions=[
                        "Add uncertainty: 'likely', 'probably', 'suggests'",
                        "Frame as hypothesis: 'One interpretation is...'",
                        "Acknowledge alternatives: 'This could also be...'",
                    ],
                    epistemic_warnings=warnings,
                )

        # TYPE1: No single gloss selection
        if claim_type == ClaimType.TYPE1_LEXICAL_RANGE:
            if self._has_single_gloss_selection(claim.content):
                return EnforcementResult(
                    allowed=False,
                    reason="Lexical range claims cannot select a single meaning in Readable mode",
                    rewrite_suggestions=[
                        "Present the range: 'This word can mean X, Y, or Z'",
                        "Avoid: 'This word means X' without alternatives",
                        "Switch to Traceable mode to select a specific sense",
                    ],
                    epistemic_warnings=warnings,
                )

        # TYPE0: Always allowed
        if claim_type == ClaimType.TYPE0_DESCRIPTIVE:
            pass  # No restrictions

        # Check epistemic pressure language
        if blocking_warnings and claim_type >= ClaimType.TYPE2_GRAMMATICAL:
            return EnforcementResult(
                allowed=False,
                reason="Epistemic pressure language not allowed in Readable mode",
                epistemic_warnings=warnings,
                rewrite_suggestions=[w.suggestion for w in blocking_warnings],
            )

        return EnforcementResult(
            allowed=True,
            reason="Claim permitted in Readable mode",
            epistemic_warnings=warnings,
        )

    def _check_traceable_mode(
        self,
        claim: Claim,
        warnings: list[EpistemicPressureWarning],
    ) -> EnforcementResult:
        """Check claim against traceable mode rules."""
        # All types allowed, but dependencies must be present
        missing = self._check_dependencies(claim)

        if missing:
            return EnforcementResult(
                allowed=False,
                reason=f"{claim.claim_type.label} claims require explicit dependencies",
                missing_dependencies=missing,
                epistemic_warnings=warnings,
                rewrite_suggestions=[f"Add {req.value} dependency" for req in missing],
            )

        return EnforcementResult(
            allowed=True,
            reason="Claim permitted in Traceable mode",
            epistemic_warnings=warnings,
        )

    def _check_dependencies(self, claim: Claim) -> list[DependencyRequirement]:
        """Check if required dependencies are present."""
        required = DEPENDENCY_REQUIREMENTS.get(claim.claim_type, [])
        missing: list[DependencyRequirement] = []

        for req in required:
            if req == DependencyRequirement.VARIANT:
                if not claim.dependencies.variants:
                    missing.append(req)
            elif req == DependencyRequirement.GRAMMAR:
                if not claim.dependencies.grammar:
                    missing.append(req)
            elif req == DependencyRequirement.LEXICON:
                if not claim.dependencies.lexicon:
                    missing.append(req)
            elif req == DependencyRequirement.CONTEXT:
                if not claim.dependencies.context:
                    missing.append(req)
            elif req == DependencyRequirement.TRADITION:
                # Check if tradition is attributed in content or dependencies
                if not (
                    claim.dependencies.context
                    or self._has_tradition_framing(claim.content)
                ):
                    missing.append(req)
            elif req == DependencyRequirement.HERMENEUTIC:
                # Check for hermeneutical framework
                if not self._has_hermeneutic_framing(claim.content):
                    missing.append(req)
            elif req == DependencyRequirement.CROSS_REF:
                # Harmonized claims need cross-references
                # Check content for references or explicit cross-ref dependencies
                if not self._has_cross_references(claim.content):
                    missing.append(req)

        return missing

    def _has_tradition_framing(self, text: str) -> bool:
        """Check if text attributes to a tradition."""
        import re

        patterns = [
            r"\bin (the )?(reformed|catholic|orthodox|lutheran|calvinist|baptist|evangelical) (tradition|reading|interpretation)\b",
            r"\bhistorically,?\s+(this|the)\b",
            r"\b(church fathers|patristic|medieval|reformation) (interpret|read|understood)\b",
            r"\btraditions? interpret\b",
            r"\baccording to\b",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_hypothesis_markers(self, text: str) -> bool:
        """Check if text uses appropriate uncertainty markers."""
        import re

        patterns = [
            r"\b(likely|probably|possibly|perhaps|may|might|could)\b",
            r"\b(suggests?|indicates?|implies?)\b",
            r"\bone (interpretation|reading|possibility)\b",
            r"\b(it seems|appears to|seems to)\b",
            r"\b(hypothesis|hypothetically|tentatively)\b",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_single_gloss_selection(self, text: str) -> bool:
        """Check if text selects a single gloss definitively."""
        import re

        # Patterns that indicate single selection
        patterns = [
            r"\bthis word means\b",
            r"\bthe meaning is\b",
            r"\bshould be translated as\b",
            r"\bthe correct (translation|meaning|sense) is\b",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_hermeneutic_framing(self, text: str) -> bool:
        """Check if text specifies hermeneutical framework."""
        import re

        patterns = [
            r"\b(hermeneutic|hermeneutical|interpretive framework)\b",
            r"\b(virtue ethics|deontological|consequentialist)\b",
            r"\bapplying (the|this) (principle|command) (to|in) (today|modern|our)\b",
            r"\bthe (cultural|temporal) (gap|distance|bridge)\b",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_cross_references(self, text: str) -> bool:
        """Check if text includes cross-references."""
        import re

        patterns = [
            r"\b(romans|galatians|ephesians|philippians|colossians|matthew|mark|luke|john|acts|hebrews|james|peter|revelation)\s+\d+:\d+",
            r"\bcf\.\s+",
            r"\bsee also\b",
            r"\bcompare\b",
            r"\bwhen read (with|alongside)\b",
        ]
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def get_dependency_requirements(
        self, claim_type: ClaimType
    ) -> list[DependencyRequirement]:
        """Get required dependencies for a claim type.

        Args:
            claim_type: The claim type to check

        Returns:
            List of required dependency types
        """
        return list(DEPENDENCY_REQUIREMENTS.get(claim_type, []))

    def get_allowed_types(
        self, mode: Literal["readable", "traceable"] | EnforcementMode
    ) -> dict[ClaimType, str]:
        """Get allowed claim types for a mode with restrictions.

        Args:
            mode: The enforcement mode

        Returns:
            Dict mapping ClaimType to restriction description
        """
        if isinstance(mode, str):
            mode = EnforcementMode(mode)

        if mode == EnforcementMode.TRACEABLE:
            return {t: "Allowed with dependencies" for t in ClaimType}

        return {
            ClaimType.TYPE0_DESCRIPTIVE: "Fully allowed",
            ClaimType.TYPE1_LEXICAL_RANGE: "Ranges only (no single selection)",
            ClaimType.TYPE2_GRAMMATICAL: "Requires hypothesis markers",
            ClaimType.TYPE3_CONTEXTUAL: "Requires hypothesis markers",
            ClaimType.TYPE4_THEOLOGICAL: "Preview only (tradition attribution required)",
            ClaimType.TYPE5_MORAL: "Forbidden (escalate to Traceable)",
            ClaimType.TYPE6_METAPHYSICAL: "Forbidden (escalate to Traceable)",
            ClaimType.TYPE7_HARMONIZED: "Forbidden (escalate to Traceable)",
        }
