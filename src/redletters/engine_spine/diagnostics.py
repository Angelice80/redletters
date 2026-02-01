"""Diagnostics bundle export with secret scrubbing per Sprint-1-DOD.

Sprint-2 Enhancement: Integrity report with DB-stored hashes for tamper-evidence.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import shutil
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field
from zipfile import ZipFile

from redletters import __version__
from redletters.engine_spine.auth import TOKEN_PATTERN, scrub_secrets


# --- Integrity Report Models (Sprint-2) ---


class IntegrityStatus(str, Enum):
    """Status codes for integrity checks."""

    MATCH = "MATCH"  # File hash matches DB hash
    MISMATCH = "MISMATCH"  # File hash differs from DB (tampering detected)
    MISSING = "MISSING"  # File doesn't exist but DB has hash
    DB_ONLY = "DB_ONLY"  # DB has entry but file not expected at path
    FILE_ONLY = "FILE_ONLY"  # File exists but no DB hash recorded
    SKIPPED_LARGE = "SKIPPED_LARGE"  # File too large to hash by default
    SKIPPED_DISABLED = "SKIPPED_DISABLED"  # Integrity checking disabled


class IntegrityResult(BaseModel):
    """Result of integrity check for a single artifact."""

    job_id: str
    artifact_type: str  # "receipt" or "artifact"
    name: str
    path: str
    status: IntegrityStatus
    expected_hash: Optional[str] = None  # Hash from DB
    actual_hash: Optional[str] = None  # Hash computed from file
    size_bytes: Optional[int] = None
    reason: Optional[str] = None  # Human-readable explanation


class IntegrityReport(BaseModel):
    """Complete integrity report for diagnostics bundle."""

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    full_integrity_mode: bool = False
    size_threshold_bytes: int = 100 * 1024 * 1024  # 100MB default

    # Summary counts
    summary: "Dict[str, int]" = Field(
        default_factory=lambda: {
            "ok": 0,
            "warn": 0,
            "fail": 0,
            "skipped": 0,
        }
    )

    # All results
    results: "List[IntegrityResult]" = Field(default_factory=list)

    # Compact failures list for quick review
    failures: "List[Dict[str, Any]]" = Field(default_factory=list)

    def add_result(self, result: IntegrityResult) -> None:
        """Add a result and update summary counts."""
        self.results.append(result)

        if result.status == IntegrityStatus.MATCH:
            self.summary["ok"] += 1
        elif result.status in (
            IntegrityStatus.SKIPPED_LARGE,
            IntegrityStatus.SKIPPED_DISABLED,
        ):
            self.summary["skipped"] += 1
        elif result.status in (IntegrityStatus.FILE_ONLY, IntegrityStatus.DB_ONLY):
            self.summary["warn"] += 1
            self.failures.append(
                {
                    "job_id": result.job_id,
                    "path": result.path,
                    "expected": result.expected_hash,
                    "actual": result.actual_hash,
                    "reason": result.reason or result.status.value,
                }
            )
        else:  # MISMATCH, MISSING
            self.summary["fail"] += 1
            self.failures.append(
                {
                    "job_id": result.job_id,
                    "path": result.path,
                    "expected": result.expected_hash,
                    "actual": result.actual_hash,
                    "reason": result.reason or result.status.value,
                }
            )

    def to_text(self) -> str:
        """Generate human-readable text report."""
        lines = [
            "=" * 60,
            "INTEGRITY REPORT",
            f"Generated: {self.generated_at.isoformat()}",
            f"Mode: {'FULL' if self.full_integrity_mode else 'DEFAULT'}",
            f"Size threshold: {self.size_threshold_bytes / (1024 * 1024):.0f}MB",
            "=" * 60,
            "",
            "SUMMARY",
            "-" * 30,
            f"  OK:      {self.summary['ok']}",
            f"  WARN:    {self.summary['warn']}",
            f"  FAIL:    {self.summary['fail']}",
            f"  SKIPPED: {self.summary['skipped']}",
            "",
        ]

        if self.failures:
            lines.extend(
                [
                    "FAILURES",
                    "-" * 30,
                ]
            )
            for f in self.failures:
                lines.append(f"  [{f['reason']}] {f['job_id']}: {f['path']}")
                if f.get("expected"):
                    lines.append(f"    expected: {f['expected']}")
                if f.get("actual"):
                    lines.append(f"    actual:   {f['actual']}")
            lines.append("")

        lines.extend(
            [
                "=" * 60,
                f"Total: {sum(self.summary.values())} checks",
                "=" * 60,
            ]
        )

        return "\n".join(lines)


# Environment variable for size threshold (bytes)
INTEGRITY_SIZE_THRESHOLD_ENV = "REDLETTERS_INTEGRITY_SIZE_THRESHOLD"
INTEGRITY_TIMEOUT_ENV = "REDLETTERS_INTEGRITY_TIMEOUT"
DEFAULT_SIZE_THRESHOLD = 100 * 1024 * 1024  # 100MB
DEFAULT_TIMEOUT_SECONDS = 60

if TYPE_CHECKING:
    from redletters.engine_spine.database import EngineDatabase
    from redletters.engine_spine.status import EngineStatusManager

logger = logging.getLogger(__name__)


class DiagnosticsExporter:
    """Export diagnostics bundle with secret scrubbing.

    Per Sprint-1-DOD:
    - Bundle includes: system_info.json, recent_logs.jsonl, job_summary.json, engine_status.json
    - Secrets are scrubbed (tokens matching rl_[A-Za-z0-9_-]{20,})
    - Double-check before export: scan for token patterns

    Per Sprint-2-DOD:
    - Bundle includes integrity_report.json and integrity_report.txt
    - Reports receipt_hash_from_db and artifact_sha256_from_db
    - Detects tampering via hash mismatch
    """

    def __init__(
        self,
        db: "EngineDatabase",
        status_manager: "EngineStatusManager | None" = None,
        logs_dir: Path | None = None,
    ):
        self._db = db
        self._status_manager = status_manager
        self._logs_dir = logs_dir

    def export_bundle(
        self,
        output_path: Path,
        as_zip: bool = True,
        full_integrity: bool = False,
    ) -> Path:
        """Export diagnostics bundle.

        Args:
            output_path: Output path (directory or .zip file)
            as_zip: If True, create ZIP archive; if False, create directory
            full_integrity: If True, hash all files regardless of size

        Returns:
            Path to created bundle

        Raises:
            SecurityError: If tokens detected in final bundle
        """
        # Create temp directory for bundle contents
        bundle_dir = output_path.with_suffix(".tmp")
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        bundle_dir.mkdir(parents=True)

        try:
            # Collect all diagnostic data
            self._write_system_info(bundle_dir / "system_info.json")
            self._write_engine_status(bundle_dir / "engine_status.json")
            self._write_job_summary(bundle_dir / "job_summary.json")
            self._write_recent_logs(bundle_dir / "recent_logs.jsonl")
            self._write_config_sanitized(bundle_dir / "config_sanitized.json")

            # Sprint-2: Generate integrity report
            self._write_integrity_report(bundle_dir, full_integrity=full_integrity)

            # CRITICAL: Scan for leaked tokens
            self._verify_no_secrets(bundle_dir)

            # Create final output
            if as_zip:
                zip_path = output_path.with_suffix(".zip")
                with ZipFile(zip_path, "w") as zf:
                    for file_path in bundle_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(bundle_dir)
                            zf.write(file_path, arcname)
                final_path = zip_path
            else:
                # Move temp to final
                if output_path.exists():
                    shutil.rmtree(output_path)
                shutil.move(bundle_dir, output_path)
                final_path = output_path
                bundle_dir = None  # Don't delete in finally

            logger.info(f"Diagnostics exported to: {final_path}")
            return final_path

        finally:
            # Clean up temp directory
            if bundle_dir and bundle_dir.exists():
                shutil.rmtree(bundle_dir)

    def _get_size_threshold(self) -> int:
        """Get size threshold from environment or default."""
        try:
            return int(
                os.environ.get(INTEGRITY_SIZE_THRESHOLD_ENV, DEFAULT_SIZE_THRESHOLD)
            )
        except ValueError:
            return DEFAULT_SIZE_THRESHOLD

    def _compute_file_hash(self, file_path: Path) -> str | None:
        """Compute SHA-256 hash of a file.

        Returns None if file doesn't exist or can't be read.
        """
        try:
            hasher = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, IOError):
            return None

    def _check_receipt_integrity(
        self,
        job: dict[str, Any],
        full_integrity: bool,
        size_threshold: int,
    ) -> IntegrityResult | None:
        """Check integrity of a job's receipt file.

        Receipts are always checked (no size threshold for receipts).
        """
        job_id = job["job_id"]
        workspace_path = job.get("workspace_path")
        receipt_hash_from_db = job.get("receipt_hash")

        if not workspace_path:
            return None  # No workspace, nothing to check

        receipt_path = Path(workspace_path) / "receipt.json"

        # No DB hash recorded
        if not receipt_hash_from_db:
            if receipt_path.exists():
                # File exists but no DB hash
                return IntegrityResult(
                    job_id=job_id,
                    artifact_type="receipt",
                    name="receipt.json",
                    path=str(receipt_path),
                    status=IntegrityStatus.FILE_ONLY,
                    actual_hash=self._compute_file_hash(receipt_path),
                    reason="Receipt file exists but no hash stored in DB",
                )
            return None  # No file, no hash - nothing to report

        # DB has hash - check file
        if not receipt_path.exists():
            return IntegrityResult(
                job_id=job_id,
                artifact_type="receipt",
                name="receipt.json",
                path=str(receipt_path),
                status=IntegrityStatus.MISSING,
                expected_hash=receipt_hash_from_db,
                reason="Receipt file missing but DB has hash",
            )

        # Both exist - compare hashes
        actual_hash = self._compute_file_hash(receipt_path)
        if actual_hash is None:
            return IntegrityResult(
                job_id=job_id,
                artifact_type="receipt",
                name="receipt.json",
                path=str(receipt_path),
                status=IntegrityStatus.MISSING,
                expected_hash=receipt_hash_from_db,
                reason="Receipt file exists but could not be read",
            )

        if actual_hash == receipt_hash_from_db:
            return IntegrityResult(
                job_id=job_id,
                artifact_type="receipt",
                name="receipt.json",
                path=str(receipt_path),
                status=IntegrityStatus.MATCH,
                expected_hash=receipt_hash_from_db,
                actual_hash=actual_hash,
            )
        else:
            return IntegrityResult(
                job_id=job_id,
                artifact_type="receipt",
                name="receipt.json",
                path=str(receipt_path),
                status=IntegrityStatus.MISMATCH,
                expected_hash=receipt_hash_from_db,
                actual_hash=actual_hash,
                reason="Receipt hash mismatch - possible tampering",
            )

    def _check_artifact_integrity(
        self,
        job_id: str,
        artifact: dict[str, Any],
        full_integrity: bool,
        size_threshold: int,
    ) -> IntegrityResult:
        """Check integrity of a single artifact.

        Applies size threshold unless full_integrity is True.
        """
        name = artifact["name"]
        path = artifact["path"]
        artifact_type = artifact["artifact_type"]
        sha256_from_db = artifact.get("sha256")
        _size_from_db = artifact.get("size_bytes")  # Reserved for future size checks

        artifact_path = Path(path)

        # No DB hash recorded
        if not sha256_from_db:
            if artifact_path.exists():
                return IntegrityResult(
                    job_id=job_id,
                    artifact_type=artifact_type,
                    name=name,
                    path=path,
                    status=IntegrityStatus.FILE_ONLY,
                    reason="Artifact file exists but no hash stored in DB",
                )
            return IntegrityResult(
                job_id=job_id,
                artifact_type=artifact_type,
                name=name,
                path=path,
                status=IntegrityStatus.DB_ONLY,
                reason="Artifact registered but file not found and no hash",
            )

        # DB has hash - check file
        if not artifact_path.exists():
            return IntegrityResult(
                job_id=job_id,
                artifact_type=artifact_type,
                name=name,
                path=path,
                status=IntegrityStatus.MISSING,
                expected_hash=sha256_from_db,
                reason="Artifact file missing but DB has hash",
            )

        # Check file size for threshold
        try:
            actual_size = artifact_path.stat().st_size
        except OSError:
            return IntegrityResult(
                job_id=job_id,
                artifact_type=artifact_type,
                name=name,
                path=path,
                status=IntegrityStatus.MISSING,
                expected_hash=sha256_from_db,
                reason="Could not stat artifact file",
            )

        # Skip large files unless full_integrity
        if not full_integrity and actual_size > size_threshold:
            return IntegrityResult(
                job_id=job_id,
                artifact_type=artifact_type,
                name=name,
                path=path,
                status=IntegrityStatus.SKIPPED_LARGE,
                expected_hash=sha256_from_db,
                size_bytes=actual_size,
                reason=f"File size {actual_size} exceeds threshold {size_threshold}",
            )

        # Compute hash and compare
        actual_hash = self._compute_file_hash(artifact_path)
        if actual_hash is None:
            return IntegrityResult(
                job_id=job_id,
                artifact_type=artifact_type,
                name=name,
                path=path,
                status=IntegrityStatus.MISSING,
                expected_hash=sha256_from_db,
                reason="Artifact file exists but could not be read",
            )

        if actual_hash == sha256_from_db:
            return IntegrityResult(
                job_id=job_id,
                artifact_type=artifact_type,
                name=name,
                path=path,
                status=IntegrityStatus.MATCH,
                expected_hash=sha256_from_db,
                actual_hash=actual_hash,
                size_bytes=actual_size,
            )
        else:
            return IntegrityResult(
                job_id=job_id,
                artifact_type=artifact_type,
                name=name,
                path=path,
                status=IntegrityStatus.MISMATCH,
                expected_hash=sha256_from_db,
                actual_hash=actual_hash,
                size_bytes=actual_size,
                reason="Artifact hash mismatch - possible tampering",
            )

    def generate_integrity_report(
        self, full_integrity: bool = False
    ) -> IntegrityReport:
        """Generate integrity report for all jobs and artifacts.

        Args:
            full_integrity: If True, hash all files regardless of size

        Returns:
            IntegrityReport with all check results
        """
        size_threshold = self._get_size_threshold()

        report = IntegrityReport(
            full_integrity_mode=full_integrity,
            size_threshold_bytes=size_threshold,
        )

        # Get all jobs
        jobs = self._db.list_jobs(limit=1000)

        for job in jobs:
            job_id = job["job_id"]

            # Check receipt integrity
            receipt_result = self._check_receipt_integrity(
                job, full_integrity, size_threshold
            )
            if receipt_result:
                report.add_result(receipt_result)

            # Check artifact integrity
            artifacts = self._db.get_job_artifacts(job_id)
            for artifact in artifacts:
                # Skip receipt artifacts (already checked above)
                if artifact["artifact_type"] == "receipt":
                    continue

                result = self._check_artifact_integrity(
                    job_id, artifact, full_integrity, size_threshold
                )
                report.add_result(result)

        return report

    def _write_integrity_report(self, bundle_dir: Path, full_integrity: bool) -> None:
        """Write integrity report files to bundle."""
        report = self.generate_integrity_report(full_integrity=full_integrity)

        # Write JSON format
        json_path = bundle_dir / "integrity_report.json"
        json_path.write_text(report.model_dump_json(indent=2))

        # Write text format
        txt_path = bundle_dir / "integrity_report.txt"
        txt_path.write_text(report.to_text())

    def _write_system_info(self, path: Path) -> None:
        """Write system information."""
        info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "redletters_version": __version__,
            "python_version": sys.version,
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
            },
            "environment": {
                # Only safe env vars
                "LANG": os.environ.get("LANG"),
                "LC_ALL": os.environ.get("LC_ALL"),
                "TERM": os.environ.get("TERM"),
                # Explicitly exclude: PATH, HOME, USER, and anything with KEY/SECRET/TOKEN
            },
        }
        path.write_text(json.dumps(info, indent=2))

    def _write_engine_status(self, path: Path) -> None:
        """Write engine status."""
        if self._status_manager:
            status = self._status_manager.get_status()
            status_dict = status.model_dump()
        else:
            status_dict = {"error": "Status manager not available"}

        path.write_text(json.dumps(status_dict, indent=2, default=str))

    def _write_job_summary(self, path: Path) -> None:
        """Write job summary (counts, recent jobs, no sensitive data)."""
        jobs = self._db.list_jobs(limit=50)

        summary = {
            "total_jobs": len(jobs),
            "by_state": {},
            "recent_jobs": [],
        }

        # Count by state
        for job in jobs:
            state = job["state"]
            summary["by_state"][state] = summary["by_state"].get(state, 0) + 1

        # Add recent jobs (sanitized)
        for job in jobs[:20]:
            sanitized = {
                "job_id": job["job_id"],
                "state": job["state"],
                "created_at": job["created_at"],
                "completed_at": job["completed_at"],
                "error_code": job["error_code"],
                # Explicitly exclude: config_json (may have paths), idempotency_key
            }
            summary["recent_jobs"].append(sanitized)

        path.write_text(json.dumps(summary, indent=2))

    def _write_recent_logs(self, path: Path) -> None:
        """Write recent event logs (scrubbed)."""
        # Get recent events
        events = self._db.get_events_since(
            after_sequence=max(0, self._db.get_current_sequence() - 1000),
            limit=1000,
        )

        with open(path, "w") as f:
            for event_data in events:
                event = event_data["event"]
                # Scrub any secrets from messages
                if "message" in event:
                    event["message"] = scrub_secrets(event["message"])
                if "payload" in event and event["payload"]:
                    event["payload"] = json.loads(
                        scrub_secrets(json.dumps(event["payload"]))
                    )
                f.write(json.dumps(event, default=str) + "\n")

    def _write_config_sanitized(self, path: Path) -> None:
        """Write sanitized configuration (no tokens, paths redacted)."""
        config_path = Path("~/.greek2english/config.toml").expanduser()

        if config_path.exists():
            try:
                content = config_path.read_text()
                # Scrub tokens
                content = scrub_secrets(content)
                # Redact full paths (keep basename)
                content = re.sub(
                    r'(["\']/[^"\']+/)([^/"\'\n]+)(["\'])',
                    r"\1***REDACTED***/\2\3",
                    content,
                )
                config_dict = {"raw_sanitized": content}
            except Exception as e:
                config_dict = {"error": str(e)}
        else:
            config_dict = {"exists": False}

        path.write_text(json.dumps(config_dict, indent=2))

    def _verify_no_secrets(self, bundle_dir: Path) -> None:
        """Verify no tokens leaked into bundle.

        Raises:
            SecurityError: If any tokens found
        """
        violations = []

        for file_path in bundle_dir.rglob("*"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
                matches = TOKEN_PATTERN.findall(content)
                if matches:
                    violations.append(
                        {
                            "file": str(file_path.relative_to(bundle_dir)),
                            "count": len(matches),
                        }
                    )
            except (UnicodeDecodeError, PermissionError):
                # Binary file or permission issue, skip
                pass

        if violations:
            # This should never happen - it means scrubbing failed
            logger.error(f"TOKEN LEAK DETECTED in diagnostics: {violations}")
            raise SecurityError(
                f"Token detected in diagnostics bundle - aborting. "
                f"Violations: {violations}"
            )


class SecurityError(Exception):
    """Security violation during diagnostics export."""

    pass


def create_diagnostics_export(
    db: "EngineDatabase",
    status_manager: "EngineStatusManager | None",
    output_path: Path,
    as_zip: bool = True,
    full_integrity: bool = False,
) -> Path:
    """Convenience function to create diagnostics export.

    Args:
        db: Engine database
        status_manager: Optional status manager
        output_path: Output path for bundle
        as_zip: If True, create ZIP archive
        full_integrity: If True, hash all files regardless of size
    """
    exporter = DiagnosticsExporter(db, status_manager)
    return exporter.export_bundle(
        output_path, as_zip=as_zip, full_integrity=full_integrity
    )


def create_reset_diagnostics(
    db: "EngineDatabase",
    status_manager: "EngineStatusManager | None",
) -> Path:
    """Create diagnostics bundle before reset.

    Per Sprint-1-DOD: auto-exports to ~/Desktop/greek2english-reset-<timestamp>.zip
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = Path(f"~/Desktop/greek2english-reset-{timestamp}").expanduser()

    return create_diagnostics_export(db, status_manager, output_path, as_zip=True)
