"""Integration tests for passage mode (Sprint 4).

Tests cover:
- Single verse parsing and translation
- Multi-verse range parsing
- Aggregated gating for multi-verse passages
- Acknowledgement flow for multi-verse gates
- ADR compliance (007-010)
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
import pytest

from redletters.pipeline.orchestrator import translate_passage, acknowledge_variant
from redletters.pipeline.schemas import GateResponsePayload, TranslateResponse
from redletters.pipeline.passage_ref import parse_passage_ref, expand_verse_ids
from redletters.variants.store import VariantStore
from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    VariantClassification,
    SignificanceLevel,
    WitnessType,
)
from redletters.sources.spine import FixtureSpine


# Dummy path for FixtureSpine that doesn't exist (creates empty spine for add_verse)
DUMMY_FIXTURE_PATH = Path("/tmp/nonexistent_passage_test_fixture.json")


@pytest.fixture
def db_conn():
    """Create in-memory database with required schemas."""
    from redletters.gates.state import AcknowledgementStore

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Create tokens table (minimal for testing)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY,
            book TEXT NOT NULL,
            chapter INTEGER NOT NULL,
            verse INTEGER NOT NULL,
            position INTEGER NOT NULL,
            surface TEXT NOT NULL,
            lemma TEXT,
            morph TEXT,
            is_red_letter INTEGER DEFAULT 0
        )
    """)

    # Create variant store schema
    variant_store = VariantStore(conn)
    variant_store.init_schema()

    # Create acknowledgement schema using the canonical schema
    ack_store = AcknowledgementStore(conn)
    ack_store.init_schema()

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def spine_with_verses():
    """Create a fixture spine with test verses."""
    spine = FixtureSpine(DUMMY_FIXTURE_PATH, source_key="test-sblgnt")

    # John 1:18 - famous variant verse
    spine.add_verse(
        "John.1.18",
        "θεὸν οὐδεὶς ἑώρακεν πώποτε μονογενὴς θεὸς ὁ ὢν εἰς τὸν κόλπον τοῦ πατρὸς ἐκεῖνος ἐξηγήσατο",
        tokens=[
            {"word": "θεὸν", "lemma": "θεός", "parse_code": "N-ASM"},
            {"word": "οὐδεὶς", "lemma": "οὐδείς", "parse_code": "A-NSM"},
            {"word": "ἑώρακεν", "lemma": "ὁράω", "parse_code": "V-RAI-3S"},
            {"word": "πώποτε", "lemma": "πώποτε", "parse_code": "ADV"},
            {"word": "μονογενὴς", "lemma": "μονογενής", "parse_code": "A-NSM"},
            {"word": "θεὸς", "lemma": "θεός", "parse_code": "N-NSM"},
            {"word": "ὁ", "lemma": "ὁ", "parse_code": "D-NSM"},
            {"word": "ὢν", "lemma": "εἰμί", "parse_code": "V-PAP-NSM"},
            {"word": "εἰς", "lemma": "εἰς", "parse_code": "PREP"},
            {"word": "τὸν", "lemma": "ὁ", "parse_code": "D-ASM"},
            {"word": "κόλπον", "lemma": "κόλπος", "parse_code": "N-ASM"},
            {"word": "τοῦ", "lemma": "ὁ", "parse_code": "D-GSM"},
            {"word": "πατρὸς", "lemma": "πατήρ", "parse_code": "N-GSM"},
            {"word": "ἐκεῖνος", "lemma": "ἐκεῖνος", "parse_code": "D-NSM"},
            {"word": "ἐξηγήσατο", "lemma": "ἐξηγέομαι", "parse_code": "V-ADI-3S"},
        ],
    )

    # John 1:19 - follows 1:18
    spine.add_verse(
        "John.1.19",
        "Καὶ αὕτη ἐστὶν ἡ μαρτυρία τοῦ Ἰωάννου",
        tokens=[
            {"word": "Καὶ", "lemma": "καί", "parse_code": "CONJ"},
            {"word": "αὕτη", "lemma": "οὗτος", "parse_code": "D-NSF"},
            {"word": "ἐστὶν", "lemma": "εἰμί", "parse_code": "V-PAI-3S"},
            {"word": "ἡ", "lemma": "ὁ", "parse_code": "D-NSF"},
            {"word": "μαρτυρία", "lemma": "μαρτυρία", "parse_code": "N-NSF"},
            {"word": "τοῦ", "lemma": "ὁ", "parse_code": "D-GSM"},
            {"word": "Ἰωάννου", "lemma": "Ἰωάννης", "parse_code": "N-GSM"},
        ],
    )

    # Matthew 3:2 - another test verse
    spine.add_verse(
        "Matthew.3.2",
        "μετανοεῖτε ἤγγικεν γὰρ ἡ βασιλεία τῶν οὐρανῶν",
        tokens=[
            {"word": "μετανοεῖτε", "lemma": "μετανοέω", "parse_code": "V-PAM-2P"},
            {"word": "ἤγγικεν", "lemma": "ἐγγίζω", "parse_code": "V-RAI-3S"},
            {"word": "γὰρ", "lemma": "γάρ", "parse_code": "CONJ"},
            {"word": "ἡ", "lemma": "ὁ", "parse_code": "D-NSF"},
            {"word": "βασιλεία", "lemma": "βασιλεία", "parse_code": "N-NSF"},
            {"word": "τῶν", "lemma": "ὁ", "parse_code": "D-GPM"},
            {"word": "οὐρανῶν", "lemma": "οὐρανός", "parse_code": "N-GPM"},
        ],
    )

    return spine


