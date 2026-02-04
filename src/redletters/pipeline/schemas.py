"""Response schemas for translate_passage vertical slice.

Stable schema for CLI and GUI consumption. Forward-compatible design
supports future additions without breaking clients.

Sprint 10: Added optional ledger field for traceable mode output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass


class ResponseType(Enum):
    """Type of response from translate_passage."""

    GATE = "gate"
    """A gate was triggered and requires acknowledgement."""

    TRANSLATION = "translation"
    """Full translation response with claims and confidence."""


@dataclass
class TranslateRequest:
    """Request to translate a passage."""

    reference: str
    """Scripture reference (e.g., 'John 1:18')."""

    mode: Literal["readable", "traceable"]
    """Enforcement mode."""

    session_id: str
    """Session identifier for acknowledgement tracking."""

    options: dict = field(default_factory=dict)
    """Additional options (style, flags, etc.)."""


@dataclass
class GateOption:
    """An option presented in a gate."""

    id: str
    label: str
    description: str
    is_default: bool = False
    reading_index: int | None = None


@dataclass
class VariantDisplay:
    """Variant for side-by-side display."""

    ref: str
    """Reference (e.g., 'John.1.18')."""

    position: int
    """Word position in verse."""

    sblgnt_reading: str
    """SBLGNT (spine) reading text."""

    sblgnt_witnesses: str
    """Witness summary for SBLGNT reading."""

    alternate_readings: list[dict]
    """Non-SBLGNT readings with witness info."""

    significance: str
    """trivial/minor/significant/major."""

    requires_acknowledgement: bool
    """True if user must acknowledge."""

    acknowledged: bool = False
    """True if already acknowledged in session."""


@dataclass
class RequiredAck:
    """A single acknowledgement required to proceed."""

    verse_id: str
    """Verse ID (e.g., 'John.1.18')."""

    variant_ref: str
    """Variant reference for acknowledgement."""

    reading_index: int | None = None
    """Default reading index (SBLGNT)."""

    significance: str = ""
    """Significance level (significant/major)."""

    message: str = ""
    """Description of what needs acknowledgement."""


@dataclass
class GateResponsePayload:
    """Response when a gate is triggered.

    The caller must handle this gate before proceeding.
    For multi-verse passages, may contain multiple required acks.
    """

    response_type: Literal["gate"] = "gate"

    gate_id: str = ""
    """Unique gate identifier."""

    gate_type: str = ""
    """variant/grammar/escalation/export."""

    title: str = ""
    """Human-readable title."""

    message: str = ""
    """Explanation of why gate triggered."""

    prompt: str = ""
    """Instructions for user."""

    options: list[GateOption] = field(default_factory=list)
    """Available choices."""

    required_dependencies: list[str] = field(default_factory=list)
    """Dependencies that must be declared if proceeding."""

    variants_side_by_side: list[VariantDisplay] = field(default_factory=list)
    """Variant readings for display (if variant gate)."""

    escalation_target_mode: str | None = None
    """Target mode if escalation required."""

    reference: str = ""
    """Scripture reference that triggered gate."""

    # Multi-verse support
    required_acks: list[RequiredAck] = field(default_factory=list)
    """All acknowledgements required for multi-verse passages."""

    verse_ids: list[str] = field(default_factory=list)
    """All verse IDs in the passage request."""

    session_id: str = ""
    """Session ID for tracking acknowledgements."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "response_type": self.response_type,
            "gate_id": self.gate_id,
            "gate_type": self.gate_type,
            "title": self.title,
            "message": self.message,
            "prompt": self.prompt,
            "options": [
                {
                    "id": o.id,
                    "label": o.label,
                    "description": o.description,
                    "is_default": o.is_default,
                }
                for o in self.options
            ],
            "required_dependencies": self.required_dependencies,
            "variants_side_by_side": [
                {
                    "ref": v.ref,
                    "position": v.position,
                    "sblgnt_reading": v.sblgnt_reading,
                    "sblgnt_witnesses": v.sblgnt_witnesses,
                    "alternate_readings": v.alternate_readings,
                    "significance": v.significance,
                    "requires_acknowledgement": v.requires_acknowledgement,
                    "acknowledged": v.acknowledged,
                }
                for v in self.variants_side_by_side
            ],
            "escalation_target_mode": self.escalation_target_mode,
            "reference": self.reference,
            "required_acks": [
                {
                    "verse_id": a.verse_id,
                    "variant_ref": a.variant_ref,
                    "reading_index": a.reading_index,
                    "significance": a.significance,
                    "message": a.message,
                }
                for a in self.required_acks
            ],
            "verse_ids": self.verse_ids,
            "session_id": self.session_id,
        }


