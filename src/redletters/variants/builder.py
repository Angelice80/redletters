"""VariantBuilder: Diff comparative editions against spine to create variants.

This module implements Sprint 2 variant generation:
- Compare edition verse text against SBLGNT spine
- Generate VariantUnit + WitnessReading objects for differences
- Assign significance levels (trivial/minor/significant/major)
- Persist to VariantStore idempotently

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
    VariantClassification,
    SignificanceLevel,
)
from redletters.variants.store import VariantStore


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
    ) -> None:
        """Register a comparative edition.

        Args:
            edition_key: Identifier for the edition (e.g., "westcott-hort")
            edition_spine: SpineProvider for the edition
            witness_siglum: Witness siglum for apparatus (e.g., "WH")
            witness_type: Type of witness
            date_range: Century range (e.g., (19, 19) for 19th century)
        """
        self._editions[edition_key] = (
            edition_spine,
            witness_siglum,
            witness_type,
            date_range,
        )

    def build_verse(self, verse_id: str) -> BuildResult:
        """Build variants for a single verse.

        Args:
            verse_id: Verse in "Book.Chapter.Verse" format

        Returns:
            BuildResult with statistics
        """
        result = BuildResult(verses_processed=1)

        # Get spine text
        spine_verse = self._spine.get_verse_text(verse_id)
        if not spine_verse:
            result.errors.append(f"Verse not found in spine: {verse_id}")
            return result

        # Collect readings from editions
        readings: list[EditionReading] = []
        for edition_key, (
            edition_spine,
            siglum,
            wtype,
            date_range,
        ) in self._editions.items():
            edition_verse = edition_spine.get_verse_text(verse_id)
            if edition_verse:
                readings.append(
                    EditionReading(
                        edition_key=edition_key,
                        text=edition_verse.text,
                        normalized_text=self._normalize_text(edition_verse.text),
                        witness_siglum=siglum,
                        witness_type=wtype,
                        date_range=date_range,
                    )
                )

        if not readings:
            # No comparative editions for this verse
            return result

        # Compare each reading against spine
        spine_normalized = self._normalize_text(spine_verse.text)

        differing_readings = []
        for reading in readings:
            if reading.normalized_text != spine_normalized:
                differing_readings.append(reading)

        if not differing_readings:
            # No differences found
            result.variants_unchanged = 1
            return result

        # Build variant unit
        variant = self._build_variant_unit(
            verse_id=verse_id,
            spine_text=spine_verse.text,
            spine_normalized=spine_normalized,
            differing_readings=differing_readings,
        )

        # Check if variant already exists
        existing = self._store.get_variant(verse_id, 0)
        if existing:
            # Update existing
            self._store.save_variant(variant, self._source_id)
            result.variants_updated = 1
        else:
            # Create new
            self._store.save_variant(variant, self._source_id)
            result.variants_created = 1

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

    def _build_variant_unit(
        self,
        verse_id: str,
        spine_text: str,
        spine_normalized: str,
        differing_readings: list[EditionReading],
    ) -> VariantUnit:
        """Build a VariantUnit from spine and differing readings."""
        # SBLGNT reading is always first (index 0)
        readings = [
            WitnessReading(
                surface_text=spine_text,
                witnesses=["SBLGNT"],
                witness_types=[WitnessType.UNCIAL],  # SBLGNT is critical edition
                date_range=(21, 21),  # 21st century edition
                normalized_text=spine_normalized,
                notes="SBLGNT (canonical spine per ADR-007)",
            )
        ]

        # Add differing readings
        for reading in differing_readings:
            readings.append(
                WitnessReading(
                    surface_text=reading.text,
                    witnesses=[reading.witness_siglum],
                    witness_types=[reading.witness_type],
                    date_range=reading.date_range,
                    normalized_text=reading.normalized_text,
                    notes=f"From {reading.edition_key}",
                )
            )

        # Classify and determine significance
        classification = self._classify_variant(spine_normalized, differing_readings)
        significance = self._determine_significance(
            spine_normalized, differing_readings, classification
        )

        return VariantUnit(
            ref=verse_id,
            position=0,  # Verse-level variant
            readings=readings,
            sblgnt_reading_index=0,
            classification=classification,
            significance=significance,
            notes=f"Auto-generated from {len(differing_readings)} edition(s)",
            source_id=self._source_id,
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize Greek text for comparison.

        - NFC normalization
        - Strip punctuation
        - Collapse whitespace
        - Lowercase for comparison
        """
        # NFC normalize
        text = unicodedata.normalize("NFC", text)

        # Strip punctuation (keep Greek letters and spaces)
        text = re.sub(r"[^\w\s]", "", text)

        # Collapse whitespace
        text = " ".join(text.split())

        # Lowercase for comparison
        text = text.lower()

        return text

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
