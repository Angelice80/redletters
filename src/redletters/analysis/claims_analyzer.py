"""Claims analyzer for reversible theology (v0.8.0).

Analyzes claims that depend on scripture references and reports
where textual uncertainty exists.

Usage:
    analyzer = ClaimsAnalyzer(conn, variant_store, confidence_scorer)
    results = analyzer.analyze_claims(claims)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from redletters.confidence.scoring import (
    CONFIDENCE_BUCKET_MEDIUM,
    bucket_confidence,
)
from redletters.export.apparatus import check_pending_gates
from redletters.variants.models import SignificanceLevel

if TYPE_CHECKING:
    from redletters.confidence.scoring import ConfidenceScorer
    from redletters.variants.store import VariantStore


@dataclass
class Claim:
    """A theological claim with dependencies on scripture references."""

    label: str
    """Unique identifier for the claim."""

    text: str
    """The claim content."""

    dependencies: list[str] = field(default_factory=list)
    """Scripture references this claim depends on (e.g., ['John.1.18', 'John.3.16'])."""


@dataclass
class DependencyAnalysis:
    """Analysis of a single dependency reference."""

    reference: str
    """Scripture reference (e.g., 'John.1.18')."""

    has_low_confidence_tokens: bool
    """Whether any tokens have confidence < 0.6."""

    low_confidence_count: int
    """Count of tokens with low confidence."""

    has_pending_gates: bool
    """Whether there are unacknowledged significant variants."""

    pending_gate_count: int
    """Count of pending gates."""

    has_significant_variants: bool
    """Whether significant/major variants exist for this reference."""

    significant_variant_count: int
    """Count of significant/major variants."""

    notes: list[str] = field(default_factory=list)
    """Descriptive notes about the dependency analysis."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "reference": self.reference,
            "has_low_confidence_tokens": self.has_low_confidence_tokens,
            "low_confidence_count": self.low_confidence_count,
            "has_pending_gates": self.has_pending_gates,
            "pending_gate_count": self.pending_gate_count,
            "has_significant_variants": self.has_significant_variants,
            "significant_variant_count": self.significant_variant_count,
            "notes": self.notes,
        }


