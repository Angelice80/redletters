"""Tests for quote command friction (v0.9.0).

Tests that quote command enforces gate acknowledgement.
"""

import json
import sqlite3
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from redletters.__main__ import cli
from redletters.variants.store import VariantStore
from redletters.variants.models import (
    VariantUnit,
    WitnessReading,
    VariantClassification,
    SignificanceLevel,
    WitnessType,
    WitnessSupport,
    WitnessSupportType,
)
from redletters.gates.state import AcknowledgementStore


@pytest.fixture
def temp_data_root(tmp_path):
    """Create a temporary data root with initialized database."""
    data_root = tmp_path / "data"
    data_root.mkdir()

    # Create database
    db_path = data_root / "redletters.db"
    conn = sqlite3.connect(str(db_path))

    # Initialize variant store
    store = VariantStore(conn)
    store.init_schema()

    # Initialize ack store
    ack_store = AcknowledgementStore(conn)
    ack_store.init_schema()

    conn.close()
    return data_root


@pytest.fixture
def data_root_with_significant_variant(temp_data_root):
    """Create data root with a significant variant requiring acknowledgement."""
    db_path = temp_data_root / "redletters.db"
    conn = sqlite3.connect(str(db_path))

    store = VariantStore(conn)

    # Add a significant variant
    variant = VariantUnit(
        ref="John.1.1",
        position=0,
        readings=[
            WitnessReading(
                surface_text="θεὸς",
                witnesses=["P66", "01"],
                witness_types=[WitnessType.PAPYRUS, WitnessType.UNCIAL],
                support_set=[
                    WitnessSupport(
                        witness_siglum="P66",
                        witness_type=WitnessSupportType.MANUSCRIPT,
                        source_pack_id="test-pack",
                        century_range=(2, 2),
                    ),
                ],
            ),
            WitnessReading(
                surface_text="ὁ θεὸς",
                witnesses=["A"],
                witness_types=[WitnessType.UNCIAL],
                support_set=[
                    WitnessSupport(
                        witness_siglum="A",
                        witness_type=WitnessSupportType.MANUSCRIPT,
                        source_pack_id="test-pack",
                        century_range=(5, 5),
                    ),
                ],
            ),
        ],
        sblgnt_reading_index=0,
        classification=VariantClassification.SUBSTITUTION,
        significance=SignificanceLevel.SIGNIFICANT,  # Requires acknowledgement
        reason_code="christological_term",
        reason_summary="Christological significance",
    )
    store.save_variant(variant)

    conn.close()
    return temp_data_root


@pytest.fixture
def data_root_with_minor_variant(temp_data_root):
    """Create data root with only minor variants (no acknowledgement required)."""
    db_path = temp_data_root / "redletters.db"
    conn = sqlite3.connect(str(db_path))

    store = VariantStore(conn)

    # Add a minor variant
    variant = VariantUnit(
        ref="John.1.1",
        position=0,
        readings=[
            WitnessReading(
                surface_text="ἐν",
                witnesses=["P66"],
                witness_types=[WitnessType.PAPYRUS],
            ),
            WitnessReading(
                surface_text="εν",
                witnesses=["A"],
                witness_types=[WitnessType.UNCIAL],
            ),
        ],
        sblgnt_reading_index=0,
        classification=VariantClassification.SPELLING,
        significance=SignificanceLevel.TRIVIAL,  # No acknowledgement required
        reason_code="spelling",
        reason_summary="Spelling variant",
    )
    store.save_variant(variant)

    conn.close()
    return temp_data_root


