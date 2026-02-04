"""Tests for v0.10.0 Schema Contracts + Validation.

Validates:
- schema_version present in each artifact type
- Snapshot includes schema_versions mapping
- Validator passes on real generated outputs
- Validator fails on tampered output
- Validator auto-detect works
"""

import json
import pytest
from pathlib import Path


class TestSchemaVersionConstants:
    """Test centralized schema version constants."""

    def test_all_schema_versions_function(self):
        """get_all_schema_versions returns all expected artifact types."""
        from redletters.export.schema_versions import get_all_schema_versions

        versions = get_all_schema_versions()

        assert "apparatus" in versions
        assert "translation" in versions
        assert "snapshot" in versions
        assert "citations" in versions
        assert "quote" in versions
        assert "dossier" in versions
        assert "confidence_bucketing" in versions

    def test_schema_versions_are_semver(self):
        """All schema versions follow semver format."""
        from redletters.export.schema_versions import get_all_schema_versions

        versions = get_all_schema_versions()

        for artifact, version in versions.items():
            parts = version.split(".")
            assert len(parts) == 3, f"{artifact}: {version} is not semver"
            for part in parts:
                assert part.isdigit(), f"{artifact}: {version} has non-numeric part"

    def test_export_schema_version_constant(self):
        """EXPORT_SCHEMA_VERSION is accessible from export module."""
        from redletters.export import EXPORT_SCHEMA_VERSION

        assert EXPORT_SCHEMA_VERSION == "1.0.0"

    def test_quote_schema_version_constant(self):
        """QUOTE_SCHEMA_VERSION is accessible from export module."""
        from redletters.export import QUOTE_SCHEMA_VERSION

        assert QUOTE_SCHEMA_VERSION == "1.0.0"

    def test_dossier_schema_version_constant(self):
        """DOSSIER_SCHEMA_VERSION is accessible from export module."""
        from redletters.export import DOSSIER_SCHEMA_VERSION

        assert DOSSIER_SCHEMA_VERSION == "1.0.0"


class TestApparatusSchemaVersion:
    """Test schema_version in apparatus export."""

    def test_apparatus_row_has_schema_version(self):
        """ApparatusRow includes schema_version field."""
        from redletters.export.apparatus import ApparatusRow
        from redletters.export import EXPORT_SCHEMA_VERSION

        row = ApparatusRow(
            variant_unit_id="test-id",
            verse_id="John.1.1",
            position=0,
            classification="substitution",
            significance="minor",
            gate_requirement="none",
            sblgnt_reading_index=0,
            readings=[{"reading_id": "r1", "text": "test"}],
            provenance_packs=["pack1"],
            reason_code="",
            reason_summary="",
            schema_version=EXPORT_SCHEMA_VERSION,
        )

        result = row.to_dict()
        assert "schema_version" in result
        assert result["schema_version"] == EXPORT_SCHEMA_VERSION


class TestTranslationSchemaVersion:
    """Test schema_version in translation export."""

    def test_translation_row_has_schema_version(self):
        """TranslationRow includes schema_version field."""
        from redletters.export.translation import TranslationRow
        from redletters.export import EXPORT_SCHEMA_VERSION

        row = TranslationRow(
            verse_id="John.1.1",
            normalized_ref="John.1.1",
            spine_text="test",
            tokens=[],
            renderings=[],
            confidence_summary={
                "textual": 1.0,
                "grammatical": 1.0,
                "lexical": 1.0,
                "interpretive": 1.0,
                "composite": 1.0,
                "bucket": "high",
            },
            provenance={},
            schema_version=EXPORT_SCHEMA_VERSION,
        )

        result = row.to_dict()
        assert "schema_version" in result
        assert result["schema_version"] == EXPORT_SCHEMA_VERSION


