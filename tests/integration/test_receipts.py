"""Integration tests for receipt generation per Sprint-1-DOD.

Verifies:
- Completed jobs produce receipt.json
- Failed jobs produce receipt.json with receipt_status: "failed"
- Cancelled jobs produce receipt.json with receipt_status: "cancelled"
- Crash jobs produce receipt with exit_code: "E_ENGINE_CRASH"
- Receipts are immutable (chmod 444)
- Receipt includes correlation IDs (run_id)
- Receipt references artifacts with path, size, sha256
- Receipt includes config_snapshot
- Receipt includes source_pins
"""

import json

import pytest

from redletters.engine_spine.broadcaster import EventBroadcaster
from redletters.engine_spine.database import EngineDatabase
from redletters.engine_spine.jobs import JobManager
from redletters.engine_spine.models import JobConfig


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "engine.db"
    database = EngineDatabase(db_path)
    database.init_schema()
    return database


@pytest.fixture
def broadcaster(db):
    """Create broadcaster."""
    return EventBroadcaster(db)


@pytest.fixture
def job_manager(db, broadcaster, tmp_path):
    """Create job manager."""
    workspace_base = tmp_path / "workspaces"
    workspace_base.mkdir()
    return JobManager(db, broadcaster, workspace_base)


class TestCompletedReceipt:
    """Tests for completed job receipts."""

    @pytest.mark.asyncio
    async def test_completed_job_produces_receipt(self, job_manager, db, tmp_path):
        """Completed jobs produce receipt.json per Sprint-1-DOD."""
        # Create job
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)

        # Start job
        db.claim_job(job.job_id)

        # Complete job (receipt object unused - verifying file on disk)
        await job_manager.complete_job(job.job_id)

        # Verify receipt file exists
        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"
        assert receipt_path.exists()

    @pytest.mark.asyncio
    async def test_completed_receipt_status(self, job_manager, db, tmp_path):
        """Completed receipt has receipt_status: 'completed'."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.complete_job(job.job_id)

        assert receipt.receipt_status == "completed"

        # Also verify from file
        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"
        receipt_data = json.loads(receipt_path.read_text())
        assert receipt_data["receipt_status"] == "completed"


class TestFailedReceipt:
    """Tests for failed job receipts."""

    @pytest.mark.asyncio
    async def test_failed_job_produces_receipt(self, job_manager, db, tmp_path):
        """Failed jobs produce receipt.json per Sprint-1-DOD."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)

        # Fail job (receipt object unused - verifying file on disk)
        await job_manager.fail_job(
            job.job_id,
            error_code="E_TEST_ERROR",
            error_message="Test failure",
        )

        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"
        assert receipt_path.exists()

    @pytest.mark.asyncio
    async def test_failed_receipt_status(self, job_manager, db, tmp_path):
        """Failed receipt has receipt_status: 'failed'."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.fail_job(
            job.job_id,
            error_code="E_TEST_ERROR",
            error_message="Test failure",
        )

        assert receipt.receipt_status == "failed"
        assert receipt.error_code == "E_TEST_ERROR"
        assert receipt.error_message == "Test failure"


class TestCancelledReceipt:
    """Tests for cancelled job receipts."""

    @pytest.mark.asyncio
    async def test_cancelled_job_produces_receipt(self, job_manager, db, tmp_path):
        """Cancelled jobs produce receipt.json per Sprint-1-DOD."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)

        # Cancel job (receipt object unused - verifying file on disk)
        await job_manager.cancel_job(job.job_id)

        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"
        assert receipt_path.exists()

    @pytest.mark.asyncio
    async def test_cancelled_receipt_status(self, job_manager, db, tmp_path):
        """Cancelled receipt has receipt_status: 'cancelled'."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        receipt = await job_manager.cancel_job(job.job_id)

        assert receipt.receipt_status == "cancelled"


class TestCrashReceipt:
    """Tests for crash recovery receipts."""

    @pytest.mark.asyncio
    async def test_crash_recovery_produces_receipt(self, job_manager, db, tmp_path):
        """Crash recovery produces receipt with exit_code: 'E_ENGINE_CRASH'."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)

        # Simulate crash by directly setting state to running
        db.claim_job(job.job_id)

        # Recover orphaned jobs
        recovered = await job_manager.recover_orphaned_jobs()
        assert job.job_id in recovered

        # Verify receipt
        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"
        assert receipt_path.exists()

        receipt_data = json.loads(receipt_path.read_text())
        assert receipt_data["exit_code"] == "E_ENGINE_CRASH"


