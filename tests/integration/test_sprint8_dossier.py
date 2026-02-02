"""Sprint 8 Integration Tests: Evidence-Grade Translation at Scale.

Tests:
- B1: Pack Spec v1.1 validation and indexing
- B3: Witness-aware variant model with source_pack_id tracking
- B4: Dossier generation with witness summaries and provenance
"""

import pytest
import tempfile
import json
from pathlib import Path

from redletters.sources.pack_loader import PackLoader
from redletters.sources.pack_validator import PackValidator
from redletters.sources.pack_indexer import PackIndexer
from redletters.variants.builder import VariantBuilder
from redletters.variants.store import VariantStore
from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessType,
    SignificanceLevel,
)
from redletters.variants.dossier import generate_dossier
from redletters.sources.spine import FixtureSpine, PackSpineAdapter


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    import sqlite3

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def pack_v11_dir(tmp_path):
    """Create a mock pack directory with Pack Spec v1.1."""
    pack_dir = tmp_path / "byzantine-john"
    pack_dir.mkdir()

    # Create v1.1 manifest with new fields
    # Note: coverage in validator is used for book directories, so use books array
    manifest = {
        "pack_id": "byzantine-john",
        "name": "Byzantine John (Test)",
        "version": "1.0.0",
        "license": "Public Domain",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "role": "comparative_layer",
        "witness_siglum": "Byz",
        "witness_type": "edition",
        "date_range": [4, 15],
        "books": ["John"],
        "verse_count": 3,
        "format": "tsv",
        # v1.1 fields
        "format_version": "1.1",
        "siglum": "Byz",
        "century_range": [4, 15],
        "coverage": ["John"],  # Use book name for validator compatibility
        "provenance": {
            "attribution": "Test data",
            "retrieval_date": "2024-01-01",
        },
    }
    with open(pack_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    # Create John chapter 1 data with proper TSV headers
    john_dir = pack_dir / "John"
    john_dir.mkdir()

    chapter_1 = """\
verse_id\ttext\tnormalized
John.1.1\tἘν ἀρχῇ ἦν ὁ λόγος\ten archē ēn ho logos
John.1.18\tμονογενὴς υἱὸς ὁ ὢν εἰς τὸν κόλπον\tmonogenēs huios ho ōn eis ton kolpon
John.1.34\tοὗτός ἐστιν ὁ υἱὸς τοῦ θεοῦ\thoustos estin ho huios tou theou
"""
    with open(john_dir / "chapter_01.tsv", "w", encoding="utf-8") as f:
        f.write(chapter_1)

    return pack_dir


@pytest.fixture
def spine_fixture(tmp_path):
    """Create a mock SBLGNT spine fixture."""
    fixture_data = {
        "John.1.1": {
            "text": "Ἐν ἀρχῇ ἦν ὁ λόγος",
            "tokens": [
                {"position": 1, "surface_text": "Ἐν", "lemma": "ἐν", "pos": "P-"},
                {"position": 2, "surface_text": "ἀρχῇ", "lemma": "ἀρχή", "pos": "N-"},
                {"position": 3, "surface_text": "ἦν", "lemma": "εἰμί", "pos": "V-"},
                {"position": 4, "surface_text": "ὁ", "lemma": "ὁ", "pos": "RA"},
                {"position": 5, "surface_text": "λόγος", "lemma": "λόγος", "pos": "N-"},
            ],
        },
        "John.1.18": {
            "text": "μονογενὴς θεὸς ὁ ὢν εἰς τὸν κόλπον τοῦ πατρός",
            "tokens": [
                {"position": 1, "surface_text": "μονογενὴς", "lemma": "μονογενής"},
                {"position": 2, "surface_text": "θεὸς", "lemma": "θεός"},
                {"position": 3, "surface_text": "ὁ", "lemma": "ὁ"},
            ],
        },
        "John.1.34": {
            "text": "οὗτός ἐστιν ὁ ἐκλεκτὸς τοῦ θεοῦ",
            "tokens": [
                {"position": 1, "surface_text": "οὗτός", "lemma": "οὗτος"},
                {"position": 2, "surface_text": "ἐστιν", "lemma": "εἰμί"},
                {"position": 3, "surface_text": "ὁ", "lemma": "ὁ"},
                {"position": 4, "surface_text": "ἐκλεκτὸς", "lemma": "ἐκλεκτός"},
            ],
        },
    }

    fixture_path = tmp_path / "spine_fixture.json"
    with open(fixture_path, "w", encoding="utf-8") as f:
        json.dump(fixture_data, f, ensure_ascii=False)

    return fixture_path


class TestPackSpecV11:
    """B1: Tests for Pack Spec v1.1."""

    def test_manifest_v11_fields(self, pack_v11_dir):
        """Test loading manifest with v1.1 fields."""
        loader = PackLoader(pack_v11_dir)
        assert loader.load()

        manifest = loader.manifest
        assert manifest is not None
        assert manifest.format_version == "1.1"
        assert manifest.siglum == "Byz"
        assert manifest.coverage == ["John"]
        assert manifest.century_range == (4, 15)
        assert manifest.provenance is not None
        assert manifest.provenance["attribution"] == "Test data"

    def test_manifest_effective_siglum(self, pack_v11_dir):
        """Test effective_siglum property."""
        loader = PackLoader(pack_v11_dir)
        loader.load()

        # Should prefer siglum over witness_siglum
        assert loader.manifest.effective_siglum == "Byz"

    def test_manifest_backward_compatibility(self, tmp_path):
        """Test loading v1.0 manifest (backward compatibility)."""
        pack_dir = tmp_path / "old-pack"
        pack_dir.mkdir()

        # Create v1.0 manifest (no format_version, no siglum)
        manifest = {
            "pack_id": "old-pack",
            "name": "Old Pack",
            "version": "1.0.0",
            "license": "Public Domain",
            "role": "comparative_layer",
            "witness_siglum": "OLD",
            "witness_type": "edition",
            "books": ["John"],
            "verse_count": 1,
            "format": "tsv",
        }
        with open(pack_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        # Create minimal TSV
        john_dir = pack_dir / "John"
        john_dir.mkdir()
        with open(john_dir / "chapter_01.tsv", "w") as f:
            f.write("John.1.1\ttest verse\n")

        loader = PackLoader(pack_dir)
        assert loader.load()
        assert loader.manifest.format_version == "1.0"  # Default
        assert loader.manifest.effective_siglum == "OLD"  # Falls back to witness_siglum


class TestPackValidator:
    """B1: Tests for pack validation."""

    def test_validate_valid_pack(self, pack_v11_dir):
        """Test validating a valid v1.1 pack."""
        validator = PackValidator(pack_v11_dir)
        result = validator.validate()

        assert result.valid, f"Validation errors: {[e.message for e in result.errors]}"
        assert len(result.errors) == 0
        assert result.verse_count > 0

    def test_validate_missing_manifest(self, tmp_path):
        """Test validation fails for missing manifest."""
        empty_dir = tmp_path / "empty-pack"
        empty_dir.mkdir()

        validator = PackValidator(empty_dir)
        result = validator.validate()

        assert not result.valid
        assert any("manifest.json" in e.message.lower() for e in result.errors)

    def test_validate_invalid_verse_id(self, tmp_path):
        """Test validation catches invalid verse IDs."""
        pack_dir = tmp_path / "bad-verses"
        pack_dir.mkdir()

        # Create manifest
        manifest = {
            "pack_id": "bad-verses",
            "name": "Bad Verses Pack",
            "version": "1.0.0",
            "license": "Public Domain",
            "role": "comparative_layer",
            "witness_siglum": "BAD",
            "witness_type": "edition",
            "books": ["John"],
            "verse_count": 1,
            "format": "tsv",
            "format_version": "1.1",
        }
        with open(pack_dir / "manifest.json", "w") as f:
            json.dump(manifest, f)

        john_dir = pack_dir / "John"
        john_dir.mkdir()

        # Create TSV with invalid verse ID
        with open(john_dir / "chapter_01.tsv", "w") as f:
            f.write("verse_id\ttext\n")
            f.write("INVALID\tsome text\n")  # Invalid verse ID format

        validator = PackValidator(pack_dir)
        result = validator.validate()

        assert len(result.warnings) > 0 or len(result.errors) > 0


class TestPackIndexer:
    """B1: Tests for pack indexing."""

    def test_generate_index(self, pack_v11_dir):
        """Test generating pack index."""
        indexer = PackIndexer(pack_v11_dir)
        index = indexer.generate()

        assert index is not None
        assert "John" in index.books
        assert index.books["John"].total_verses > 0

    def test_index_summary(self, pack_v11_dir):
        """Test getting index summary."""
        indexer = PackIndexer(pack_v11_dir)
        indexer.generate()
        summary = indexer.get_summary()

        assert summary["total_verses"] > 0
        assert "John" in summary["books"]


class TestWitnessAwareVariants:
    """B3: Tests for witness-aware variant model."""

    def test_source_pack_id_tracking(self, temp_db, spine_fixture, pack_v11_dir):
        """Test that source_pack_id is tracked in readings."""
        spine = FixtureSpine(spine_fixture, "sblgnt-test")

        byz_loader = PackLoader(pack_v11_dir)
        byz_loader.load()
        byz_spine = PackSpineAdapter(byz_loader, "byzantine-john")

        store = VariantStore(temp_db)
        store.init_schema()

        builder = VariantBuilder(spine, store)
        builder.add_edition(
            "byzantine-john",
            byz_spine,
            "Byz",
            date_range=(4, 15),
            source_pack_id="byzantine-john",  # Track provenance
        )

        builder.build_verse("John.1.18")

        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

        # Check source_pack_id on non-spine reading
        variant = variants[0]
        for reading in variant.readings:
            if "Byz" in reading.witnesses:
                assert reading.source_pack_id == "byzantine-john"

    def test_get_provenance_summary(self, temp_db):
        """Test getting provenance summary from variant."""
        store = VariantStore(temp_db)
        store.init_schema()

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="μονογενὴς θεὸς",
                    witnesses=["SBLGNT"],
                    witness_types=[WitnessType.UNCIAL],
                    source_pack_id=None,  # Spine
                ),
                WitnessReading(
                    surface_text="μονογενὴς υἱὸς",
                    witnesses=["Byz"],
                    witness_types=[WitnessType.UNCIAL],
                    source_pack_id="byzantine-john",
                ),
                WitnessReading(
                    surface_text="μονογενὴς υἱὸς ὁ",
                    witnesses=["WH"],
                    witness_types=[WitnessType.VERSION],
                    source_pack_id="westcott-hort-john",
                ),
            ],
            significance=SignificanceLevel.MAJOR,
        )

        provenance = variant.get_provenance_summary()
        assert "byzantine-john" in provenance
        assert "westcott-hort-john" in provenance
        assert len(provenance) == 2  # Excludes None

    def test_get_witness_summary_by_type(self):
        """Test grouping witnesses by type."""
        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="μονογενὴς θεὸς",
                    witnesses=["P66", "P75", "B", "א"],
                    witness_types=[
                        WitnessType.PAPYRUS,
                        WitnessType.PAPYRUS,
                        WitnessType.UNCIAL,
                        WitnessType.UNCIAL,
                    ],
                ),
                WitnessReading(
                    surface_text="μονογενὴς υἱὸς",
                    witnesses=["A", "C", "Byz"],
                    witness_types=[
                        WitnessType.UNCIAL,
                        WitnessType.UNCIAL,
                        WitnessType.UNCIAL,
                    ],
                ),
            ],
        )

        by_type = variant.get_witness_summary_by_type()

        assert WitnessType.PAPYRUS in by_type
        assert "P66" in by_type[WitnessType.PAPYRUS]
        assert "P75" in by_type[WitnessType.PAPYRUS]

        assert WitnessType.UNCIAL in by_type
        assert "B" in by_type[WitnessType.UNCIAL]
        assert "א" in by_type[WitnessType.UNCIAL]


