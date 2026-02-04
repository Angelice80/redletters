"""Variant dossier generation for traceability.

Sprint 8: B4 - Creates detailed dossier of variant readings with
witness support, provenance, and acknowledgement state.

Sprint 9: B3 - Enhanced with support summary, evidence class labels,
and counts by witness type. No epistemic inflation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessType,
    SignificanceLevel,
)
from redletters.variants.store import VariantStore
from redletters.export.schema_versions import DOSSIER_SCHEMA_VERSION


@dataclass
class WitnessSummary:
    """Summary of witnesses grouped by type (legacy)."""

    editions: list[str] = field(default_factory=list)
    papyri: list[str] = field(default_factory=list)
    uncials: list[str] = field(default_factory=list)
    minuscules: list[str] = field(default_factory=list)
    versions: list[str] = field(default_factory=list)
    fathers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "editions": self.editions,
            "papyri": self.papyri,
            "uncials": self.uncials,
            "minuscules": self.minuscules,
            "versions": self.versions,
            "fathers": self.fathers,
        }


# Sprint 9: B3 - Support summary types


@dataclass
class TypeSummary:
    """Summary for a single witness type (Sprint 9: B3)."""

    count: int
    sigla: list[str]
    century_range: tuple[int, int] | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "count": self.count,
            "sigla": self.sigla,
            "century_range": list(self.century_range) if self.century_range else None,
        }


@dataclass
class SupportSummary:
    """Counts and details by witness type (Sprint 9: B3).

    Provides a clear breakdown of support without epistemic inflation.
    """

    total_count: int
    by_type: dict[str, TypeSummary]  # "edition" -> TypeSummary
    earliest_century: int | None
    provenance_packs: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_count": self.total_count,
            "by_type": {k: v.to_dict() for k, v in self.by_type.items()},
            "earliest_century": self.earliest_century,
            "provenance_packs": self.provenance_packs,
        }


def determine_evidence_class(support_summary: SupportSummary) -> str:
    """Determine evidence class label for a reading (Sprint 9: B3).

    Labels:
    - "edition-level evidence": Only critical editions support this reading
    - "manuscript-level evidence": Supported by specific manuscripts
    - "tradition aggregate": Supported by tradition aggregates (Byz, f1, etc.)
    - "mixed evidence": Multiple types of support

    IMPORTANT: These are descriptive labels, NOT value judgments.
    No epistemic inflation (e.g., "earlier is more likely original").
    """
    types_present = set(support_summary.by_type.keys())

    if not types_present:
        return "no recorded support"

    if types_present == {"edition"}:
        return "edition-level evidence"
    elif types_present == {"manuscript"}:
        return "manuscript-level evidence"
    elif types_present == {"tradition"}:
        return "tradition aggregate"
    elif "manuscript" in types_present:
        # Prioritize manuscript if present with other types
        return "manuscript-level evidence"
    elif len(types_present) == 1 and "other" in types_present:
        return "secondary evidence"
    else:
        return "mixed evidence"


# v0.9.0: MinorityMetadata for fringe reading preservation


@dataclass
class MinorityMetadata:
    """Metadata for minority/fringe reading preservation (v0.9.0).

    Provides objective attestation data without false equivalence.
    All fields are nullable to avoid forced inference from thin air.
    """

    attestation_strength: str | None = None
    """Strength of manuscript support: 'strong', 'moderate', 'weak', or None if unknown.

    Conservative derivation:
    - strong: Multiple manuscripts OR early attestation (2nd-3rd century)
    - moderate: Mixed support (some MSS but limited)
    - weak: Single late source OR tradition-only
    - None: Insufficient data to assess
    """

    historical_uptake: str | None = None
    """Historical adoption level: 'high', 'medium', 'low', or None if unknown.

    Must come from pack metadata; not inferred.
    """

    ideological_usage: list[str] = field(default_factory=list)
    """Documented historical associations (controlled vocabulary).

    Only populated when pack metadata explicitly provides this.
    Example: ['adoptionist_controversy', 'trinitarian_debates']
    Empty list is the default - we do not infer ideology.
    """

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "attestation_strength": self.attestation_strength,
            "historical_uptake": self.historical_uptake,
            "ideological_usage": self.ideological_usage,
        }


# v0.9.0: Incentive tags derivation


def derive_incentive_tags(
    readings: list["WitnessReading"],
    support_summaries: list["SupportSummary"],
) -> list[str]:
    """Derive incentive logic tags for a variant unit (v0.9.0).

    These are neutral descriptive labels - not arguments for any position.
    Tags apply to the variant unit as a whole, not individual readings.

    Conservative rules (testable, deterministic):
    - brevity_preference_present: readings differ in length by >= 2 tokens
    - age_bias_risk: earliest_century differs by >= 2 centuries between readings

    Args:
        readings: List of WitnessReading objects in the variant unit
        support_summaries: Corresponding SupportSummary objects for each reading

    Returns:
        List of tag strings (may be empty)
    """
    if len(readings) < 2:
        return []

    tags: list[str] = []

    # Check for brevity preference: readings differ in word count
    texts = [r.surface_text for r in readings]
    word_counts = [len(t.split()) for t in texts]
    if max(word_counts) - min(word_counts) >= 2:
        tags.append("brevity_preference_present")

    # Check for age bias risk: earliest centuries differ significantly
    earliest_centuries = []
    for ss in support_summaries:
        if ss.earliest_century is not None:
            earliest_centuries.append(ss.earliest_century)

    if len(earliest_centuries) >= 2:
        century_spread = max(earliest_centuries) - min(earliest_centuries)
        if century_spread >= 2:
            tags.append("age_bias_risk")

    return tags


def derive_minority_metadata(support_summary: "SupportSummary") -> MinorityMetadata:
    """Derive minority metadata from support summary (v0.9.0).

    Conservative derivation rules:
    - strong: total_count >= 3 OR earliest_century <= 3
    - moderate: total_count >= 1 AND total_count < 3 AND earliest_century in [4, 6]
    - weak: total_count == 1 AND (earliest_century is None or > 6)
    - None: No data (total_count == 0)

    historical_uptake and ideological_usage are NOT derived - must come from metadata.

    Args:
        support_summary: SupportSummary from the reading

    Returns:
        MinorityMetadata with attestation_strength populated
    """
    if support_summary.total_count == 0:
        return MinorityMetadata(attestation_strength=None)

    # Check for strong: multiple witnesses or early attestation
    is_early = (
        support_summary.earliest_century is not None
        and support_summary.earliest_century <= 3
    )
    has_multiple = support_summary.total_count >= 3

    if has_multiple or is_early:
        return MinorityMetadata(attestation_strength="strong")

    # Check for moderate: some support but limited
    is_mid_century = (
        support_summary.earliest_century is not None
        and 4 <= support_summary.earliest_century <= 6
    )
    if support_summary.total_count >= 1 and is_mid_century:
        return MinorityMetadata(attestation_strength="moderate")

    # Otherwise weak
    if support_summary.total_count == 1:
        return MinorityMetadata(attestation_strength="weak")

    # Moderate fallback for 2 witnesses with no early data
    if support_summary.total_count == 2:
        return MinorityMetadata(attestation_strength="moderate")

    return MinorityMetadata(attestation_strength=None)


# v0.8.0: ConsequenceSummary for variant impact analysis


@dataclass
class ConsequenceSummary:
    """Summary of consequences for a variant (v0.8.0).

    Describes what KIND of impact a variant has, without making
    value judgments about which reading is better.

    This is purely descriptive: "This variant affects X" not
    "This variant matters because X".
    """

    affects_surface: bool
    """Does the variant change the Greek surface text?"""

    affects_gloss: bool
    """Does the variant change lemma/sense interpretation?"""

    affects_omission_addition: bool
    """Does the variant involve token presence/absence?"""

    notes: list[str] = field(default_factory=list)
    """Neutral descriptive tags (e.g., "christological term")."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "affects_surface": self.affects_surface,
            "affects_gloss": self.affects_gloss,
            "affects_omission_addition": self.affects_omission_addition,
            "notes": self.notes,
        }