class TestSnapshotSchemaVersions:
    """Test schema_versions in snapshot."""

    def test_snapshot_includes_schema_versions_dict(self):
        """Snapshot includes schema_versions mapping."""
        from redletters.export.snapshot import Snapshot, CONFIDENCE_BUCKETING_VERSION
        from redletters.export import EXPORT_SCHEMA_VERSION
        from redletters.export.schema_versions import get_all_schema_versions

        snapshot = Snapshot(
            tool_version="0.10.0",
            schema_version=EXPORT_SCHEMA_VERSION,
            git_commit=None,
            timestamp="2026-02-02T00:00:00Z",
            packs=[],
            export_hashes={},
            confidence_bucketing_version=CONFIDENCE_BUCKETING_VERSION,
            schema_versions=get_all_schema_versions(),
        )

        result = snapshot.to_dict()
        assert "schema_versions" in result
        assert "apparatus" in result["schema_versions"]
        assert "translation" in result["schema_versions"]
        assert "quote" in result["schema_versions"]
        assert "dossier" in result["schema_versions"]

    def test_snapshot_from_dict_preserves_schema_versions(self):
        """Snapshot.from_dict preserves schema_versions field."""
        from redletters.export.snapshot import Snapshot

        data = {
            "tool_version": "0.10.0",
            "schema_version": "1.0.0",
            "git_commit": None,
            "timestamp": "2026-02-02T00:00:00Z",
            "packs": [],
            "export_hashes": {},
            "schema_versions": {"apparatus": "1.0.0", "quote": "1.0.0"},
        }

        snapshot = Snapshot.from_dict(data)
        assert snapshot.schema_versions == {"apparatus": "1.0.0", "quote": "1.0.0"}


class TestDossierSchemaVersion:
    """Test schema_version in dossier output."""

    def test_dossier_has_schema_version(self):
        """Dossier includes schema_version field."""
        from redletters.variants.dossier import (
            Dossier,
            DossierSpine,
            DossierProvenance,
        )
        from redletters.export.schema_versions import DOSSIER_SCHEMA_VERSION

        dossier = Dossier(
            reference="John.1.1",
            scope="verse",
            generated_at="2026-02-02T00:00:00Z",
            spine=DossierSpine(
                source_id="morphgnt-sblgnt", text="test", is_default=True
            ),
            variants=[],
            provenance=DossierProvenance(
                spine_source="morphgnt-sblgnt",
                comparative_packs=[],
                build_timestamp="2026-02-02T00:00:00Z",
            ),
        )

        result = dossier.to_dict()
        assert "schema_version" in result
        assert result["schema_version"] == DOSSIER_SCHEMA_VERSION


class TestValidatorBasics:
    """Test basic validator functionality."""

    def test_validate_valid_json(self, tmp_path):
        """Validator passes on valid JSON file."""
        from redletters.export.validator import validate_output

        # Create valid quote file
        quote_data = {
            "reference": "John 1:1",
            "reference_normalized": "John.1.1",
            "mode": "readable",
            "spine_text": "test",
            "provenance": {"packs_used": [], "session_id": "test"},
            "gate_status": {"gates_cleared": True, "forced_responsibility": False},
            "generated_at": "2026-02-02T00:00:00Z",
            "schema_version": "1.0.0",
        }

        file_path = tmp_path / "quote.json"
        file_path.write_text(json.dumps(quote_data))

        result = validate_output(file_path, artifact_type="quote")

        assert result.valid
        assert result.artifact_type == "quote"
        assert result.records_checked == 1
        assert result.schema_version_found == "1.0.0"

    def test_validate_missing_required_field(self, tmp_path):
        """Validator fails when required field is missing."""
        from redletters.export.validator import validate_output

        # Create quote file missing gate_status
        quote_data = {
            "reference": "John 1:1",
            "mode": "readable",
            "spine_text": "test",
            "provenance": {"packs_used": [], "session_id": "test"},
            # Missing: gate_status
            "generated_at": "2026-02-02T00:00:00Z",
            "schema_version": "1.0.0",
        }

        file_path = tmp_path / "quote.json"
        file_path.write_text(json.dumps(quote_data))

        result = validate_output(file_path, artifact_type="quote")

        assert not result.valid
        assert any("gate_status" in e for e in result.errors)

    def test_validate_invalid_json(self, tmp_path):
        """Validator fails on invalid JSON."""
        from redletters.export.validator import validate_output

        file_path = tmp_path / "broken.json"
        file_path.write_text("{ not valid json")

        result = validate_output(file_path, artifact_type="quote")

        assert not result.valid
        assert any("Invalid JSON" in e for e in result.errors)

    def test_validate_file_not_found(self, tmp_path):
        """Validator fails when file doesn't exist."""
        from redletters.export.validator import validate_output

        result = validate_output(tmp_path / "nonexistent.json", artifact_type="quote")

        assert not result.valid
        assert any("not found" in e for e in result.errors)


