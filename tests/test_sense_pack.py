"""Tests for sense pack schema and validation (v0.6.0).

Covers:
- SensePackManifest creation and serialization
- SensePackValidator for manifest and data validation
- SensePackLoader for reading sense data
- Citation-grade provenance fields
"""

import json

from redletters.sources.sense_pack import (
    SensePackManifest,
    SensePackLoader,
    SenseEntry,
    validate_sense_pack,
    SENSE_PACK_ROLE,
)


class TestSensePackManifest:
    """Tests for SensePackManifest dataclass."""

    def test_from_dict_minimal(self):
        """Test creating manifest with minimal required fields."""
        data = {
            "pack_id": "test-senses",
            "name": "Test Sense Pack",
            "version": "1.0.0",
            "role": "sense_pack",
            "license": "CC0",
            "source_id": "test_senses",
            "source_title": "Test Sense Dictionary",
        }
        manifest = SensePackManifest.from_dict(data)

        assert manifest.pack_id == "test-senses"
        assert manifest.name == "Test Sense Pack"
        assert manifest.license == "CC0"
        assert manifest.source_id == "test_senses"
        assert manifest.source_title == "Test Sense Dictionary"
        assert manifest.role == SENSE_PACK_ROLE

    def test_from_dict_full_citation(self):
        """Test creating manifest with full citation fields."""
        data = {
            "pack_id": "lsj-excerpt",
            "name": "LSJ Greek-English Lexicon Excerpt",
            "version": "1.0.0",
            "role": "sense_pack",
            "license": "CC BY-SA 4.0",
            "source_id": "LSJ",
            "source_title": "A Greek-English Lexicon",
            "edition": "9th edition with revised supplement",
            "publisher": "Clarendon Press",
            "year": 1996,
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "source_url": "https://lsj.gr/",
            "notes": "Public domain excerpts only",
        }
        manifest = SensePackManifest.from_dict(data)

        assert manifest.source_id == "LSJ"
        assert manifest.edition == "9th edition with revised supplement"
        assert manifest.publisher == "Clarendon Press"
        assert manifest.year == 1996
        assert manifest.license_url == "https://creativecommons.org/licenses/by-sa/4.0/"

    def test_to_dict_roundtrip(self):
        """Test manifest serialization roundtrip."""
        data = {
            "pack_id": "test-pack",
            "name": "Test",
            "version": "1.0.0",
            "role": "sense_pack",
            "license": "CC0",
            "source_id": "test",
            "source_title": "Test Dictionary",
            "edition": "1st",
            "year": 2026,
        }
        manifest = SensePackManifest.from_dict(data)
        result = manifest.to_dict()

        assert result["pack_id"] == "test-pack"
        assert result["source_id"] == "test"
        assert result["edition"] == "1st"
        assert result["year"] == 2026

    def test_requires_license_acceptance_cc0(self):
        """Test that CC0 does not require license acceptance."""
        manifest = SensePackManifest.from_dict(
            {
                "pack_id": "test",
                "name": "Test",
                "license": "CC0",
                "source_id": "test",
                "source_title": "Test",
            }
        )
        assert not manifest.requires_license_acceptance

    def test_requires_license_acceptance_public_domain(self):
        """Test that Public Domain does not require acceptance."""
        manifest = SensePackManifest.from_dict(
            {
                "pack_id": "test",
                "name": "Test",
                "license": "Public Domain",
                "source_id": "test",
                "source_title": "Test",
            }
        )
        assert not manifest.requires_license_acceptance

    def test_requires_license_acceptance_cc_by_sa(self):
        """Test that CC BY-SA requires license acceptance."""
        manifest = SensePackManifest.from_dict(
            {
                "pack_id": "test",
                "name": "Test",
                "license": "CC BY-SA 4.0",
                "source_id": "test",
                "source_title": "Test",
            }
        )
        assert manifest.requires_license_acceptance

    def test_citation_dict(self):
        """Test citation_dict returns proper provenance fields."""
        manifest = SensePackManifest.from_dict(
            {
                "pack_id": "bdag-sample",
                "name": "BDAG Sample",
                "license": "Fair Use",
                "source_id": "BDAG",
                "source_title": "A Greek-English Lexicon of the NT",
                "edition": "3rd",
                "publisher": "University of Chicago Press",
                "year": 2000,
            }
        )
        citation = manifest.citation_dict()

        assert citation["source_id"] == "BDAG"
        assert citation["source_title"] == "A Greek-English Lexicon of the NT"
        assert citation["license"] == "Fair Use"
        assert citation["edition"] == "3rd"
        assert citation["publisher"] == "University of Chicago Press"
        assert citation["year"] == 2000