class TestDossierGeneration:
    """B4: Tests for dossier generation."""

    def test_generate_dossier_basic(self, temp_db):
        """Test basic dossier generation."""
        store = VariantStore(temp_db)
        store.init_schema()

        # Create a variant
        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="μονογενὴς θεὸς",
                    witnesses=["P66", "B"],
                    witness_types=[WitnessType.PAPYRUS, WitnessType.UNCIAL],
                ),
                WitnessReading(
                    surface_text="μονογενὴς υἱὸς",
                    witnesses=["A", "Byz"],
                    witness_types=[WitnessType.UNCIAL, WitnessType.UNCIAL],
                    source_pack_id="byzantine-john",
                ),
            ],
            significance=SignificanceLevel.MAJOR,
            reason_code="theological_keyword",
            reason_summary="Theological term change (God/Son)",
        )
        store.save_variant(variant)

        # Generate dossier
        dossier = generate_dossier(store, "John.1.18", scope="verse")

        assert dossier is not None
        assert dossier.reference == "John.1.18"
        assert dossier.scope == "verse"
        assert len(dossier.variants) == 1

        dv = dossier.variants[0]
        assert dv.significance == "major"
        assert dv.reason.code == "theological_keyword"
        assert len(dv.readings) == 2

    def test_dossier_witness_summary(self, temp_db):
        """Test that dossier includes witness summaries."""
        store = VariantStore(temp_db)
        store.init_schema()

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="μονογενὴς θεὸς",
                    witnesses=["P66", "P75", "B", "א", "vg", "syr"],
                    witness_types=[
                        WitnessType.PAPYRUS,
                        WitnessType.PAPYRUS,
                        WitnessType.UNCIAL,
                        WitnessType.UNCIAL,
                        WitnessType.VERSION,
                        WitnessType.VERSION,
                    ],
                ),
            ],
            significance=SignificanceLevel.SIGNIFICANT,
        )
        store.save_variant(variant)

        dossier = generate_dossier(store, "John.1.18")

        reading = dossier.variants[0].readings[0]
        summary = reading.witness_summary

        assert len(summary.papyri) == 2
        assert "P66" in summary.papyri
        assert "P75" in summary.papyri

        assert len(summary.uncials) == 2
        assert "B" in summary.uncials
        assert "א" in summary.uncials

        assert len(summary.versions) == 2

    def test_dossier_acknowledgement_state(self, temp_db):
        """Test that dossier includes acknowledgement state."""
        store = VariantStore(temp_db)
        store.init_schema()

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="μονογενὴς θεὸς",
                    witnesses=["SBLGNT"],
                    witness_types=[WitnessType.UNCIAL],
                ),
            ],
            significance=SignificanceLevel.SIGNIFICANT,
        )
        store.save_variant(variant)

        # Generate with ack state
        ack_state = {"John.1.18": 0}
        dossier = generate_dossier(
            store,
            "John.1.18",
            ack_state=ack_state,
            session_id="test-session",
        )

        dv = dossier.variants[0]
        assert dv.acknowledgement.required is True
        assert dv.acknowledgement.acknowledged is True
        assert dv.acknowledgement.acknowledged_reading == 0

    def test_dossier_gating_requirement(self, temp_db):
        """Test that dossier reflects gating requirements."""
        store = VariantStore(temp_db)
        store.init_schema()

        # Significant variant - requires ack
        variant_sig = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="θεὸς",
                    witnesses=["SBLGNT"],
                    witness_types=[WitnessType.UNCIAL],
                ),
            ],
            significance=SignificanceLevel.SIGNIFICANT,
        )
        store.save_variant(variant_sig)

        # Minor variant - no ack required
        variant_minor = VariantUnit(
            ref="John.1.1",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="ἐν",
                    witnesses=["SBLGNT"],
                    witness_types=[WitnessType.UNCIAL],
                ),
            ],
            significance=SignificanceLevel.MINOR,
        )
        store.save_variant(variant_minor)

        dossier_sig = generate_dossier(store, "John.1.18")
        dossier_minor = generate_dossier(store, "John.1.1")

        assert dossier_sig.variants[0].gating_requirement == "requires_acknowledgement"
        assert dossier_minor.variants[0].gating_requirement == "none"

    def test_dossier_provenance(self, temp_db):
        """Test that dossier includes provenance info."""
        store = VariantStore(temp_db)
        store.init_schema()

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="μονογενὴς θεὸς",
                    witnesses=["SBLGNT"],
                    witness_types=[WitnessType.UNCIAL],
                    source_pack_id=None,
                ),
                WitnessReading(
                    surface_text="μονογενὴς υἱὸς",
                    witnesses=["Byz"],
                    witness_types=[WitnessType.UNCIAL],
                    source_pack_id="byzantine-john",
                ),
            ],
            significance=SignificanceLevel.SIGNIFICANT,
        )
        store.save_variant(variant)

        dossier = generate_dossier(store, "John.1.18")

        assert dossier.provenance.spine_source == "morphgnt-sblgnt"
        assert "byzantine-john" in dossier.provenance.comparative_packs

    def test_dossier_to_dict(self, temp_db):
        """Test dossier serialization to dict."""
        store = VariantStore(temp_db)
        store.init_schema()

        variant = VariantUnit(
            ref="John.1.18",
            position=0,
            readings=[
                WitnessReading(
                    surface_text="μονογενὴς θεὸς",
                    witnesses=["SBLGNT"],
                    witness_types=[WitnessType.UNCIAL],
                ),
            ],
            significance=SignificanceLevel.SIGNIFICANT,
            reason_code="theological_keyword",
            reason_summary="Test reason",
        )
        store.save_variant(variant)

        dossier = generate_dossier(store, "John.1.18")
        dossier_dict = dossier.to_dict()

        # Verify structure
        assert "reference" in dossier_dict
        assert "scope" in dossier_dict
        assert "generated_at" in dossier_dict
        assert "spine" in dossier_dict
        assert "variants" in dossier_dict
        assert "provenance" in dossier_dict

        # Verify variants
        assert len(dossier_dict["variants"]) == 1
        v = dossier_dict["variants"][0]
        assert v["ref"] == "John.1.18"
        assert v["reason"]["code"] == "theological_keyword"
        assert len(v["readings"]) == 1

        # Should be JSON-serializable
        json_str = json.dumps(dossier_dict)
        assert json_str is not None