class TestValidatorJsonl:
    """Test validator for JSONL files."""

    def test_validate_valid_jsonl(self, tmp_path):
        """Validator passes on valid JSONL file."""
        from redletters.export.validator import validate_output

        # Create valid apparatus JSONL
        records = [
            {
                "variant_unit_id": "vu1",
                "verse_id": "John.1.1",
                "position": 0,
                "classification": "substitution",
                "significance": "minor",
                "gate_requirement": "none",
                "sblgnt_reading_index": 0,
                "readings": [{"reading_id": "r1", "text": "test"}],
                "provenance_packs": ["pack1"],
                "schema_version": "1.0.0",
            },
            {
                "variant_unit_id": "vu2",
                "verse_id": "John.1.2",
                "position": 0,
                "classification": "omission",
                "significance": "significant",
                "gate_requirement": "requires_acknowledgement",
                "sblgnt_reading_index": 0,
                "readings": [{"reading_id": "r2", "text": "test2"}],
                "provenance_packs": ["pack1"],
                "schema_version": "1.0.0",
            },
        ]

        file_path = tmp_path / "apparatus.jsonl"
        file_path.write_text("\n".join(json.dumps(r) for r in records))

        result = validate_output(file_path, artifact_type="apparatus")

        assert result.valid
        assert result.artifact_type == "apparatus"
        assert result.records_checked == 2

    def test_validate_jsonl_with_error_on_line_2(self, tmp_path):
        """Validator reports line number for JSONL errors."""
        from redletters.export.validator import validate_output

        records = [
            {
                "variant_unit_id": "vu1",
                "verse_id": "John.1.1",
                "readings": [{"reading_id": "r1"}],
                "schema_version": "1.0.0",
            },
            {
                "variant_unit_id": "vu2",
                # Missing: verse_id, readings
                "schema_version": "1.0.0",
            },
        ]

        file_path = tmp_path / "apparatus.jsonl"
        file_path.write_text("\n".join(json.dumps(r) for r in records))

        result = validate_output(file_path, artifact_type="apparatus")

        assert not result.valid
        assert any("Line 2" in e for e in result.errors)


class TestValidatorAutoDetect:
    """Test auto-detection of artifact types."""

    def test_autodetect_quote_from_content(self, tmp_path):
        """Validator auto-detects quote from gate_status field."""
        from redletters.export.validator import validate_output

        quote_data = {
            "reference": "John 1:1",
            "reference_normalized": "John.1.1",
            "mode": "readable",
            "spine_text": "test",
            "provenance": {"packs_used": [], "session_id": "test"},
            "gate_status": {"gates_cleared": True, "forced_responsibility": False},
            "generated_at": "2026-02-02T00:00:00Z",
            "schema_version": "1.0.0",
        }

        file_path = tmp_path / "output.json"
        file_path.write_text(json.dumps(quote_data))

        result = validate_output(file_path)  # No artifact_type

        assert result.valid
        assert result.artifact_type == "quote"

    def test_autodetect_snapshot_from_content(self, tmp_path):
        """Validator auto-detects snapshot from tool_version + export_hashes."""
        from redletters.export.validator import validate_output

        snapshot_data = {
            "tool_version": "0.10.0",
            "schema_version": "1.0.0",
            "timestamp": "2026-02-02T00:00:00Z",
            "packs": [],
            "export_hashes": {"apparatus.jsonl": "abc123"},
        }

        file_path = tmp_path / "output.json"
        file_path.write_text(json.dumps(snapshot_data))

        result = validate_output(file_path)  # No artifact_type

        assert result.valid
        assert result.artifact_type == "snapshot"

    def test_autodetect_from_filename(self, tmp_path):
        """Validator auto-detects from filename patterns."""
        from redletters.export.validator import validate_output

        dossier_data = {
            "reference": "John.1.1",
            "scope": "verse",
            "generated_at": "2026-02-02T00:00:00Z",
            "spine": {"source_id": "test", "text": "test", "is_default": True},
            "variants": [],
            "provenance": {
                "spine_source": "test",
                "comparative_packs": [],
                "build_timestamp": "2026-02-02T00:00:00Z",
            },
            "schema_version": "1.0.0",
        }

        file_path = tmp_path / "my_dossier.json"
        file_path.write_text(json.dumps(dossier_data))

        result = validate_output(file_path)  # No artifact_type

        assert result.valid
        assert result.artifact_type == "dossier"


