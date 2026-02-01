"""API route definitions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Annotated, Literal
from pydantic import BaseModel, Field

from redletters.config import Settings
from redletters.db.connection import get_connection
from redletters.engine.query import parse_reference, get_tokens_for_reference
from redletters.engine.generator import CandidateGenerator
from redletters.engine.ranker import RenderingRanker
from redletters.api.models import (
    QueryResponseModel,
    SpanModel,
    HealthModel,
    ParsedRefModel,
)

router = APIRouter()
settings = Settings()


@router.get("/health", response_model=HealthModel)
async def health_check():
    """Health check endpoint."""
    db_connected = False
    try:
        conn = get_connection(settings.db_path)
        conn.execute("SELECT 1")
        conn.close()
        db_connected = True
    except Exception:
        pass

    return HealthModel(
        status="ok" if db_connected else "degraded",
        version="0.1.0",
        db_connected=db_connected,
    )


@router.get("/query", response_model=QueryResponseModel)
async def query_reference(
    ref: Annotated[str, Query(description="Scripture reference (e.g., 'Matthew 3:2')")],
    style: Annotated[str | None, Query(description="Filter by rendering style")] = None,
):
    """
    Query a scripture reference and get candidate renderings.

    Returns 3-5 candidate renderings with full interpretive receipts.
    """
    conn = get_connection(settings.db_path)

    try:
        parsed_ref = parse_reference(ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tokens = get_tokens_for_reference(conn, parsed_ref)

    if not tokens:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No tokens found for {ref}")

    generator = CandidateGenerator(conn)
    ranker = RenderingRanker(conn)

    candidates = generator.generate_all(tokens)
    ranked = ranker.rank(candidates, tokens)

    if style:
        ranked = [r for r in ranked if r["style"] == style]

    greek_text = " ".join(t["surface"] for t in tokens)

    conn.close()

    return QueryResponseModel(
        reference=ref,
        parsed_ref=ParsedRefModel(
            book=parsed_ref.book, chapter=parsed_ref.chapter, verse=parsed_ref.verse
        ),
        greek_text=greek_text,
        token_count=len(tokens),
        renderings=ranked,
    )


@router.get("/spans", response_model=list[SpanModel])
async def list_spans():
    """List all red-letter speech spans in the database."""
    conn = get_connection(settings.db_path)

    cursor = conn.execute(
        """
        SELECT book, chapter, verse_start, verse_end, speaker, confidence, source
        FROM speech_spans
        ORDER BY book, chapter, verse_start
    """
    )

    spans = []
    for row in cursor:
        spans.append(
            SpanModel(
                book=row["book"],
                chapter=row["chapter"],
                verse_start=row["verse_start"],
                verse_end=row["verse_end"],
                speaker=row["speaker"],
                confidence=row["confidence"],
                source=row["source"],
            )
        )

    conn.close()
    return spans


@router.get("/tokens")
async def get_tokens(ref: Annotated[str, Query(description="Scripture reference")]):
    """Get raw token data for a reference (for debugging)."""
    conn = get_connection(settings.db_path)

    try:
        parsed_ref = parse_reference(ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    tokens = get_tokens_for_reference(conn, parsed_ref)
    conn.close()

    return {"reference": ref, "tokens": tokens}


# Pydantic models for translate endpoint


class TranslateRequestModel(BaseModel):
    """Request body for translate endpoint.

    Accepts human references ("John 1:18", "Jn 1:18-19") or verse_ids ("John.1.18").
    """

    reference: str | None = Field(
        None, description="Scripture reference (e.g., 'John 1:18', 'John 1:18-19')"
    )
    verse_id: str | None = Field(
        None, description="Verse ID for backward compatibility (e.g., 'John.1.18')"
    )
    mode: Literal["readable", "traceable"] = Field(
        default="readable", description="Enforcement mode"
    )
    session_id: str = Field(
        default="api-default", description="Session ID for tracking"
    )
    translator: Literal["fake", "literal", "fluent"] = Field(
        default="literal", description="Translator type to use"
    )
    options: dict = Field(default_factory=dict, description="Additional options")


class AcknowledgeRequestModel(BaseModel):
    """Request body for acknowledge endpoint."""

    session_id: str = Field(..., description="Session ID")
    variant_ref: str = Field(..., description="Variant reference (e.g., 'John.1.18')")
    reading_index: int = Field(..., description="Index of chosen reading")


@router.post("/translate")
async def translate_reference(request: TranslateRequestModel):
    """
    Translate a scripture passage with receipt-grade output.

    Accepts either:
    - {"reference": "John 1:18-19"} - human reference (preferred)
    - {"verse_id": "John.1.18"} - verse_id format (backward compatible)

    Returns either:
    - GateResponse: If a gate requires acknowledgement (variant or escalation)
    - TranslateResponse: Full translation with claims, confidence, provenance

    The response includes:
    - SBLGNT text (canonical spine, always marked as default)
    - Variants side-by-side (never buried in footnotes)
    - Claims with type classification and enforcement results
    - Layered confidence (textual/grammatical/lexical/interpretive)
    - Explicit dependencies for traceable mode
    - Full provenance and receipts
    - Per-verse blocks for multi-verse passages
    - session_id for session tracking
    """
    from redletters.pipeline import (
        translate_passage,
        GateResponsePayload,
        get_translator,
    )

    # Determine reference to use (prefer reference, fall back to verse_id)
    ref = request.reference or request.verse_id
    if not ref:
        raise HTTPException(
            status_code=400,
            detail="Either 'reference' or 'verse_id' must be provided",
        )

    conn = get_connection(settings.db_path)

    # Get the appropriate translator
    translator_instance = get_translator(
        translator_type=request.translator,
        source_id="api",
        source_license="",
    )

    try:
        result = translate_passage(
            conn=conn,
            reference=ref,
            mode=request.mode,
            session_id=request.session_id,
            options=request.options,
            translator=translator_instance,
        )
    except ValueError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    conn.close()

    # Add session_id and translator_type to result before returning
    if isinstance(result, GateResponsePayload):
        result.session_id = request.session_id
        return result.to_dict()
    else:
        result.session_id = request.session_id
        result.translator_type = request.translator
        return result.to_dict()


@router.post("/acknowledge")
async def acknowledge_reading(request: AcknowledgeRequestModel):
    """
    Acknowledge a variant reading for a session.

    This must be called before translate will proceed past a variant gate.
    The acknowledgement is persisted for the session.
    """
    from redletters.pipeline.orchestrator import acknowledge_variant

    conn = get_connection(settings.db_path)

    try:
        acknowledge_variant(
            conn=conn,
            session_id=request.session_id,
            variant_ref=request.variant_ref,
            reading_index=request.reading_index,
            context="api-acknowledge",
        )
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))

    conn.close()

    return {
        "success": True,
        "session_id": request.session_id,
        "variant_ref": request.variant_ref,
        "reading_index": request.reading_index,
    }