class TestAcknowledgementStoreGetSessionAcks:
    """B4: Test the new get_session_acks method."""

    def test_get_session_acks(self, temp_db):
        """Test getting all session acks as dict."""
        from redletters.gates.state import AcknowledgementStore, AcknowledgementState

        store = AcknowledgementStore(temp_db)
        store.init_schema()

        session_id = "test-session"
        state = AcknowledgementState(session_id=session_id)

        # Acknowledge multiple variants
        ack1 = state.acknowledge_variant("John.1.18", 0, "test")
        ack2 = state.acknowledge_variant("John.1.34", 1, "test")
        ack3 = state.acknowledge_variant("John.3.16", 0, "test")

        store.persist_variant_ack(ack1)
        store.persist_variant_ack(ack2)
        store.persist_variant_ack(ack3)

        # Get session acks
        acks = store.get_session_acks(session_id)

        assert len(acks) == 3
        assert acks["John.1.18"] == 0
        assert acks["John.1.34"] == 1
        assert acks["John.3.16"] == 0

    def test_get_session_acks_empty(self, temp_db):
        """Test getting acks for session with no acks."""
        from redletters.gates.state import AcknowledgementStore

        store = AcknowledgementStore(temp_db)
        store.init_schema()

        acks = store.get_session_acks("nonexistent-session")
        assert len(acks) == 0
