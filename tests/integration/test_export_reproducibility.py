"""Integration tests for export reproducibility.

v0.5.0: Reproducible Scholar Exports

Tests:
- Exporting same scope twice yields identical hashes
- Verify passes with unchanged data
- Verify fails if export content differs
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from redletters.export import EXPORT_SCHEMA_VERSION
from redletters.export.identifiers import file_hash
from redletters.export.apparatus import ApparatusExporter
from redletters.export.translation import TranslationExporter
from redletters.export.snapshot import SnapshotGenerator, SnapshotVerifier
from redletters.variants.store import VariantStore
from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    WitnessSupport,
    WitnessSupportType,
    VariantClassification,
    SignificanceLevel,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for exports."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def variant_store():
    """Create in-memory variant store with test data."""
    conn = sqlite3.connect(":memory:")
    store = VariantStore(conn)
    store.init_schema()

    # Create test variant
    variant = VariantUnit(
        ref="John.1.18",
        position=3,
        readings=[
            WitnessReading(
                surface_text="μονογενὴς θεός",
                normalized_text="μονογενης θεος",
                witnesses=["p66", "p75", "B"],
                witness_types=[],
                support_set=[
                    WitnessSupport(
                        witness_siglum="SBLGNT",
                        witness_type=WitnessSupportType.EDITION,
                        source_pack_id="test-pack",
                        century_range=(19, 21),
                    ),
                ],
            ),
            WitnessReading(
                surface_text="μονογενὴς υἱός",
                normalized_text="μονογενης υιος",
                witnesses=["A", "C"],
                witness_types=[],
                support_set=[
                    WitnessSupport(
                        witness_siglum="WH",
                        witness_type=WitnessSupportType.EDITION,
                        source_pack_id="wh-pack",
                        century_range=(19, 19),
                    ),
                ],
            ),
        ],
        sblgnt_reading_index=0,
        classification=VariantClassification.SUBSTITUTION,
        significance=SignificanceLevel.SIGNIFICANT,
    )
    store.save_variant(variant)

    yield store
    conn.close()


class TestApparatusExportReproducibility:
    """Test apparatus export reproducibility."""

    def test_export_twice_same_hash(self, variant_store, temp_dir):
        """Exporting same scope twice should yield identical files."""
        exporter = ApparatusExporter(variant_store)

        # Export twice
        path1 = temp_dir / "apparatus1.jsonl"
        path2 = temp_dir / "apparatus2.jsonl"

        exporter.export_to_file("John.1.18", path1)
        exporter.export_to_file("John.1.18", path2)

        # Compare hashes
        hash1 = file_hash(str(path1))
        hash2 = file_hash(str(path2))

        assert hash1 == hash2, "Same export should produce identical files"

    def test_export_contains_schema_version(self, variant_store, temp_dir):
        """Export rows should include schema version."""
        exporter = ApparatusExporter(variant_store)
        rows = exporter.export_to_list("John.1.18")

        assert len(rows) == 1
        assert rows[0]["schema_version"] == EXPORT_SCHEMA_VERSION

    def test_export_contains_stable_ids(self, variant_store, temp_dir):
        """Export rows should contain stable IDs."""
        exporter = ApparatusExporter(variant_store)
        rows = exporter.export_to_list("John.1.18")

        row = rows[0]
        assert row["variant_unit_id"] == "John.1.18:3"
        assert row["verse_id"] == "John.1.18"

        # Readings should have stable IDs
        for reading in row["readings"]:
            assert "reading_id" in reading
            assert reading["reading_id"].startswith("John.1.18:3#")


class TestTranslationExportReproducibility:
    """Test translation export reproducibility."""

    def test_export_twice_same_hash(self, temp_dir):
        """Exporting same ledger twice should yield identical files."""
        ledger_data = [
            {
                "verse_id": "John.1.18",
                "normalized_ref": "John 1:18",
                "tokens": [
                    {
                        "position": 0,
                        "surface": "θεόν",
                        "normalized": "θεον",
                        "lemma": "θεός",
                        "morph": "N-ASM",
                        "gloss": "God",
                        "gloss_source": "test",
                        "confidence": {
                            "textual": 0.9,
                            "grammatical": 0.9,
                            "lexical": 0.9,
                            "interpretive": 0.9,
                        },
                    },
                ],
                "provenance": {
                    "spine_source_id": "sblgnt",
                    "comparative_sources_used": [],
                },
            },
        ]

        exporter = TranslationExporter()

        path1 = temp_dir / "translation1.jsonl"
        path2 = temp_dir / "translation2.jsonl"

        exporter.export_to_file(ledger_data, path1)
        exporter.export_to_file(ledger_data, path2)

        hash1 = file_hash(str(path1))
        hash2 = file_hash(str(path2))

        assert hash1 == hash2, "Same ledger should produce identical files"

    def test_export_contains_token_ids(self, temp_dir):
        """Export rows should contain stable token IDs."""
        ledger_data = [
            {
                "verse_id": "John.1.18",
                "normalized_ref": "John 1:18",
                "tokens": [
                    {
                        "position": 0,
                        "surface": "θεόν",
                        "normalized": "θεον",
                        "lemma": "θεός",
                        "gloss": "God",
                        "gloss_source": "test",
                        "confidence": {},
                    },
                    {
                        "position": 1,
                        "surface": "οὐδείς",
                        "normalized": "ουδεις",
                        "lemma": "οὐδείς",
                        "gloss": "no one",
                        "gloss_source": "test",
                        "confidence": {},
                    },
                ],
                "provenance": {},
            },
        ]

        exporter = TranslationExporter()
        rows = exporter.export_to_list(ledger_data)

        row = rows[0]
        assert row["tokens"][0]["token_id"] == "John.1.18:0"
        assert row["tokens"][1]["token_id"] == "John.1.18:1"


class TestSnapshotGeneration:
    """Test snapshot generation."""

    def test_snapshot_includes_metadata(self, temp_dir):
        """Snapshot should include tool version and schema version."""
        generator = SnapshotGenerator()
        snapshot = generator.generate()

        assert snapshot.tool_version is not None
        assert snapshot.schema_version == EXPORT_SCHEMA_VERSION

    def test_snapshot_with_export_files(self, temp_dir):
        """Snapshot should hash export files."""
        # Create test file
        test_file = temp_dir / "test.jsonl"
        test_file.write_text('{"key":"value"}\n')

        generator = SnapshotGenerator()
        snapshot = generator.generate(export_files=[test_file])

        assert "test.jsonl" in snapshot.export_hashes
        assert len(snapshot.export_hashes["test.jsonl"]) == 64  # SHA256

    def test_snapshot_save_load(self, temp_dir):
        """Snapshot should round-trip through save/load."""
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"

        # Save
        snapshot = generator.save(snapshot_path)

        # Load
        verifier = SnapshotVerifier()
        loaded = verifier.load_snapshot(snapshot_path)

        assert loaded.tool_version == snapshot.tool_version
        assert loaded.schema_version == snapshot.schema_version


class TestSnapshotVerification:
    """Test snapshot verification."""

    def test_verify_unchanged_files_pass(self, temp_dir):
        """Verify should pass for unchanged files."""
        # Create test file
        test_file = temp_dir / "test.jsonl"
        test_file.write_text('{"key":"value"}\n')

        # Generate snapshot
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"
        generator.save(snapshot_path, export_files=[test_file])

        # Verify
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, [test_file])

        assert result.valid is True
        assert len(result.errors) == 0

    def test_verify_changed_files_fail(self, temp_dir):
        """Verify should fail for changed files."""
        # Create test file
        test_file = temp_dir / "test.jsonl"
        test_file.write_text('{"key":"value"}\n')

        # Generate snapshot
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"
        generator.save(snapshot_path, export_files=[test_file])

        # Modify file
        test_file.write_text('{"key":"different"}\n')

        # Verify
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, [test_file])

        assert result.valid is False
        assert len(result.errors) > 0
        assert "mismatch" in result.errors[0].lower()

    def test_verify_missing_file_fails(self, temp_dir):
        """Verify should fail for missing files."""
        # Create snapshot without files
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"
        generator.save(snapshot_path)

        # Try to verify non-existent file
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, [temp_dir / "missing.jsonl"])

        assert result.valid is False
        assert any("not found" in e.lower() for e in result.errors)

    def test_verify_extra_file_warns(self, temp_dir):
        """Verify should warn about files not in snapshot."""
        # Create test file
        test_file = temp_dir / "test.jsonl"
        test_file.write_text('{"key":"value"}\n')

        # Generate snapshot WITHOUT the file
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"
        generator.save(snapshot_path, export_files=[])

        # Verify with the file
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, [test_file])

        # Should have warning about file not in snapshot
        assert any("not in snapshot" in w.lower() for w in result.warnings)


class TestCitationsInSnapshot:
    """Test citations integration with snapshot system."""

    def test_citations_export_determinism(self, temp_dir):
        """Citations export should be deterministic."""
        from redletters.export.citations import CitationsExporter
        from redletters.sources.sense_db import init_sense_pack_schema

        # Create test database with sense pack schema
        conn = sqlite3.connect(":memory:")
        init_sense_pack_schema(conn)

        # Install a test sense pack
        conn.execute(
            """
            INSERT INTO installed_sense_packs
            (pack_id, name, version, license, source_id, source_title,
             edition, publisher, year, license_url, source_url, notes,
             installed_at, install_path, sense_count, pack_hash, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '', '', '', datetime('now'), '', 0, '', 0)
            """,
            (
                "test-lexicon",
                "Test Lexicon",
                "1.0.0",
                "CC0",
                "TestLex",
                "Test Lexicon Full Title",
                "1st",
                "Test Publisher",
                2020,
            ),
        )
        conn.commit()

        # Export twice
        exporter = CitationsExporter(conn=conn)
        path1 = temp_dir / "citations1.json"
        path2 = temp_dir / "citations2.json"

        exporter.export_to_file(path1, format="csljson")
        exporter.export_to_file(path2, format="csljson")

        # Compare hashes
        hash1 = file_hash(str(path1))
        hash2 = file_hash(str(path2))

        assert hash1 == hash2, "Citations export should be deterministic"
        conn.close()

    def test_citations_in_snapshot_verify(self, temp_dir):
        """Citations file should be verifiable in snapshot."""
        from redletters.export.citations import CitationsExporter
        from redletters.sources.sense_db import init_sense_pack_schema

        # Create test database with sense pack schema
        conn = sqlite3.connect(":memory:")
        init_sense_pack_schema(conn)

        # Install a test sense pack
        conn.execute(
            """
            INSERT INTO installed_sense_packs
            (pack_id, name, version, license, source_id, source_title,
             edition, publisher, year, license_url, source_url, notes,
             installed_at, install_path, sense_count, pack_hash, priority)
            VALUES (?, ?, ?, ?, ?, ?, '', '', NULL, '', '', '', datetime('now'), '', 0, '', 0)
            """,
            ("test-pack", "Test Pack", "1.0.0", "CC0", "Test", "Test Pack"),
        )
        conn.commit()

        # Export citations
        exporter = CitationsExporter(conn=conn)
        citations_path = temp_dir / "citations.json"
        exporter.export_to_file(citations_path, format="csljson")

        # Generate snapshot including citations
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"
        generator.save(snapshot_path, export_files=[citations_path])

        # Verify
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, [citations_path])

        assert result.valid is True, f"Citations verification failed: {result.errors}"
        assert "citations.json" in result.file_hashes

        conn.close()


class TestEndToEndReproducibility:
    """End-to-end reproducibility tests."""

    def test_full_export_verify_cycle(self, variant_store, temp_dir):
        """Full export -> snapshot -> verify cycle should pass."""
        # Export apparatus
        app_exporter = ApparatusExporter(variant_store)
        app_path = temp_dir / "apparatus.jsonl"
        app_exporter.export_to_file("John.1.18", app_path)

        # Export translation (mock)
        trans_exporter = TranslationExporter()
        trans_path = temp_dir / "translation.jsonl"
        trans_exporter.export_to_file(
            [
                {
                    "verse_id": "John.1.18",
                    "normalized_ref": "John 1:18",
                    "tokens": [],
                    "provenance": {},
                }
            ],
            trans_path,
        )

        # Generate snapshot
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"
        generator.save(snapshot_path, export_files=[app_path, trans_path])

        # Verify
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, [app_path, trans_path])

        assert result.valid is True, f"Verification failed: {result.errors}"

    def test_export_twice_verify_both(self, variant_store, temp_dir):
        """Exporting twice should produce verifiable identical files."""
        exporter = ApparatusExporter(variant_store)

        # Export twice
        path1 = temp_dir / "run1" / "apparatus.jsonl"
        path2 = temp_dir / "run2" / "apparatus.jsonl"

        path1.parent.mkdir(parents=True, exist_ok=True)
        path2.parent.mkdir(parents=True, exist_ok=True)

        exporter.export_to_file("John.1.18", path1)
        exporter.export_to_file("John.1.18", path2)

        # Snapshot from run1
        generator = SnapshotGenerator()
        snapshot_path = temp_dir / "snapshot.json"
        generator.save(snapshot_path, export_files=[path1])

        # Verify run2 files against run1 snapshot
        # (they should match because content is identical)
        verifier = SnapshotVerifier()
        result = verifier.verify(snapshot_path, [path2])

        # Note: paths differ but content matches
        # Verification is by filename, so this should work
        assert result.valid is True
