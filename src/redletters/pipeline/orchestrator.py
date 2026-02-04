"""Orchestration pipeline for translate_passage.

Wires together all subsystems to provide the vertical slice:
1. Parse reference
2. Fetch SBLGNT spine text (via Source Pack or database)
3. Fetch variants (build on-demand if needed)
4. Detect gates (variants, escalation)
5. Check acknowledgements
6. Run translator
7. Classify and enforce claims
8. Compute layered confidence
9. Return GateResponse or TranslateResponse

Sprint 2 additions:
- Source Pack spine provider integration
- On-demand variant building from comparative editions
- Fallback to database tokens for backward compatibility
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Literal

from redletters.engine.query import get_tokens_for_reference
from redletters.pipeline.passage_ref import (
    normalize_reference,
    PassageRefError,
)
from redletters.variants.store import VariantStore
from redletters.variants.models import VariantUnit
from redletters.gates.state import AcknowledgementStore, AcknowledgementState

from redletters.claims.taxonomy import (
    Claim,
    ClaimType,
    TextSpan,
    ClaimDependency,
    VariantDependency,
    GrammarDependency,
    LexiconDependency,
    ContextDependency,
)
from redletters.claims.classifier import ClaimClassifier, ClaimContext
from redletters.claims.enforcement import EnforcementEngine
from redletters.claims.epistemic_pressure import EpistemicPressureDetector
from redletters.confidence.scoring import (
    ConfidenceCalculator,
    TextualConfidence,
    GrammaticalConfidence,
    LexicalConfidence,
)
from redletters.pipeline.schemas import (
    TranslateResponse,
    GateResponsePayload,
    GateOption,
    VariantDisplay,
    ClaimResult,
    DependencyInfo,
    ConfidenceResult,
    LayerScore,
    ProvenanceInfo,
    ReceiptSummary,
    RequiredAck,
    VerseBlock,
)
from redletters.pipeline.translator import (
    Translator,
    FakeTranslator,
    TranslationContext,
)


# ============================================================================
# Spine data retrieval (Sprint 2: Source Pack integration)
# ============================================================================


def _get_spine_data(
    conn: sqlite3.Connection,
    canonical_ref: str,
    parsed_ref,
    options: dict,
) -> tuple[str, list[dict]]:
    """Get spine text and tokens for a verse.

    Tries Source Pack spine provider first, falls back to database.

    Args:
        conn: Database connection
        canonical_ref: Verse ID in "Book.Chapter.Verse" format
        parsed_ref: Parsed scripture reference
        options: Options dict (may contain 'spine_provider')

    Returns:
        Tuple of (sblgnt_text, tokens)

    Raises:
        ValueError: If no spine data available
    """
    # Check for Source Pack spine provider in options
    spine_provider = options.get("spine_provider")

    if spine_provider is not None:
        # Use Source Pack spine
        verse = spine_provider.get_verse_text(canonical_ref)
        if verse:
            tokens = spine_provider.get_verse_tokens(canonical_ref)
            # Convert to dict format expected by pipeline
            token_dicts = []
            for i, tok in enumerate(tokens):
                token_dicts.append(
                    {
                        "id": i + 1,
                        "book": parsed_ref.book,
                        "chapter": parsed_ref.chapter,
                        "verse": parsed_ref.verse,
                        "position": tok.get("position", i + 1),
                        "surface": tok.get("surface_text", tok.get("word", "")),
                        "lemma": tok.get("lemma", ""),
                        "morph": tok.get("parse_code", ""),
                        "is_red_letter": False,
                    }
                )
            return verse.text, token_dicts

    # Fall back to database tokens
    tokens = get_tokens_for_reference(conn, parsed_ref)
    if tokens:
        sblgnt_text = " ".join(t["surface"] for t in tokens)
        return sblgnt_text, tokens

    # If spine provider exists but verse not found, raise specific error
    if spine_provider is not None:
        raise ValueError(f"Verse not found in spine: {canonical_ref}")

    raise ValueError(f"No tokens found for {canonical_ref}")


def _ensure_variants(
    variant_store: VariantStore,
    canonical_ref: str,
    options: dict,
) -> list[VariantUnit]:
    """Ensure variants exist for a verse, building on-demand if needed.

    Args:
        variant_store: Variant store
        canonical_ref: Verse ID
        options: Options dict (may contain 'variant_builder')

    Returns:
        List of VariantUnit objects
    """
    # Check for existing variants
    variants = variant_store.get_variants_for_verse(canonical_ref)
    if variants:
        return variants

    # Check for variant builder in options (for on-demand building)
    variant_builder = options.get("variant_builder")
    if variant_builder is not None:
        # Build variants on-demand
        variant_builder.build_verse(canonical_ref)
        variants = variant_store.get_variants_for_verse(canonical_ref)

    return variants


def _parse_passage_reference(reference: str) -> tuple[str, list[str]]:
    """Parse a reference into normalized form and verse_ids.

    Handles both human references ("John 1:18-19") and verse_ids ("John.1.18").

    Args:
        reference: Human reference or verse_id

    Returns:
        Tuple of (normalized_reference, verse_ids)

    Raises:
        ValueError: If parsing fails
    """
    try:
        return normalize_reference(reference)
    except PassageRefError as e:
        raise ValueError(str(e))


def translate_passage(
    conn: sqlite3.Connection,
    reference: str,
    mode: Literal["readable", "traceable"],
    session_id: str,
    options: dict | None = None,
    translator: Translator | None = None,
) -> GateResponsePayload | TranslateResponse:
    """Orchestrate translation of a scripture passage.

    This is the single entrypoint for both CLI and GUI.
    Supports both single verses and multi-verse passages.

    Args:
        conn: Database connection
        reference: Scripture reference (e.g., "John 1:18", "Jn 1:18-19")
        mode: "readable" or "traceable"
        session_id: Session ID for acknowledgement tracking
        options: Additional options
        translator: Translator implementation (defaults to FakeTranslator)

    Returns:
        GateResponsePayload if any gate requires acknowledgement
        TranslateResponse if translation completes successfully

    Raises:
        ValueError: If reference cannot be parsed or no tokens found
    """
    options = options or {}
    translator = translator or FakeTranslator(
        scenario=options.get("scenario", "default")
    )

    # 1. Parse reference using passage parser (handles human refs and verse_ids)
    try:
        normalized_ref, verse_ids = _parse_passage_reference(reference)
    except ValueError as e:
        raise ValueError(f"Invalid reference '{reference}': {e}")

    if not verse_ids:
        raise ValueError(f"No verse IDs found for reference: {reference}")

    # 2. Initialize stores
    variant_store = VariantStore(conn)
    ack_store = AcknowledgementStore(conn)

    # Ensure schemas exist
    try:
        variant_store.init_schema()
    except Exception:
        pass  # Schema may already exist

    try:
        ack_store.init_schema()
    except Exception:
        pass  # Schema may already exist

    # 3. Load acknowledgement state
    ack_state = ack_store.load_session_state(session_id)

    # 4. Collect data for all verses
    verse_data: list[dict] = []  # Per-verse spine/token data
    all_variants: list[VariantUnit] = []  # All variants across passage

    for verse_id in verse_ids:
        # Parse verse_id to get components for spine lookup
        parts = verse_id.split(".")
        if len(parts) != 3:
            raise ValueError(f"Invalid verse_id format: {verse_id}")

        book, chapter_str, verse_str = parts
        chapter = int(chapter_str)
        verse = int(verse_str)

        # Create a fake parsed_ref for the helper function
        from dataclasses import dataclass as dc

        @dc
        class _FakeRef:
            book: str
            chapter: int
            verse: int
            verse_end: int | None = None

        fake_ref = _FakeRef(book=book, chapter=chapter, verse=verse)

        # Fetch spine data for this verse
        try:
            sblgnt_text, tokens = _get_spine_data(conn, verse_id, fake_ref, options)
        except ValueError:
            # Try fallback: maybe this verse doesn't exist in spine
            sblgnt_text = ""
            tokens = []

        verse_data.append(
            {
                "verse_id": verse_id,
                "sblgnt_text": sblgnt_text,
                "tokens": tokens,
            }
        )

        # Fetch variants for this verse
        variants = _ensure_variants(variant_store, verse_id, options)
        all_variants.extend(variants)

    # 5. Check for gates across ALL verses (aggregate gating)
    significant_variants = [v for v in all_variants if v.is_significant]
    unacked_variants = [
        v for v in significant_variants if not ack_state.has_acknowledged_variant(v.ref)
    ]

    if unacked_variants:
        # Return aggregated gate for ALL unacknowledged variants
        return _create_passage_variant_gate(
            unacked_variants, all_variants, ack_state, normalized_ref, verse_ids
        )

    # If we only have one verse, use the simpler single-verse path for backward compat
    if len(verse_ids) == 1:
        return _translate_single_verse(
            conn=conn,
            verse_id=verse_ids[0],
            verse_data=verse_data[0],
            all_variants=all_variants,
            normalized_ref=normalized_ref,
            mode=mode,
            session_id=session_id,
            options=options,
            translator=translator,
            ack_state=ack_state,
        )

    # Multi-verse passage translation
    return _translate_multi_verse(
        conn=conn,
        verse_ids=verse_ids,
        verse_data=verse_data,
        all_variants=all_variants,
        normalized_ref=normalized_ref,
        mode=mode,
        session_id=session_id,
        options=options,
        translator=translator,
        ack_state=ack_state,
    )


def _create_passage_variant_gate(
    unacked_variants: list[VariantUnit],
    all_variants: list[VariantUnit],
    ack_state: AcknowledgementState,
    normalized_ref: str,
    verse_ids: list[str],
) -> GateResponsePayload:
    """Create aggregated gate for multi-verse passage with unacked variants."""

    # Build required_acks list
    required_acks = []
    for v in unacked_variants:
        required_acks.append(
            RequiredAck(
                verse_id=v.ref,
                variant_ref=v.ref,
                reading_index=v.sblgnt_reading_index,
                significance=v.significance.value,
                message=f"{v.significance.value.title()} variant at {v.ref}",
            )
        )

    # Build options for the first unacked variant (user can ack one at a time)
    first_variant = unacked_variants[0]
    options = []
    for i, reading in enumerate(first_variant.readings):
        is_sblgnt = i == first_variant.sblgnt_reading_index
        label = reading.surface_text
        if is_sblgnt:
            label += " [SBLGNT]"

        options.append(
            GateOption(
                id=f"reading_{i}",
                label=label,
                description=f"Witnesses: {reading.witness_summary}",
                is_default=is_sblgnt,
                reading_index=i,
            )
        )

    options.append(
        GateOption(
            id="view_full",
            label="View full apparatus",
            description="See complete witness data before deciding",
        )
    )

    # Build variant displays for all variants
    variant_displays = _build_variant_displays(all_variants, ack_state)

    # Build message based on count
    if len(unacked_variants) == 1:
        message = f"A {first_variant.significance.value} variant exists at {first_variant.ref}"
    else:
        refs = [v.ref for v in unacked_variants]
        message = f"{len(unacked_variants)} variants require acknowledgement: {', '.join(refs)}"

    return GateResponsePayload(
        response_type="gate",
        gate_id=f"variant_{first_variant.ref}_{datetime.now().timestamp()}",
        gate_type="variant",
        title="Variant Acknowledgement Required",
        message=message,
        prompt="Please acknowledge which reading you want to use. The SBLGNT reading is marked as default.",
        options=options,
        required_dependencies=["variant"],
        variants_side_by_side=variant_displays,
        reference=normalized_ref,
        required_acks=required_acks,
        verse_ids=verse_ids,
    )


def _translate_single_verse(
    conn: sqlite3.Connection,
    verse_id: str,
    verse_data: dict,
    all_variants: list[VariantUnit],
    normalized_ref: str,
    mode: Literal["readable", "traceable"],
    session_id: str,
    options: dict,
    translator: Translator,
    ack_state: AcknowledgementState,
) -> GateResponsePayload | TranslateResponse:
    """Translate a single verse (backward compatible path)."""
    sblgnt_text = verse_data["sblgnt_text"]
    tokens = verse_data["tokens"]

    # Parse verse_id components for ScriptureRef-like object
    parts = verse_id.split(".")
    book, chapter, verse = parts[0], int(parts[1]), int(parts[2])

    # 7. Run translator
    context = TranslationContext(
        reference=normalized_ref,
        mode=mode,
        tokens=tokens,
        variants=[v.to_dict() for v in all_variants],
        session_id=session_id,
        options=options,
    )

    draft = translator.translate(sblgnt_text, context)

    # 8. Process claims through classifier and enforcer
    classifier = ClaimClassifier()
    enforcer = EnforcementEngine()
    pressure_detector = EpistemicPressureDetector()

    claims_results: list[ClaimResult] = []
    escalation_required = False
    escalation_claim_type: ClaimType | None = None

    for tc in draft.claims:
        # Build claim context
        claim_context = ClaimContext(
            text_span=TextSpan(
                book=book,
                chapter=chapter,
                verse_start=verse,
                verse_end=None,
            ),
            has_variant_at_span=bool(all_variants),
            has_grammar_ambiguity=any(
                d.get("dep_type") == "grammar" and d.get("alternatives")
                for d in tc.dependencies
            ),
            has_lexical_ambiguity=any(
                d.get("dep_type") == "lexicon" and len(d.get("sense_range", [])) > 2
                for d in tc.dependencies
            ),
        )

        # Classify claim
        classification = classifier.classify(tc.content, claim_context)

        # Override with hint if provided
        if tc.claim_type_hint is not None:
            claim_type = ClaimType(tc.claim_type_hint)
        else:
            claim_type = classification.claim_type

        # Build Claim object for enforcement
        claim = Claim(
            claim_type=claim_type,
            text_span=claim_context.text_span,
            content=tc.content,
            confidence=claim_type.base_confidence,
            dependencies=_build_dependencies(tc.dependencies),
            mode=mode,
            classification_confidence=classification.confidence,
            classification_signals=classification.signals,
        )

        # Enforce
        enforcement = enforcer.check_claim(claim, mode)

        # Detect epistemic pressure
        pressure_warnings = pressure_detector.detect(tc.content)

        # Build result
        claim_result = ClaimResult(
            content=tc.content,
            claim_type=claim_type.value,
            claim_type_label=claim_type.label,
            classification_confidence=classification.confidence,
            signals=classification.signals,
            enforcement_allowed=enforcement.allowed,
            enforcement_reason=enforcement.reason,
            warnings=[str(w) for w in pressure_warnings],
            rewrite_suggestions=enforcement.rewrite_suggestions,
            dependencies=_convert_dependencies(tc.dependencies),
            hypothesis_markers_required=enforcement.hypothesis_markers_required,
        )

        claims_results.append(claim_result)

        # Check if escalation gate needed
        if not enforcement.allowed and enforcement.required_escalation:
            escalation_required = True
            escalation_claim_type = enforcement.required_escalation

    # 6b. Escalation gate (if claim type requires traceable mode)
    if escalation_required and mode == "readable" and escalation_claim_type:
        return _create_escalation_gate(
            escalation_claim_type, normalized_ref, all_variants, ack_state
        )

    # 9. Compute layered confidence
    significant_variants = [v for v in all_variants if v.is_significant]
    confidence = _compute_confidence(all_variants, tokens, claims_results, ack_state)

    # 10. Build variant display
    variant_displays = _build_variant_displays(all_variants, ack_state)

    # 11. Build provenance (with license info from spine provider if available)
    spine_provider = options.get("spine_provider")
    if spine_provider is not None and hasattr(spine_provider, "source_key"):
        spine_source = spine_provider.source_key
        # Extract license if available
        if hasattr(spine_provider, "license") and spine_provider.license:
            spine_source = f"{spine_provider.source_key} ({spine_provider.license})"
        sources_used = [spine_provider.source_key]
    else:
        spine_source = "SBLGNT"
        sources_used = ["SBLGNT", "MorphGNT"]

    provenance = ProvenanceInfo(
        spine_source=spine_source,
        spine_marker="default",
        sources_used=sources_used,
        variant_unit_ids=[v.ref for v in all_variants],
        witness_summaries=[
            {"ref": v.ref, "reading_count": v.reading_count} for v in all_variants
        ],
    )

    # 12. Build receipt
    receipt = ReceiptSummary(
        checks_run=[
            "reference_parse",
            "token_fetch",
            "variant_lookup",
            "acknowledgement_check",
            "translation",
            "claim_classification",
            "claim_enforcement",
            "epistemic_pressure_detection",
            "confidence_calculation",
        ],
        gates_satisfied=[
            v.ref
            for v in significant_variants
            if ack_state.has_acknowledged_variant(v.ref)
        ],
        gates_pending=[],  # All gates satisfied if we got here
        enforcement_results=[
            {
                "claim_preview": c.content[:50] + "..."
                if len(c.content) > 50
                else c.content,
                "allowed": c.enforcement_allowed,
                "type": c.claim_type_label,
            }
            for c in claims_results
        ],
        timestamp=datetime.now().isoformat(),
    )

    # 13. Extract ledger from draft if present (Sprint 10: TraceableTranslator)
    ledger = getattr(draft, "ledger", None)

    # 14. Build final response
    return TranslateResponse(
        response_type="translation",
        reference=normalized_ref,
        normalized_ref=normalized_ref,
        verse_ids=[verse_id],
        mode=mode,
        sblgnt_text=sblgnt_text,
        translation_text=draft.translation_text,
        verse_blocks=[
            VerseBlock(
                verse_id=verse_id,
                sblgnt_text=sblgnt_text,
                translation_text=draft.translation_text,
                variants=[v for v in variant_displays if v.ref == verse_id],
                tokens=tokens,
                confidence=confidence,
            )
        ],
        variants=variant_displays,
        claims=claims_results,
        confidence=confidence,
        provenance=provenance,
        receipts=receipt,
        tokens=tokens,
        ledger=ledger,
    )


def _translate_multi_verse(
    conn: sqlite3.Connection,
    verse_ids: list[str],
    verse_data: list[dict],
    all_variants: list[VariantUnit],
    normalized_ref: str,
    mode: Literal["readable", "traceable"],
    session_id: str,
    options: dict,
    translator: Translator,
    ack_state: AcknowledgementState,
) -> GateResponsePayload | TranslateResponse:
    """Translate a multi-verse passage."""

    # Combine spine text and tokens
    combined_sblgnt = " ".join(
        vd["sblgnt_text"] for vd in verse_data if vd["sblgnt_text"]
    )
    combined_tokens = []
    for vd in verse_data:
        combined_tokens.extend(vd["tokens"])

    # Run translator on combined text
    context = TranslationContext(
        reference=normalized_ref,
        mode=mode,
        tokens=combined_tokens,
        variants=[v.to_dict() for v in all_variants],
        session_id=session_id,
        options=options,
    )

    draft = translator.translate(combined_sblgnt, context)

    # Process claims
    classifier = ClaimClassifier()
    enforcer = EnforcementEngine()
    pressure_detector = EpistemicPressureDetector()

    claims_results: list[ClaimResult] = []
    escalation_required = False
    escalation_claim_type: ClaimType | None = None

    # Extract book/chapter from first verse for text span
    first_parts = verse_ids[0].split(".")
    last_parts = verse_ids[-1].split(".")
    book = first_parts[0]
    chapter = int(first_parts[1])
    verse_start = int(first_parts[2])
    verse_end = int(last_parts[2]) if len(verse_ids) > 1 else None

    for tc in draft.claims:
        claim_context = ClaimContext(
            text_span=TextSpan(
                book=book,
                chapter=chapter,
                verse_start=verse_start,
                verse_end=verse_end,
            ),
            has_variant_at_span=bool(all_variants),
            has_grammar_ambiguity=any(
                d.get("dep_type") == "grammar" and d.get("alternatives")
                for d in tc.dependencies
            ),
            has_lexical_ambiguity=any(
                d.get("dep_type") == "lexicon" and len(d.get("sense_range", [])) > 2
                for d in tc.dependencies
            ),
        )

        classification = classifier.classify(tc.content, claim_context)

        if tc.claim_type_hint is not None:
            claim_type = ClaimType(tc.claim_type_hint)
        else:
            claim_type = classification.claim_type

        claim = Claim(
            claim_type=claim_type,
            text_span=claim_context.text_span,
            content=tc.content,
            confidence=claim_type.base_confidence,
            dependencies=_build_dependencies(tc.dependencies),
            mode=mode,
            classification_confidence=classification.confidence,
            classification_signals=classification.signals,
        )

        enforcement = enforcer.check_claim(claim, mode)
        pressure_warnings = pressure_detector.detect(tc.content)

        claim_result = ClaimResult(
            content=tc.content,
            claim_type=claim_type.value,
            claim_type_label=claim_type.label,
            classification_confidence=classification.confidence,
            signals=classification.signals,
            enforcement_allowed=enforcement.allowed,
            enforcement_reason=enforcement.reason,
            warnings=[str(w) for w in pressure_warnings],
            rewrite_suggestions=enforcement.rewrite_suggestions,
            dependencies=_convert_dependencies(tc.dependencies),
            hypothesis_markers_required=enforcement.hypothesis_markers_required,
        )

        claims_results.append(claim_result)

        if not enforcement.allowed and enforcement.required_escalation:
            escalation_required = True
            escalation_claim_type = enforcement.required_escalation

    # Check escalation gate
    if escalation_required and mode == "readable" and escalation_claim_type:
        return _create_escalation_gate(
            escalation_claim_type, normalized_ref, all_variants, ack_state
        )

    # Build per-verse blocks
    verse_blocks = []
    variant_displays = _build_variant_displays(all_variants, ack_state)

    for vd in verse_data:
        vid = vd["verse_id"]
        verse_variants = [v for v in variant_displays if v.ref == vid]

        # Compute per-verse confidence
        verse_variant_units = [v for v in all_variants if v.ref == vid]
        verse_confidence = _compute_confidence(
            verse_variant_units, vd["tokens"], [], ack_state
        )

        verse_blocks.append(
            VerseBlock(
                verse_id=vid,
                sblgnt_text=vd["sblgnt_text"],
                translation_text="",  # Per-verse translation not split yet
                variants=verse_variants,
                tokens=vd["tokens"],
                confidence=verse_confidence,
            )
        )

    # Compute passage-level confidence
    passage_confidence = _compute_confidence(
        all_variants, combined_tokens, claims_results, ack_state
    )

    # Build provenance
    spine_provider = options.get("spine_provider")
    if spine_provider is not None and hasattr(spine_provider, "source_key"):
        spine_source = spine_provider.source_key
        if hasattr(spine_provider, "license") and spine_provider.license:
            spine_source = f"{spine_provider.source_key} ({spine_provider.license})"
        sources_used = [spine_provider.source_key]
    else:
        spine_source = "SBLGNT"
        sources_used = ["SBLGNT", "MorphGNT"]

    provenance = ProvenanceInfo(
        spine_source=spine_source,
        spine_marker="default",
        sources_used=sources_used,
        variant_unit_ids=[v.ref for v in all_variants],
        witness_summaries=[
            {"ref": v.ref, "reading_count": v.reading_count} for v in all_variants
        ],
    )

    # Build receipt
    significant_variants = [v for v in all_variants if v.is_significant]
    receipt = ReceiptSummary(
        checks_run=[
            "reference_parse",
            "multi_verse_token_fetch",
            "variant_lookup",
            "acknowledgement_check",
            "passage_translation",
            "claim_classification",
            "claim_enforcement",
            "epistemic_pressure_detection",
            "confidence_calculation",
        ],
        gates_satisfied=[
            v.ref
            for v in significant_variants
            if ack_state.has_acknowledged_variant(v.ref)
        ],
        gates_pending=[],
        enforcement_results=[
            {
                "claim_preview": c.content[:50] + "..."
                if len(c.content) > 50
                else c.content,
                "allowed": c.enforcement_allowed,
                "type": c.claim_type_label,
            }
            for c in claims_results
        ],
        timestamp=datetime.now().isoformat(),
    )

    # Extract ledger from draft if present (Sprint 10: TraceableTranslator)
    ledger = getattr(draft, "ledger", None)

    return TranslateResponse(
        response_type="translation",
        reference=normalized_ref,
        normalized_ref=normalized_ref,
        verse_ids=verse_ids,
        mode=mode,
        sblgnt_text=combined_sblgnt,
        translation_text=draft.translation_text,
        verse_blocks=verse_blocks,
        variants=variant_displays,
        claims=claims_results,
        confidence=passage_confidence,
        provenance=provenance,
        receipts=receipt,
        tokens=combined_tokens,
        ledger=ledger,
    )


def _create_escalation_gate(
    claim_type: ClaimType,
    reference: str,
    variants: list[VariantUnit],
    ack_state: AcknowledgementState,
) -> GateResponsePayload:
    """Create a gate response for mode escalation."""
    options = [
        GateOption(
            id="switch_mode",
            label="Switch to Traceable Mode",
            description="Allows this claim type with full dependency tracking",
            is_default=True,
        ),
        GateOption(
            id="rewrite",
            label="Rewrite claim",
            description="Modify the claim to fit Readable mode",
        ),
        GateOption(
            id="cancel",
            label="Cancel",
            description="Abandon this claim",
        ),
    ]

    variant_displays = _build_variant_displays(variants, ack_state)

    return GateResponsePayload(
        response_type="gate",
        gate_id=f"escalation_{claim_type.value}_{datetime.now().timestamp()}",
        gate_type="escalation",
        title="Mode Escalation Required",
        message=f"{claim_type.label} claims require Traceable mode",
        prompt="This claim type is forbidden in Readable mode. Please choose how to proceed.",
        options=options,
        required_dependencies=["tradition", "hermeneutic"]
        if claim_type >= ClaimType.TYPE5_MORAL
        else ["tradition"],
        variants_side_by_side=variant_displays,
        escalation_target_mode="traceable",
        reference=reference,
    )


def _build_variant_displays(
    variants: list[VariantUnit],
    ack_state: AcknowledgementState,
) -> list[VariantDisplay]:
    """Build variant display objects for side-by-side rendering."""
    displays = []

    for v in variants:
        sblgnt = v.sblgnt_reading
        if not sblgnt:
            continue

        alternate_readings = []
        for i, reading in enumerate(v.readings):
            if i != v.sblgnt_reading_index:
                alternate_readings.append(
                    {
                        "index": i,
                        "surface_text": reading.surface_text,
                        "witnesses": reading.witness_summary,
                        "has_papyri": reading.has_papyri,
                        "has_primary_uncials": reading.has_primary_uncials,
                    }
                )

        displays.append(
            VariantDisplay(
                ref=v.ref,
                position=v.position,
                sblgnt_reading=sblgnt.surface_text,
                sblgnt_witnesses=sblgnt.witness_summary,
                alternate_readings=alternate_readings,
                significance=v.significance.value,
                requires_acknowledgement=v.requires_acknowledgement,
                acknowledged=ack_state.has_acknowledged_variant(v.ref),
            )
        )

    return displays


def _build_dependencies(deps: list[dict]) -> ClaimDependency:
    """Convert raw dependency dicts to ClaimDependency."""
    result = ClaimDependency()

    for d in deps:
        dep_type = d.get("dep_type", "")

        if dep_type == "variant":
            result.variants.append(
                VariantDependency(
                    variant_unit_ref=d.get("variant_unit_ref", ""),
                    reading_chosen=d.get("reading_chosen", 0),
                    rationale=d.get("rationale", ""),
                    witnesses=d.get("witnesses", []),
                )
            )
        elif dep_type == "grammar":
            result.grammar.append(
                GrammarDependency(
                    token_ref=d.get("token_ref", ""),
                    parse_choice=d.get("parse_choice", ""),
                    alternatives=d.get("alternatives", []),
                    rationale=d.get("rationale", ""),
                )
            )
        elif dep_type == "lexicon":
            result.lexicon.append(
                LexiconDependency(
                    lemma=d.get("lemma", ""),
                    sense_chosen=d.get("sense_chosen", ""),
                    sense_range=d.get("sense_range", []),
                    rationale=d.get("rationale", ""),
                )
            )
        elif dep_type in ("context", "tradition", "hermeneutic", "cross_ref"):
            result.context.append(
                ContextDependency(
                    assumption=d.get("assumption", d.get("ref", "")),
                    evidence=d.get("evidence", d.get("choice", "")),
                    alternatives=d.get("alternatives", []),
                )
            )

    return result


def _convert_dependencies(deps: list[dict]) -> list[DependencyInfo]:
    """Convert raw dependency dicts to DependencyInfo list."""
    result = []

    for d in deps:
        dep_type = d.get("dep_type", "unknown")

        if dep_type == "variant":
            result.append(
                DependencyInfo(
                    dep_type="variant",
                    ref=d.get("variant_unit_ref", ""),
                    choice=f"reading_{d.get('reading_chosen', 0)}",
                    rationale=d.get("rationale", ""),
                )
            )
        elif dep_type == "grammar":
            result.append(
                DependencyInfo(
                    dep_type="grammar",
                    ref=d.get("token_ref", ""),
                    choice=d.get("parse_choice", ""),
                    rationale=d.get("rationale", ""),
                    alternatives=d.get("alternatives", []),
                )
            )
        elif dep_type == "lexicon":
            result.append(
                DependencyInfo(
                    dep_type="lexicon",
                    ref=d.get("lemma", ""),
                    choice=d.get("sense_chosen", ""),
                    rationale=d.get("rationale", ""),
                    alternatives=d.get("sense_range", []),
                )
            )
        elif dep_type in ("context", "tradition", "hermeneutic"):
            result.append(
                DependencyInfo(
                    dep_type=dep_type,
                    ref=d.get("assumption", ""),
                    choice=d.get("evidence", ""),
                    rationale="",
                )
            )
        elif dep_type == "cross_ref":
            result.append(
                DependencyInfo(
                    dep_type="cross_ref",
                    ref=d.get("ref", ""),
                    choice=d.get("choice", ""),
                    rationale="",
                )
            )

    return result


def _compute_confidence(
    variants: list[VariantUnit],
    tokens: list[dict],
    claims: list[ClaimResult],
    ack_state: AcknowledgementState,
) -> ConfidenceResult:
    """Compute layered confidence score."""
    calculator = ConfidenceCalculator()

    # Textual confidence: based on variants
    has_variant = bool(variants)
    significant_variants = [v for v in variants if v.is_significant]

    if not has_variant:
        textual = TextualConfidence.calculate(variant_exists=False)
    elif significant_variants:
        # Get best attestation from SBLGNT readings
        papyri = any(v.sblgnt_reading and v.sblgnt_reading.has_papyri for v in variants)
        uncials = []
        for v in variants:
            if v.sblgnt_reading:
                uncials.extend(
                    [
                        w
                        for w in v.sblgnt_reading.witnesses
                        if w in {"א", "B", "A", "C", "D"}
                    ]
                )
        uncials = list(set(uncials))

        textual = TextualConfidence.calculate(
            variant_exists=True,
            papyri_support=papyri,
            primary_uncials=uncials,
            witness_agreement=0.7 if significant_variants else 0.9,
        )
    else:
        textual = TextualConfidence.calculate(
            variant_exists=True,
            witness_agreement=0.9,
        )

    # Grammatical confidence: based on claim dependencies
    has_grammar_ambiguity = any(
        any(d.dep_type == "grammar" and d.alternatives for d in c.dependencies)
        for c in claims
    )

    if has_grammar_ambiguity:
        grammatical = GrammaticalConfidence.calculate(
            parse_count=2,
            context_disambiguates=True,
        )
    else:
        grammatical = GrammaticalConfidence.default_high()

    # Lexical confidence: based on sense range breadth
    max_sense_range = 1
    for c in claims:
        for d in c.dependencies:
            if d.dep_type == "lexicon":
                max_sense_range = max(max_sense_range, len(d.alternatives) + 1)

    if max_sense_range > 3:
        lexical = LexicalConfidence.calculate(
            lemma="",
            sense_count=max_sense_range,
            collocation_supported=True,
        )
    else:
        lexical = LexicalConfidence.default_high()

    # Calculate layered confidence
    layered = calculator.calculate(
        textual=textual,
        grammatical=grammatical,
        lexical=lexical,
    )

    # Build result
    explanation = calculator.explain(layered)

    return ConfidenceResult(
        composite=layered.composite,
        weakest_layer=layered.weakest_layer,
        textual=LayerScore(
            score=layered.textual.score,
            rationale=layered.textual.rationale,
        ),
        grammatical=LayerScore(
            score=layered.grammatical.score,
            rationale=layered.grammatical.rationale,
        ),
        lexical=LayerScore(
            score=layered.lexical.score,
            rationale=layered.lexical.rationale,
        ),
        interpretive=LayerScore(
            score=layered.interpretive.score,
            rationale=layered.interpretive.rationale,
        ),
        weights=layered.weights,
        explanations=[explanation.summary],
        improvement_suggestions=explanation.improvement_suggestions,
    )


def acknowledge_variant(
    conn: sqlite3.Connection,
    session_id: str,
    variant_ref: str,
    reading_index: int,
    context: str = "translate_passage",
) -> bool:
    """Acknowledge a variant reading for a session.

    Args:
        conn: Database connection
        session_id: Session identifier
        variant_ref: Variant reference (e.g., "John.1.18")
        reading_index: Index of chosen reading
        context: Context description

    Returns:
        True if acknowledgement was persisted
    """
    ack_store = AcknowledgementStore(conn)

    try:
        ack_store.init_schema()
    except Exception:
        pass

    state = ack_store.load_session_state(session_id)
    ack = state.acknowledge_variant(
        ref=variant_ref,
        reading_chosen=reading_index,
        context=context,
    )
    ack_store.persist_variant_ack(ack)

    return True
