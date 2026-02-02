"""Pydantic models for API."""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ReceiptModel(BaseModel):
    """Interpretive receipt for a single token."""

    surface: str = Field(..., description="Greek surface form")
    lemma: str = Field(..., description="Dictionary form")
    morph: dict = Field(..., description="Morphological constraints")
    chosen_sense_id: str = Field(..., description="Selected sense identifier")
    chosen_gloss: str = Field(..., description="English gloss used")
    sense_source: str = Field(..., description="Lexicon source")
    sense_weight: float = Field(..., description="Default sense weight")
    sense_domain: Optional[str] = Field(None, description="Semantic domain")
    rationale: str = Field(..., description="Explanation for choice")
    ambiguity_type: Optional[str] = Field(
        None, description="Type of ambiguity if present"
    )
    alternate_glosses: Optional[List[str]] = Field(
        None, description="Other possible glosses"
    )
    definition: Optional[str] = Field(None, description="Full definition")


class ScoreBreakdownModel(BaseModel):
    """Breakdown of how a score was calculated."""

    morph_fit: float
    sense_weight: float
    collocation_bonus: float
    uncommon_penalty: float
    weights_used: Dict[str, float]


class RenderingModel(BaseModel):
    """A single candidate rendering."""

    style: str = Field(..., description="Rendering style name")
    text: str = Field(..., description="Full rendered text")
    score: float = Field(..., description="Composite ranking score")
    score_breakdown: ScoreBreakdownModel = Field(
        ..., description="Score calculation details"
    )
    receipts: List[ReceiptModel] = Field(
        ..., description="Token-level interpretive receipts"
    )


class ParsedRefModel(BaseModel):
    """Parsed scripture reference."""

    book: str
    chapter: int
    verse: int


class QueryResponseModel(BaseModel):
    """Response for a query request."""

    reference: str = Field(..., description="Original reference string")
    parsed_ref: ParsedRefModel = Field(..., description="Parsed reference components")
    greek_text: str = Field(..., description="Greek text of the passage")
    token_count: int = Field(..., description="Number of tokens")
    renderings: List[RenderingModel] = Field(..., description="Candidate renderings")


class SpanModel(BaseModel):
    """A red-letter speech span."""

    book: str
    chapter: int
    verse_start: int
    verse_end: int
    speaker: str
    confidence: float
    source: Optional[str]


class HealthModel(BaseModel):
    """Health check response."""

    status: str
    version: str
    db_connected: bool


# --- Source Management Models (Sprint 6) ---


class SourceStatusModel(BaseModel):
    """Source with installation status."""

    source_id: str = Field(..., description="Unique source identifier")
    name: str = Field(..., description="Human-readable name")
    role: str = Field(..., description="Source role (canonical_spine, etc.)")
    license: str = Field(..., description="License identifier")
    requires_eula: bool = Field(..., description="True if EULA acceptance required")
    installed: bool = Field(..., description="True if source is installed")
    install_path: Optional[str] = Field(None, description="Path if installed")
    installed_at: Optional[str] = Field(
        None, description="ISO timestamp of installation"
    )
    version: Optional[str] = Field(None, description="Installed version")
    eula_accepted: Optional[bool] = Field(None, description="True if EULA was accepted")


class SourcesListResponse(BaseModel):
    """Response for GET /sources."""

    data_root: str = Field(..., description="Root directory for source data")
    sources: List[SourceStatusModel] = Field(..., description="List of all sources")


class SourcesStatusResponse(BaseModel):
    """Response for GET /sources/status."""

    data_root: str = Field(..., description="Root directory for source data")
    manifest_path: str = Field(..., description="Path to installed sources manifest")
    spine_installed: bool = Field(
        ..., description="True if canonical spine is installed"
    )
    spine_source_id: Optional[str] = Field(None, description="ID of spine source")
    sources: Dict[str, SourceStatusModel] = Field(
        ..., description="Status by source_id"
    )