class TestQuoteFriction:
    """Tests for quote command gate friction."""

    def test_quote_succeeds_with_no_significant_variants(
        self, data_root_with_minor_variant
    ):
        """Quote should succeed when no significant variants exist."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name

        result = runner.invoke(
            cli,
            [
                "quote",
                "John 1:1",
                "--data-root",
                str(data_root_with_minor_variant),
                "--out",
                out_path,
            ],
        )

        # Should succeed
        assert result.exit_code == 0, result.output
        assert "Quote generated" in result.output

        # Check output
        output = json.loads(Path(out_path).read_text())
        assert output["gate_status"]["gates_cleared"] is True
        assert output["gate_status"]["forced_responsibility"] is False

    def test_quote_fails_with_pending_gates(self, data_root_with_significant_variant):
        """Quote should fail when significant variants are unacknowledged."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name

        result = runner.invoke(
            cli,
            [
                "quote",
                "John 1:1",
                "--data-root",
                str(data_root_with_significant_variant),
                "--out",
                out_path,
            ],
        )

        # Should fail
        assert result.exit_code == 1
        assert "pending gate" in result.output.lower()

    def test_quote_succeeds_with_force(self, data_root_with_significant_variant):
        """Quote should succeed with --force, marking forced_responsibility."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name

        result = runner.invoke(
            cli,
            [
                "quote",
                "John 1:1",
                "--data-root",
                str(data_root_with_significant_variant),
                "--out",
                out_path,
                "--force",
            ],
        )

        # Should succeed
        assert result.exit_code == 0, result.output
        assert "forced_responsibility" in result.output

        # Check output
        output = json.loads(Path(out_path).read_text())
        assert output["gate_status"]["gates_cleared"] is False
        assert output["gate_status"]["forced_responsibility"] is True
        assert "pending_gates" in output["gate_status"]
        assert len(output["gate_status"]["pending_gates"]) > 0

    def test_quote_succeeds_after_acknowledgement(
        self, data_root_with_significant_variant
    ):
        """Quote should succeed after gates are acknowledged."""
        from datetime import datetime
        from redletters.gates.state import VariantAcknowledgement

        # First acknowledge the gate
        db_path = data_root_with_significant_variant / "redletters.db"
        conn = sqlite3.connect(str(db_path))
        ack_store = AcknowledgementStore(conn)
        ack_store.init_schema()
        ack = VariantAcknowledgement(
            ref="John.1.1",
            reading_chosen=0,
            timestamp=datetime.now(),
            context="Reviewed",
            session_id="cli-default",
        )
        ack_store.persist_variant_ack(ack)
        conn.close()

        # Now quote should succeed
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name

        result = runner.invoke(
            cli,
            [
                "quote",
                "John 1:1",
                "--data-root",
                str(data_root_with_significant_variant),
                "--out",
                out_path,
            ],
        )

        # Should succeed
        assert result.exit_code == 0, result.output
        assert "Quote generated" in result.output

        # Check output
        output = json.loads(Path(out_path).read_text())
        assert output["gate_status"]["gates_cleared"] is True
        assert output["gate_status"]["forced_responsibility"] is False


class TestQuoteOutput:
    """Tests for quote output format."""

    def test_quote_output_has_required_fields(self, data_root_with_minor_variant):
        """Quote output should have all required fields."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name

        result = runner.invoke(
            cli,
            [
                "quote",
                "John 1:1",
                "--data-root",
                str(data_root_with_minor_variant),
                "--out",
                out_path,
            ],
        )

        assert result.exit_code == 0, result.output

        output = json.loads(Path(out_path).read_text())

        # Required fields
        assert "reference" in output
        assert "reference_normalized" in output
        assert "mode" in output
        assert "provenance" in output
        assert "gate_status" in output
        assert "generated_at" in output
        assert "schema_version" in output

        # Provenance fields
        assert "packs_used" in output["provenance"]
        assert "session_id" in output["provenance"]

        # Gate status fields
        assert "gates_cleared" in output["gate_status"]
        assert "forced_responsibility" in output["gate_status"]

    def test_quote_output_mode_is_captured(self, data_root_with_minor_variant):
        """Quote output should capture the mode parameter."""
        runner = CliRunner()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            out_path = f.name

        result = runner.invoke(
            cli,
            [
                "quote",
                "John 1:1",
                "--mode",
                "traceable",
                "--data-root",
                str(data_root_with_minor_variant),
                "--out",
                out_path,
            ],
        )

        assert result.exit_code == 0, result.output

        output = json.loads(Path(out_path).read_text())
        assert output["mode"] == "traceable"

    def test_quote_output_to_stdout(self, data_root_with_minor_variant):
        """Quote should output to stdout when no --out specified."""
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "quote",
                "John 1:1",
                "--data-root",
                str(data_root_with_minor_variant),
            ],
        )

        assert result.exit_code == 0, result.output

        # Output should be valid JSON
        output = json.loads(result.output)
        assert "reference" in output
        assert output["reference"] == "John 1:1"