@dataclass
class ClaimAnalysis:
    """Analysis result for a single claim."""

    label: str
    """Claim identifier."""

    text: str
    """The claim text."""

    dependencies_analyzed: int
    """Number of dependencies analyzed."""

    has_uncertainty: bool
    """Whether any dependency has uncertainty."""

    uncertainty_score: str
    """Overall uncertainty: 'high', 'medium', 'low', or 'none'."""

    dependency_analyses: list[DependencyAnalysis] = field(default_factory=list)
    """Analysis for each dependency."""

    summary_notes: list[str] = field(default_factory=list)
    """Summary notes about overall claim uncertainty."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "label": self.label,
            "text": self.text,
            "dependencies_analyzed": self.dependencies_analyzed,
            "has_uncertainty": self.has_uncertainty,
            "uncertainty_score": self.uncertainty_score,
            "dependency_analyses": [d.to_dict() for d in self.dependency_analyses],
            "summary_notes": self.summary_notes,
        }


class ClaimsAnalyzer:
    """Analyzer for theological claims depending on scripture references.

    Reports where textual uncertainty exists in the dependencies of
    theological claims, enabling "reversible theology" - the ability
    to reassess conclusions when textual evidence changes.

    Usage:
        analyzer = ClaimsAnalyzer(conn, variant_store)
        results = analyzer.analyze_claims(claims, session_id="my-session")
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        variant_store: VariantStore,
        confidence_scorer: ConfidenceScorer | None = None,
    ):
        """Initialize analyzer.

        Args:
            conn: Database connection
            variant_store: Variant store for querying variants
            confidence_scorer: Optional confidence scorer for token analysis
        """
        self._conn = conn
        self._variant_store = variant_store
        self._confidence_scorer = confidence_scorer

    def analyze_claim(
        self,
        claim: Claim,
        session_id: str = "default",
    ) -> ClaimAnalysis:
        """Analyze a single claim's dependencies for uncertainty.

        Args:
            claim: The claim to analyze
            session_id: Session ID for gate acknowledgement check

        Returns:
            ClaimAnalysis with uncertainty information
        """
        dependency_analyses = []
        total_low_conf = 0
        total_pending = 0
        total_significant = 0

        for ref in claim.dependencies:
            analysis = self._analyze_dependency(ref, session_id)
            dependency_analyses.append(analysis)

            if analysis.has_low_confidence_tokens:
                total_low_conf += analysis.low_confidence_count
            if analysis.has_pending_gates:
                total_pending += analysis.pending_gate_count
            if analysis.has_significant_variants:
                total_significant += analysis.significant_variant_count

        # Determine overall uncertainty
        has_uncertainty = (
            total_low_conf > 0 or total_pending > 0 or total_significant > 0
        )

        # Score uncertainty
        if total_pending > 0:
            uncertainty_score = "high"  # Unacknowledged gates = high uncertainty
        elif total_significant > 0:
            uncertainty_score = "medium"  # Has variants but acknowledged
        elif total_low_conf > 0:
            uncertainty_score = "low"  # Only low confidence tokens
        else:
            uncertainty_score = "none"

        # Build summary notes
        summary_notes = []
        if total_pending > 0:
            summary_notes.append(
                f"Claim has {total_pending} pending gate(s) requiring acknowledgement"
            )
        if total_significant > 0:
            summary_notes.append(
                f"Claim depends on {total_significant} significant variant(s)"
            )
        if total_low_conf > 0:
            summary_notes.append(f"Claim has {total_low_conf} low-confidence token(s)")
        if not has_uncertainty:
            summary_notes.append("No significant textual uncertainty detected")

        return ClaimAnalysis(
            label=claim.label,
            text=claim.text,
            dependencies_analyzed=len(claim.dependencies),
            has_uncertainty=has_uncertainty,
            uncertainty_score=uncertainty_score,
            dependency_analyses=dependency_analyses,
            summary_notes=summary_notes,
        )

    def _analyze_dependency(
        self,
        reference: str,
        session_id: str,
    ) -> DependencyAnalysis:
        """Analyze a single dependency reference.

        Args:
            reference: Scripture reference
            session_id: Session ID for gate check

        Returns:
            DependencyAnalysis for the reference
        """
        notes = []

        # Check for pending gates
        pending_gates = check_pending_gates(
            self._conn, reference, session_id, self._variant_store
        )
        has_pending = len(pending_gates) > 0

        # Check for significant variants (even if acknowledged)
        variants = self._variant_store.get_variants_for_verse(reference)
        significant_variants = [
            v
            for v in variants
            if v.significance
            in (SignificanceLevel.SIGNIFICANT, SignificanceLevel.MAJOR)
        ]
        has_significant = len(significant_variants) > 0

        # Check for low confidence tokens (if scorer available)
        low_conf_count = 0
        has_low_conf = False
        if self._confidence_scorer:
            low_conf_count = self._count_low_confidence_tokens(reference)
            has_low_conf = low_conf_count > 0

        # Build notes
        if has_pending:
            refs = [g.variant_ref for g in pending_gates]
            notes.append(f"Pending gates: {', '.join(refs)}")
        if has_significant:
            notes.append(f"{len(significant_variants)} significant variant(s) in scope")
        if has_low_conf:
            notes.append(
                f"{low_conf_count} token(s) with confidence < {CONFIDENCE_BUCKET_MEDIUM}"
            )

        return DependencyAnalysis(
            reference=reference,
            has_low_confidence_tokens=has_low_conf,
            low_confidence_count=low_conf_count,
            has_pending_gates=has_pending,
            pending_gate_count=len(pending_gates),
            has_significant_variants=has_significant,
            significant_variant_count=len(significant_variants),
            notes=notes,
        )

    def _count_low_confidence_tokens(self, reference: str) -> int:
        """Count tokens with low confidence in a verse.

        Returns count of tokens where composite confidence < 0.6.
        """
        if not self._confidence_scorer:
            return 0

        # Try to get confidence for the verse
        try:
            score = self._confidence_scorer.score_verse(reference)
            if score:
                # Check bucket - if medium or high, no low-confidence tokens
                bucket = bucket_confidence(score.composite)
                if bucket == "low":
                    return 1  # Simplified: count verse as 1 unit
            return 0
        except Exception:
            return 0

    def analyze_claims(
        self,
        claims: list[Claim],
        session_id: str = "default",
    ) -> list[ClaimAnalysis]:
        """Analyze multiple claims.

        Args:
            claims: List of claims to analyze
            session_id: Session ID for gate checks

        Returns:
            List of ClaimAnalysis results
        """
        return [self.analyze_claim(claim, session_id) for claim in claims]

    def analyze_from_dict(
        self,
        data: dict,
        session_id: str = "default",
    ) -> list[ClaimAnalysis]:
        """Analyze claims from a dictionary structure.

        Expected format:
        {
            "claims": [
                {"label": "id", "text": "claim content", "dependencies": ["John.1.18"]}
            ]
        }

        Args:
            data: Dictionary with claims
            session_id: Session ID for gate checks

        Returns:
            List of ClaimAnalysis results
        """
        claims = []
        for item in data.get("claims", []):
            claim = Claim(
                label=item.get("label", ""),
                text=item.get("text", ""),
                dependencies=item.get("dependencies", []),
            )
            claims.append(claim)

        return self.analyze_claims(claims, session_id)