class InstallSourceRequest(BaseModel):
    """Request body for POST /sources/install."""

    source_id: str = Field(..., description="Source ID to install")
    accept_eula: bool = Field(False, description="Accept EULA terms")


class InstallSourceResponse(BaseModel):
    """Response for POST /sources/install."""

    success: bool = Field(..., description="True if installation succeeded")
    source_id: str = Field(..., description="Source ID")
    message: str = Field(..., description="Status message")
    install_path: Optional[str] = Field(
        None, description="Installation path if successful"
    )
    eula_required: bool = Field(
        False, description="True if EULA acceptance is required"
    )
    error: Optional[str] = Field(None, description="Error code if failed")


class UninstallSourceRequest(BaseModel):
    """Request body for POST /sources/uninstall."""

    source_id: str = Field(..., description="Source ID to uninstall")


class UninstallSourceResponse(BaseModel):
    """Response for POST /sources/uninstall."""

    success: bool = Field(..., description="True if uninstallation succeeded")
    source_id: str = Field(..., description="Source ID")
    message: str = Field(..., description="Status message")
    error: Optional[str] = Field(None, description="Error code if failed")


class LicenseInfoResponse(BaseModel):
    """Response for GET /sources/license."""

    source_id: str = Field(..., description="Source ID")
    name: str = Field(..., description="Source name")
    license: str = Field(..., description="License identifier")
    license_url: Optional[str] = Field(None, description="URL to full license text")
    requires_eula: bool = Field(..., description="True if EULA acceptance required")
    eula_summary: Optional[str] = Field(None, description="Summary text for UI display")
    notes: Optional[str] = Field(None, description="Additional notes")


# --- Sprint 7: Variant Build Models ---


class VariantBuildRequest(BaseModel):
    """Request for POST /variants/build (Sprint 7: B2, Sprint 9: B5)."""

    reference: str = Field(..., description="Reference: book name, chapter, or passage")
    scope: str = Field(
        "passage",
        description="Scope: 'book', 'chapter', or 'passage'",
    )
    source_id: Optional[str] = Field(
        None, description="Specific comparative source to use (legacy)"
    )
    force: bool = Field(False, description="Force rebuild even if variants exist")
    # Sprint 9: B5 - Multi-pack aggregation
    include_all_installed_sources: bool = Field(
        True, description="Use all installed comparative packs (default: True)"
    )
    source_pack_ids: Optional[List[str]] = Field(
        None,
        description="Specific pack IDs to use (overrides include_all_installed_sources)",
    )


class VariantBuildResponse(BaseModel):
    """Response for POST /variants/build."""

    success: bool = Field(..., description="True if build completed")
    reference: str = Field(..., description="Reference that was built")
    scope: str = Field(..., description="Scope used")
    verses_processed: int = Field(..., description="Number of verses processed")
    variants_created: int = Field(..., description="New variants created")
    variants_updated: int = Field(..., description="Existing variants updated")
    variants_unchanged: int = Field(..., description="Variants unchanged")
    errors: List[str] = Field(
        default_factory=list, description="Any errors encountered"
    )
    message: str = Field(..., description="Summary message")


# --- Sprint 7: Multi-Ack Models (B3) ---


class AckItem(BaseModel):
    """Single acknowledgement item for batch acks."""

    variant_ref: str = Field(..., description="Variant reference")
    reading_index: int = Field(..., description="Index of chosen reading")


class AcknowledgeMultiRequest(BaseModel):
    """Extended request for POST /acknowledge with multi-ack support (Sprint 7: B3).

    Supports both single ack (backward compatible) and batch acks.
    """

    session_id: str = Field(..., description="Session ID")

    # Single ack (backward compatible)
    variant_ref: Optional[str] = Field(None, description="Variant reference (single)")
    reading_index: Optional[int] = Field(None, description="Reading index (single)")

    # Multi-ack
    acks: Optional[List[AckItem]] = Field(None, description="List of acks for batch")

    # Scope metadata
    scope: str = Field("verse", description="Scope: 'verse', 'passage', or 'book'")


