"""Integration tests for diagnostics bundle per Sprint-1-DOD and Sprint-2-DOD.

Sprint-1 Verifies:
- redletters diagnostics export produces output
- Bundle includes system_info.json
- Bundle includes recent_logs.jsonl
- Bundle includes job_summary.json
- Bundle includes engine_status.json
- Secrets are scrubbed (no rl_ tokens)

Sprint-2 Verifies:
- Integrity report with receipt_hash_from_db and artifact_sha256_from_db
- Hash MATCH for valid files
- Hash MISMATCH for tampered files
- MISSING for deleted files
- SKIPPED_LARGE for files exceeding threshold
- full_integrity mode hashes all files
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from zipfile import ZipFile

import pytest

from redletters.engine_spine.auth import TOKEN_PATTERN
from redletters.engine_spine.database import EngineDatabase
from redletters.engine_spine.diagnostics import (
    DiagnosticsExporter,
    INTEGRITY_SIZE_THRESHOLD_ENV,
    IntegrityStatus,
    SecurityError,
    create_diagnostics_export,
)


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "engine.db"
    database = EngineDatabase(db_path)
    database.init_schema()
    return database


class TestDiagnosticsExport:
    """Tests for diagnostics export."""

    def test_export_produces_zip(self, db, tmp_path):
        """Export produces ZIP file."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=True)

        assert result.suffix == ".zip"
        assert result.exists()

    def test_export_produces_directory(self, db, tmp_path):
        """Export can produce directory instead of ZIP."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        assert result.is_dir()


class TestBundleContents:
    """Tests for bundle contents."""

    def test_bundle_includes_system_info(self, db, tmp_path):
        """Bundle includes system_info.json per Sprint-1-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        system_info_path = result / "system_info.json"
        assert system_info_path.exists()

        data = json.loads(system_info_path.read_text())
        assert "timestamp" in data
        assert "redletters_version" in data
        assert "platform" in data

    def test_bundle_includes_job_summary(self, db, tmp_path):
        """Bundle includes job_summary.json per Sprint-1-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        job_summary_path = result / "job_summary.json"
        assert job_summary_path.exists()

        data = json.loads(job_summary_path.read_text())
        assert "total_jobs" in data
        assert "by_state" in data

    def test_bundle_includes_recent_logs(self, db, tmp_path):
        """Bundle includes recent_logs.jsonl per Sprint-1-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        logs_path = result / "recent_logs.jsonl"
        assert logs_path.exists()

    def test_bundle_includes_engine_status(self, db, tmp_path):
        """Bundle includes engine_status.json per Sprint-1-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        status_path = result / "engine_status.json"
        assert status_path.exists()


class TestSecretScrubbing:
    """Tests for secret scrubbing."""

    def test_no_tokens_in_bundle(self, db, tmp_path):
        """No auth tokens in bundle per Sprint-1-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        # Scan all files for tokens
        for file_path in result.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
                matches = TOKEN_PATTERN.findall(content)
                assert len(matches) == 0, f"Token found in {file_path}: {matches}"
            except UnicodeDecodeError:
                pass  # Binary file

    def test_grep_finds_nothing(self, db, tmp_path):
        """grep -r 'rl_' finds nothing per Sprint-1-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        # Simulate grep -r "rl_" - should find nothing
        for file_path in result.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
                # Look for any rl_ prefixed token pattern
                if re.search(r"rl_[A-Za-z0-9_-]{20,}", content):
                    pytest.fail(f"Token pattern found in {file_path}")
            except UnicodeDecodeError:
                pass

    def test_scrubbing_detects_leaked_token(self, db, tmp_path):
        """Export fails if token somehow leaks."""
        # This tests the safety verification

        # Create a mock exporter that would leak a token
        class LeakyExporter(DiagnosticsExporter):
            def _write_system_info(self, path):
                # Intentionally include a token
                path.write_text(
                    json.dumps(
                        {
                            "secret": "rl_" + "a" * 40,  # Token pattern
                        }
                    )
                )

        output_path = tmp_path / "diagnostics"
        exporter = LeakyExporter(db)

        with pytest.raises(SecurityError):
            exporter.export_bundle(output_path, as_zip=False)


class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_create_diagnostics_export(self, db, tmp_path):
        """create_diagnostics_export convenience function works."""
        output_path = tmp_path / "diagnostics"
        result = create_diagnostics_export(db, None, output_path, as_zip=True)

        assert result.exists()
        assert result.suffix == ".zip"


class TestZipContents:
    """Tests for ZIP archive contents."""

    def test_zip_contains_expected_files(self, db, tmp_path):
        """ZIP contains all expected files."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=True)

        with ZipFile(result) as zf:
            names = zf.namelist()
            assert "system_info.json" in names
            assert "job_summary.json" in names
            assert "recent_logs.jsonl" in names
            assert "engine_status.json" in names


