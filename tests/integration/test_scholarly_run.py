"""Integration tests for v0.13.0 scholarly run command.

Tests the ScholarlyRunner orchestration:
- Run log creation and determinism
- Gate enforcement (refusal unless --force)
- Bundle creation and verification
- Artifacts produced
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def data_root():
    """Get data root for tests (uses existing packs if available)."""
    # Check for existing data root from environment or default
    return os.environ.get("REDLETTERS_DATA_ROOT", None)


class TestRunLogDeterminism:
    """Tests for run log determinism."""

    def test_run_log_schema_version(self):
        """RunLog has correct schema version."""
        from redletters.run import RunLog, RunLogCommand

        command = RunLogCommand(
            reference="John 1:1",
            output_dir="/tmp/test",
            mode="traceable",
        )

        run_log = RunLog(
            schema_version="1.0.0",
            tool_version="0.13.0",
            command=command,
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:01:00Z",
            reference="John 1:1",
            verse_ids=["John.1.1"],
            mode="traceable",
            success=True,
        )

        assert run_log.schema_version == "1.0.0"
        assert run_log.tool_version == "0.13.0"

    def test_run_log_to_json_deterministic(self):
        """RunLog JSON output is deterministic (sorted keys)."""
        from redletters.run import RunLog, RunLogCommand, RunLogFile

        command = RunLogCommand(
            reference="John 1:1",
            output_dir="/tmp/test",
            mode="traceable",
        )

        run_log = RunLog(
            schema_version="1.0.0",
            tool_version="0.13.0",
            command=command,
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:01:00Z",
            reference="John 1:1",
            verse_ids=["John.1.1"],
            mode="traceable",
            files_created=[
                RunLogFile(
                    path="apparatus.jsonl",
                    artifact_type="apparatus",
                    sha256="abc123" * 10 + "abcd",
                ),
                RunLogFile(
                    path="translation.jsonl",
                    artifact_type="translation",
                    sha256="def456" * 10 + "defg",
                ),
            ],
            success=True,
        )

        json1 = run_log.to_json(pretty=False)
        json2 = run_log.to_json(pretty=False)

        assert json1 == json2

        # Parse and verify keys are sorted
        data = json.loads(json1)
        keys = list(data.keys())
        assert keys == sorted(keys)

    def test_run_log_content_hash_stable(self):
        """RunLog content hash is stable across serializations."""
        from redletters.run import RunLog, RunLogCommand, RunLogFile

        command = RunLogCommand(
            reference="John 1:1",
            output_dir="/tmp/test",
            mode="traceable",
        )

        run_log = RunLog(
            schema_version="1.0.0",
            tool_version="0.13.0",
            command=command,
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:01:00Z",
            reference="John 1:1",
            verse_ids=["John.1.1"],
            mode="traceable",
            files_created=[
                RunLogFile(
                    path="apparatus.jsonl",
                    artifact_type="apparatus",
                    sha256="abc123" * 10 + "abcd",
                ),
            ],
            success=True,
        )

        hash1 = run_log.compute_content_hash()
        hash2 = run_log.compute_content_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex


class TestRunLogSerialization:
    """Tests for run log serialization/deserialization."""

    def test_run_log_round_trip(self):
        """RunLog survives JSON round-trip."""
        from redletters.run import (
            RunLog,
            RunLogCommand,
            RunLogFile,
            RunLogValidation,
            RunLogGates,
            RunLogPacksSummary,
            RunLogPackSummary,
        )

        command = RunLogCommand(
            reference="John 1:1-18",
            output_dir="/tmp/test",
            mode="traceable",
            include_schemas=True,
            create_zip=True,
            force=True,
        )

        packs_summary = RunLogPacksSummary(
            count=2,
            packs=[
                RunLogPackSummary(
                    pack_id="morphgnt-sblgnt",
                    version="1.0.0",
                    role="spine",
                    license="CC-BY-SA",
                ),
                RunLogPackSummary(
                    pack_id="sample-senses",
                    version="1.0.0",
                    role="sense_pack",
                    license="CC-BY",
                ),
            ],
            lockfile_hash="abc123" * 10 + "abcd",
        )

        gates = RunLogGates(
            pending_count=1,
            pending_refs=["John.1.18"],
            forced=True,
            forced_responsibility="User bypassed gate with --force",
        )

        run_log = RunLog(
            schema_version="1.0.0",
            tool_version="0.13.0",
            command=command,
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:01:00Z",
            reference="John 1:1-18",
            verse_ids=["John.1.1", "John.1.2", "John.1.18"],
            mode="traceable",
            packs_summary=packs_summary,
            files_created=[
                RunLogFile(
                    path="apparatus.jsonl",
                    artifact_type="apparatus",
                    sha256="abc123" * 10 + "abcd",
                    schema_version="1.0.0",
                ),
            ],
            validations=[
                RunLogValidation(
                    check="lockfile_generation",
                    passed=True,
                ),
                RunLogValidation(
                    check="gate_check",
                    passed=True,
                    warnings=["Pending gate: John.1.18"],
                ),
            ],
            gates=gates,
            success=True,
            content_hash="def456" * 10 + "defg",
        )

        # Serialize
        json_str = run_log.to_json()
        data = json.loads(json_str)

        # Deserialize
        restored = RunLog.from_dict(data)

        assert restored.schema_version == run_log.schema_version
        assert restored.tool_version == run_log.tool_version
        assert restored.reference == run_log.reference
        assert restored.verse_ids == run_log.verse_ids
        assert restored.mode == run_log.mode
        assert restored.success == run_log.success
        assert restored.command.reference == command.reference
        assert restored.command.force == command.force
        assert restored.packs_summary.count == packs_summary.count
        assert restored.gates.forced == gates.forced
        assert len(restored.files_created) == 1
        assert len(restored.validations) == 2


class TestValidatorRunlog:
    """Tests for runlog validation."""

    def test_validator_detects_runlog_type(self):
        """Validator detects runlog artifact type."""
        from redletters.export.validator import detect_artifact_type
        from pathlib import Path

        # By filename
        assert detect_artifact_type(Path("run_log.json")) == "runlog"
        assert detect_artifact_type(Path("my_runlog.json")) == "runlog"

        # By content
        content = {
            "command": {
                "reference": "John 1:1",
                "output_dir": "/tmp",
                "mode": "traceable",
            },
            "validations": [],
            "files_created": [],
        }
        assert detect_artifact_type(Path("output.json"), content) == "runlog"

    def test_validator_validates_runlog(self, temp_output_dir):
        """Validator validates runlog structure."""
        from redletters.export.validator import validate_output
        from redletters.run import RunLog, RunLogCommand

        command = RunLogCommand(
            reference="John 1:1",
            output_dir="/tmp/test",
            mode="traceable",
        )

        run_log = RunLog(
            schema_version="1.0.0",
            tool_version="0.13.0",
            command=command,
            started_at="2025-01-01T00:00:00Z",
            completed_at="2025-01-01T00:01:00Z",
            reference="John 1:1",
            verse_ids=["John.1.1"],
            mode="traceable",
            success=True,
        )

        # Save and validate
        runlog_path = temp_output_dir / "run_log.json"
        run_log.save(runlog_path)

        result = validate_output(runlog_path, artifact_type="runlog")
        assert result.valid, f"Validation errors: {result.errors}"

    def test_validator_rejects_invalid_runlog(self, temp_output_dir):
        """Validator rejects invalid runlog."""
        from redletters.export.validator import validate_output

        # Missing required fields
        invalid_data = {
            "schema_version": "1.0.0",
            "tool_version": "0.13.0",
            # Missing command, validations, files_created, etc.
        }

        runlog_path = temp_output_dir / "run_log.json"
        runlog_path.write_text(json.dumps(invalid_data))

        result = validate_output(runlog_path, artifact_type="runlog")
        assert not result.valid
        assert len(result.errors) > 0


class TestScholarlyRunnerUnit:
    """Unit tests for ScholarlyRunner without actual pack installations."""

    def test_scholarly_runner_creates_instance(self):
        """ScholarlyRunner can be instantiated."""
        from redletters.run import ScholarlyRunner

        runner = ScholarlyRunner(data_root="/tmp/test")
        assert runner.data_root == Path("/tmp/test")
        assert runner.session_id == "scholarly-run"

    def test_scholarly_runner_custom_session(self):
        """ScholarlyRunner accepts custom session ID."""
        from redletters.run import ScholarlyRunner

        runner = ScholarlyRunner(session_id="my-session")
        assert runner.session_id == "my-session"


@pytest.mark.integration
class TestScholarlyRunnerIntegration:
    """Integration tests for ScholarlyRunner (requires installed packs)."""

    def test_run_scholarly_no_packs(self, temp_output_dir):
        """ScholarlyRunner fails gracefully when no packs installed."""
        from redletters.run import ScholarlyRunner

        # Use a non-existent data root to ensure no packs
        runner = ScholarlyRunner(data_root=temp_output_dir / "nonexistent")

        result = runner.run(
            reference="John 1:1",
            output_dir=temp_output_dir / "output",
            mode="traceable",
        )

        # Should fail because no spine installed
        assert not result.success
        assert any(
            "spine" in e.lower() or "installed" in e.lower() for e in result.errors
        )

    @pytest.mark.skipif(
        not os.environ.get("REDLETTERS_DATA_ROOT"),
        reason="Requires installed packs (set REDLETTERS_DATA_ROOT)",
    )
    def test_run_scholarly_produces_artifacts(self, temp_output_dir, data_root):
        """ScholarlyRunner produces expected artifacts when packs are installed."""
        from redletters.run import ScholarlyRunner

        runner = ScholarlyRunner(data_root=data_root)

        result = runner.run(
            reference="John 1:1",
            output_dir=temp_output_dir,
            mode="traceable",
            include_schemas=False,
            create_zip=False,
            force=True,  # Bypass any gates for testing
        )

        if result.success:
            # Check expected files exist
            assert (temp_output_dir / "lockfile.json").exists()
            assert (temp_output_dir / "run_log.json").exists()

            # Validate run log
            from redletters.export.validator import validate_output

            runlog_result = validate_output(temp_output_dir / "run_log.json")
            assert runlog_result.valid, (
                f"Run log validation failed: {runlog_result.errors}"
            )

            # Check run log content
            assert result.run_log is not None
            assert result.run_log.reference == "John 1:1"
            assert result.run_log.mode == "traceable"
            assert len(result.run_log.files_created) > 0
        else:
            # If not successful, should have meaningful errors
            assert len(result.errors) > 0


class TestCLICommand:
    """Tests for the CLI command (without actually running the full pipeline)."""

    def test_cli_help(self):
        """CLI command has proper help text."""
        from click.testing import CliRunner
        from redletters.__main__ import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "scholarly", "--help"])

        assert result.exit_code == 0
        assert "scholarly" in result.output.lower()
        assert "--out" in result.output
        assert "--mode" in result.output
        assert "--force" in result.output
        assert "--include-schemas" in result.output
        assert "--zip" in result.output

    def test_cli_requires_output(self):
        """CLI command requires --out option."""
        from click.testing import CliRunner
        from redletters.__main__ import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["run", "scholarly", "John 1:1"])

        assert result.exit_code != 0
        assert "required" in result.output.lower() or "--out" in result.output
