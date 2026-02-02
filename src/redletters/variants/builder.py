"""VariantBuilder: Diff comparative editions against spine to create variants.

This module implements Sprint 2 variant generation:
- Compare edition verse text against SBLGNT spine
- Generate VariantUnit + WitnessReading objects for differences
- Assign significance levels (trivial/minor/significant/major)
- Persist to VariantStore idempotently

Sprint 9 enhancements:
- Multi-pack aggregation: aggregate diffs from multiple packs
- Support set deduplication: merge identical readings, dedupe witnesses
- Idempotency: re-running build does not duplicate supports

Design assumptions:
- Spine is always SBLGNT (per ADR-007)
- Variants are stored at verse level (not token level)
- Significance is computed deterministically from diff characteristics
- Re-running for same verse is idempotent (no duplicates)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from redletters.sources.spine import SpineProvider
from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessType,
    WitnessSupportType,
    WitnessSupport,
    VariantClassification,
    SignificanceLevel,
)
from redletters.variants.store import VariantStore


def normalize_for_aggregation(text: str) -> str:
    """Canonical normalization for reading comparison (Sprint 9: B2).

    This normalizer is used to determine if two readings are "identical"
    for the purpose of merging support sets.

    Normalization steps:
    1. NFD decomposition to split base chars from combining diacriticals
    2. Remove combining marks (accents, breathing)
    3. Lowercase
    4. Collapse whitespace
    5. Remove punctuation
    """
    # NFD decomposition
    text = unicodedata.normalize("NFD", text)
    # Remove combining characters (accents, breathing marks)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Lowercase
    text = text.lower()
    # Collapse whitespace
    text = " ".join(text.split())
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    return text


def map_witness_type_to_support_type(
    wtype: WitnessType, siglum: str
) -> WitnessSupportType:
    """Map legacy WitnessType to new WitnessSupportType (Sprint 9: B1).

    Args:
        wtype: Legacy WitnessType enum
        siglum: Witness siglum for additional context

    Returns:
        Appropriate WitnessSupportType
    """
    # Check for known edition sigla
    edition_sigla = {"SBLGNT", "WH", "NA28", "NA27", "UBS5", "Treg", "Tisch"}
    if siglum in edition_sigla:
        return WitnessSupportType.EDITION

    # Check for tradition aggregates
    tradition_sigla = {"Byz", "f1", "f13", "M", "K"}
    if siglum in tradition_sigla:
        return WitnessSupportType.TRADITION

    # Map by WitnessType
    if wtype == WitnessType.PAPYRUS:
        return WitnessSupportType.MANUSCRIPT
    elif wtype == WitnessType.UNCIAL:
        return WitnessSupportType.MANUSCRIPT
    elif wtype == WitnessType.MINUSCULE:
        return WitnessSupportType.MANUSCRIPT
    elif wtype == WitnessType.VERSION:
        return WitnessSupportType.OTHER
    elif wtype == WitnessType.FATHER:
        return WitnessSupportType.OTHER
    else:
        return WitnessSupportType.OTHER


def dedupe_support_set(
    supports: list[WitnessSupport],
) -> tuple[list[WitnessSupport], list[str]]:
    """Deduplicate support entries (Sprint 9: B2).

    Rules:
    - Same siglum from same pack → keep first only
    - Same siglum from different packs → keep both (different provenance)
    - Returns (deduped_list, warnings)
    """
    seen: dict[tuple[str, str], WitnessSupport] = {}  # (siglum, pack_id) -> support
    warnings: list[str] = []
    result: list[WitnessSupport] = []

    for s in supports:
        key = (s.witness_siglum, s.source_pack_id)
        if key in seen:
            # Exact duplicate (same siglum, same pack) → skip
            continue
        else:
            # Check if same siglum from different pack
            same_siglum = [
                existing
                for (sig, _), existing in seen.items()
                if sig == s.witness_siglum
            ]
            if same_siglum:
                # Same witness from different pack - keep both but warn
                warnings.append(
                    f"Witness {s.witness_siglum} appears in multiple packs: "
                    f"{same_siglum[0].source_pack_id}, {s.source_pack_id}"
                )
            seen[key] = s
            result.append(s)

    return result, warnings


@dataclass
class VariantReason:
    """Reason classification for a variant (Sprint 7: B4)."""

    code: str  # theological_keyword, article_particle, word_order, spelling, lexical
    summary: str  # Human-readable reason
    detail: str | None = None  # Additional detail if available


@dataclass
class BuildResult:
    """Result of building variants for a verse or range."""

    verses_processed: int = 0
    variants_created: int = 0
    variants_updated: int = 0
    variants_unchanged: int = 0
    errors: list[str] = field(default_factory=list)

    def merge(self, other: "BuildResult") -> "BuildResult":
        """Merge another result into this one."""
        self.verses_processed += other.verses_processed
        self.variants_created += other.variants_created
        self.variants_updated += other.variants_updated
        self.variants_unchanged += other.variants_unchanged
        self.errors.extend(other.errors)
        return self


@dataclass
class EditionReading:
    """A reading from a specific edition."""

    edition_key: str
    text: str
    normalized_text: str
    witness_siglum: str  # E.g., "WH" for Westcott-Hort
    witness_type: WitnessType = WitnessType.VERSION
    date_range: tuple[int, int] | None = None
    # Sprint 8: Provenance tracking (B3)
    source_pack_id: str | None = None
    # Sprint 9: Support type for aggregation (B1)
    support_type: WitnessSupportType | None = None

    def to_witness_support(self) -> WitnessSupport:
        """Convert to WitnessSupport for aggregation (Sprint 9: B1)."""
        return WitnessSupport(
            witness_siglum=self.witness_siglum,
            witness_type=self.support_type
            or map_witness_type_to_support_type(self.witness_type, self.witness_siglum),
            source_pack_id=self.source_pack_id or self.edition_key,
            century_range=self.date_range,
        )


class VariantBuilder:
    """Build variants by comparing editions against spine.

    Usage:
        builder = VariantBuilder(spine, variant_store)
        builder.add_edition("westcott-hort", wh_spine, "WH")

        # Build for single verse
        result = builder.build_verse("John.1.18")

        # Build for range
        result = builder.build_range("John.1.1", "John.1.18")

        # Build on-demand (returns existing or builds new)
        variants = builder.ensure_variants("John.1.18")
    """

    def __init__(
        self,
        spine: SpineProvider,
        variant_store: VariantStore,
        source_id: int | None = None,
    ):
        """Initialize builder.

        Args:
            spine: Canonical spine provider (SBLGNT)
            variant_store: Store for persisting variants
            source_id: Optional source ID for provenance tracking
        """
        self._spine = spine
        self._store = variant_store
        self._source_id = source_id
        self._editions: dict[
            str, tuple[SpineProvider, str, WitnessType, tuple[int, int] | None]
        ] = {}

    def add_edition(
        self,
        edition_key: str,
        edition_spine: SpineProvider,
        witness_siglum: str,
        witness_type: WitnessType = WitnessType.VERSION,
        date_range: tuple[int, int] | None = None,
        source_pack_id: str | None = None,
        support_type: WitnessSupportType | None = None,
    ) -> None:
        """Register a comparative edition.

        Args:
            edition_key: Identifier for the edition (e.g., "westcott-hort")
            edition_spine: SpineProvider for the edition
            witness_siglum: Witness siglum for apparatus (e.g., "WH")
            witness_type: Type of witness (legacy)
            date_range: Century range (e.g., (19, 19) for 19th century)
            source_pack_id: Pack ID for provenance tracking (Sprint 8)
            support_type: WitnessSupportType for Sprint 9 aggregation (optional)
        """
        self._editions[edition_key] = (
            edition_spine,
            witness_siglum,
            witness_type,
            date_range,
            source_pack_id or edition_key,  # Default to edition_key if not provided
            support_type,  # Sprint 9: B1
        )

    def build_verse(self, verse_id: str, merge_mode: bool = True) -> BuildResult:
        """Build variants for a single verse.

        Args:
            verse_id: Verse in "Book.Chapter.Verse" format
            merge_mode: If True, merge with existing variant (Sprint 9).
                       If False, replace existing variant (legacy behavior).

        Returns:
            BuildResult with statistics

        Sprint 9: Multi-pack aggregation with merge_mode=True:
        - If variant already exists, merge new readings by normalized text
        - Add new support entries without duplicating
        - Idempotent: re-running doesn't create duplicates
        """
        result = BuildResult(verses_processed=1)

        # Get spine text
        spine_verse = self._spine.get_verse_text(verse_id)
        if not spine_verse:
            result.errors.append(f"Verse not found in spine: {verse_id}")
            return result

        # Collect readings from editions
        readings: list[EditionReading] = []
        for edition_key, edition_data in self._editions.items():
            # Support 4-tuple (legacy), 5-tuple (Sprint 8), and 6-tuple (Sprint 9)
            if len(edition_data) >= 6:
                (
                    edition_spine,
                    siglum,
                    wtype,
                    date_range,
                    source_pack_id,
                    support_type,
                ) = edition_data
            elif len(edition_data) == 5:
                edition_spine, siglum, wtype, date_range, source_pack_id = edition_data
                support_type = None
            else:
                edition_spine, siglum, wtype, date_range = edition_data
                source_pack_id = edition_key
                support_type = None

            edition_verse = edition_spine.get_verse_text(verse_id)
            if edition_verse:
                readings.append(
                    EditionReading(
                        edition_key=edition_key,
                        text=edition_verse.text,
                        normalized_text=normalize_for_aggregation(edition_verse.text),
                        witness_siglum=siglum,
                        witness_type=wtype,
                        date_range=date_range,
                        source_pack_id=source_pack_id,
                        support_type=support_type,
                    )
                )

        if not readings:
            # No comparative editions for this verse
            return result

        # Normalize spine text using aggregation normalizer
        spine_normalized = normalize_for_aggregation(spine_verse.text)

        # Separate readings into spine-matching and differing
        differing_readings = []
        for reading in readings:
            if reading.normalized_text != spine_normalized:
                differing_readings.append(reading)

        if not differing_readings:
            # No differences found
            result.variants_unchanged = 1
            return result

        # Sprint 9: Check for existing variant and merge if merge_mode
        existing_variant_id = self._store.get_variant_id(verse_id, 0)

        if existing_variant_id and merge_mode:
            # Merge mode: aggregate with existing variant
            result = self._merge_into_existing(
                verse_id=verse_id,
                variant_id=existing_variant_id,
                spine_normalized=spine_normalized,
                differing_readings=differing_readings,
                result=result,
            )
        else:
            # Build new variant unit (or replace existing)
            variant = self._build_variant_unit(
                verse_id=verse_id,
                spine_text=spine_verse.text,
                spine_normalized=spine_normalized,
                differing_readings=differing_readings,
            )

            if existing_variant_id:
                self._store.save_variant(variant, self._source_id)
                result.variants_updated = 1
            else:
                self._store.save_variant(variant, self._source_id)
                result.variants_created = 1

        return result

    def _merge_into_existing(
        self,
        verse_id: str,
        variant_id: int,
        spine_normalized: str,
        differing_readings: list[EditionReading],
        result: BuildResult,
    ) -> BuildResult:
        """Merge new readings into an existing variant (Sprint 9: B2).

        For each differing reading:
        - If normalized text matches existing reading → add support entry
        - If normalized text is new → add new reading with support

        This ensures idempotency: re-running doesn't duplicate.
        """
        supports_added = 0
        readings_added = 0

        for reading in differing_readings:
            # Check if this reading's normalized text already exists
            existing_reading_id = self._store.get_reading_id_by_normalized(
                verse_id, 0, reading.normalized_text
            )

            # Create support entry
            support = reading.to_witness_support()

            if existing_reading_id:
                # Add support to existing reading (idempotent via UNIQUE constraint)
                added = self._store.add_support_to_reading(existing_reading_id, support)
                if added:
                    supports_added += 1
            else:
                # Create new reading with support
                new_reading = WitnessReading(
                    surface_text=reading.text,
                    witnesses=[reading.witness_siglum],
                    witness_types=[reading.witness_type],
                    date_range=reading.date_range,
                    normalized_text=reading.normalized_text,
                    notes=f"From {reading.edition_key}",
                    source_pack_id=reading.source_pack_id,
                    support_set=[support],
                )
                self._store.add_reading_to_variant(
                    variant_id, new_reading, self._source_id
                )
                readings_added += 1

        self._store._conn.commit()

        if supports_added > 0 or readings_added > 0:
            result.variants_updated = 1
        else:
            result.variants_unchanged = 1

        return result

    def build_range(self, start_verse: str, end_verse: str) -> BuildResult:
        """Build variants for a verse range.

        Args:
            start_verse: Starting verse ID
            end_verse: Ending verse ID (inclusive)

        Returns:
            BuildResult with statistics
        """
        result = BuildResult()

        # Parse verse IDs
        start_parts = start_verse.split(".")
        end_parts = end_verse.split(".")

        if len(start_parts) < 3 or len(end_parts) < 3:
            result.errors.append(f"Invalid verse range: {start_verse} - {end_verse}")
            return result

        start_book = start_parts[0]
        end_book = end_parts[0]

        if start_book != end_book:
            result.errors.append(
                f"Cross-book ranges not supported: {start_book} to {end_book}"
            )
            return result

        try:
            start_ch = int(start_parts[1])
            start_v = int(start_parts[2])
            end_ch = int(end_parts[1])
            end_v = int(end_parts[2])
        except ValueError as e:
            result.errors.append(f"Invalid verse numbers: {e}")
            return result

        # Build each verse in range
        for chapter in range(start_ch, end_ch + 1):
            v_start = start_v if chapter == start_ch else 1
            v_end = (
                end_v if chapter == end_ch else 200
            )  # High number, will stop at missing

            for verse in range(v_start, v_end + 1):
                verse_id = f"{start_book}.{chapter}.{verse}"
                if not self._spine.has_verse(verse_id):
                    continue

                verse_result = self.build_verse(verse_id)
                result.merge(verse_result)

        return result

    def ensure_variants(self, verse_id: str) -> list[VariantUnit]:
        """Ensure variants exist for a verse (build on-demand if missing).

        Args:
            verse_id: Verse identifier

        Returns:
            List of VariantUnit objects for the verse
        """
        # Check if variants already exist
        existing = self._store.get_variants_for_verse(verse_id)
        if existing:
            return existing

        # Build variants on-demand
        if self._editions:
            self.build_verse(verse_id)

        return self._store.get_variants_for_verse(verse_id)

    def build_chapter(self, book: str, chapter: int) -> BuildResult:
        """Build variants for an entire chapter (Sprint 7: B2).

        Args:
            book: Book name (e.g., "John")
            chapter: Chapter number

        Returns:
            BuildResult with statistics
        """
        result = BuildResult()

        # Get all verses for this chapter from spine
        for verse in range(1, 200):  # Max reasonable verse count
            verse_id = f"{book}.{chapter}.{verse}"
            if not self._spine.has_verse(verse_id):
                if verse > 1:
                    # End of chapter
                    break
                continue

            verse_result = self.build_verse(verse_id)
            result.merge(verse_result)

        return result

    def build_book(self, book: str) -> BuildResult:
        """Build variants for an entire book (Sprint 7: B2).

        Args:
            book: Book name (e.g., "John")

        Returns:
            BuildResult with statistics
        """
        result = BuildResult()

        # Build each chapter
        for chapter in range(1, 100):  # Max reasonable chapter count
            verse_id = f"{book}.{chapter}.1"
            if not self._spine.has_verse(verse_id):
                if chapter > 1:
                    break
                continue

            chapter_result = self.build_chapter(book, chapter)
            result.merge(chapter_result)

        return result

    def build_passage(self, start_ref: str, end_ref: str) -> BuildResult:
        """Build variants for a passage range (Sprint 7: B2).

        Alias for build_range with better naming.
        """
        return self.build_range(start_ref, end_ref)

    def _build_variant_unit(
        self,
        verse_id: str,
        spine_text: str,
        spine_normalized: str,
        differing_readings: list[EditionReading],
    ) -> VariantUnit:
        """Build a VariantUnit from spine and differing readings.

        Sprint 9: Enhanced with support_set for each reading and
        aggregation of readings with identical normalized text.
        """
        # SBLGNT reading is always first (index 0)
        # Sprint 9: Add SBLGNT to support_set
        sblgnt_support = WitnessSupport(
            witness_siglum="SBLGNT",
            witness_type=WitnessSupportType.EDITION,
            source_pack_id="sblgnt-canonical",
            century_range=(21, 21),
        )
        readings = [
            WitnessReading(
                surface_text=spine_text,
                witnesses=["SBLGNT"],
                witness_types=[WitnessType.UNCIAL],  # SBLGNT is critical edition
                date_range=(21, 21),  # 21st century edition
                normalized_text=spine_normalized,
                notes="SBLGNT (canonical spine per ADR-007)",
                support_set=[sblgnt_support],
            )
        ]

        # Sprint 9: Group differing readings by normalized text and merge support
        grouped: dict[str, list[EditionReading]] = {}
        for reading in differing_readings:
            norm = reading.normalized_text
            if norm not in grouped:
                grouped[norm] = []
            grouped[norm].append(reading)

        # Build one WitnessReading per unique normalized text
        for norm_text, group in grouped.items():
            # Collect all support entries for this reading
            support_entries = [r.to_witness_support() for r in group]
            deduped_supports, _ = dedupe_support_set(support_entries)

            # Use first reading's surface text (they may vary in accents)
            first = group[0]

            # Collect witnesses for legacy fields
            witnesses = list({r.witness_siglum for r in group})
            witness_types = [r.witness_type for r in group[: len(witnesses)]]

            # Determine date range from all supports
            earliest = None
            latest = None
            for s in deduped_supports:
                if s.century_range:
                    if earliest is None or s.century_range[0] < earliest:
                        earliest = s.century_range[0]
                    if latest is None or s.century_range[1] > latest:
                        latest = s.century_range[1]

            # Build notes listing all contributing editions
            edition_keys = list({r.edition_key for r in group})
            notes = f"From {', '.join(edition_keys)}"

            readings.append(
                WitnessReading(
                    surface_text=first.text,
                    witnesses=witnesses,
                    witness_types=witness_types,
                    date_range=(earliest, latest) if earliest else None,
                    normalized_text=norm_text,
                    notes=notes,
                    source_pack_id=first.source_pack_id,  # First pack for legacy field
                    support_set=deduped_supports,
                )
            )

        # Classify and determine significance
        classification = self._classify_variant(spine_normalized, differing_readings)
        significance = self._determine_significance(
            spine_normalized, differing_readings, classification
        )

        # Classify reason (Sprint 7: B4)
        reason = self._classify_reason(
            spine_normalized, differing_readings, classification, significance
        )

        return VariantUnit(
            ref=verse_id,
            position=0,  # Verse-level variant
            readings=readings,
            sblgnt_reading_index=0,
            classification=classification,
            significance=significance,
            notes=f"Auto-generated from {len(differing_readings)} edition(s). Reason: {reason.summary}",
            source_id=self._source_id,
            reason_code=reason.code,
            reason_summary=reason.summary,
            reason_detail=reason.detail,
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize Greek text for comparison.

        Sprint 9: Now delegates to normalize_for_aggregation for consistency
        across all variant building operations.
        """
        return normalize_for_aggregation(text)

    def _classify_variant(
        self,
        spine_normalized: str,
        readings: list[EditionReading],
    ) -> VariantClassification:
        """Classify the type of variant.

        Uses simple heuristics:
        - If word counts differ significantly: OMISSION or ADDITION
        - If words are reordered: WORD_ORDER
        - If single word differs: SUBSTITUTION
        - If minor character differences: SPELLING
        """
        spine_words = spine_normalized.split()

        for reading in readings:
            reading_words = reading.normalized_text.split()

            word_diff = len(spine_words) - len(reading_words)

            if word_diff > 2:
                return VariantClassification.OMISSION
            elif word_diff < -2:
                return VariantClassification.ADDITION
            elif abs(word_diff) <= 2 and word_diff != 0:
                # Check if it's really omission/addition vs substitution
                common = set(spine_words) & set(reading_words)
                if len(common) > len(spine_words) * 0.7:
                    return (
                        VariantClassification.OMISSION
                        if word_diff > 0
                        else VariantClassification.ADDITION
                    )
                return VariantClassification.SUBSTITUTION
            else:
                # Same word count
                if set(spine_words) == set(reading_words):
                    return VariantClassification.WORD_ORDER
                elif self._is_spelling_difference(
                    spine_normalized, reading.normalized_text
                ):
                    return VariantClassification.SPELLING
                else:
                    return VariantClassification.SUBSTITUTION

        return VariantClassification.SUBSTITUTION

    def _is_spelling_difference(self, text1: str, text2: str) -> bool:
        """Check if difference is just spelling (high similarity)."""
        ratio = SequenceMatcher(None, text1, text2).ratio()
        return ratio > 0.9

    def _strip_accents(self, text: str) -> str:
        """Strip Greek accents for keyword matching."""
        # NFD decomposition splits base chars from accents
        import unicodedata

        nfd = unicodedata.normalize("NFD", text)
        # Keep only non-combining characters (remove accents)
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    def _determine_significance(
        self,
        spine_normalized: str,
        readings: list[EditionReading],
        classification: VariantClassification,
    ) -> SignificanceLevel:
        """Determine significance level based on variant characteristics.

        Significance heuristics:
        - Theological keywords differences are MAJOR (checked first!)
        - SPELLING differences (without theological impact) are TRIVIAL
        - WORD_ORDER is usually MINOR
        - Single word SUBSTITUTION is MINOR unless it's a key term
        - Multi-word OMISSION/ADDITION is SIGNIFICANT
        """
        # Check for theological keywords FIRST (before classification check)
        # These are checked without accents for robust matching
        theological_terms = {
            "θεος",
            "θεου",
            "θεον",
            "θεω",  # God
            "χριστος",
            "χριστου",
            "χριστον",  # Christ
            "ιησους",
            "ιησου",
            "ιησουν",  # Jesus
            "κυριος",
            "κυριου",
            "κυριον",  # Lord
            "πνευμα",
            "πνευματος",  # Spirit
            "υιος",
            "υιου",
            "υιον",  # Son
            "πατηρ",
            "πατρος",  # Father
            "μονογενης",  # Only-begotten
            "αμαρτια",
            "αμαρτιας",  # Sin
            "πιστις",
            "πιστεως",  # Faith
        }

        # Strip accents for robust matching
        spine_stripped = self._strip_accents(spine_normalized)

        for reading in readings:
            reading_stripped = self._strip_accents(reading.normalized_text)
            for term in theological_terms:
                # Check if term presence differs between spine and reading
                term_in_spine = term in spine_stripped
                term_in_reading = term in reading_stripped
                if term_in_spine != term_in_reading:
                    return SignificanceLevel.MAJOR

        # Now check other criteria
        # Spelling without theological impact is trivial
        if classification == VariantClassification.SPELLING:
            return SignificanceLevel.TRIVIAL

        # Word order is usually minor
        if classification == VariantClassification.WORD_ORDER:
            return SignificanceLevel.MINOR

        # Check word count difference
        spine_words = spine_normalized.split()
        max_diff = 0
        for reading in readings:
            reading_words = reading.normalized_text.split()
            diff = abs(len(spine_words) - len(reading_words))
            max_diff = max(max_diff, diff)

        # Significant differences in word count
        if max_diff >= 3:
            return SignificanceLevel.SIGNIFICANT

        # Default based on classification
        if classification in (
            VariantClassification.OMISSION,
            VariantClassification.ADDITION,
        ):
            return (
                SignificanceLevel.SIGNIFICANT
                if max_diff >= 2
                else SignificanceLevel.MINOR
            )

        return SignificanceLevel.MINOR

    def _classify_reason(
        self,
        spine_normalized: str,
        readings: list[EditionReading],
        classification: VariantClassification,
        significance: SignificanceLevel,
    ) -> VariantReason:
        """Classify the reason for a variant (Sprint 7: B4).

        Returns a human-readable reason for why the variant exists.
        """
        # Check for theological keywords first
        theological_terms = {
            "θεος": "God",
            "θεου": "God",
            "θεον": "God",
            "θεω": "God",
            "χριστος": "Christ",
            "χριστου": "Christ",
            "χριστον": "Christ",
            "ιησους": "Jesus",
            "ιησου": "Jesus",
            "ιησουν": "Jesus",
            "κυριος": "Lord",
            "κυριου": "Lord",
            "κυριον": "Lord",
            "πνευμα": "Spirit",
            "πνευματος": "Spirit",
            "υιος": "Son",
            "υιου": "Son",
            "υιον": "Son",
            "πατηρ": "Father",
            "πατρος": "Father",
            "μονογενης": "only-begotten",
        }

        spine_stripped = self._strip_accents(spine_normalized)

        for reading in readings:
            reading_stripped = self._strip_accents(reading.normalized_text)
            for term, meaning in theological_terms.items():
                term_in_spine = term in spine_stripped
                term_in_reading = term in reading_stripped
                if term_in_spine != term_in_reading:
                    if term_in_spine:
                        return VariantReason(
                            code="theological_keyword",
                            summary=f"Theological term change ({meaning})",
                            detail=f"Spine has '{term}' ({meaning}), alternate does not",
                        )
                    else:
                        return VariantReason(
                            code="theological_keyword",
                            summary=f"Theological term change ({meaning})",
                            detail=f"Alternate has '{term}' ({meaning}), spine does not",
                        )

        # Check for article/particle only differences
        function_words = {
            "ο",
            "η",
            "το",
            "τον",
            "την",
            "του",
            "της",
            "τω",
            "τη",
            "και",
            "δε",
            "γαρ",
            "αλλα",
            "ουν",
            "τε",
        }

        spine_words = set(self._strip_accents(spine_normalized).split())
        for reading in readings:
            reading_words = set(self._strip_accents(reading.normalized_text).split())
            diff = spine_words.symmetric_difference(reading_words)
            if diff and all(w in function_words for w in diff):
                return VariantReason(
                    code="article_particle",
                    summary="Function word variation",
                    detail=f"Difference in: {', '.join(diff)}",
                )

        # Check classification-based reasons
        if classification == VariantClassification.WORD_ORDER:
            return VariantReason(
                code="word_order",
                summary="Word order difference",
                detail="Same words in different order",
            )

        if classification == VariantClassification.SPELLING:
            return VariantReason(
                code="spelling",
                summary="Spelling variation",
                detail="Orthographic difference only",
            )

        if classification == VariantClassification.OMISSION:
            return VariantReason(
                code="omission",
                summary="Text omission",
                detail="Words present in one reading but not the other",
            )

        if classification == VariantClassification.ADDITION:
            return VariantReason(
                code="addition",
                summary="Text addition",
                detail="Additional words in one reading",
            )

        # Default: lexical variation
        return VariantReason(
            code="lexical",
            summary="Lexical variation",
            detail="Different word choice",
        )