@pytest.fixture
def variant_store_with_major_variant(db_conn):
    """Create variant store with a MAJOR variant at John 1:18."""
    store = VariantStore(db_conn)

    # Famous John 1:18 variant: μονογενὴς θεός vs ὁ μονογενὴς υἱός
    variant = VariantUnit(
        ref="John.1.18",
        position=5,  # Position of μονογενὴς θεός
        readings=[
            WitnessReading(
                surface_text="μονογενὴς θεός",
                witnesses=["P66", "P75", "א", "B", "C*", "L"],
                witness_types=[
                    WitnessType.PAPYRUS,
                    WitnessType.PAPYRUS,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                ],
                date_range=(2, 5),
            ),
            WitnessReading(
                surface_text="ὁ μονογενὴς υἱός",
                witnesses=["A", "C³", "Θ", "Ψ", "f¹", "f¹³", "33", "Byz"],
                witness_types=[
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.UNCIAL,
                    WitnessType.MINUSCULE,
                    WitnessType.MINUSCULE,
                    WitnessType.MINUSCULE,
                    WitnessType.MINUSCULE,
                ],
                date_range=(4, 9),
            ),
        ],
        sblgnt_reading_index=0,
        classification=VariantClassification.SUBSTITUTION,
        significance=SignificanceLevel.MAJOR,
    )

    store.save_variant(variant)
    return store


class TestPassageRefParsing:
    """Tests for passage reference parsing in pipeline context."""

    def test_single_verse_parses_correctly(self):
        """Single verse reference produces one verse_id."""
        parsed = parse_passage_ref("John 1:18")
        assert parsed.verse_ids == ["John.1.18"]
        assert parsed.normalized_ref == "John 1:18"

    def test_range_parses_to_ordered_verse_ids(self):
        """Range reference produces ordered list of verse_ids."""
        parsed = parse_passage_ref("John 1:18-19")
        assert parsed.verse_ids == ["John.1.18", "John.1.19"]
        assert parsed.normalized_ref == "John 1:18-19"

    def test_en_dash_range_parses_correctly(self):
        """En-dash range parses same as hyphen."""
        parsed = parse_passage_ref("John 1:18–19")  # en-dash
        assert parsed.verse_ids == ["John.1.18", "John.1.19"]

    def test_abbreviated_book_normalizes(self):
        """Book abbreviations normalize to canonical names."""
        parsed = parse_passage_ref("Jn 1:18")
        assert parsed.book == "John"
        assert parsed.verse_ids == ["John.1.18"]

    def test_matthew_variants(self):
        """Matthew abbreviations work correctly."""
        assert expand_verse_ids("Matt 3:2") == ["Matthew.3.2"]
        assert expand_verse_ids("Mt 3:2") == ["Matthew.3.2"]