# --- Sprint-2: Integrity Report Tests ---


def create_job_with_receipt(db, tmp_path, job_id: str) -> tuple[str, str]:
    """Helper to create a job with a receipt file and artifact.

    Returns (workspace_path, receipt_hash).
    """
    workspace_path = tmp_path / "workspaces" / job_id
    workspace_path.mkdir(parents=True, exist_ok=True)

    # Create job in DB
    db.create_job(
        job_id=job_id,
        config_json=json.dumps({"input_paths": ["/test/path"]}),
        config_hash="testhash",
        input_spec_json=json.dumps({"paths": ["/test/path"]}),
        workspace_path=str(workspace_path),
    )

    # Create receipt file
    receipt_content = json.dumps({"job_id": job_id, "status": "completed"})
    receipt_path = workspace_path / "receipt.json"
    receipt_path.write_text(receipt_content)

    # Compute hash
    receipt_hash = hashlib.sha256(receipt_content.encode()).hexdigest()

    # Update job with receipt hash
    conn = db.connect()
    conn.execute(
        "UPDATE jobs SET receipt_hash = ? WHERE job_id = ?",
        (receipt_hash, job_id),
    )
    conn.commit()

    return str(workspace_path), receipt_hash


def create_artifact(
    db,
    job_id: str,
    workspace_path: str,
    name: str,
    content: bytes,
    artifact_type: str = "output",
) -> tuple[str, str]:
    """Helper to create an artifact file with DB registration.

    Returns (artifact_path, sha256).
    """
    artifact_path = os.path.join(workspace_path, name)
    with open(artifact_path, "wb") as f:
        f.write(content)

    sha256 = hashlib.sha256(content).hexdigest()

    # Register in DB
    artifact_id = db.register_artifact(
        job_id=job_id,
        name=name,
        path=artifact_path,
        artifact_type=artifact_type,
    )
    db.complete_artifact(artifact_id, len(content), sha256)

    return artifact_path, sha256


