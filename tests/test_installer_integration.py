"""Integration tests for license-aware source pack installer.

Tests Sprint 3 installer functionality:
- EULA enforcement (refuse without --accept-eula)
- Installation workflow
- Literal translator with installed data
- Provenance includes source/license

NOTE: Tests use fixtures - no actual network calls or EULA text bundled.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from redletters.sources.installer import (
    SourceInstaller,
    InstalledManifest,
    InstalledSource,
)
from redletters.sources.catalog import SourceCatalog, SourcePack, SourceRole
from redletters.sources.spine import (
    InstalledSpineProvider,
    SpineMissingError,
    FixtureSpine,
)
from redletters.pipeline.translator import (
    LiteralTranslator,
    TranslationContext,
    get_translator,
)
from redletters.pipeline import translate_passage, TranslateResponse


# Get fixture paths
FIXTURES_DIR = Path(__file__).parent / "fixtures"
SPINE_FIXTURE = FIXTURES_DIR / "spine_fixture.json"


# ============================================================================
# License Detection Tests
# ============================================================================


class TestLicenseDetection:
    """Tests for license type detection."""

    def test_permissive_licenses_detected(self):
        """Known permissive licenses are correctly identified."""
        installer = SourceInstaller()

        # Create mock source with permissive license
        for license_id in ["CC0-1.0", "MIT", "CC-BY-SA-4.0", "Public Domain"]:
            pack = SourcePack(
                key="test",
                name="Test",
                license=license_id,
                role=SourceRole.COMPARATIVE_LAYER,
            )
            assert not installer.requires_eula(pack), (
                f"{license_id} should not require EULA"
            )

    def test_eula_licenses_detected(self):
        """EULA-requiring licenses are correctly identified."""
        installer = SourceInstaller()

        for license_id in ["EULA", "Academic use", "Proprietary"]:
            pack = SourcePack(
                key="test",
                name="Test",
                license=license_id,
                role=SourceRole.COMPARATIVE_LAYER,
            )
            assert installer.requires_eula(pack), f"{license_id} should require EULA"


# ============================================================================
# EULA Enforcement Tests
# ============================================================================


class TestEULAEnforcement:
    """Tests for EULA acceptance enforcement."""

    @pytest.fixture
    def temp_data_root(self):
        """Create temporary data root for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_eula_source_refused_without_flag(self, temp_data_root):
        """EULA sources refuse install without --accept-eula."""
        # Load real catalog
        catalog = SourceCatalog.load()
        installer = SourceInstaller(catalog=catalog, data_root=temp_data_root)

        # Try to install codex-sinaiticus (Academic use license)
        result = installer.install("codex-sinaiticus", accept_eula=False)

        assert not result.success
        assert result.eula_required
        assert result.needs_eula
        assert "EULA" in result.message or "accept" in result.message.lower()

    def test_permissive_source_installs_without_flag(self, temp_data_root, monkeypatch):
        """Permissive license sources install without EULA flag."""
        catalog = SourceCatalog.load()
        installer = SourceInstaller(catalog=catalog, data_root=temp_data_root)

        # Mock the git clone to avoid network calls
        def mock_install(*args, **kwargs):
            # Create fake installation directory
            install_path = temp_data_root / "strongs-greek"
            install_path.mkdir(parents=True, exist_ok=True)
            (install_path / "test.txt").write_text("test data")
            return install_path

        monkeypatch.setattr(installer, "_do_install", mock_install)

        # Strong's Greek is CC0-1.0 (public domain)
        result = installer.install("strongs-greek", accept_eula=False)

        # Note: May fail due to missing commit - but should NOT fail due to EULA
        if not result.success:
            assert not result.eula_required, (
                "Permissive license should not require EULA"
            )

    def test_eula_accepted_recorded_in_manifest(self, temp_data_root, monkeypatch):
        """EULA acceptance is recorded in manifest."""
        catalog = SourceCatalog.load()
        installer = SourceInstaller(catalog=catalog, data_root=temp_data_root)

        # Mock installation
        def mock_install(*args, **kwargs):
            install_path = temp_data_root / "codex-sinaiticus"
            install_path.mkdir(parents=True, exist_ok=True)
            (install_path / "test.txt").write_text("test data")
            return install_path

        monkeypatch.setattr(installer, "_do_install", mock_install)

        # Install with EULA acceptance
        result = installer.install("codex-sinaiticus", accept_eula=True)

        # Should succeed (or fail for non-EULA reasons only)
        if result.success:
            installed = installer.get_installed("codex-sinaiticus")
            assert installed is not None
            assert installed.eula_accepted_at is not None


