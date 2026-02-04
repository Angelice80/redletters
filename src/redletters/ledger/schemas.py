"""Ledger schemas for traceable translation evidence.

Sprint 10: Token-level evidence model for receipt-grade translation
output. Reuses ADR-010 confidence layers and Sprint 9 evidence classes.

Non-negotiables:
- Evidence class remains explicit (manuscript/edition/tradition)
- Confidence layers always visible (ADR-010)
- Provenance tracks spine + comparative sources
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TokenConfidence:
    """Per-token confidence using ADR-010 four-layer model.

    Each layer is scored 0.0-1.0 with human-readable explanations.
    All four layers must always be visible - no collapsing to single score.
    """

    textual: float
    """Layer 1: 0.0-1.0 manuscript agreement for this token."""

    grammatical: float
    """Layer 2: 0.0-1.0 parse ambiguity level."""

    lexical: float
    """Layer 3: 0.0-1.0 semantic range breadth."""

    interpretive: float
    """Layer 4: 0.0-1.0 inference distance (tied to ClaimType)."""

    explanations: dict[str, str] = field(default_factory=dict)
    """Human-readable explanations per layer."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "textual": round(self.textual, 3),
            "grammatical": round(self.grammatical, 3),
            "lexical": round(self.lexical, 3),
            "interpretive": round(self.interpretive, 3),
            "explanations": self.explanations,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenConfidence":
        """Deserialize from dictionary."""
        return cls(
            textual=data.get("textual", 1.0),
            grammatical=data.get("grammatical", 1.0),
            lexical=data.get("lexical", 1.0),
            interpretive=data.get("interpretive", 1.0),
            explanations=data.get("explanations", {}),
        )

    @classmethod
    def default_high(cls) -> "TokenConfidence":
        """Create high-confidence default (all layers at 0.9)."""
        return cls(
            textual=0.9,
            grammatical=0.9,
            lexical=0.9,
            interpretive=0.9,
            explanations={
                "textual": "No variant at this position",
                "grammatical": "Unambiguous parse",
                "lexical": "Clear semantic meaning",
                "interpretive": "Minimal inference required",
            },
        )

    @classmethod
    def default_uncertain(cls) -> "TokenConfidence":
        """Create uncertain default (all layers at 0.5)."""
        return cls(
            textual=0.5,
            grammatical=0.5,
            lexical=0.5,
            interpretive=0.5,
            explanations={
                "textual": "Variant exists",
                "grammatical": "Parse ambiguity present",
                "lexical": "Multiple senses possible",
                "interpretive": "Context-dependent interpretation",
            },
        )


@dataclass
class TokenLedger:
    """Per-token analysis in the translation ledger.

    Provides complete provenance for each Greek token including:
    - Surface form and normalized lookup form
    - Lemma and morphological parse
    - Gloss with source attribution
    - Four-layer confidence per ADR-010
    """

    position: int
    """0-indexed token position in verse."""

    surface: str
    """Original Greek surface form (with accents)."""

    normalized: str
    """Accent-stripped form for dictionary lookup."""

    lemma: str | None
    """Dictionary headword (if available)."""

    morph: str | None
    """Morphological parse code (if available)."""

    gloss: str
    """English gloss from lexicon."""

    gloss_source: str
    """Provenance of gloss (e.g., 'basic_glosses', 'morphgnt')."""

    notes: list[str] = field(default_factory=list)
    """Linguistic notes (elision, crasis, article handling, etc.)."""

    confidence: TokenConfidence = field(default_factory=TokenConfidence.default_high)
    """Four-layer confidence scores per ADR-010."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "position": self.position,
            "surface": self.surface,
            "normalized": self.normalized,
            "lemma": self.lemma,
            "morph": self.morph,
            "gloss": self.gloss,
            "gloss_source": self.gloss_source,
            "notes": self.notes,
            "confidence": self.confidence.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TokenLedger":
        """Deserialize from dictionary."""
        conf_data = data.get("confidence", {})
        confidence = (
            TokenConfidence.from_dict(conf_data)
            if conf_data
            else TokenConfidence.default_high()
        )
        return cls(
            position=data["position"],
            surface=data["surface"],
            normalized=data["normalized"],
            lemma=data.get("lemma"),
            morph=data.get("morph"),
            gloss=data["gloss"],
            gloss_source=data.get("gloss_source", "unknown"),
            notes=data.get("notes", []),
            confidence=confidence,
        )


@dataclass
class SegmentLedger:
    """Phrase-level alignment mapping (optional).

    Maps ranges of Greek tokens to English phrase segments,
    tracking transformations applied during fluent translation.
    """

    token_range: tuple[int, int]
    """Start/end positions (inclusive)."""

    greek_phrase: str
    """Concatenated Greek tokens."""

    english_phrase: str
    """Translated segment."""

    alignment_type: str
    """'literal' | 'reordered' | 'smoothed'."""

    transformation_notes: list[str] = field(default_factory=list)
    """Applied transformations (e.g., 'POSTPOSITIVE_DE')."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "token_range": list(self.token_range),
            "greek_phrase": self.greek_phrase,
            "english_phrase": self.english_phrase,
            "alignment_type": self.alignment_type,
            "transformation_notes": self.transformation_notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SegmentLedger":
        """Deserialize from dictionary."""
        token_range = data.get("token_range", [0, 0])
        return cls(
            token_range=tuple(token_range),
            greek_phrase=data.get("greek_phrase", ""),
            english_phrase=data.get("english_phrase", ""),
            alignment_type=data.get("alignment_type", "literal"),
            transformation_notes=data.get("transformation_notes", []),
        )