@dataclass
class DependencyInfo:
    """A single dependency record."""

    dep_type: str
    """variant/grammar/lexicon/context/tradition/hermeneutic/cross_ref."""

    ref: str
    """Reference to the dependency source."""

    choice: str
    """What was chosen/assumed."""

    rationale: str = ""
    """Why this choice was made."""

    alternatives: list[str] = field(default_factory=list)
    """Other possibilities not taken."""


@dataclass
class ClaimResult:
    """A classified claim with enforcement result."""

    content: str
    """The claim text."""

    claim_type: int
    """TYPE0-7 numeric value."""

    claim_type_label: str
    """Human-readable type (Descriptive, Lexical Range, etc.)."""

    classification_confidence: float
    """Classifier confidence in type assignment."""

    signals: list[str]
    """Patterns that influenced classification."""

    enforcement_allowed: bool
    """True if allowed in current mode."""

    enforcement_reason: str
    """Why allowed/blocked."""

    warnings: list[str]
    """Epistemic pressure warnings."""

    rewrite_suggestions: list[str]
    """Suggestions for improving claim."""

    dependencies: list[DependencyInfo]
    """Explicit dependencies for this claim."""

    hypothesis_markers_required: bool = False
    """True if claim needs uncertainty markers."""


@dataclass
class LayerScore:
    """Score for a single confidence layer."""

    score: float
    rationale: str
    details: dict = field(default_factory=dict)