class TestSingleVerseTranslation:
    """Tests for single verse translation."""

    def test_single_verse_translates_successfully(self, db_conn, spine_with_verses):
        """Single verse without variants translates successfully."""
        result = translate_passage(
            conn=db_conn,
            reference="Matthew 3:2",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        assert result.response_type == "translation"
        assert "Matthew.3.2" in result.verse_ids
        assert result.sblgnt_text is not None
        assert len(result.sblgnt_text) > 0

    def test_single_verse_returns_normalized_ref(self, db_conn, spine_with_verses):
        """Response includes normalized reference."""
        result = translate_passage(
            conn=db_conn,
            reference="Mt 3:2",  # Abbreviated
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        assert result.normalized_ref == "Matthew 3:2"


class TestMultiVerseTranslation:
    """Tests for multi-verse passage translation."""

    def test_multi_verse_range_returns_all_verse_ids(self, db_conn, spine_with_verses):
        """Multi-verse range includes all verse_ids in response."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18-19",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        # Without variants, should return translation
        assert isinstance(result, TranslateResponse)
        assert "John.1.18" in result.verse_ids
        assert "John.1.19" in result.verse_ids
        assert len(result.verse_ids) == 2

    def test_multi_verse_has_per_verse_blocks(self, db_conn, spine_with_verses):
        """Multi-verse response includes per-verse blocks."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18-19",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        assert len(result.verse_blocks) == 2

        verse_block_ids = [vb.verse_id for vb in result.verse_blocks]
        assert "John.1.18" in verse_block_ids
        assert "John.1.19" in verse_block_ids

    def test_multi_verse_combines_sblgnt_text(self, db_conn, spine_with_verses):
        """Combined SBLGNT text includes all verses."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18-19",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        # Combined text should have content from both verses
        assert "θεὸν" in result.sblgnt_text  # From John 1:18
        assert "Ἰωάννου" in result.sblgnt_text  # From John 1:19


class TestVariantGating:
    """Tests for variant gate handling in passages."""

    def test_major_variant_triggers_gate(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """MAJOR variant triggers gate response."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, GateResponsePayload)
        assert result.response_type == "gate"
        assert result.gate_type == "variant"
        assert "John.1.18" in result.message

    def test_gate_includes_side_by_side_variants(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """Gate response includes side-by-side variant display."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, GateResponsePayload)
        assert len(result.variants_side_by_side) > 0

        # Check variant display has expected content
        variant = result.variants_side_by_side[0]
        assert variant.ref == "John.1.18"
        assert "μονογενὴς θεός" in variant.sblgnt_reading

    def test_gate_includes_required_acks(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """Gate response includes required_acks list."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, GateResponsePayload)
        assert len(result.required_acks) > 0
        assert result.required_acks[0].variant_ref == "John.1.18"


class TestMultiVerseGating:
    """Tests for aggregated gating across multi-verse passages."""

    def test_multi_verse_with_one_gated_returns_single_gate(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """Multi-verse where one verse has MAJOR variant returns ONE gate."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18-19",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        # Should return gate, not translation
        assert isinstance(result, GateResponsePayload)
        assert result.gate_type == "variant"

        # Gate should reference the passage
        assert result.verse_ids == ["John.1.18", "John.1.19"]

    def test_gate_shows_all_required_acks(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """Gate response lists all required acknowledgements."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18-19",
            mode="readable",
            session_id="test-session",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, GateResponsePayload)
        # Should have at least one required ack (for John.1.18)
        assert len(result.required_acks) >= 1

        # Verify the variant is in required_acks
        ack_refs = [ra.variant_ref for ra in result.required_acks]
        assert "John.1.18" in ack_refs


class TestAcknowledgementFlow:
    """Tests for acknowledgement and retry flow."""

    def test_acknowledge_then_translate_succeeds(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """Acknowledging variant then re-translating succeeds."""
        session = "test-ack-session"

        # First call triggers gate
        result1 = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id=session,
            options={"spine_provider": spine_with_verses},
        )
        assert isinstance(result1, GateResponsePayload)

        # Acknowledge the variant (choose reading 0 = SBLGNT)
        acknowledge_variant(db_conn, session, "John.1.18", 0, "test")

        # Second call should succeed
        result2 = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id=session,
            options={"spine_provider": spine_with_verses},
        )
        assert isinstance(result2, TranslateResponse)
        assert result2.response_type == "translation"

    def test_multi_verse_ack_flow(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """Multi-verse passage: ack all variants, then translate succeeds."""
        session = "test-multi-ack"

        # First call triggers gate
        result1 = translate_passage(
            conn=db_conn,
            reference="John 1:18-19",
            mode="readable",
            session_id=session,
            options={"spine_provider": spine_with_verses},
        )
        assert isinstance(result1, GateResponsePayload)

        # Acknowledge all required variants
        for ra in result1.required_acks:
            acknowledge_variant(
                db_conn, session, ra.variant_ref, ra.reading_index or 0, "test"
            )

        # Second call should succeed
        result2 = translate_passage(
            conn=db_conn,
            reference="John 1:18-19",
            mode="readable",
            session_id=session,
            options={"spine_provider": spine_with_verses},
        )
        assert isinstance(result2, TranslateResponse)
        assert len(result2.verse_ids) == 2

    def test_acknowledged_variant_marked_in_response(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """Acknowledged variants are marked in translation response."""
        session = "test-marked"

        # Acknowledge first
        acknowledge_variant(db_conn, session, "John.1.18", 0, "test")

        # Then translate
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id=session,
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        # Find the variant in the response
        john_variant = next((v for v in result.variants if v.ref == "John.1.18"), None)
        assert john_variant is not None
        assert john_variant.acknowledged is True


class TestADRCompliance:
    """Tests verifying ADR-007 through ADR-010 compliance."""

    def test_adr007_sblgnt_is_canonical_spine(self, db_conn, spine_with_verses):
        """ADR-007: SBLGNT is the canonical spine (default reading)."""
        result = translate_passage(
            conn=db_conn,
            reference="Matthew 3:2",
            mode="readable",
            session_id="test",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        # Provenance should indicate SBLGNT
        assert (
            "SBLGNT" in result.provenance.spine_source
            or "sblgnt" in result.provenance.spine_source.lower()
        )

    def test_adr008_variants_side_by_side(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """ADR-008: Variants surfaced side-by-side (not footnotes)."""
        session = "test-sbs"
        acknowledge_variant(db_conn, session, "John.1.18", 0, "test")

        result = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id=session,
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        # Variants should be present in side-by-side format
        assert len(result.variants) > 0
        variant = result.variants[0]
        assert variant.sblgnt_reading is not None
        assert len(variant.alternate_readings) > 0

    def test_adr008_significant_requires_acknowledgement(
        self, db_conn, spine_with_verses, variant_store_with_major_variant
    ):
        """ADR-008: Significant/major variants require acknowledgement."""
        result = translate_passage(
            conn=db_conn,
            reference="John 1:18",
            mode="readable",
            session_id="test-new",
            options={"spine_provider": spine_with_verses},
        )

        # Should trigger gate, not proceed silently
        assert isinstance(result, GateResponsePayload)
        assert result.gate_type == "variant"

    def test_adr010_layered_confidence_in_response(self, db_conn, spine_with_verses):
        """ADR-010: Response includes layered confidence scoring."""
        result = translate_passage(
            conn=db_conn,
            reference="Matthew 3:2",
            mode="readable",
            session_id="test",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        assert result.confidence is not None

        # Should have all four layers
        assert result.confidence.textual is not None
        assert result.confidence.grammatical is not None
        assert result.confidence.lexical is not None
        assert result.confidence.interpretive is not None

        # Should have composite score
        assert 0 <= result.confidence.composite <= 1


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility with existing callers."""

    def test_verse_id_format_still_works(self, db_conn, spine_with_verses):
        """Existing verse_id format (Book.Chapter.Verse) still works."""
        result = translate_passage(
            conn=db_conn,
            reference="Matthew.3.2",  # verse_id format
            mode="readable",
            session_id="test",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)
        assert "Matthew.3.2" in result.verse_ids

    def test_single_verse_response_shape_unchanged(self, db_conn, spine_with_verses):
        """Single verse response has expected fields for backward compat."""
        result = translate_passage(
            conn=db_conn,
            reference="Matthew 3:2",
            mode="readable",
            session_id="test",
            options={"spine_provider": spine_with_verses},
        )

        assert isinstance(result, TranslateResponse)

        # Key fields that existing callers expect
        assert hasattr(result, "sblgnt_text")
        assert hasattr(result, "translation_text")
        assert hasattr(result, "variants")
        assert hasattr(result, "claims")
        assert hasattr(result, "confidence")
        assert hasattr(result, "provenance")
        assert hasattr(result, "receipts")
        assert hasattr(result, "tokens")

        # to_dict should work
        d = result.to_dict()
        assert "sblgnt_text" in d
        assert "translation_text" in d