@dataclass
class EvidenceClassSummary:
    """Counts by witness type from dossier/support.

    Per non-negotiables: These are EXPLICIT counts by type.
    No collapsing into a single 'support score'.
    """

    manuscript_count: int
    """MANUSCRIPT type witnesses (papyri, uncials, minuscules)."""

    edition_count: int
    """EDITION type witnesses (critical editions like NA28, SBLGNT)."""

    tradition_count: int
    """TRADITION type witnesses (Byz, f1, f13)."""

    other_count: int
    """OTHER type witnesses (fathers, versions)."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "manuscript_count": self.manuscript_count,
            "edition_count": self.edition_count,
            "tradition_count": self.tradition_count,
            "other_count": self.other_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvidenceClassSummary":
        """Deserialize from dictionary."""
        return cls(
            manuscript_count=data.get("manuscript_count", 0),
            edition_count=data.get("edition_count", 0),
            tradition_count=data.get("tradition_count", 0),
            other_count=data.get("other_count", 0),
        )

    @classmethod
    def empty(cls) -> "EvidenceClassSummary":
        """Create empty summary."""
        return cls(
            manuscript_count=0,
            edition_count=0,
            tradition_count=0,
            other_count=0,
        )

    @property
    def total_count(self) -> int:
        """Total witness count across all types."""
        return (
            self.manuscript_count
            + self.edition_count
            + self.tradition_count
            + self.other_count
        )

    @property
    def evidence_class_label(self) -> str:
        """Determine evidence class label (matches Sprint 9 dossier logic).

        Labels are descriptive, NOT value judgments.
        """
        types_present = []
        if self.manuscript_count > 0:
            types_present.append("manuscript")
        if self.edition_count > 0:
            types_present.append("edition")
        if self.tradition_count > 0:
            types_present.append("tradition")
        if self.other_count > 0:
            types_present.append("other")

        if not types_present:
            return "no recorded support"
        if types_present == ["edition"]:
            return "edition-level evidence"
        if types_present == ["manuscript"]:
            return "manuscript-level evidence"
        if types_present == ["tradition"]:
            return "tradition aggregate"
        if "manuscript" in types_present:
            return "manuscript-level evidence"
        if types_present == ["other"]:
            return "secondary evidence"
        return "mixed evidence"


@dataclass
class SensePackCitation:
    """Citation-grade metadata for a sense pack (v0.6.0)."""

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

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        result = {
            "pack_id": self.pack_id,
            "source_id": self.source_id,
        }
        if self.source_title:
            result["source_title"] = self.source_title
        if self.edition:
            result["edition"] = self.edition
        if self.publisher:
            result["publisher"] = self.publisher
        if self.year:
            result["year"] = self.year
        if self.license:
            result["license"] = self.license
        if self.license_url:
            result["license_url"] = self.license_url
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "SensePackCitation":
        """Deserialize from dictionary."""
        return cls(
            pack_id=data.get("pack_id", ""),
            source_id=data.get("source_id", ""),
            source_title=data.get("source_title", ""),
            edition=data.get("edition", ""),
            publisher=data.get("publisher", ""),
            year=data.get("year"),
            license=data.get("license", ""),
            license_url=data.get("license_url", ""),
        )


@dataclass
class LedgerProvenance:
    """Source attribution for the ledger.

    Tracks spine source (always SBLGNT per ADR-007),
    comparative sources used in variant analysis,
    and sense packs used for gloss provenance (v0.6.0).
    """

    spine_source_id: str
    """Always SBLGNT per ADR-007."""

    comparative_sources_used: list[str]
    """Pack IDs used in variant analysis."""

    evidence_class_summary: EvidenceClassSummary = field(
        default_factory=EvidenceClassSummary.empty
    )
    """Counts by type from dossier/support."""

    # v0.6.0: Sense pack citation metadata
    sense_packs_used: list[SensePackCitation] = field(default_factory=list)
    """Sense packs used for gloss lookups with citation-grade metadata."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        result = {
            "spine_source_id": self.spine_source_id,
            "comparative_sources_used": self.comparative_sources_used,
            "evidence_class_summary": self.evidence_class_summary.to_dict(),
        }
        # v0.6.0: Include sense packs if present
        if self.sense_packs_used:
            result["sense_packs_used"] = [sp.to_dict() for sp in self.sense_packs_used]
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "LedgerProvenance":
        """Deserialize from dictionary."""
        ecs_data = data.get("evidence_class_summary", {})
        ecs = (
            EvidenceClassSummary.from_dict(ecs_data)
            if ecs_data
            else EvidenceClassSummary.empty()
        )
        # v0.6.0: Parse sense packs
        sense_packs = [
            SensePackCitation.from_dict(sp) for sp in data.get("sense_packs_used", [])
        ]
        return cls(
            spine_source_id=data.get("spine_source_id", "sblgnt"),
            comparative_sources_used=data.get("comparative_sources_used", []),
            evidence_class_summary=ecs,
            sense_packs_used=sense_packs,
        )