class TestReceiptImmutability:
    """Tests for receipt immutability."""

    @pytest.mark.asyncio
    async def test_receipt_chmod_444(self, job_manager, db, tmp_path):
        """Receipt is chmod 444 (read-only) per Sprint-1-DOD."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        await job_manager.complete_job(job.job_id)

        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"

        # Check permissions
        mode = receipt_path.stat().st_mode & 0o777
        assert mode == 0o444  # Read-only for all


class TestReceiptContents:
    """Tests for receipt content requirements."""

    @pytest.mark.asyncio
    async def test_receipt_includes_run_id(self, job_manager, db, tmp_path):
        """Receipt includes run_id per Sprint-1-DOD."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.complete_job(job.job_id)

        assert receipt.run_id is not None
        assert len(receipt.run_id) > 0

    @pytest.mark.asyncio
    async def test_receipt_includes_config_snapshot(self, job_manager, db, tmp_path):
        """Receipt includes config_snapshot per Sprint-1-DOD."""
        config = JobConfig(
            input_paths=["/test/path"],
            style="meaning-first",
            options={"key": "value"},
        )
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.complete_job(job.job_id)

        assert "input_paths" in receipt.config_snapshot
        assert receipt.config_snapshot["input_paths"] == ["/test/path"]
        assert receipt.config_snapshot["style"] == "meaning-first"

    @pytest.mark.asyncio
    async def test_receipt_includes_source_pins(self, job_manager, db, tmp_path):
        """Receipt includes source_pins per Sprint-1-DOD."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.complete_job(job.job_id)

        # source_pins should be a dict (may be empty if no sources loaded)
        assert isinstance(receipt.source_pins, dict)

    @pytest.mark.asyncio
    async def test_receipt_includes_timestamps(self, job_manager, db, tmp_path):
        """Receipt includes timestamps."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.complete_job(job.job_id)

        assert receipt.timestamps.created is not None
        assert receipt.timestamps.started is not None
        assert receipt.timestamps.completed is not None

    @pytest.mark.asyncio
    async def test_receipt_outputs_array(self, job_manager, db, tmp_path):
        """Receipt includes outputs array per Sprint-1-DOD."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.complete_job(job.job_id)

        # outputs should be a list
        assert isinstance(receipt.outputs, list)

    @pytest.mark.asyncio
    async def test_receipt_schema_version(self, job_manager, db, tmp_path):
        """Receipt includes schema_version."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        receipt = await job_manager.complete_job(job.job_id)

        assert receipt.schema_version == "1.0"


class TestAtomicReceiptWrite:
    """Tests for atomic receipt write invariants (Sprint-2 hardening)."""

    @pytest.mark.asyncio
    async def test_no_temp_files_left_behind(self, job_manager, db, tmp_path):
        """Atomic write leaves no temp files after completion."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        await job_manager.complete_job(job.job_id)

        workspace = tmp_path / "workspaces" / job.job_id
        temp_files = list(workspace.glob("*.tmp.*"))
        assert temp_files == [], f"Temp files left behind: {temp_files}"

    @pytest.mark.asyncio
    async def test_receipt_hash_matches_content(self, job_manager, db, tmp_path):
        """Receipt hash in DB matches file content (tamper-evidence)."""
        import hashlib

        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        await job_manager.complete_job(job.job_id)

        # Get hash from DB
        job_data = db.get_job(job.job_id)
        db_hash = job_data["receipt_hash"]

        # Compute hash from file
        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"
        file_content = receipt_path.read_bytes()
        file_hash = hashlib.sha256(file_content).hexdigest()

        assert db_hash == file_hash, "DB hash must match file content"

    @pytest.mark.asyncio
    async def test_receipt_content_integrity(self, job_manager, db, tmp_path):
        """Receipt file content is valid JSON matching DB record."""
        config = JobConfig(input_paths=["/test/path"])
        job = await job_manager.create_job(config)
        db.claim_job(job.job_id)
        await job_manager.complete_job(job.job_id)

        # Get receipt from DB
        job_data = db.get_job(job.job_id)
        db_receipt = json.loads(job_data["receipt_json"])

        # Get receipt from file
        workspace = tmp_path / "workspaces" / job.job_id
        receipt_path = workspace / "receipt.json"
        file_receipt = json.loads(receipt_path.read_text())

        # Core fields must match
        assert db_receipt["job_id"] == file_receipt["job_id"]
        assert db_receipt["receipt_status"] == file_receipt["receipt_status"]
        assert db_receipt["run_id"] == file_receipt["run_id"]

    @pytest.mark.asyncio
    async def test_multiple_receipts_no_temp_collision(self, job_manager, db, tmp_path):
        """Multiple rapid receipt writes don't collide on temp files."""
        jobs = []
        for i in range(5):
            config = JobConfig(input_paths=[f"/test/path{i}"])
            job = await job_manager.create_job(config)
            db.claim_job(job.job_id)
            jobs.append(job)

        # Complete all jobs rapidly
        for job in jobs:
            await job_manager.complete_job(job.job_id)

        # Verify all receipts exist and no temp files
        for job in jobs:
            workspace = tmp_path / "workspaces" / job.job_id
            assert (workspace / "receipt.json").exists()
            temp_files = list(workspace.glob("*.tmp.*"))
            assert temp_files == []