@dataclass
class ConfidenceResult:
    """Layered confidence scoring result."""

    composite: float
    """Weighted composite score."""

    weakest_layer: str
    """Name of lowest-scoring layer."""

    textual: LayerScore = field(default_factory=lambda: LayerScore(1.0, ""))
    """Layer 1: Manuscript witness agreement."""

    grammatical: LayerScore = field(default_factory=lambda: LayerScore(1.0, ""))
    """Layer 2: Parse ambiguity."""

    lexical: LayerScore = field(default_factory=lambda: LayerScore(1.0, ""))
    """Layer 3: Lexical sense selection."""

    interpretive: LayerScore = field(default_factory=lambda: LayerScore(1.0, ""))
    """Layer 4: Inference distance."""

    weights: dict[str, float] = field(
        default_factory=lambda: {
            "textual": 0.30,
            "grammatical": 0.25,
            "lexical": 0.25,
            "interpretive": 0.20,
        }
    )

    explanations: list[str] = field(default_factory=list)
    """Human-readable explanations."""

    improvement_suggestions: list[str] = field(default_factory=list)
    """Suggestions for improving confidence."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "composite": round(self.composite, 3),
            "weakest_layer": self.weakest_layer,
            "layers": {
                "textual": {
                    "score": round(self.textual.score, 3),
                    "rationale": self.textual.rationale,
                },
                "grammatical": {
                    "score": round(self.grammatical.score, 3),
                    "rationale": self.grammatical.rationale,
                },
                "lexical": {
                    "score": round(self.lexical.score, 3),
                    "rationale": self.lexical.rationale,
                },
                "interpretive": {
                    "score": round(self.interpretive.score, 3),
                    "rationale": self.interpretive.rationale,
                },
            },
            "weights": self.weights,
            "explanations": self.explanations,
            "improvement_suggestions": self.improvement_suggestions,
        }


@dataclass
class SensePackProvenance:
    """Citation-grade provenance for a sense pack (v0.6.0)."""

    pack_id: str
    """Pack identifier."""

    source_id: str
    """Stable citation key (e.g., 'LSJ', 'BDAG')."""

    source_title: str = ""
    """Full bibliographic title."""

    edition: str = ""
    """Edition string."""

    publisher: str = ""
    """Publisher name."""

    year: int | None = None
    """Publication year."""

    license: str = ""
    """License identifier."""

    license_url: str = ""
    """Link to license text."""


@dataclass
class ProvenanceInfo:
    """Provenance tracking for the translation.

    v0.6.0: Added sense_packs_used for citation-grade lexicon provenance.
    """

    spine_source: str = "SBLGNT"
    """Canonical text source (always SBLGNT)."""

    spine_marker: str = "default"
    """SBLGNT is marked as default reading."""

    sources_used: list[str] = field(default_factory=list)
    """All sources consulted (lexicons, etc.)."""

    variant_unit_ids: list[str] = field(default_factory=list)
    """IDs of variant units at this passage."""

    witness_summaries: list[dict] = field(default_factory=list)
    """Summary of manuscript witnesses."""

    # v0.6.0: Sense pack citation metadata
    sense_packs_used: list[SensePackProvenance] = field(default_factory=list)
    """Sense packs used with citation-grade metadata."""


@dataclass
class ReceiptSummary:
    """Summary of checks and gates processed."""

    checks_run: list[str] = field(default_factory=list)
    """Names of validation checks run."""

    gates_satisfied: list[str] = field(default_factory=list)
    """Gate IDs that were acknowledged."""

    gates_pending: list[str] = field(default_factory=list)
    """Gate IDs still requiring acknowledgement."""

    enforcement_results: list[dict] = field(default_factory=list)
    """Per-claim enforcement summaries."""

    timestamp: str = ""
    """ISO timestamp of processing."""


@dataclass
class VerseBlock:
    """Translation block for a single verse in a multi-verse passage."""

    verse_id: str
    """Canonical verse ID (e.g., 'John.1.18')."""

    sblgnt_text: str = ""
    """Greek text from SBLGNT (spine) for this verse."""

    translation_text: str = ""
    """Generated translation for this verse."""

    variants: list[VariantDisplay] = field(default_factory=list)
    """Variants at this verse."""

    tokens: list[dict] = field(default_factory=list)
    """Token-level data for this verse."""

    confidence: ConfidenceResult | None = None
    """Per-verse confidence scoring."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "verse_id": self.verse_id,
            "sblgnt_text": self.sblgnt_text,
            "translation_text": self.translation_text,
            "variants": [
                {
                    "ref": v.ref,
                    "position": v.position,
                    "sblgnt_reading": v.sblgnt_reading,
                    "sblgnt_witnesses": v.sblgnt_witnesses,
                    "alternate_readings": v.alternate_readings,
                    "significance": v.significance,
                    "requires_acknowledgement": v.requires_acknowledgement,
                    "acknowledged": v.acknowledged,
                }
                for v in self.variants
            ],
            "tokens": self.tokens,
            "confidence": self.confidence.to_dict() if self.confidence else None,
        }