class TestSensePackValidator:
    """Tests for SensePackValidator."""

    def test_validate_missing_directory(self, tmp_path):
        """Test validation fails for missing directory."""
        result = validate_sense_pack(tmp_path / "nonexistent")
        assert not result.valid
        assert any("does not exist" in e.message for e in result.errors)

    def test_validate_missing_manifest(self, tmp_path):
        """Test validation fails for missing manifest.json."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()

        result = validate_sense_pack(pack_dir)
        assert not result.valid
        assert any("manifest.json not found" in e.message for e in result.errors)

    def test_validate_invalid_json(self, tmp_path):
        """Test validation fails for invalid JSON manifest."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text("{invalid json")

        result = validate_sense_pack(pack_dir)
        assert not result.valid
        assert any("Invalid JSON" in e.message for e in result.errors)

    def test_validate_wrong_role(self, tmp_path):
        """Test validation fails for non-sense_pack role."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test",
                    "role": "comparative_layer",  # Wrong role
                    "license": "CC0",
                    "source_id": "test",
                    "source_title": "Test",
                }
            )
        )

        result = validate_sense_pack(pack_dir)
        assert not result.valid
        assert any("role" in e.message.lower() for e in result.errors)

    def test_validate_missing_required_fields(self, tmp_path):
        """Test validation fails for missing required fields."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test",
                    "role": "sense_pack",
                    # Missing: license, source_id, source_title
                }
            )
        )

        result = validate_sense_pack(pack_dir)
        assert not result.valid
        assert len(result.errors) >= 3  # At least 3 missing fields

    def test_validate_valid_manifest_missing_data(self, tmp_path):
        """Test validation fails for missing sense data file."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "test",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.tsv",
                }
            )
        )

        result = validate_sense_pack(pack_dir)
        assert not result.valid
        assert any("not found" in e.message for e in result.errors)

    def test_validate_valid_tsv_pack(self, tmp_path):
        """Test validation succeeds for valid TSV sense pack."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "test",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.tsv",
                }
            )
        )
        (pack_dir / "senses.tsv").write_text(
            "lemma\tsense_id\tgloss\tdefinition\tdomain\tweight\n"
            "λόγος\tlogos.1\tword\tspoken word\tspeech\t0.8\n"
            "λόγος\tlogos.2\treason\tlogical principle\tcognition\t0.6\n"
        )

        result = validate_sense_pack(pack_dir)
        assert result.valid
        assert result.sense_count == 2
        assert result.manifest is not None
        assert result.manifest.source_id == "test"

    def test_validate_valid_json_pack(self, tmp_path):
        """Test validation succeeds for valid JSON sense pack."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "test",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.json",
                }
            )
        )
        (pack_dir / "senses.json").write_text(
            json.dumps(
                [
                    {"lemma": "θεός", "sense_id": "theos.1", "gloss": "God"},
                    {"lemma": "θεός", "sense_id": "theos.2", "gloss": "god"},
                ]
            )
        )

        result = validate_sense_pack(pack_dir)
        assert result.valid
        assert result.sense_count == 2

    def test_validate_tsv_missing_columns(self, tmp_path):
        """Test validation fails for TSV missing required columns."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "test",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.tsv",
                }
            )
        )
        (pack_dir / "senses.tsv").write_text(
            "lemma\tgloss\n"  # Missing sense_id column
            "λόγος\tword\n"
        )

        result = validate_sense_pack(pack_dir)
        assert not result.valid
        assert any("sense_id" in e.message for e in result.errors)

    def test_validate_strict_mode(self, tmp_path):
        """Test strict mode treats warnings as errors."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "Test-Pack",  # Should be lowercase slug
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "test",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.tsv",
                }
            )
        )
        (pack_dir / "senses.tsv").write_text(
            "lemma\tsense_id\tgloss\nλόγος\tlogos.1\tword\n"
        )

        # Non-strict: warning only
        result = validate_sense_pack(pack_dir, strict=False)
        assert result.valid
        assert len(result.warnings) > 0

        # Strict: warning becomes error
        result_strict = validate_sense_pack(pack_dir, strict=True)
        assert not result_strict.valid


class TestSensePackLoader:
    """Tests for SensePackLoader."""

    def test_load_tsv_pack(self, tmp_path):
        """Test loading TSV sense pack."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "TestDict",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.tsv",
                }
            )
        )
        (pack_dir / "senses.tsv").write_text(
            "lemma\tsense_id\tgloss\tdefinition\tdomain\tweight\n"
            "λόγος\tlogos.1\tword\tspoken word\tspeech\t0.8\n"
            "λόγος\tlogos.2\treason\tlogical principle\tcognition\t0.6\n"
            "θεός\ttheos.1\tGod\tthe divine being\treligion\t0.9\n"
        )

        loader = SensePackLoader(pack_dir)
        assert loader.load()
        assert len(loader) == 3

        senses = list(loader.iter_senses())
        assert len(senses) == 3
        assert senses[0].lemma == "λόγος"
        assert senses[0].sense_id == "logos.1"
        assert senses[0].gloss == "word"
        assert senses[0].source_id == "TestDict"

    def test_load_json_pack(self, tmp_path):
        """Test loading JSON sense pack."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "TestDict",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.json",
                }
            )
        )
        (pack_dir / "senses.json").write_text(
            json.dumps(
                [
                    {
                        "lemma": "θεός",
                        "sense_id": "theos.1",
                        "gloss": "God",
                        "weight": 0.9,
                    },
                    {
                        "lemma": "θεός",
                        "sense_id": "theos.2",
                        "gloss": "god",
                        "weight": 0.5,
                    },
                ]
            )
        )

        loader = SensePackLoader(pack_dir)
        assert loader.load()
        assert len(loader) == 2

        manifest = loader.manifest
        assert manifest is not None
        assert manifest.source_id == "TestDict"

    def test_get_senses_for_lemma(self, tmp_path):
        """Test filtering senses by lemma."""
        pack_dir = tmp_path / "test-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "pack_id": "test",
                    "name": "Test Pack",
                    "role": "sense_pack",
                    "license": "CC0",
                    "source_id": "test",
                    "source_title": "Test Dictionary",
                    "data_file": "senses.tsv",
                }
            )
        )
        (pack_dir / "senses.tsv").write_text(
            "lemma\tsense_id\tgloss\n"
            "λόγος\tlogos.1\tword\n"
            "λόγος\tlogos.2\treason\n"
            "θεός\ttheos.1\tGod\n"
        )

        loader = SensePackLoader(pack_dir)
        loader.load()

        logos_senses = loader.get_senses_for_lemma("λόγος")
        assert len(logos_senses) == 2

        theos_senses = loader.get_senses_for_lemma("θεός")
        assert len(theos_senses) == 1

        missing = loader.get_senses_for_lemma("missing")
        assert len(missing) == 0


class TestSenseEntry:
    """Tests for SenseEntry dataclass."""

    def test_to_dict(self):
        """Test SenseEntry serialization."""
        entry = SenseEntry(
            lemma="λόγος",
            sense_id="logos.1",
            gloss="word",
            definition="spoken word",
            domain="speech",
            weight=0.8,
            source_id="LSJ",
        )
        result = entry.to_dict()

        assert result["lemma"] == "λόγος"
        assert result["sense_id"] == "logos.1"
        assert result["gloss"] == "word"
        assert result["source_id"] == "LSJ"
        assert result["weight"] == 0.8


class TestSensePackRoleInCatalog:
    """Test that sense_pack role is in catalog."""

    def test_sense_pack_role_exists(self):
        """Test that SENSE_PACK role is defined."""
        from redletters.sources.catalog import SourceRole

        assert hasattr(SourceRole, "SENSE_PACK")
        assert SourceRole.SENSE_PACK.value == "sense_pack"