class TestIntegrityReportGeneration:
    """Tests for integrity report generation per Sprint-2-DOD."""

    def test_bundle_includes_integrity_report_json(self, db, tmp_path):
        """Bundle includes integrity_report.json per Sprint-2-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        report_path = result / "integrity_report.json"
        assert report_path.exists()

        data = json.loads(report_path.read_text())
        assert "summary" in data
        assert "results" in data
        assert "failures" in data
        assert "ok" in data["summary"]
        assert "fail" in data["summary"]

    def test_bundle_includes_integrity_report_txt(self, db, tmp_path):
        """Bundle includes integrity_report.txt per Sprint-2-DOD."""
        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        report_path = result / "integrity_report.txt"
        assert report_path.exists()

        content = report_path.read_text()
        assert "INTEGRITY REPORT" in content
        assert "SUMMARY" in content


class TestIntegrityReceiptMatch:
    """Tests for receipt integrity MATCH status."""

    def test_receipt_hash_match(self, db, tmp_path):
        """Receipt with matching hash returns MATCH status."""
        workspace_path, receipt_hash = create_job_with_receipt(
            db, tmp_path, "match_job"
        )

        exporter = DiagnosticsExporter(db)
        report = exporter.generate_integrity_report()

        # Find the receipt result
        receipt_results = [r for r in report.results if r.artifact_type == "receipt"]
        assert len(receipt_results) == 1

        result = receipt_results[0]
        assert result.status == IntegrityStatus.MATCH
        assert result.expected_hash == receipt_hash
        assert result.actual_hash == receipt_hash
        assert report.summary["ok"] == 1
        assert report.summary["fail"] == 0


class TestIntegrityReceiptMismatch:
    """Tests for receipt tampering detection."""

    def test_receipt_tamper_returns_mismatch(self, db, tmp_path):
        """Tampered receipt returns MISMATCH status."""
        workspace_path, original_hash = create_job_with_receipt(
            db, tmp_path, "tamper_job"
        )

        # Tamper with the receipt file
        receipt_path = os.path.join(workspace_path, "receipt.json")
        with open(receipt_path, "w") as f:
            f.write(json.dumps({"job_id": "tamper_job", "status": "TAMPERED!"}))

        exporter = DiagnosticsExporter(db)
        report = exporter.generate_integrity_report()

        receipt_results = [r for r in report.results if r.artifact_type == "receipt"]
        assert len(receipt_results) == 1

        result = receipt_results[0]
        assert result.status == IntegrityStatus.MISMATCH
        assert result.expected_hash == original_hash
        assert result.actual_hash != original_hash
        assert report.summary["fail"] == 1

        # Should be in failures list
        assert len(report.failures) == 1
        assert report.failures[0]["job_id"] == "tamper_job"


class TestIntegrityArtifactMismatch:
    """Tests for artifact tampering detection."""

    def test_artifact_tamper_returns_mismatch(self, db, tmp_path):
        """Tampered artifact returns MISMATCH status."""
        workspace_path, _ = create_job_with_receipt(db, tmp_path, "artifact_job")

        # Create artifact
        original_content = b"original content"
        artifact_path, original_hash = create_artifact(
            db, "artifact_job", workspace_path, "output.txt", original_content
        )

        # Tamper with artifact
        with open(artifact_path, "wb") as f:
            f.write(b"tampered content")

        exporter = DiagnosticsExporter(db)
        report = exporter.generate_integrity_report()

        artifact_results = [
            r
            for r in report.results
            if r.artifact_type == "output" and r.name == "output.txt"
        ]
        assert len(artifact_results) == 1

        result = artifact_results[0]
        assert result.status == IntegrityStatus.MISMATCH
        assert result.expected_hash == original_hash
        assert result.actual_hash != original_hash


class TestIntegrityMissing:
    """Tests for missing artifact detection."""

    def test_missing_artifact_returns_missing(self, db, tmp_path):
        """Missing artifact file returns MISSING status."""
        workspace_path, _ = create_job_with_receipt(db, tmp_path, "missing_job")

        # Create artifact in DB but don't create the file
        artifact_id = db.register_artifact(
            job_id="missing_job",
            name="missing.txt",
            path=os.path.join(workspace_path, "missing.txt"),
            artifact_type="output",
        )
        db.complete_artifact(artifact_id, 100, "abc123")

        exporter = DiagnosticsExporter(db)
        report = exporter.generate_integrity_report()

        missing_results = [r for r in report.results if r.name == "missing.txt"]
        assert len(missing_results) == 1

        result = missing_results[0]
        assert result.status == IntegrityStatus.MISSING
        assert report.summary["fail"] >= 1


class TestIntegritySkippedLarge:
    """Tests for large file skipping behavior."""

    def test_large_artifact_skipped_by_default(self, db, tmp_path, monkeypatch):
        """Large artifact is SKIPPED_LARGE by default."""
        # Set a tiny threshold for testing
        monkeypatch.setenv(INTEGRITY_SIZE_THRESHOLD_ENV, "100")

        workspace_path, _ = create_job_with_receipt(db, tmp_path, "large_job")

        # Create a file larger than threshold
        large_content = b"x" * 200  # 200 bytes, threshold is 100
        artifact_path, artifact_hash = create_artifact(
            db, "large_job", workspace_path, "large.bin", large_content
        )

        exporter = DiagnosticsExporter(db)
        report = exporter.generate_integrity_report(full_integrity=False)

        large_results = [r for r in report.results if r.name == "large.bin"]
        assert len(large_results) == 1

        result = large_results[0]
        assert result.status == IntegrityStatus.SKIPPED_LARGE
        assert result.size_bytes == 200
        assert report.summary["skipped"] >= 1

    def test_full_integrity_hashes_large_files(self, db, tmp_path, monkeypatch):
        """Full integrity mode hashes files regardless of size."""
        # Set a tiny threshold for testing
        monkeypatch.setenv(INTEGRITY_SIZE_THRESHOLD_ENV, "100")

        workspace_path, _ = create_job_with_receipt(db, tmp_path, "full_job")

        # Create a file larger than threshold
        large_content = b"x" * 200
        artifact_path, artifact_hash = create_artifact(
            db, "full_job", workspace_path, "large.bin", large_content
        )

        exporter = DiagnosticsExporter(db)
        report = exporter.generate_integrity_report(full_integrity=True)

        large_results = [r for r in report.results if r.name == "large.bin"]
        assert len(large_results) == 1

        result = large_results[0]
        assert result.status == IntegrityStatus.MATCH  # Not SKIPPED_LARGE
        assert result.actual_hash == artifact_hash
        assert report.summary["ok"] >= 1


class TestIntegrityZipContents:
    """Tests for integrity report in ZIP archive."""

    def test_zip_contains_integrity_reports(self, db, tmp_path):
        """ZIP archive contains both integrity report files."""
        create_job_with_receipt(db, tmp_path, "zip_job")

        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=True)

        with ZipFile(result) as zf:
            names = zf.namelist()
            assert "integrity_report.json" in names
            assert "integrity_report.txt" in names


class TestIntegrityConvenienceFunction:
    """Tests for convenience function with full_integrity flag."""

    def test_convenience_function_supports_full_integrity(
        self, db, tmp_path, monkeypatch
    ):
        """create_diagnostics_export supports full_integrity flag."""
        monkeypatch.setenv(INTEGRITY_SIZE_THRESHOLD_ENV, "100")

        workspace_path, _ = create_job_with_receipt(db, tmp_path, "conv_job")
        large_content = b"x" * 200
        create_artifact(db, "conv_job", workspace_path, "large.bin", large_content)

        output_path = tmp_path / "diagnostics"
        result = create_diagnostics_export(
            db, None, output_path, as_zip=False, full_integrity=True
        )

        report_path = result / "integrity_report.json"
        data = json.loads(report_path.read_text())

        # Should have hashed the large file (MATCH), not skipped it
        assert data["full_integrity_mode"] is True
        assert data["summary"]["ok"] >= 1


class TestIntegrityTextReport:
    """Tests for human-readable text report format."""

    def test_text_report_contains_failure_details(self, db, tmp_path):
        """Text report includes failure details."""
        workspace_path, original_hash = create_job_with_receipt(
            db, tmp_path, "text_job"
        )

        # Tamper to create a failure
        receipt_path = os.path.join(workspace_path, "receipt.json")
        with open(receipt_path, "w") as f:
            f.write(json.dumps({"tampered": True}))

        output_path = tmp_path / "diagnostics"
        exporter = DiagnosticsExporter(db)
        result = exporter.export_bundle(output_path, as_zip=False)

        report_path = result / "integrity_report.txt"
        content = report_path.read_text()

        assert "FAILURES" in content
        assert "text_job" in content
        assert "MISMATCH" in content or "possible tampering" in content.lower()
