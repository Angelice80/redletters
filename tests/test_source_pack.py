"""Tests for the Source Pack system (Sprint 2).

Tests:
- Catalog loading and validation
- Path resolution
- Spine provider functionality
- Edition loading
- Variant building
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from redletters.sources.catalog import (
    SourceCatalog,
    SourcePack,
    SourceRole,
    CatalogValidationError,
)
from redletters.sources.resolver import SourceResolver
from redletters.sources.spine import SBLGNTSpine, FixtureSpine, VerseText
from redletters.sources.editions import MorphGNTLoader, FixtureLoader
from redletters.variants.builder import VariantBuilder
from redletters.variants.store import VariantStore
from redletters.variants.models import SignificanceLevel


# Get fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SPINE_FIXTURE = FIXTURES_DIR / "spine_fixture.json"
COMPARATIVE_FIXTURE = FIXTURES_DIR / "comparative_fixture.json"


# ============================================================================
# Catalog Tests
# ============================================================================


class TestSourceCatalog:
    """Test catalog loading and validation."""

    def test_load_catalog_from_repo(self):
        """Catalog loads from repo root."""
        catalog = SourceCatalog.load()

        assert catalog is not None
        assert len(catalog.sources) > 0
        assert catalog.spine is not None
        assert catalog.spine.key == "morphgnt-sblgnt"

    def test_catalog_has_required_fields(self):
        """All sources have required fields."""
        catalog = SourceCatalog.load()

        for key, source in catalog.sources.items():
            assert source.name, f"{key} missing name"
            assert source.license, f"{key} missing license"
            assert source.role is not None, f"{key} missing role"

    def test_catalog_spine_is_sblgnt(self):
        """Per ADR-007: SBLGNT is the canonical spine."""
        catalog = SourceCatalog.load()
        spine = catalog.spine

        assert spine is not None
        assert spine.is_spine
        assert "sblgnt" in spine.key.lower()
        assert spine.role == SourceRole.CANONICAL_SPINE

    def test_catalog_validation_warnings(self):
        """Validation returns warnings for issues."""
        catalog = SourceCatalog.load()
        warnings = catalog.validate()

        # Warnings should be list (may be empty if catalog is perfect)
        assert isinstance(warnings, list)

    def test_source_pack_from_dict(self):
        """SourcePack can be created from dict."""
        data = {
            "name": "Test Source",
            "license": "MIT",
            "role": "comparative_layer",
            "version": "1.0",
            "repo": "https://github.com/test/test",
        }

        pack = SourcePack.from_dict("test-source", data)

        assert pack.key == "test-source"
        assert pack.name == "Test Source"
        assert pack.license == "MIT"
        assert pack.role == SourceRole.COMPARATIVE_LAYER
        assert not pack.is_spine
        assert pack.is_comparative

    def test_source_pack_missing_required_field(self):
        """SourcePack raises error for missing required fields."""
        data = {
            "name": "Test Source",
            # Missing license and role
        }

        with pytest.raises(CatalogValidationError) as exc_info:
            SourcePack.from_dict("test-source", data)

        assert "license" in str(exc_info.value) or "role" in str(exc_info.value)

    def test_source_pack_invalid_role(self):
        """SourcePack raises error for invalid role."""
        data = {
            "name": "Test Source",
            "license": "MIT",
            "role": "invalid_role",
        }

        with pytest.raises(CatalogValidationError) as exc_info:
            SourcePack.from_dict("test-source", data)

        assert "Invalid role" in str(exc_info.value)

    def test_pinned_commit_detection(self):
        """Detects valid 40-char commit SHAs."""
        data = {
            "name": "Test",
            "license": "MIT",
            "role": "comparative_layer",
            "commit": "b4d1e66a22c389aae24fe6e4e80db34e1e5c0b11",
        }
        pack = SourcePack.from_dict("test", data)
        assert pack.has_pinned_commit

        # Short commit
        data["commit"] = "b4d1e66"
        pack = SourcePack.from_dict("test", data)
        assert not pack.has_pinned_commit


# ============================================================================
# Resolver Tests
# ============================================================================


class TestSourceResolver:
    """Test path resolution."""

    def test_resolver_finds_repo_root(self):
        """Resolver locates repo root."""
        resolver = SourceResolver()
        assert resolver.repo_root.exists()
        assert (resolver.repo_root / "pyproject.toml").exists()

    def test_resolver_resolve_spine(self):
        """Resolver can resolve spine source."""
        resolver = SourceResolver()
        resolved = resolver.resolve_spine()

        assert resolved is not None
        assert resolved.pack.is_spine

    def test_resolver_resolve_by_key(self):
        """Resolver can resolve by source key."""
        resolver = SourceResolver()
        resolved = resolver.resolve("morphgnt-sblgnt")

        assert resolved is not None
        assert resolved.pack.key == "morphgnt-sblgnt"

    def test_resolver_unknown_key(self):
        """Resolver raises KeyError for unknown source."""
        resolver = SourceResolver()

        with pytest.raises(KeyError):
            resolver.resolve("nonexistent-source")

    def test_resolver_fixture_path(self):
        """Resolver can find fixture files."""
        resolver = SourceResolver()
        path = resolver.get_fixture_path("spine_fixture.json")

        assert path is not None
        assert path.exists()


# ============================================================================
# Spine Tests
# ============================================================================


class TestFixtureSpine:
    """Test FixtureSpine provider."""

    def test_load_json_fixture(self):
        """Loads JSON fixture file."""
        spine = FixtureSpine(SPINE_FIXTURE, source_key="test-fixture")

        assert spine.has_verse("John.1.18")
        assert spine.has_verse("John.3.16")
        assert spine.has_verse("Matthew.3.2")

    def test_get_verse_text(self):
        """Gets verse text correctly."""
        spine = FixtureSpine(SPINE_FIXTURE)
        verse = spine.get_verse_text("John.1.18")

        assert verse is not None
        assert isinstance(verse, VerseText)
        assert "Θεὸν" in verse.text
        assert "μονογενὴς" in verse.text

    def test_get_verse_tokens(self):
        """Gets verse tokens with morphology."""
        spine = FixtureSpine(SPINE_FIXTURE)
        tokens = spine.get_verse_tokens("John.1.18")

        assert len(tokens) > 0
        assert tokens[0]["surface_text"] == "Θεὸν"
        assert tokens[0]["lemma"] == "θεός"

    def test_missing_verse(self):
        """Returns None for missing verse."""
        spine = FixtureSpine(SPINE_FIXTURE)
        verse = spine.get_verse_text("Revelation.99.99")

        assert verse is None

    def test_add_verse_programmatically(self):
        """Can add verses programmatically for tests."""
        spine = FixtureSpine(SPINE_FIXTURE)
        spine.add_verse(
            "Test.1.1", "Τεστ τεξτ", [{"position": 1, "surface_text": "Τεστ"}]
        )

        assert spine.has_verse("Test.1.1")
        verse = spine.get_verse_text("Test.1.1")
        assert verse.text == "Τεστ τεξτ"


class TestSBLGNTSpine:
    """Test SBLGNT spine with MorphGNT data."""

    @pytest.fixture
    def morphgnt_path(self):
        """Get path to MorphGNT test data."""
        repo_root = Path(__file__).parent.parent
        candidates = [
            repo_root / "tests" / "data" / "morphgnt-snapshot",
            repo_root / "tests" / "fixtures",
        ]
        for candidate in candidates:
            if candidate.exists() and list(candidate.glob("*morphgnt*")):
                return candidate
        pytest.skip("MorphGNT test data not available")

    def test_load_morphgnt_directory(self, morphgnt_path):
        """Loads MorphGNT directory."""
        spine = SBLGNTSpine(morphgnt_path)

        # Should have loaded some verses
        assert spine.verse_count > 0

    def test_verse_id_format(self, morphgnt_path):
        """Verses use Book.Chapter.Verse format."""
        spine = SBLGNTSpine(morphgnt_path)
        verses = spine.list_verses()

        if verses:
            assert "." in verses[0]
            parts = verses[0].split(".")
            assert len(parts) == 3


# ============================================================================
# Edition Loader Tests
# ============================================================================


class TestMorphGNTLoader:
    """Test MorphGNT format loader."""

    def test_load_sample_file(self):
        """Loads sample MorphGNT TSV file."""
        sample_path = FIXTURES_DIR / "morphgnt_sample.tsv"
        if not sample_path.exists():
            pytest.skip("morphgnt_sample.tsv not found")

        loader = MorphGNTLoader()
        tokens = loader.load_file(sample_path)

        assert len(tokens) > 0
        assert "verse_id" in tokens[0]
        assert "surface_text" in tokens[0]

    def test_token_fields(self):
        """Tokens have required fields."""
        sample_path = FIXTURES_DIR / "morphgnt_sample.tsv"
        if not sample_path.exists():
            pytest.skip("morphgnt_sample.tsv not found")

        loader = MorphGNTLoader()
        tokens = loader.load_file(sample_path)

        if tokens:
            token = tokens[0]
            assert "verse_id" in token
            assert "position" in token
            assert "surface_text" in token
            assert "lemma" in token
            assert "pos" in token


class TestFixtureLoader:
    """Test fixture format loader."""

    def test_load_json_fixture(self):
        """Loads JSON fixture."""
        loader = FixtureLoader()
        tokens = loader.load_file(SPINE_FIXTURE)

        assert len(tokens) > 0
        # Should have tokens from multiple verses
        verse_ids = {t["verse_id"] for t in tokens}
        assert len(verse_ids) >= 3


# ============================================================================
# Variant Builder Tests
# ============================================================================


class TestVariantBuilder:
    """Test variant building from edition diffs."""

    @pytest.fixture
    def db_connection(self):
        """Create in-memory database with variant schema."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        store = VariantStore(conn)
        store.init_schema()
        yield conn
        conn.close()

    @pytest.fixture
    def spine(self):
        """Create fixture spine."""
        return FixtureSpine(SPINE_FIXTURE, source_key="sblgnt-fixture")

    @pytest.fixture
    def comparative(self):
        """Create comparative fixture spine."""
        return FixtureSpine(COMPARATIVE_FIXTURE, source_key="wh-fixture")

    def test_build_variant_from_diff(self, db_connection, spine, comparative):
        """Builds variant when editions differ."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        result = builder.build_verse("John.1.18")

        assert result.verses_processed == 1
        assert result.variants_created == 1 or result.variants_updated == 1

        # Check variant was stored
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

        variant = variants[0]
        assert len(variant.readings) >= 2
        assert variant.sblgnt_reading_index == 0

    def test_no_variant_when_identical(self, db_connection, spine, comparative):
        """No variant created when texts are identical."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        result = builder.build_verse("Matthew.3.2")

        # Texts are identical, so no variant
        assert result.variants_created == 0
        assert result.variants_unchanged == 1

    def test_idempotent_rebuild(self, db_connection, spine, comparative):
        """Rebuilding same verse is idempotent."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        # Build twice
        result1 = builder.build_verse("John.1.18")
        result2 = builder.build_verse("John.1.18")

        # First should create, second should update
        assert result1.variants_created == 1
        assert result2.variants_updated == 1

        # Should still be just one variant
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

    def test_significance_major_for_theological(
        self, db_connection, spine, comparative
    ):
        """Variants affecting theological terms get MAJOR significance."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        builder.build_verse("John.1.18")

        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

        # θεὸς vs υἱὸς is a MAJOR variant
        variant = variants[0]
        assert variant.significance == SignificanceLevel.MAJOR

    def test_ensure_variants_on_demand(self, db_connection, spine, comparative):
        """ensure_variants builds on-demand if missing."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        # Initially no variants
        assert len(store.get_variants_for_verse("John.1.18")) == 0

        # ensure_variants builds them
        variants = builder.ensure_variants("John.1.18")
        assert len(variants) == 1

        # Second call returns cached
        variants2 = builder.ensure_variants("John.1.18")
        assert len(variants2) == 1

    def test_build_range(self, db_connection, spine, comparative):
        """Can build variants for a verse range."""
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("test-wh", comparative, "WH")

        # Build John 1:18 to 3:16 (sparse range in fixture)
        result = builder.build_range("John.1.18", "John.3.16")

        assert result.verses_processed >= 2
        assert result.errors == []


# ============================================================================
# Integration Tests
# ============================================================================


class TestSourcePackIntegration:
    """Integration tests for the complete source pack flow."""

    @pytest.fixture
    def db_connection(self):
        """Create in-memory database."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        # Initialize schemas
        from redletters.variants.store import VariantStore

        store = VariantStore(conn)
        store.init_schema()

        yield conn
        conn.close()

    def test_full_flow_fixture_to_variants(self, db_connection):
        """Complete flow: load fixture -> build variants -> query."""
        # Load spines
        spine = FixtureSpine(SPINE_FIXTURE, source_key="sblgnt")
        comparative = FixtureSpine(COMPARATIVE_FIXTURE, source_key="wh")

        # Build variants
        store = VariantStore(db_connection)
        builder = VariantBuilder(spine, store)
        builder.add_edition("wh", comparative, "WH")

        # Build for John 1:18
        result = builder.build_verse("John.1.18")
        assert result.variants_created == 1

        # Query variants
        variants = store.get_variants_for_verse("John.1.18")
        assert len(variants) == 1

        # Check SBLGNT is default
        variant = variants[0]
        assert variant.sblgnt_reading_index == 0
        sblgnt_reading = variant.sblgnt_reading
        assert sblgnt_reading is not None
        assert "θεὸς" in sblgnt_reading.surface_text

        # Check WH reading is alternate
        wh_reading = variant.readings[1]
        assert "υἱὸς" in wh_reading.surface_text or "WH" in wh_reading.witnesses

    def test_catalog_to_spine_resolution(self):
        """Can go from catalog to resolved spine path."""
        catalog = SourceCatalog.load()
        resolver = SourceResolver(catalog)

        resolved = resolver.resolve_spine()
        assert resolved is not None
        assert resolved.pack.is_spine

        # Should have valid root path even if files not present
        assert resolved.root_path is not None
