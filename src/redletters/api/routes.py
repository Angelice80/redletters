"""API route definitions."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

try:
    from typing import Annotated, Literal
except ImportError:
    from typing_extensions import Annotated, Literal
from pydantic import BaseModel, Field

# Keep typing imports in namespace for Pydantic annotation evaluation
__typing_imports__ = (List, Optional)

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
    SourceStatusModel,
    SourcesListResponse,
    SourcesStatusResponse,
    InstallSourceRequest,
    InstallSourceResponse,
    UninstallSourceRequest,
    UninstallSourceResponse,
    LicenseInfoResponse,
    # Sprint 7: Variant build and multi-ack models (B2, B3)
    VariantBuildRequest,
    AcknowledgeMultiRequest,
    AckItem,
)
from redletters.sources.catalog import SourcePack
from redletters.sources.installer import SourceInstaller

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
    style: Annotated[
        Optional[str], Query(description="Filter by rendering style")
    ] = None,
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


@router.get("/spans", response_model=List[SpanModel])
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

    reference: Optional[str] = Field(
        None, description="Scripture reference (e.g., 'John 1:18', 'John 1:18-19')"
    )
    verse_id: Optional[str] = Field(
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


# --- Source Management Endpoints (Sprint 6) ---


def _get_installer() -> SourceInstaller:
    """Get a SourceInstaller instance."""
    return SourceInstaller()


def _source_to_status_model(
    source: SourcePack, installer: SourceInstaller
) -> SourceStatusModel:
    """Convert SourcePack to SourceStatusModel with installation status."""
    installed = installer.get_installed(source.key)
    return SourceStatusModel(
        source_id=source.key,
        name=source.name,
        role=source.role.value,
        license=source.license,
        requires_eula=installer.requires_eula(source),
        installed=installed is not None,
        install_path=installed.install_path if installed else None,
        installed_at=installed.installed_at if installed else None,
        version=installed.version if installed else None,
        eula_accepted=installed.eula_accepted_at is not None if installed else None,
    )


@router.get("/sources")
async def list_sources():
    """
    List all configured sources from the catalog.

    Returns source metadata with installation status for each source.
    """

    installer = _get_installer()

    sources = [
        _source_to_status_model(source, installer)
        for source in installer.catalog.sources.values()
    ]

    return SourcesListResponse(
        data_root=str(installer.data_root),
        sources=sources,
    )


@router.get("/sources/status")
async def get_sources_status():
    """
    Get installation status for all sources.

    Returns detailed status including spine installation state.
    """

    installer = _get_installer()
    status = installer.status()

    # Find spine source
    spine = installer.catalog.spine
    spine_installed = False
    spine_source_id = None
    if spine:
        spine_source_id = spine.key
        spine_installed = installer.is_installed(spine.key)

    # Convert to status models
    sources_dict = {}
    for source_id, source_info in status["sources"].items():
        source = installer.catalog.get(source_id)
        if source:
            sources_dict[source_id] = _source_to_status_model(source, installer)

    return SourcesStatusResponse(
        data_root=status["data_root"],
        manifest_path=status["manifest_path"],
        spine_installed=spine_installed,
        spine_source_id=spine_source_id,
        sources=sources_dict,
    )


@router.post("/sources/install")
async def install_source(request: InstallSourceRequest):
    """
    Install a source from the catalog.

    For sources with EULA requirements, accept_eula must be True.
    Returns installation result with path on success or error details on failure.
    """

    installer = _get_installer()

    # Validate source exists
    source = installer.catalog.get(request.source_id)
    if source is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "source_not_found",
                "message": f"Source '{request.source_id}' not found in catalog",
            },
        )

    # Perform installation
    result = installer.install(
        source_id=request.source_id,
        accept_eula=request.accept_eula,
    )

    return InstallSourceResponse(
        success=result.success,
        source_id=result.source_id,
        message=result.message,
        install_path=result.install_path if result.success else None,
        eula_required=result.eula_required,
        error=result.error if not result.success else None,
    )


@router.post("/sources/uninstall")
async def uninstall_source(request: UninstallSourceRequest):
    """
    Uninstall an installed source.

    Removes the source files and updates the manifest.
    """

    installer = _get_installer()

    # Validate source exists in catalog
    source = installer.catalog.get(request.source_id)
    if source is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "source_not_found",
                "message": f"Source '{request.source_id}' not found in catalog",
            },
        )

    # Perform uninstallation
    result = installer.uninstall(source_id=request.source_id)

    if not result.success and result.error == "not_installed":
        raise HTTPException(
            status_code=400,
            detail={
                "code": "not_installed",
                "message": f"Source '{request.source_id}' is not installed",
            },
        )

    return UninstallSourceResponse(
        success=result.success,
        source_id=result.source_id,
        message=result.message,
        error=result.error if not result.success else None,
    )


@router.get("/sources/license")
async def get_license_info(
    source_id: Annotated[str, Query(description="Source ID to get license info for")],
):
    """
    Get license information for a source.

    Returns license details including EULA requirement status.
    Useful for displaying EULA modal in the GUI.
    """

    installer = _get_installer()

    # Validate source exists
    source = installer.catalog.get(source_id)
    if source is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "source_not_found",
                "message": f"Source '{source_id}' not found in catalog",
            },
        )

    # Generate EULA summary if required
    eula_summary = None
    if installer.requires_eula(source):
        eula_summary = (
            f"This source ({source.name}) is distributed under the {source.license} license. "
            "By installing, you acknowledge and accept the license terms."
        )

    return LicenseInfoResponse(
        source_id=source.key,
        name=source.name,
        license=source.license,
        license_url=source.license_url if source.license_url else None,
        requires_eula=installer.requires_eula(source),
        eula_summary=eula_summary,
        notes=source.notes if source.notes else None,
    )


# --- Sprint 7: Variant Build Endpoint (B2) ---


@router.post("/variants/build")
async def build_variants(request: VariantBuildRequest):
    """
    Build variants for a reference (book, chapter, or passage).

    Sprint 7: B2 - Bulk variant building.
    Sprint 9: B5 - Multi-pack aggregation with include_all_installed_sources.

    Compares comparative editions against SBLGNT spine to generate variants.
    With multi-pack support, identical readings from different packs are merged.
    """
    from redletters.variants.store import VariantStore
    from redletters.variants.builder import VariantBuilder
    from redletters.sources.pack_loader import PackLoader
    from redletters.pipeline.passage_ref import normalize_reference

    conn = get_connection(settings.db_path)

    try:
        # Initialize variant store
        variant_store = VariantStore(conn)
        variant_store.init_schema()

        # Get spine provider
        installer = _get_installer()
        spine_source = installer.catalog.spine
        if not spine_source or not installer.is_installed(spine_source.key):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "spine_not_installed",
                    "message": "Spine not installed",
                },
            )

        spine_installed = installer.get_installed(spine_source.key)
        from redletters.sources.spine import SBLGNTSpine

        spine = SBLGNTSpine(spine_installed.install_path, spine_source.key)

        # Initialize variant builder
        builder = VariantBuilder(spine, variant_store)

        # Sprint 9: B5 - Determine which packs to use
        packs_to_use: list[str] = []

        if request.source_pack_ids:
            # Explicit pack list takes precedence
            packs_to_use = request.source_pack_ids
        elif request.source_id:
            # Legacy single source_id (backward compat)
            packs_to_use = [request.source_id]
        elif request.include_all_installed_sources:
            # All installed comparative packs (Sprint 9 default)
            for source in installer.catalog.comparative_editions:
                if installer.is_installed(source.key):
                    packs_to_use.append(source.key)

        # Add editions from selected packs
        packs_loaded = 0
        for pack_id in packs_to_use:
            source = installer.catalog.get(pack_id)
            if not source:
                continue

            if not installer.is_installed(source.key):
                continue

            installed = installer.get_installed(source.key)
            if source.is_pack:
                # Load pack
                pack = PackLoader(installed.install_path)
                if pack.load():
                    # Create a simple spine-like provider from pack
                    from redletters.sources.spine import PackSpineAdapter

                    pack_spine = PackSpineAdapter(pack, source.key)
                    builder.add_edition(
                        edition_key=source.key,
                        edition_spine=pack_spine,
                        witness_siglum=source.witness_siglum or source.key,
                        date_range=source.date_range,
                        source_pack_id=source.key,
                    )
                    packs_loaded += 1

        # Parse reference and determine scope
        ref = request.reference
        scope = request.scope

        # Build based on scope
        if scope == "book":
            # Extract book name
            book = ref.split()[0] if " " in ref else ref.split(".")[0]
            result = builder.build_book(book)
        elif scope == "chapter":
            # Parse chapter ref like "John 1" or "John.1"
            parts = ref.replace(".", " ").split()
            book = parts[0]
            chapter = int(parts[1]) if len(parts) > 1 else 1
            result = builder.build_chapter(book, chapter)
        else:
            # Passage scope
            normalized, verse_ids = normalize_reference(ref)
            if len(verse_ids) == 1:
                result = builder.build_verse(verse_ids[0])
            else:
                result = builder.build_range(verse_ids[0], verse_ids[-1])

        conn.close()

        from redletters.api.models import VariantBuildResponse

        return VariantBuildResponse(
            success=len(result.errors) == 0,
            reference=ref,
            scope=scope,
            verses_processed=result.verses_processed,
            variants_created=result.variants_created,
            variants_updated=result.variants_updated,
            variants_unchanged=result.variants_unchanged,
            errors=result.errors,
            message=f"Built variants for {ref} using {packs_loaded} pack(s): "
            f"{result.variants_created} created, "
            f"{result.variants_updated} updated, {result.variants_unchanged} unchanged",
        )

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))


# --- Sprint 7: Extended Acknowledge Endpoint (B3) ---


@router.post("/acknowledge/multi")
async def acknowledge_readings_multi(request: AcknowledgeMultiRequest):
    """
    Acknowledge multiple variant readings at once (Sprint 7: B3).

    Supports both single ack (backward compatible) and batch acks.
    Records scope metadata for audit trail.
    """
    from redletters.pipeline.orchestrator import acknowledge_variant
    from redletters.gates.state import AcknowledgementStore

    conn = get_connection(settings.db_path)

    # Initialize store with scope support
    ack_store = AcknowledgementStore(conn)
    try:
        ack_store.init_schema()
    except Exception:
        pass

    acked = []
    errors = []

    try:
        # Collect acks to process
        to_ack = []

        # Single ack (backward compatible)
        if request.variant_ref is not None and request.reading_index is not None:
            to_ack.append(
                AckItem(
                    variant_ref=request.variant_ref,
                    reading_index=request.reading_index,
                )
            )

        # Multi-ack
        if request.acks:
            to_ack.extend(request.acks)

        # Process each ack
        for ack_item in to_ack:
            try:
                acknowledge_variant(
                    conn=conn,
                    session_id=request.session_id,
                    variant_ref=ack_item.variant_ref,
                    reading_index=ack_item.reading_index,
                    context=f"api-acknowledge-{request.scope}",
                )
                acked.append(ack_item.variant_ref)
            except Exception as e:
                errors.append(f"{ack_item.variant_ref}: {str(e)}")

        conn.close()

        return {
            "success": len(errors) == 0,
            "session_id": request.session_id,
            "acknowledged": acked,
            "count": len(acked),
            "scope": request.scope,
            "errors": errors,
        }

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))


# --- Sprint 8: Variant Dossier Endpoint (B4) ---


@router.get("/variants/dossier")
async def get_variant_dossier(
    reference: Annotated[
        str, Query(description="Scripture reference (e.g., 'John.1.18')")
    ],
    scope: Annotated[
        str, Query(description="Scope: 'verse', 'passage', 'chapter', or 'book'")
    ] = "verse",
    session_id: Annotated[
        Optional[str], Query(description="Session ID for ack state")
    ] = None,
):
    """
    Get a variant dossier for a reference (Sprint 8: B4).

    Returns a complete dossier with:
    - Spine reading info
    - All variants with witness support by type
    - Provenance (source packs)
    - Acknowledgement state
    - Gating requirements
    """
    from redletters.variants.store import VariantStore
    from redletters.variants.dossier import generate_dossier
    from redletters.gates.state import AcknowledgementStore

    conn = get_connection(settings.db_path)

    try:
        # Initialize stores
        variant_store = VariantStore(conn)

        # Get acknowledgement state for session
        ack_state: dict[str, int] = {}
        if session_id:
            try:
                ack_store = AcknowledgementStore(conn)
                ack_state = ack_store.get_session_acks(session_id)
            except Exception:
                pass  # Ack store may not be initialized

        # Generate dossier
        dossier = generate_dossier(
            variant_store=variant_store,
            reference=reference,
            scope=scope,
            ack_state=ack_state,
            session_id=session_id,
        )

        conn.close()

        # Return as dict (Pydantic will validate)
        return dossier.to_dict()

    except ValueError as e:
        conn.close()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