def derive_consequence_summary(classification: str) -> ConsequenceSummary:
    """Derive consequence summary from variant classification (v0.8.0).

    Args:
        classification: VariantClassification value string

    Returns:
        ConsequenceSummary describing the type of impact

    Mapping:
    - OMISSION: surface=T, gloss=F, omission=T
    - ADDITION: surface=T, gloss=F, omission=T
    - SUBSTITUTION: surface=T, gloss=T, omission=F
    - WORD_ORDER: surface=T, gloss=F, omission=F
    - SPELLING: surface=F, gloss=F, omission=F
    - CONFLATION: surface=T, gloss=T, omission=F
    """
    if classification == "omission":
        return ConsequenceSummary(
            affects_surface=True,
            affects_gloss=False,
            affects_omission_addition=True,
            notes=["text absence in some witnesses"],
        )
    elif classification == "addition":
        return ConsequenceSummary(
            affects_surface=True,
            affects_gloss=False,
            affects_omission_addition=True,
            notes=["additional text in some witnesses"],
        )
    elif classification == "substitution":
        return ConsequenceSummary(
            affects_surface=True,
            affects_gloss=True,
            affects_omission_addition=False,
            notes=["different word(s) at this position"],
        )
    elif classification == "word_order":
        return ConsequenceSummary(
            affects_surface=True,
            affects_gloss=False,
            affects_omission_addition=False,
            notes=["word arrangement differs"],
        )
    elif classification == "spelling":
        return ConsequenceSummary(
            affects_surface=False,
            affects_gloss=False,
            affects_omission_addition=False,
            notes=["orthographic variation only"],
        )
    elif classification == "conflation":
        return ConsequenceSummary(
            affects_surface=True,
            affects_gloss=True,
            affects_omission_addition=False,
            notes=["combined or harmonized readings"],
        )
    else:
        # Unknown classification - conservative defaults
        return ConsequenceSummary(
            affects_surface=True,
            affects_gloss=True,
            affects_omission_addition=False,
            notes=[f"classification: {classification}"],
        )