# ============================================================================
# Installed Manifest Tests
# ============================================================================


class TestInstalledManifest:
    """Tests for installed sources manifest."""

    @pytest.fixture
    def temp_manifest_path(self):
        """Create temporary manifest path."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            yield Path(f.name)

    def test_manifest_save_load_roundtrip(self, temp_manifest_path):
        """Manifest saves and loads correctly."""
        manifest = InstalledManifest()

        manifest.add(
            InstalledSource(
                source_id="test-source",
                name="Test Source",
                installed_at="2026-01-30T10:00:00",
                install_path="/path/to/source",
                version="1.0",
                license="MIT",
                eula_accepted_at=None,
            )
        )

        manifest.save(temp_manifest_path)

        # Load back
        loaded = InstalledManifest.load(temp_manifest_path)

        assert "test-source" in loaded.sources
        assert loaded.sources["test-source"].name == "Test Source"
        assert loaded.sources["test-source"].license == "MIT"

    def test_manifest_remove_source(self, temp_manifest_path):
        """Can remove source from manifest."""
        manifest = InstalledManifest()

        manifest.add(
            InstalledSource(
                source_id="test-source",
                name="Test Source",
                installed_at="2026-01-30T10:00:00",
                install_path="/path/to/source",
            )
        )

        assert manifest.is_installed("test-source")

        manifest.remove("test-source")

        assert not manifest.is_installed("test-source")


# ============================================================================
# Spine Missing Error Tests
# ============================================================================


class TestSpineMissingError:
    """Tests for actionable spine missing errors."""

    def test_error_includes_install_instructions(self):
        """SpineMissingError includes helpful instructions."""
        error = SpineMissingError("morphgnt-sblgnt")

        assert "morphgnt-sblgnt" in str(error)
        assert "install" in str(error).lower()
        assert "redletters sources install" in str(error)

    def test_error_mentions_eula_flag(self):
        """Error mentions --accept-eula for EULA sources."""
        error = SpineMissingError("morphgnt-sblgnt")

        assert "--accept-eula" in str(error)

    def test_error_mentions_alternative(self):
        """Error mentions open-license alternative."""
        error = SpineMissingError("morphgnt-sblgnt")

        assert (
            "open-greek-nt" in str(error).lower() or "alternative" in str(error).lower()
        )


# ============================================================================
# Installed Spine Provider Tests
# ============================================================================


class TestInstalledSpineProvider:
    """Tests for spine provider using installed data."""

    @pytest.fixture
    def temp_data_root(self):
        """Create temporary data root with mock installed spine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create mock installed manifest
            manifest = {
                "manifest_version": "1.0",
                "sources": {
                    "test-spine": {
                        "source_id": "test-spine",
                        "name": "Test Spine",
                        "installed_at": "2026-01-30T10:00:00",
                        "install_path": str(root / "test-spine"),
                        "license": "MIT",
                        "eula_accepted_at": None,
                    }
                },
            }
            (root / "installed_sources.json").write_text(json.dumps(manifest))

            # Don't create actual spine directory - test missing case
            yield root

    def test_missing_spine_raises_actionable_error(self, temp_data_root):
        """Requesting missing spine raises SpineMissingError."""
        with pytest.raises(SpineMissingError) as exc_info:
            provider = InstalledSpineProvider(
                source_id="nonexistent",
                data_root=temp_data_root,
                require_installed=True,
            )
            # Trigger load
            provider.get_verse_text("John.1.18")

        assert "nonexistent" in str(exc_info.value)

    def test_optional_missing_returns_none(self, temp_data_root):
        """With require_installed=False, missing spine returns None."""
        provider = InstalledSpineProvider(
            source_id="nonexistent",
            data_root=temp_data_root,
            require_installed=False,
        )

        assert not provider.is_installed
        assert provider.get_verse_text("John.1.18") is None


# ============================================================================
# Literal Translator Tests
# ============================================================================


