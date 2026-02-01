"""Pydantic models for API."""

from __future__ import annotations

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
    sense_domain: str | None = Field(None, description="Semantic domain")
    rationale: str = Field(..., description="Explanation for choice")
    ambiguity_type: str | None = Field(None, description="Type of ambiguity if present")
    alternate_glosses: list[str] | None = Field(
        None, description="Other possible glosses"
    )
    definition: str | None = Field(None, description="Full definition")


class ScoreBreakdownModel(BaseModel):
    """Breakdown of how a score was calculated."""

    morph_fit: float
    sense_weight: float
    collocation_bonus: float
    uncommon_penalty: float
    weights_used: dict[str, float]


class RenderingModel(BaseModel):
    """A single candidate rendering."""

    style: str = Field(..., description="Rendering style name")
    text: str = Field(..., description="Full rendered text")
    score: float = Field(..., description="Composite ranking score")
    score_breakdown: ScoreBreakdownModel = Field(
        ..., description="Score calculation details"
    )
    receipts: list[ReceiptModel] = Field(
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
    renderings: list[RenderingModel] = Field(..., description="Candidate renderings")


class SpanModel(BaseModel):
    """A red-letter speech span."""

    book: str
    chapter: int
    verse_start: int
    verse_end: int
    speaker: str
    confidence: float
    source: str | None


class HealthModel(BaseModel):
    """Health check response."""

    status: str
    version: str
    db_connected: bool