@dataclass
class WitnessInfo:
    """Info about a single witness."""

    siglum: str
    type: str
    century: int | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "siglum": self.siglum,
            "type": self.type,
            "century": self.century,
        }


@dataclass
class DossierReading:
    """A reading in the dossier.

    Sprint 9: Enhanced with support_summary and evidence_class.
    v0.9.0: Added minority_metadata and incentive_tags.
    """

    index: int
    text: str
    is_spine: bool
    witnesses: list[WitnessInfo]
    witness_summary: WitnessSummary
    source_packs: list[str]
    # Sprint 9: B3 - Support summary with counts by type
    support_summary: SupportSummary | None = None
    evidence_class: str = ""
    # v0.9.0: Minority metadata for fringe reading preservation
    minority_metadata: MinorityMetadata | None = None
    # v0.9.0: Incentive logic tags (neutral descriptive labels)
    incentive_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "index": self.index,
            "text": self.text,
            "is_spine": self.is_spine,
            "witnesses": [w.to_dict() for w in self.witnesses],
            "witness_summary": self.witness_summary.to_dict(),
            "source_packs": self.source_packs,
            # Sprint 9: B3
            "evidence_class": self.evidence_class,
            # v0.9.0
            "incentive_tags": self.incentive_tags,
        }
        if self.support_summary:
            result["support_summary"] = self.support_summary.to_dict()
        # v0.9.0: Include minority_metadata
        if self.minority_metadata:
            result["minority_metadata"] = self.minority_metadata.to_dict()
        return result


@dataclass
class DossierReason:
    """Reason classification for a variant."""

    code: str
    summary: str
    detail: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "code": self.code,
            "summary": self.summary,
            "detail": self.detail,
        }


@dataclass
class DossierAcknowledgement:
    """Acknowledgement state for a variant."""

    required: bool
    acknowledged: bool
    acknowledged_reading: int | None = None
    session_id: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "required": self.required,
            "acknowledged": self.acknowledged,
            "acknowledged_reading": self.acknowledged_reading,
            "session_id": self.session_id,
        }


@dataclass
class DossierVariant:
    """A variant in the dossier.

    v0.8.0: Added consequence and confidence_bucket fields.
    """

    ref: str
    position: int
    classification: str
    significance: str
    gating_requirement: str
    reason: DossierReason
    readings: list[DossierReading]
    acknowledgement: DossierAcknowledgement
    # v0.8.0: Consequence summary
    consequence: ConsequenceSummary | None = None
    # v0.8.0: Confidence bucket (from composite score if available)
    confidence_bucket: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "ref": self.ref,
            "position": self.position,
            "classification": self.classification,
            "significance": self.significance,
            "gating_requirement": self.gating_requirement,
            "reason": self.reason.to_dict(),
            "readings": [r.to_dict() for r in self.readings],
            "acknowledgement": self.acknowledgement.to_dict(),
        }
        # v0.8.0: Include consequence if present
        if self.consequence:
            result["consequence"] = self.consequence.to_dict()
        if self.confidence_bucket:
            result["confidence_bucket"] = self.confidence_bucket
        return result