@dataclass
class VerseLedger:
    """Top-level per-verse structure in the ledger.

    Contains complete token-level analysis with optional
    phrase-level segment mappings for fluent translations.
    """

    verse_id: str
    """Internal verse identifier (e.g., 'John.1.18')."""

    normalized_ref: str
    """Human-readable reference (e.g., 'John 1:18')."""

    tokens: list[TokenLedger]
    """Ordered token-level analysis."""

    translation_segments: list[SegmentLedger] = field(default_factory=list)
    """Optional phrase-level mappings."""

    provenance: LedgerProvenance = field(
        default_factory=lambda: LedgerProvenance(
            spine_source_id="sblgnt", comparative_sources_used=[]
        )
    )
    """Source attribution."""

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "verse_id": self.verse_id,
            "normalized_ref": self.normalized_ref,
            "tokens": [t.to_dict() for t in self.tokens],
            "translation_segments": [s.to_dict() for s in self.translation_segments],
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VerseLedger":
        """Deserialize from dictionary."""
        tokens = [TokenLedger.from_dict(t) for t in data.get("tokens", [])]
        segments = [
            SegmentLedger.from_dict(s) for s in data.get("translation_segments", [])
        ]
        prov_data = data.get("provenance", {})
        provenance = (
            LedgerProvenance.from_dict(prov_data)
            if prov_data
            else LedgerProvenance(spine_source_id="sblgnt", comparative_sources_used=[])
        )
        return cls(
            verse_id=data["verse_id"],
            normalized_ref=data.get("normalized_ref", data["verse_id"]),
            tokens=tokens,
            translation_segments=segments,
            provenance=provenance,
        )

    @property
    def token_count(self) -> int:
        """Number of tokens in this verse."""
        return len(self.tokens)

    def get_gloss_sources(self) -> set[str]:
        """Get unique gloss sources used in this verse."""
        return {t.gloss_source for t in self.tokens}

    def get_average_confidence(self) -> dict[str, float]:
        """Get average confidence per layer across all tokens."""
        if not self.tokens:
            return {
                "textual": 0.0,
                "grammatical": 0.0,
                "lexical": 0.0,
                "interpretive": 0.0,
            }

        n = len(self.tokens)
        return {
            "textual": sum(t.confidence.textual for t in self.tokens) / n,
            "grammatical": sum(t.confidence.grammatical for t in self.tokens) / n,
            "lexical": sum(t.confidence.lexical for t in self.tokens) / n,
            "interpretive": sum(t.confidence.interpretive for t in self.tokens) / n,
        }
