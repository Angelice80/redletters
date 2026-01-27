"""API route definitions."""

from fastapi import APIRouter, HTTPException, Query
from typing import Annotated

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
