"""Analysis module for theological dependency tracking (v0.8.0).

Provides tools to analyze claims that depend on textual readings
and identify where uncertainty exists.
"""

from __future__ import annotations

from redletters.analysis.claims_analyzer import (
    ClaimsAnalyzer,
    ClaimAnalysis,
    Claim,
)

__all__ = [
    "ClaimsAnalyzer",
    "ClaimAnalysis",
    "Claim",
]