# --- Sprint 8: Dossier Models (B4) ---


class WitnessInfoModel(BaseModel):
    """Info about a single witness."""

    siglum: str = Field(..., description="Witness siglum (e.g., 'P66', 'א', 'B')")
    type: str = Field(..., description="Witness type (papyrus, uncial, etc.)")
    century: Optional[int] = Field(None, description="Century of witness")


class WitnessSummaryModel(BaseModel):
    """Summary of witnesses grouped by type."""

    editions: List[str] = Field(default_factory=list, description="Edition witnesses")
    papyri: List[str] = Field(default_factory=list, description="Papyrus witnesses")
    uncials: List[str] = Field(default_factory=list, description="Uncial witnesses")
    minuscules: List[str] = Field(
        default_factory=list, description="Minuscule witnesses"
    )
    versions: List[str] = Field(default_factory=list, description="Version witnesses")
    fathers: List[str] = Field(
        default_factory=list, description="Church father witnesses"
    )


class DossierReadingModel(BaseModel):
    """A reading in the dossier."""

    index: int = Field(..., description="Reading index")
    text: str = Field(..., description="Greek text of this reading")
    is_spine: bool = Field(..., description="True if this is the SBLGNT reading")
    witnesses: List[WitnessInfoModel] = Field(..., description="Individual witnesses")
    witness_summary: WitnessSummaryModel = Field(..., description="Witnesses by type")
    source_packs: List[str] = Field(..., description="Source pack IDs")


class DossierReasonModel(BaseModel):
    """Reason classification for a variant."""

    code: str = Field(..., description="Reason code")
    summary: str = Field(..., description="Human-readable summary")
    detail: Optional[str] = Field(None, description="Additional detail")


class DossierAcknowledgementModel(BaseModel):
    """Acknowledgement state for a variant."""

    required: bool = Field(..., description="True if acknowledgement required")
    acknowledged: bool = Field(..., description="True if already acknowledged")
    acknowledged_reading: Optional[int] = Field(
        None, description="Index of acknowledged reading"
    )
    session_id: Optional[str] = Field(None, description="Session ID")


class DossierVariantModel(BaseModel):
    """A variant in the dossier."""

    ref: str = Field(..., description="Variant reference")
    position: int = Field(..., description="Word position in verse")
    classification: str = Field(..., description="Variant type")
    significance: str = Field(..., description="Significance level")
    gating_requirement: str = Field(
        ..., description="Gating requirement (none, requires_acknowledgement)"
    )
    reason: DossierReasonModel = Field(..., description="Reason for variant")
    readings: List[DossierReadingModel] = Field(..., description="All readings")
    acknowledgement: DossierAcknowledgementModel = Field(
        ..., description="Acknowledgement state"
    )


class DossierSpineModel(BaseModel):
    """Spine info in the dossier."""

    source_id: str = Field(..., description="Spine source ID")
    text: str = Field(..., description="Spine text")
    is_default: bool = Field(True, description="True if this is the default reading")


class DossierProvenanceModel(BaseModel):
    """Provenance info in the dossier."""

    spine_source: str = Field(..., description="Spine source ID")
    comparative_packs: List[str] = Field(..., description="Comparative pack IDs")
    build_timestamp: str = Field(..., description="ISO timestamp of build")


class DossierResponse(BaseModel):
    """Complete variant dossier response (Sprint 8: B4)."""

    reference: str = Field(..., description="Scripture reference")
    scope: str = Field(..., description="Scope used (verse, chapter, book)")
    generated_at: str = Field(..., description="ISO timestamp of generation")
    spine: DossierSpineModel = Field(..., description="Spine reading info")
    variants: List[DossierVariantModel] = Field(..., description="All variants")
    provenance: DossierProvenanceModel = Field(..., description="Provenance info")
    witness_density_note: Optional[str] = Field(
        None, description="Note about witness density"
    )