@dataclass
class TranslateResponse:
    """Full translation response with claims and confidence.

    This is returned when all gates are satisfied and translation completes.
    For multi-verse passages, includes per-verse blocks.
    """

    response_type: Literal["translation"] = "translation"

    reference: str = ""
    """Scripture reference (human-readable, e.g., 'John 1:18-19')."""

    normalized_ref: str = ""
    """Normalized reference (e.g., 'John 1:18-19')."""

    verse_ids: list[str] = field(default_factory=list)
    """All verse IDs in the passage."""

    mode: str = "readable"
    """Enforcement mode used."""

    # Text content (combined for single-verse backward compat)
    sblgnt_text: str = ""
    """Greek text from SBLGNT (spine) - combined for all verses."""

    translation_text: str = ""
    """Generated translation - combined for all verses."""

    # Per-verse blocks (for multi-verse passages)
    verse_blocks: list[VerseBlock] = field(default_factory=list)
    """Per-verse translation blocks."""

    # Variants (always present, may be empty) - combined view
    variants: list[VariantDisplay] = field(default_factory=list)
    """All variants at this passage (side-by-side display)."""

    # Claims with enforcement
    claims: list[ClaimResult] = field(default_factory=list)
    """Classified and enforced claims."""

    # Layered confidence (composite for passage)
    confidence: ConfidenceResult | None = None
    """Four-layer confidence scoring (passage-level composite)."""

    # Provenance
    provenance: ProvenanceInfo = field(default_factory=ProvenanceInfo)
    """Source and witness tracking."""

    # Receipts
    receipts: ReceiptSummary = field(default_factory=ReceiptSummary)
    """Processing audit trail."""

    # Token-level data (for advanced display) - combined
    tokens: list[dict] = field(default_factory=list)
    """Token-level morphological data (all verses combined)."""

    # Session tracking
    session_id: str = ""
    """Session ID for tracking."""

    # Translator info
    translator_type: str = ""
    """Type of translator used (fake/literal/fluent/traceable)."""

    # Sprint 10: Traceable ledger (token-level evidence)
    ledger: list | None = None
    """Token-level ledger for traceable mode (list of VerseLedger).

    Populated only when mode='traceable' and translator_type='traceable'.
    Contains per-verse token analysis with gloss provenance and confidence.
    None in readable mode.
    """

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "response_type": self.response_type,
            "reference": self.reference,
            "normalized_ref": self.normalized_ref,
            "verse_ids": self.verse_ids,
            "mode": self.mode,
            "sblgnt_text": self.sblgnt_text,
            "translation_text": self.translation_text,
            "verse_blocks": [vb.to_dict() for vb in self.verse_blocks],
            "variants": [
                {
                    "ref": v.ref,
                    "position": v.position,
                    "sblgnt_reading": v.sblgnt_reading,
                    "sblgnt_witnesses": v.sblgnt_witnesses,
                    "alternate_readings": v.alternate_readings,
                    "significance": v.significance,
                    "requires_acknowledgement": v.requires_acknowledgement,
                    "acknowledged": v.acknowledged,
                }
                for v in self.variants
            ],
            "claims": [
                {
                    "content": c.content,
                    "claim_type": c.claim_type,
                    "claim_type_label": c.claim_type_label,
                    "classification_confidence": round(c.classification_confidence, 3),
                    "signals": c.signals,
                    "enforcement_allowed": c.enforcement_allowed,
                    "enforcement_reason": c.enforcement_reason,
                    "warnings": c.warnings,
                    "rewrite_suggestions": c.rewrite_suggestions,
                    "dependencies": [
                        {
                            "dep_type": d.dep_type,
                            "ref": d.ref,
                            "choice": d.choice,
                            "rationale": d.rationale,
                            "alternatives": d.alternatives,
                        }
                        for d in c.dependencies
                    ],
                    "hypothesis_markers_required": c.hypothesis_markers_required,
                }
                for c in self.claims
            ],
            "confidence": self.confidence.to_dict() if self.confidence else None,
            "provenance": {
                "spine_source": self.provenance.spine_source,
                "spine_marker": self.provenance.spine_marker,
                "sources_used": self.provenance.sources_used,
                "variant_unit_ids": self.provenance.variant_unit_ids,
                "witness_summaries": self.provenance.witness_summaries,
                # v0.6.0: Sense pack citation metadata
                "sense_packs_used": [
                    {
                        "pack_id": sp.pack_id,
                        "source_id": sp.source_id,
                        **(
                            {"source_title": sp.source_title} if sp.source_title else {}
                        ),
                        **({"edition": sp.edition} if sp.edition else {}),
                        **({"publisher": sp.publisher} if sp.publisher else {}),
                        **({"year": sp.year} if sp.year else {}),
                        **({"license": sp.license} if sp.license else {}),
                        **({"license_url": sp.license_url} if sp.license_url else {}),
                    }
                    for sp in self.provenance.sense_packs_used
                ],
            },
            "receipts": {
                "checks_run": self.receipts.checks_run,
                "gates_satisfied": self.receipts.gates_satisfied,
                "gates_pending": self.receipts.gates_pending,
                "enforcement_results": self.receipts.enforcement_results,
                "timestamp": self.receipts.timestamp,
            },
            "tokens": self.tokens,
            "session_id": self.session_id,
            "translator_type": self.translator_type,
            # Sprint 10: Traceable ledger
            "ledger": (
                [vl.to_dict() for vl in self.ledger]
                if self.ledger is not None
                else None
            ),
        }