class TestValidatorTamperedOutput:
    """Test that validator fails on tampered output."""

    def test_tampered_missing_schema_version(self, tmp_path):
        """Validator fails when schema_version is removed."""
        from redletters.export.validator import validate_output

        # Valid quote data with schema_version removed
        quote_data = {
            "reference": "John 1:1",
            "reference_normalized": "John.1.1",
            "mode": "readable",
            "spine_text": "test",
            "provenance": {"packs_used": [], "session_id": "test"},
            "gate_status": {"gates_cleared": True, "forced_responsibility": False},
            "generated_at": "2026-02-02T00:00:00Z",
            # schema_version intentionally removed
        }

        file_path = tmp_path / "quote.json"
        file_path.write_text(json.dumps(quote_data))

        result = validate_output(file_path, artifact_type="quote")

        assert not result.valid
        assert any("schema_version" in e for e in result.errors)

    def test_tampered_invalid_schema_version_format(self, tmp_path):
        """Validator fails when schema_version has wrong format."""
        from redletters.export.validator import validate_output

        quote_data = {
            "reference": "John 1:1",
            "reference_normalized": "John.1.1",
            "mode": "readable",
            "spine_text": "test",
            "provenance": {"packs_used": [], "session_id": "test"},
            "gate_status": {"gates_cleared": True, "forced_responsibility": False},
            "generated_at": "2026-02-02T00:00:00Z",
            "schema_version": "not-semver",  # Invalid format
        }

        file_path = tmp_path / "quote.json"
        file_path.write_text(json.dumps(quote_data))

        result = validate_output(file_path, artifact_type="quote")

        assert not result.valid
        assert any("semver" in e for e in result.errors)

    def test_tampered_empty_readings_array(self, tmp_path):
        """Validator fails when apparatus has empty readings."""
        from redletters.export.validator import validate_output

        apparatus_data = {
            "variant_unit_id": "vu1",
            "verse_id": "John.1.1",
            "position": 0,
            "classification": "substitution",
            "significance": "minor",
            "gate_requirement": "none",
            "sblgnt_reading_index": 0,
            "readings": [],  # Empty - invalid
            "provenance_packs": ["pack1"],
            "schema_version": "1.0.0",
        }

        file_path = tmp_path / "apparatus.jsonl"
        file_path.write_text(json.dumps(apparatus_data))

        result = validate_output(file_path, artifact_type="apparatus")

        assert not result.valid
        assert any("non-empty" in e for e in result.errors)


class TestSchemaFilesExist:
    """Test that JSON Schema files exist."""

    @pytest.fixture
    def schemas_dir(self):
        """Get path to schemas directory."""
        return Path(__file__).parent.parent / "docs" / "schemas"

    def test_apparatus_schema_exists(self, schemas_dir):
        """Apparatus schema file exists."""
        assert (schemas_dir / "apparatus-v1.0.0.schema.json").exists()

    def test_translation_schema_exists(self, schemas_dir):
        """Translation schema file exists."""
        assert (schemas_dir / "translation-v1.0.0.schema.json").exists()

    def test_quote_schema_exists(self, schemas_dir):
        """Quote schema file exists."""
        assert (schemas_dir / "quote-v1.0.0.schema.json").exists()

    def test_snapshot_schema_exists(self, schemas_dir):
        """Snapshot schema file exists."""
        assert (schemas_dir / "snapshot-v1.0.0.schema.json").exists()

    def test_citations_schema_exists(self, schemas_dir):
        """Citations schema file exists."""
        assert (schemas_dir / "citations-v1.0.0.schema.json").exists()

    def test_dossier_schema_exists(self, schemas_dir):
        """Dossier schema file exists."""
        assert (schemas_dir / "dossier-v1.0.0.schema.json").exists()

    def test_schema_files_are_valid_json(self, schemas_dir):
        """All schema files are valid JSON."""
        for schema_file in schemas_dir.glob("*.schema.json"):
            content = schema_file.read_text()
            data = json.loads(content)  # Will raise if invalid
            assert "$schema" in data
            assert "title" in data