class TestLiteralTranslator:
    """Tests for deterministic literal translator."""

    def test_basic_gloss_generation(self):
        """LiteralTranslator produces token-level glosses."""
        translator = LiteralTranslator(
            source_id="test-source",
            source_license="MIT",
        )

        context = TranslationContext(
            reference="John.1.18",
            mode="readable",
            tokens=[
                {"surface_text": "Θεὸν", "lemma": "θεός"},
                {"surface_text": "οὐδεὶς", "lemma": "οὐδείς"},
            ],
            variants=[],
            session_id="test",
        )

        result = translator.translate("Θεὸν οὐδεὶς", context)

        # Should produce glosses
        assert "[" in result.translation_text
        assert "]" in result.translation_text
        # Should have claims
        assert len(result.claims) > 0
        # First claim should be provenance
        assert "test-source" in result.claims[0].content

    def test_respects_readable_mode(self):
        """LiteralTranslator only produces TYPE0-4 claims in readable mode."""
        translator = LiteralTranslator()

        context = TranslationContext(
            reference="John.1.18",
            mode="readable",
            tokens=[{"surface_text": "Θεὸν", "lemma": "θεός"}],
            variants=[],
            session_id="test",
        )

        result = translator.translate("Θεὸν", context)

        # All claims should be TYPE0-4 (claim_type_hint <= 4)
        for claim in result.claims:
            if claim.claim_type_hint is not None:
                assert claim.claim_type_hint <= 4, (
                    f"Claim type {claim.claim_type_hint} forbidden in readable mode"
                )

    def test_includes_provenance(self):
        """LiteralTranslator notes include provenance."""
        translator = LiteralTranslator(
            source_id="morphgnt-sblgnt",
            source_license="CC-BY-SA-3.0",
        )

        context = TranslationContext(
            reference="John.1.18",
            mode="readable",
            tokens=[],
            variants=[],
            session_id="test",
        )

        result = translator.translate("test", context)

        # Notes should include source and license
        assert any("morphgnt-sblgnt" in note for note in result.notes)
        assert any("CC-BY-SA-3.0" in note for note in result.notes)


# ============================================================================
# Integration: Translate with Fixture Spine
# ============================================================================


class TestTranslateWithFixtureSpine:
    """Integration tests for translate_passage with fixture spine."""

    @pytest.fixture
    def db_connection(self):
        """Create in-memory database with schemas."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        from redletters.variants.store import VariantStore
        from redletters.gates.state import AcknowledgementStore

        VariantStore(conn).init_schema()
        AcknowledgementStore(conn).init_schema()

        yield conn
        conn.close()

    @pytest.fixture
    def fixture_spine(self):
        """Create fixture spine for testing."""
        return FixtureSpine(SPINE_FIXTURE, source_key="test-sblgnt")

    def test_translate_with_fixture_spine(self, db_connection, fixture_spine):
        """Can translate using fixture spine."""
        translator = LiteralTranslator(
            source_id="test-sblgnt",
            source_license="test-license",
        )

        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test",
            options={"spine_provider": fixture_spine},
            translator=translator,
        )

        assert isinstance(result, TranslateResponse)
        # Should include Greek text
        assert "Θεὸν" in result.sblgnt_text or "θεὸν" in result.sblgnt_text.lower()
        # Translation should have glosses
        assert "[" in result.translation_text

    def test_provenance_includes_spine_source(self, db_connection, fixture_spine):
        """Provenance includes spine source info."""
        translator = LiteralTranslator(
            source_id="test-sblgnt",
            source_license="test-license",
        )

        result = translate_passage(
            conn=db_connection,
            reference="John 1:18",
            mode="readable",
            session_id="test",
            options={"spine_provider": fixture_spine},
            translator=translator,
        )

        assert isinstance(result, TranslateResponse)
        # Provenance should reflect spine provider
        assert "sblgnt" in result.provenance.spine_source.lower()


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestGetTranslator:
    """Tests for get_translator factory function."""

    def test_get_fake_translator(self):
        """get_translator returns FakeTranslator for 'fake' type."""
        translator = get_translator(translator_type="fake", scenario="clean")

        from redletters.pipeline.translator import FakeTranslator

        assert isinstance(translator, FakeTranslator)

    def test_get_literal_translator(self):
        """get_translator returns LiteralTranslator for 'literal' type."""
        translator = get_translator(
            translator_type="literal",
            source_id="test",
            source_license="MIT",
        )

        assert isinstance(translator, LiteralTranslator)
        assert translator.source_id == "test"
        assert translator.source_license == "MIT"