@dataclass
class DossierSpine:
    """Spine info in the dossier."""

    source_id: str
    text: str
    is_default: bool = True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "text": self.text,
            "is_default": self.is_default,
        }


@dataclass
class DossierProvenance:
    """Provenance info in the dossier."""

    spine_source: str
    comparative_packs: list[str]
    build_timestamp: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "spine_source": self.spine_source,
            "comparative_packs": self.comparative_packs,
            "build_timestamp": self.build_timestamp,
        }


# v0.8.0: Coverage summary for absence as data


@dataclass
class PackCoverage:
    """Coverage status for a single pack (v0.8.0).

    Records whether a pack has data for the requested scope,
    treating absence of data as meaningful information.
    """

    pack_id: str
    """ID of the pack being checked."""

    covers_scope: bool
    """Does the pack have data for this scope?"""

    reason: str
    """Reason code: 'has_readings', 'no_readings_in_scope', 'not_in_pack_coverage'."""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "pack_id": self.pack_id,
            "covers_scope": self.covers_scope,
            "reason": self.reason,
        }


@dataclass
class Dossier:
    """Complete variant dossier for a reference.

    v0.8.0: Added coverage_summary for absence-as-data tracking.
    v0.10.0: Added schema_version for validation.
    """

    reference: str
    scope: str
    generated_at: str
    spine: DossierSpine
    variants: list[DossierVariant]
    provenance: DossierProvenance
    witness_density_note: str | None = None
    # v0.8.0: Coverage summary tracking pack participation
    coverage_summary: list[PackCoverage] = field(default_factory=list)
    # v0.10.0: Schema version for validation
    schema_version: str = DOSSIER_SCHEMA_VERSION

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {
            "reference": self.reference,
            "scope": self.scope,
            "generated_at": self.generated_at,
            "spine": self.spine.to_dict(),
            "variants": [v.to_dict() for v in self.variants],
            "provenance": self.provenance.to_dict(),
            "witness_density_note": self.witness_density_note,
            "schema_version": self.schema_version,  # v0.10.0
        }
        # v0.8.0: Include coverage summary if present
        if self.coverage_summary:
            result["coverage_summary"] = [c.to_dict() for c in self.coverage_summary]
        return result


