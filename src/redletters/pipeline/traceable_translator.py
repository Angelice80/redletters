"""Traceable translator implementation.

Sprint 10: Produces fluent-ish English with complete token-level ledger.
Deterministic output for reproducibility.

Non-negotiables:
- TYPE5+ claims NEVER appear in readable mode (per ADR-009)
- Confidence layers always visible (per ADR-010)
- Evidence class explicit (manuscript/edition/tradition)
- SBLGNT remains canonical spine (per ADR-007)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from redletters.ledger.schemas import (
    EvidenceClassSummary,
    LedgerProvenance,
    TokenConfidence,
    TokenLedger,
    VerseLedger,
)
from redletters.lexicon.provider import (
    BasicGlossProvider,
    GlossResult,
    LexiconProvider,
    normalize_greek,
)
from redletters.pipeline.translator import (
    FluentTranslator,
    TranslationClaim,
    TranslationContext,
    TranslationDraft,
)


@dataclass
class TraceableTranslationResult:
    """Result from TraceableTranslator.

    Contains both the translation draft and the token-level ledger.
    """

    draft: TranslationDraft
    """Standard translation draft with text and claims."""

    ledger: list[VerseLedger]
    """Token-level ledger for each verse."""


@dataclass
class TraceableTranslationDraft(TranslationDraft):
    """Draft translation with ledger for TraceableTranslator."""

    ledger: list[VerseLedger] = field(default_factory=list)
    """Token-level ledger for each verse (traceable mode only)."""


class TraceableTranslator:
    """Produces fluent English with complete token-level ledger.

    Deterministic output for reproducibility.

    Features:
    - Token-level gloss with provenance tracking
    - Four-layer confidence per ADR-010
    - Fluent transformation using existing FluentTranslator
    - Evidence class summary from dossier/support

    Mode Enforcement:
    - Readable mode: TYPE0-4 claims only, ledger is None
    - Traceable mode: All claim types, full ledger returned

    Non-negotiables:
    - TYPE5+ forbidden in readable mode (ADR-009)
    - Confidence always decomposed (ADR-010)
    - SBLGNT canonical spine (ADR-007)
    """

    def __init__(
        self,
        lexicon_providers: list[LexiconProvider] | None = None,
        source_id: str = "sblgnt",
        source_license: str = "SBLGNT License",
    ):
        """Initialize traceable translator.

        Args:
            lexicon_providers: List of providers to try for gloss lookup
            source_id: Source pack ID for provenance
            source_license: License string for provenance
        """
        if lexicon_providers is None:
            lexicon_providers = [BasicGlossProvider()]
        self._providers = lexicon_providers
        self._source_id = source_id
        self._source_license = source_license

        # Use FluentTranslator for English output
        self._fluent = FluentTranslator(
            source_id=source_id,
            source_license=source_license,
        )

    def translate(
        self,
        spine_text: str,
        context: TranslationContext,
    ) -> TraceableTranslationDraft:
        """Translate Greek text with token-level ledger.

        Args:
            spine_text: Greek text (space-separated tokens)
            context: Translation context with tokens, mode, etc.

        Returns:
            TraceableTranslationDraft with text, claims, and ledger
        """
        # Step 1: Get fluent translation
        fluent_draft = self._fluent.translate(spine_text, context)

        # Step 2: Build token-level ledger (only in traceable mode)
        ledger: list[VerseLedger] | None = None
        if context.mode == "traceable":
            ledger = self._build_ledger(spine_text, context)

        # Step 3: Filter claims for mode
        filtered_claims = self._filter_claims_for_mode(
            fluent_draft.claims, context.mode
        )

        # Step 4: Build notes
        notes = [
            "TraceableTranslator: token-level ledger with fluent output",
            f"Source: {self._source_id}",
            f"Mode: {context.mode}",
            f"Lexicon providers: {', '.join(p.source_id for p in self._providers)}",
        ]

        return TraceableTranslationDraft(
            translation_text=fluent_draft.translation_text,
            claims=filtered_claims,
            notes=notes,
            style="traceable",
            ledger=ledger if ledger else [],
        )

    def _build_ledger(
        self,
        spine_text: str,
        context: TranslationContext,
    ) -> list[VerseLedger]:
        """Build token-level ledger for each verse.

        Args:
            spine_text: Greek text
            context: Translation context with tokens

        Returns:
            List of VerseLedger, one per verse
        """
        # Group tokens by verse
        verse_groups = self._group_tokens_by_verse(context)

        # Build ledger for each verse
        ledgers = []
        for verse_id, tokens in verse_groups.items():
            verse_ledger = self._build_verse_ledger(
                verse_id=verse_id,
                tokens=tokens,
                context=context,
            )
            ledgers.append(verse_ledger)

        return ledgers

    def _group_tokens_by_verse(
        self, context: TranslationContext
    ) -> dict[str, list[dict]]:
        """Group tokens by verse ID.

        Args:
            context: Translation context

        Returns:
            Dict mapping verse_id to list of tokens
        """
        verse_groups: dict[str, list[dict]] = {}

        for token in context.tokens:
            # Extract verse ID from token ref or use context reference
            verse_id = token.get("verse_id", token.get("ref", context.reference))
            # Normalize verse_id (strip token position if present)
            if ":" in verse_id:
                verse_id = verse_id.rsplit(":", 1)[0]

            if verse_id not in verse_groups:
                verse_groups[verse_id] = []
            verse_groups[verse_id].append(token)

        # If no tokens grouped, create single group with reference
        if not verse_groups and context.reference:
            verse_groups[context.reference] = context.tokens

        return verse_groups

    def _build_verse_ledger(
        self,
        verse_id: str,
        tokens: list[dict],
        context: TranslationContext,
    ) -> VerseLedger:
        """Build ledger for a single verse.

        Args:
            verse_id: Verse identifier
            tokens: Token data for this verse
            context: Translation context

        Returns:
            VerseLedger for the verse
        """
        # Build token ledgers
        token_ledgers = []
        for i, token in enumerate(tokens):
            token_ledger = self._build_token_ledger(token, position=i, context=context)
            token_ledgers.append(token_ledger)

        # Build provenance from context
        provenance = self._build_provenance(context)

        # Build normalized reference
        normalized_ref = self._normalize_reference(verse_id)

        return VerseLedger(
            verse_id=verse_id,
            normalized_ref=normalized_ref,
            tokens=token_ledgers,
            translation_segments=[],  # Optional, not built yet
            provenance=provenance,
        )

    def _build_token_ledger(
        self,
        token: dict,
        position: int,
        context: TranslationContext,
    ) -> TokenLedger:
        """Build ledger entry for a single token.

        Args:
            token: Token dictionary with morphology
            position: Position in verse
            context: Translation context

        Returns:
            TokenLedger for the token
        """
        # Extract token data
        surface = token.get("surface_text", token.get("surface", token.get("word", "")))
        lemma = token.get("lemma", "")
        morph = token.get("parse_code", token.get("morph", ""))

        # Normalize for lookup
        normalized = normalize_greek(surface)
        lemma_normalized = normalize_greek(lemma) if lemma else normalized

        # Lookup gloss
        gloss_result = self._lookup_gloss(lemma_normalized)
        if gloss_result is None:
            # Fallback: try surface form
            gloss_result = self._lookup_gloss(normalized)

        if gloss_result is not None:
            gloss = gloss_result.gloss
            gloss_source = gloss_result.source
            lexical_confidence = gloss_result.confidence
        else:
            # No gloss found - use lemma or surface
            gloss = lemma if lemma else surface
            gloss_source = "unknown"
            lexical_confidence = 0.3  # Low confidence for unknown words

        # Build confidence scores
        confidence = self._build_token_confidence(
            token=token,
            lexical_confidence=lexical_confidence,
            context=context,
        )

        # Build notes
        notes = []
        if self._is_article(token):
            notes.append("article")
        if self._is_proper_noun(token):
            notes.append("proper noun")
        if gloss_result and gloss_result.alternatives:
            notes.append(f"semantic range: {', '.join(gloss_result.alternatives[:3])}")

        return TokenLedger(
            position=position,
            surface=surface,
            normalized=normalized,
            lemma=lemma if lemma else None,
            morph=morph if morph else None,
            gloss=gloss,
            gloss_source=gloss_source,
            notes=notes,
            confidence=confidence,
        )

    def _lookup_gloss(self, key: str) -> GlossResult | None:
        """Lookup gloss trying each provider.

        Args:
            key: Normalized Greek text

        Returns:
            First successful GlossResult, or None
        """
        for provider in self._providers:
            result = provider.lookup(key)
            if result is not None:
                return result
        return None

    def _build_token_confidence(
        self,
        token: dict,
        lexical_confidence: float,
        context: TranslationContext,
    ) -> TokenConfidence:
        """Build four-layer confidence for a token.

        Args:
            token: Token dictionary
            lexical_confidence: Confidence from gloss lookup
            context: Translation context

        Returns:
            TokenConfidence with all four layers
        """
        explanations = {}

        # Textual confidence: based on variant presence
        textual = 0.9
        explanations["textual"] = "No variant at this position"
        # Check if there's a variant at this token's position
        token_pos = token.get("position", 0)
        for variant in context.variants:
            var_pos = variant.get("position", -1)
            if var_pos == token_pos:
                textual = 0.6 if variant.get("significance") == "significant" else 0.7
                explanations["textual"] = (
                    f"Variant exists ({variant.get('significance', 'unknown')})"
                )
                break

        # Grammatical confidence: based on parse ambiguity
        morph = token.get("parse_code", token.get("morph", ""))
        grammatical = 0.9
        explanations["grammatical"] = "Unambiguous parse"
        if morph:
            # Check for ambiguous cases
            if len(morph) >= 5 and morph[4] == "G":  # Genitive
                grammatical = 0.7
                explanations["grammatical"] = "Genitive case (multiple interpretations)"
            elif len(morph) >= 3 and morph[2] == "E":  # Middle/passive
                grammatical = 0.7
                explanations["grammatical"] = "Middle/passive voice (ambiguous)"

        # Lexical confidence: from gloss lookup
        lexical = lexical_confidence
        if lexical >= 0.8:
            explanations["lexical"] = "Clear semantic meaning"
        elif lexical >= 0.6:
            explanations["lexical"] = "Multiple senses possible"
        else:
            explanations["lexical"] = "Uncertain gloss (not in lexicon)"

        # Interpretive confidence: based on inference required
        # Lower for context-dependent words
        interpretive = 0.85
        explanations["interpretive"] = "Minimal inference required"
        lemma = token.get("lemma", "")
        lemma_norm = normalize_greek(lemma) if lemma else ""
        # Words with broad semantic range require more interpretation
        if lemma_norm in ["λόγος", "πίστις", "σάρξ", "πνεῦμα", "ψυχή"]:
            interpretive = 0.6
            explanations["interpretive"] = "Context-dependent interpretation"

        return TokenConfidence(
            textual=textual,
            grammatical=grammatical,
            lexical=lexical,
            interpretive=interpretive,
            explanations=explanations,
        )

    def _build_provenance(self, context: TranslationContext) -> LedgerProvenance:
        """Build provenance from context.

        Args:
            context: Translation context

        Returns:
            LedgerProvenance with spine and comparative sources
        """
        # Get comparative sources from context options
        comparative_sources = context.options.get("comparative_sources", [])
        if not comparative_sources and context.variants:
            # Extract from variants
            for variant in context.variants:
                for alt in variant.get("alternate_readings", []):
                    source = alt.get("source_pack_id")
                    if source and source not in comparative_sources:
                        comparative_sources.append(source)

        # Build evidence class summary from context
        evidence_summary = self._build_evidence_summary(context)

        return LedgerProvenance(
            spine_source_id="sblgnt",  # Always SBLGNT per ADR-007
            comparative_sources_used=comparative_sources,
            evidence_class_summary=evidence_summary,
        )

    def _build_evidence_summary(
        self, context: TranslationContext
    ) -> EvidenceClassSummary:
        """Build evidence class summary from context variants.

        Args:
            context: Translation context

        Returns:
            EvidenceClassSummary with counts by type
        """
        manuscript_count = 0
        edition_count = 0
        tradition_count = 0
        other_count = 0

        # Count witnesses from variants
        for variant in context.variants:
            for reading in [variant] + variant.get("alternate_readings", []):
                witness_types = reading.get("witness_types", [])
                for wtype in witness_types:
                    if wtype in ["papyrus", "uncial", "minuscule"]:
                        manuscript_count += 1
                    elif wtype == "edition":
                        edition_count += 1
                    elif wtype == "tradition":
                        tradition_count += 1
                    else:
                        other_count += 1

        # If no variants, assume edition-level evidence (SBLGNT)
        if not context.variants:
            edition_count = 1

        return EvidenceClassSummary(
            manuscript_count=manuscript_count,
            edition_count=edition_count,
            tradition_count=tradition_count,
            other_count=other_count,
        )

    def _filter_claims_for_mode(
        self, claims: list[TranslationClaim], mode: str
    ) -> list[TranslationClaim]:
        """Filter claims based on mode.

        Readable mode: TYPE0-4 only (per ADR-009)
        Traceable mode: All types allowed

        Args:
            claims: Claims from translator
            mode: "readable" or "traceable"

        Returns:
            Filtered claims
        """
        if mode == "traceable":
            return claims

        # Readable mode: filter to TYPE0-4
        filtered = []
        for claim in claims:
            if claim.claim_type_hint is not None and claim.claim_type_hint <= 4:
                filtered.append(claim)
            elif claim.claim_type_hint is None:
                # Unknown type, treat conservatively
                filtered.append(claim)
            # TYPE5+ silently dropped per ADR-009

        return filtered

    def _normalize_reference(self, verse_id: str) -> str:
        """Convert verse_id to human-readable reference.

        Args:
            verse_id: Internal verse ID (e.g., "John.1.18")

        Returns:
            Human-readable reference (e.g., "John 1:18")
        """
        # Handle different formats
        if "." in verse_id:
            parts = verse_id.split(".")
            if len(parts) >= 3:
                return f"{parts[0]} {parts[1]}:{parts[2]}"
            elif len(parts) == 2:
                return f"{parts[0]} {parts[1]}"
        return verse_id

    def _is_article(self, token: dict) -> bool:
        """Check if token is an article."""
        pos = token.get("pos", "")
        lemma = token.get("lemma", "")
        lemma_norm = normalize_greek(lemma) if lemma else ""
        return pos in ("T", "RA") or lemma_norm in ["ο", "η", "το"]

    def _is_proper_noun(self, token: dict) -> bool:
        """Check if token is a proper noun."""
        pos = token.get("pos", "")
        lemma = token.get("lemma", "")

        if pos in ("NP", "PN"):
            return True
        if lemma and lemma[0].isupper():
            return True
        return False
