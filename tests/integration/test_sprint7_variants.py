"""Sprint 7 Integration Tests: Real Data + Bulk Build + Gate Hygiene.

Tests:
- B1: Pack installation and loading
- B2: Bulk variant building
- B3: Multi-ack support
- B4: Reason classification
"""

import pytest
import tempfile
import json
from pathlib import Path

from redletters.sources.pack_loader import PackLoader
from redletters.sources.spine import FixtureSpine, PackSpineAdapter
from redletters.variants.builder import VariantBuilder
from redletters.variants.store import VariantStore
from redletters.variants.models import SignificanceLevel


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
def wh_pack_dir(tmp_path):
    """Create a mock W-H pack directory."""
    pack_dir = tmp_path / "westcott-hort-john"
    pack_dir.mkdir()

    # Create manifest
    manifest = {
        "pack_id": "westcott-hort-john",
        "name": "Westcott-Hort John (Test)",
        "version": "1.0.0",
        "license": "Public Domain",
        "role": "comparative_layer",
        "witness_siglum": "WH",
        "witness_type": "version",
        "date_range": [19, 19],
        "books": ["John"],
        "verse_count": 5,
        "format": "tsv",
    }
    with open(pack_dir / "manifest.json", "w") as f:
        json.dump(manifest, f)

    # Create John chapter 1 data with key variant
    john_dir = pack_dir / "John"
    john_dir.mkdir()

    # W-H has υἱός at 1:18, SBLGNT has θεός
    chapter_1 = """\
# Test W-H John 1
John.1.1\tἘν ἀρχῇ ἦν ὁ λόγος
John.1.2\tοὗτος ἦν ἐν ἀρχῇ πρὸς τὸν θεόν
John.1.18\tμονογενὴς υἱὸς ὁ ὢν εἰς τὸν κόλπον τοῦ πατρός
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
        "John.1.2": {
            "text": "οὗτος ἦν ἐν ἀρχῇ πρὸς τὸν θεόν",
            "tokens": [],
        },
        "John.1.18": {
            "text": "μονογενὴς θεὸς ὁ ὢν εἰς τὸν κόλπον τοῦ πατρός",
            "tokens": [
                {"position": 1, "surface_text": "μονογενὴς", "lemma": "μονογενής"},
                {
                    "position": 2,
                    "surface_text": "θεὸς",
                    "lemma": "θεός",
                },  # SBLGNT reading
                {"position": 3, "surface_text": "ὁ", "lemma": "ὁ"},
            ],
        },
    }

    fixture_path = tmp_path / "spine_fixture.json"
    with open(fixture_path, "w", encoding="utf-8") as f:
        json.dump(fixture_data, f, ensure_ascii=False)

    return fixture_path


class TestPackLoader:
    """B1: Tests for pack loading."""

    def test_load_pack_manifest(self, wh_pack_dir):
        """Test loading pack manifest."""
        loader = PackLoader(wh_pack_dir)
        assert loader.load()
        assert loader.manifest is not None
        assert loader.manifest.pack_id == "westcott-hort-john"
        assert loader.manifest.license == "Public Domain"
        assert loader.manifest.witness_siglum == "WH"

    def test_load_pack_verses(self, wh_pack_dir):
        """Test loading verse data from pack."""
        loader = PackLoader(wh_pack_dir)
        loader.load()

        verse = loader.get_verse("John.1.18")
        assert verse is not None
        assert "υἱὸς" in verse.text  # W-H reading
        assert "θεὸς" not in verse.text  # Not SBLGNT reading

    def test_get_verses_for_chapter(self, wh_pack_dir):
        """Test getting all verses for a chapter."""
        loader = PackLoader(wh_pack_dir)
        loader.load()

        verses = loader.get_verses_for_chapter("John", 1)
        assert len(verses) >= 3

    def test_has_verse(self, wh_pack_dir):
        """Test checking if verse exists."""
        loader = PackLoader(wh_pack_dir)
        loader.load()

        assert loader.has_verse("John.1.1")
        assert loader.has_verse("John.1.18")
        assert not loader.has_verse("John.2.1")


class TestPackSpineAdapter:
    """B1: Tests for PackSpineAdapter."""

    def test_adapter_get_verse_text(self, wh_pack_dir):
        """Test getting verse text through adapter."""
        loader = PackLoader(wh_pack_dir)
        loader.load()

        adapter = PackSpineAdapter(loader, "wh-test")
        verse = adapter.get_verse_text("John.1.18")

        assert verse is not None
        assert verse.verse_id == "John.1.18"
        assert "υἱὸς" in verse.text

    def test_adapter_has_verse(self, wh_pack_dir):
        """Test checking verse existence through adapter."""
        loader = PackLoader(wh_pack_dir)
        loader.load()

        adapter = PackSpineAdapter(loader, "wh-test")
        assert adapter.has_verse("John.1.1")
        assert not adapter.has_verse("Matthew.1.1")


class TestBulkVariantBuild:
    """B2: Tests for bulk variant building."""

    def test_build_verse(self, temp_db, spine_fixture, wh_pack_dir):
        """Test building variants for a single verse."""
        # Setup spine
        spine = FixtureSpine(spine_fixture, "sblgnt-test")

        # Setup comparative edition
        wh_loader = PackLoader(wh_pack_dir)
        wh_loader.load()
        wh_spine = PackSpineAdapter(wh_loader, "wh-test")

        # Setup variant store
        store = VariantStore(temp_db)
        store.init_schema()

        # Build
        builder = VariantBuilder(spine, store)
        builder.add_edition("westcott-hort", wh_spine, "WH", date_range=(19, 19))

        result = builder.build_verse("John.1.18")

        assert result.verses_processed == 1
        assert result.variants_created == 1 or result.variants_updated == 1

        # Verify variant exists
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1
        assert variants[0].significance == SignificanceLevel.MAJOR  # Theological term

    def test_build_idempotent(self, temp_db, spine_fixture, wh_pack_dir):
        """Test that re-building is idempotent."""
        spine = FixtureSpine(spine_fixture, "sblgnt-test")
        wh_loader = PackLoader(wh_pack_dir)
        wh_loader.load()
        wh_spine = PackSpineAdapter(wh_loader, "wh-test")

        store = VariantStore(temp_db)
        store.init_schema()

        builder = VariantBuilder(spine, store)
        builder.add_edition("westcott-hort", wh_spine, "WH")

        # Build twice
        result1 = builder.build_verse("John.1.18")
        result2 = builder.build_verse("John.1.18")

        # Second build should update, not create new
        assert result1.variants_created + result1.variants_updated == 1
        assert result2.variants_updated == 1 or result2.variants_unchanged == 1

        # Should still be exactly 1 variant
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

    def test_build_chapter(self, temp_db, spine_fixture, wh_pack_dir):
        """Test building variants for a chapter."""
        spine = FixtureSpine(spine_fixture, "sblgnt-test")
        wh_loader = PackLoader(wh_pack_dir)
        wh_loader.load()
        wh_spine = PackSpineAdapter(wh_loader, "wh-test")

        store = VariantStore(temp_db)
        store.init_schema()

        builder = VariantBuilder(spine, store)
        builder.add_edition("westcott-hort", wh_spine, "WH")

        result = builder.build_chapter("John", 1)

        # Should process all verses in chapter
        assert result.verses_processed >= 1
        assert len(result.errors) == 0


class TestReasonClassification:
    """B4: Tests for reason classification."""

    def test_theological_keyword_reason(self, temp_db, spine_fixture, wh_pack_dir):
        """Test that theological keyword variants get correct reason."""
        spine = FixtureSpine(spine_fixture, "sblgnt-test")
        wh_loader = PackLoader(wh_pack_dir)
        wh_loader.load()
        wh_spine = PackSpineAdapter(wh_loader, "wh-test")

        store = VariantStore(temp_db)
        store.init_schema()

        builder = VariantBuilder(spine, store)
        builder.add_edition("westcott-hort", wh_spine, "WH")

        builder.build_verse("John.1.18")

        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

        variant = variants[0]
        assert variant.reason_code == "theological_keyword"
        assert "Son" in variant.reason_summary or "God" in variant.reason_summary


class TestMultiAck:
    """B3: Tests for multi-ack support."""

    def test_acknowledge_multiple(self, temp_db):
        """Test acknowledging multiple variants at once."""
        from redletters.gates.state import AcknowledgementStore, AcknowledgementState

        store = AcknowledgementStore(temp_db)
        store.init_schema()

        session_id = "test-session-multi"
        state = AcknowledgementState(session_id=session_id)

        # Acknowledge multiple variants
        refs = ["John.1.18", "John.1.34", "John.3.16"]
        for ref in refs:
            ack = state.acknowledge_variant(ref, 0, "test-multi")
            store.persist_variant_ack(ack)

        # Verify all were persisted
        loaded_state = store.load_session_state(session_id)
        assert len(loaded_state.acknowledged_variants) == 3

        for ref in refs:
            assert loaded_state.has_acknowledged_variant(ref)

    def test_ack_scope_persistence(self, temp_db):
        """Test that ack scope is recorded."""
        from redletters.gates.state import AcknowledgementStore, AcknowledgementState

        store = AcknowledgementStore(temp_db)
        store.init_schema()

        session_id = "test-session-scope"
        state = AcknowledgementState(session_id=session_id)

        # Acknowledge with passage scope (recorded in context)
        ack = state.acknowledge_variant("John.1.18", 0, "api-acknowledge-passage")
        store.persist_variant_ack(ack)

        # Verify context was stored
        loaded_state = store.load_session_state(session_id)
        assert (
            loaded_state.acknowledged_variants["John.1.18"].context
            == "api-acknowledge-passage"
        )


class TestVariantStore:
    """Additional VariantStore tests for Sprint 7."""

    def test_save_variant_with_reason(self, temp_db):
        """Test saving variant with reason fields."""
        from redletters.variants.models import VariantUnit, WitnessReading, WitnessType

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
                WitnessReading(
                    surface_text="μονογενὴς υἱὸς",
                    witnesses=["WH"],
                    witness_types=[WitnessType.VERSION],
                ),
            ],
            significance=SignificanceLevel.MAJOR,
            reason_code="theological_keyword",
            reason_summary="Theological term change (God/Son)",
            reason_detail="Key Christological variant",
        )

        variant_id = store.save_variant(variant)
        assert variant_id > 0

        loaded = store.get_variant("John.1.18", 0)
        assert loaded is not None
        assert loaded.significance == SignificanceLevel.MAJOR