class DossierGenerator:
    """Generates variant dossiers.

    Usage:
        generator = DossierGenerator(variant_store)
        dossier = generator.generate("John.1.18", scope="verse")
    """

    def __init__(
        self,
        variant_store: VariantStore,
        spine_source_id: str = "morphgnt-sblgnt",
        ack_state: dict[str, int] | None = None,
        session_id: str | None = None,
    ):
        """Initialize generator.

        Args:
            variant_store: Store to query variants from
            spine_source_id: ID of the canonical spine source
            ack_state: Dict of variant_ref -> acknowledged_reading_index
            session_id: Session ID for ack state tracking
        """
        self._store = variant_store
        self._spine_source_id = spine_source_id
        self._ack_state = ack_state or {}
        self._session_id = session_id

    def generate(
        self,
        reference: str,
        scope: str = "verse",
    ) -> Dossier:
        """Generate a dossier for a reference.

        Args:
            reference: Scripture reference (e.g., "John.1.18")
            scope: "verse", "passage", "chapter", or "book"

        Returns:
            Dossier object
        """
        # Get variants based on scope
        variants = self._get_variants_for_scope(reference, scope)

        # Build dossier variants
        dossier_variants = [self._build_dossier_variant(v) for v in variants]

        # Collect provenance from all variants
        all_packs: set[str] = set()
        for v in variants:
            all_packs.update(v.get_provenance_summary())

        # Get spine text (from first variant's SBLGNT reading)
        spine_text = ""
        if variants and variants[0].sblgnt_reading:
            spine_text = variants[0].sblgnt_reading.surface_text

        # Generate witness density note
        density_notes = []
        for v in variants:
            note = v.get_witness_density_note()
            if note:
                density_notes.append(f"{v.ref}: {note}")

        # v0.8.0: Build coverage summary (absence as data)
        coverage_summary = self._build_coverage_summary(all_packs, variants)

        return Dossier(
            reference=reference,
            scope=scope,
            generated_at=datetime.now(timezone.utc).isoformat(),
            spine=DossierSpine(
                source_id=self._spine_source_id,
                text=spine_text,
                is_default=True,
            ),
            variants=dossier_variants,
            provenance=DossierProvenance(
                spine_source=self._spine_source_id,
                comparative_packs=sorted(all_packs),
                build_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            witness_density_note="; ".join(density_notes) if density_notes else None,
            coverage_summary=coverage_summary,
        )

    def _get_variants_for_scope(self, reference: str, scope: str) -> list[VariantUnit]:
        """Get variants based on scope."""
        if scope == "verse":
            return self._store.get_variants_for_verse(reference)
        elif scope == "chapter":
            # Parse reference to get book and chapter
            parts = reference.split(".")
            if len(parts) >= 2:
                book, chapter = parts[0], int(parts[1])
                return self._store.get_significant_variants(book=book, chapter=chapter)
        elif scope == "book":
            parts = reference.split(".")
            if parts:
                book = parts[0]
                return self._store.get_significant_variants(book=book)

        # Default: single verse
        return self._store.get_variants_for_verse(reference)

    def _build_coverage_summary(
        self,
        packs_with_readings: set[str],
        variants: list[VariantUnit],
    ) -> list[PackCoverage]:
        """Build coverage summary for all packs (v0.8.0).

        For each pack that contributed to the dossier, record:
        - has_readings: Pack contributed readings to at least one variant
        - no_readings_in_scope: Pack is in provenance but contributed no readings

        Args:
            packs_with_readings: Set of pack IDs that contributed readings
            variants: All variants in this scope

        Returns:
            List of PackCoverage entries
        """
        coverage: list[PackCoverage] = []

        # Collect all packs mentioned anywhere (readings or support_set)
        all_mentioned_packs: set[str] = set()
        packs_with_actual_readings: set[str] = set()

        for variant in variants:
            for reading in variant.readings:
                # Check source_pack_id
                if reading.source_pack_id:
                    all_mentioned_packs.add(reading.source_pack_id)
                    packs_with_actual_readings.add(reading.source_pack_id)
                # Check support_set
                for support in reading.support_set:
                    all_mentioned_packs.add(support.source_pack_id)
                    packs_with_actual_readings.add(support.source_pack_id)

        # Also include any packs from the broader provenance
        all_mentioned_packs.update(packs_with_readings)

        # Build coverage entry for each pack
        for pack_id in sorted(all_mentioned_packs):
            if pack_id in packs_with_actual_readings:
                coverage.append(
                    PackCoverage(
                        pack_id=pack_id,
                        covers_scope=True,
                        reason="has_readings",
                    )
                )
            else:
                coverage.append(
                    PackCoverage(
                        pack_id=pack_id,
                        covers_scope=False,
                        reason="no_readings_in_scope",
                    )
                )

        return coverage

    def _build_support_summary(self, reading) -> SupportSummary:
        """Build support summary from a WitnessReading (Sprint 9: B3).

        Groups support entries by type and computes:
        - Total count
        - Count per type with sigla list
        - Earliest attested century
        - Provenance pack list

        No epistemic inflation: just factual counts and labels.
        """

        by_type: dict[str, TypeSummary] = {}
        earliest_century = None
        packs: set[str] = set()

        # Process support_set
        for support in reading.support_set:
            type_key = support.witness_type.value
            if type_key not in by_type:
                by_type[type_key] = TypeSummary(count=0, sigla=[], century_range=None)

            ts = by_type[type_key]
            ts.count += 1
            if support.witness_siglum not in ts.sigla:
                ts.sigla.append(support.witness_siglum)

            # Track century range
            if support.century_range:
                cent = support.century_range[0]
                if earliest_century is None or cent < earliest_century:
                    earliest_century = cent
                # Update type's century range
                if ts.century_range is None:
                    ts.century_range = support.century_range
                else:
                    ts.century_range = (
                        min(ts.century_range[0], support.century_range[0]),
                        max(ts.century_range[1], support.century_range[1]),
                    )

            packs.add(support.source_pack_id)

        # Also check legacy date_range
        if reading.date_range and reading.date_range[0]:
            if earliest_century is None or reading.date_range[0] < earliest_century:
                earliest_century = reading.date_range[0]

        # Add legacy source_pack_id
        if reading.source_pack_id:
            packs.add(reading.source_pack_id)

        total_count = sum(ts.count for ts in by_type.values())

        return SupportSummary(
            total_count=total_count,
            by_type=by_type,
            earliest_century=earliest_century,
            provenance_packs=sorted(packs),
        )

    def _build_dossier_variant(self, variant: VariantUnit) -> DossierVariant:
        """Build a DossierVariant from a VariantUnit."""
        # First pass: build support summaries for all readings
        support_summaries = [
            self._build_support_summary(reading) for reading in variant.readings
        ]

        # v0.9.0: Derive incentive tags for the unit (applies to all readings)
        unit_incentive_tags = derive_incentive_tags(variant.readings, support_summaries)

        # Build readings
        dossier_readings = []
        for i, reading in enumerate(variant.readings):
            is_spine = i == variant.sblgnt_reading_index

            # Build witness info from legacy fields
            witnesses = []
            for siglum, wtype in zip(reading.witnesses, reading.witness_types):
                century = reading.date_range[0] if reading.date_range else None
                witnesses.append(
                    WitnessInfo(
                        siglum=siglum,
                        type=wtype.value,
                        century=century,
                    )
                )

            # Also add witnesses from support_set (Sprint 9)
            seen_sigla = {w.siglum for w in witnesses}
            for support in reading.support_set:
                if support.witness_siglum not in seen_sigla:
                    century = (
                        support.century_range[0] if support.century_range else None
                    )
                    witnesses.append(
                        WitnessInfo(
                            siglum=support.witness_siglum,
                            type=support.witness_type.value,
                            century=century,
                        )
                    )
                    seen_sigla.add(support.witness_siglum)

            # Build witness summary (legacy)
            summary = WitnessSummary()
            for siglum, wtype in zip(reading.witnesses, reading.witness_types):
                if wtype == WitnessType.PAPYRUS:
                    summary.papyri.append(siglum)
                elif wtype == WitnessType.UNCIAL:
                    summary.uncials.append(siglum)
                elif wtype == WitnessType.MINUSCULE:
                    summary.minuscules.append(siglum)
                elif wtype == WitnessType.VERSION:
                    summary.versions.append(siglum)
                elif wtype == WitnessType.FATHER:
                    summary.fathers.append(siglum)
                else:
                    summary.editions.append(siglum)

            # Source packs (combine legacy and support_set)
            source_packs = reading.get_source_packs()

            # Use pre-computed support summary
            support_summary = support_summaries[i]
            evidence_class = determine_evidence_class(support_summary)

            # v0.9.0: Derive minority metadata from support
            minority_meta = derive_minority_metadata(support_summary)

            dossier_readings.append(
                DossierReading(
                    index=i,
                    text=reading.surface_text,
                    is_spine=is_spine,
                    witnesses=witnesses,
                    witness_summary=summary,
                    source_packs=source_packs,
                    support_summary=support_summary,
                    evidence_class=evidence_class,
                    minority_metadata=minority_meta,
                    incentive_tags=unit_incentive_tags,  # v0.9.0
                )
            )

        # Determine gating requirement
        gating = "none"
        if variant.significance in (
            SignificanceLevel.SIGNIFICANT,
            SignificanceLevel.MAJOR,
        ):
            gating = "requires_acknowledgement"

        # Check ack state
        acked = self._ack_state.get(variant.ref)
        is_acked = acked is not None

        # v0.8.0: Derive consequence summary from classification
        consequence = derive_consequence_summary(variant.classification.value)

        return DossierVariant(
            ref=variant.ref,
            position=variant.position,
            classification=variant.classification.value,
            significance=variant.significance.value,
            gating_requirement=gating,
            reason=DossierReason(
                code=variant.reason_code or "unknown",
                summary=variant.reason_summary or "No reason recorded",
                detail=variant.reason_detail,
            ),
            readings=dossier_readings,
            acknowledgement=DossierAcknowledgement(
                required=variant.requires_acknowledgement,
                acknowledged=is_acked,
                acknowledged_reading=acked,
                session_id=self._session_id,
            ),
            consequence=consequence,
        )


def generate_dossier(
    variant_store: VariantStore,
    reference: str,
    scope: str = "verse",
    spine_source_id: str = "morphgnt-sblgnt",
    ack_state: dict[str, int] | None = None,
    session_id: str | None = None,
) -> Dossier:
    """Convenience function to generate a dossier.

    Args:
        variant_store: Store to query variants from
        reference: Scripture reference
        scope: "verse", "passage", "chapter", or "book"
        spine_source_id: ID of the canonical spine source
        ack_state: Dict of variant_ref -> acknowledged_reading_index
        session_id: Session ID for ack state tracking

    Returns:
        Dossier object
    """
    generator = DossierGenerator(
        variant_store=variant_store,
        spine_source_id=spine_source_id,
        ack_state=ack_state,
        session_id=session_id,
    )
    return generator.generate(reference, scope=scope)
