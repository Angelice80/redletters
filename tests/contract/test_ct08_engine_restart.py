"""Contract test CT-08: Engine restart mid-run per SPRINT-1-DOD.

This test verifies crash recovery semantics:
- Jobs in 'running' state on startup are detected as orphaned
- Orphaned jobs are failed with E_ENGINE_CRASH
- Crash receipt is produced with correct exit_code
- Sequence numbers remain monotonic across restart

There are two levels of testing:
1. Contract tests (TestCrashRecoveryContract) - verify the recovery logic
2. Process-level tests (TestProcessLevelCrashRecovery) - verify actual process restart

NOTE: Process-level tests require subprocess orchestration and may be slow.
They are marked with @pytest.mark.slow for selective execution.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from redletters.engine_spine.database import EngineDatabase
from redletters.engine_spine.models import JobState


@pytest.fixture
def db(tmp_path):
    """Create test database."""
    db_path = tmp_path / "engine.db"
    database = EngineDatabase(db_path)
    database.init_schema()
    return database


def create_test_job(
    db,
    job_id: str,
    state: str = "queued",
    workspace_path: str = "/tmp/test_workspace",
) -> dict:
    """Helper to create a test job record."""
    db.create_job(
        job_id=job_id,
        config_json=json.dumps({"input_paths": ["/test/path"]}),
        config_hash="testhash",
        input_spec_json=json.dumps({"paths": ["/test/path"]}),
        workspace_path=workspace_path,
    )
    if state != "queued":
        db.update_job_state(job_id, JobState(state))
    return db.get_job(job_id)


class TestCrashRecoveryContract:
    """Contract tests for crash recovery logic.

    These tests verify the database and job manager correctly handle
    orphaned jobs without requiring actual process termination.
    """

    def test_orphaned_jobs_detected(self, db):
        """Jobs in running/cancelling state are detected as orphaned."""
        # Create jobs in various states
        create_test_job(db, "job_queued", state="queued")
        create_test_job(db, "job_running", state="running")
        create_test_job(db, "job_cancelling", state="cancelling")
        create_test_job(db, "job_completed", state="completed")
        create_test_job(db, "job_failed", state="failed")

        # Get orphaned jobs
        orphaned = db.get_orphaned_jobs()
        orphaned_ids = {j["job_id"] for j in orphaned}

        # Only running and cancelling should be orphaned
        assert orphaned_ids == {"job_running", "job_cancelling"}

    def test_orphaned_job_failed_with_crash_error(self, db, tmp_path):
        """Orphaned jobs are marked failed with E_ENGINE_CRASH."""
        from redletters.engine_spine.broadcaster import EventBroadcaster
        from redletters.engine_spine.jobs import JobManager

        # Create workspace directory
        workspace_path = tmp_path / "workspaces" / "job_running"
        workspace_path.mkdir(parents=True)
        (workspace_path / "input").mkdir()
        (workspace_path / "output").mkdir()
        (workspace_path / "temp").mkdir()

        # Create a "running" job (simulates crash mid-execution)
        create_test_job(
            db, "job_running", state="running", workspace_path=str(workspace_path)
        )

        # Create job manager
        broadcaster = EventBroadcaster(db)
        job_manager = JobManager(
            db=db,
            broadcaster=broadcaster,
            workspace_base=tmp_path / "workspaces",
        )

        # Run recovery
        import asyncio

        recovered = asyncio.get_event_loop().run_until_complete(
            job_manager.recover_orphaned_jobs()
        )

        # Verify job was recovered
        assert "job_running" in recovered

        # Verify job state is failed
        job = db.get_job("job_running")
        assert job["state"] == "failed"
        assert job["error_code"] == "E_ENGINE_CRASH"
        assert "unexpectedly" in job["error_message"].lower()

    def test_crash_receipt_produced(self, db, tmp_path):
        """Crash recovery produces receipt.json with correct exit_code."""
        from redletters.engine_spine.broadcaster import EventBroadcaster
        from redletters.engine_spine.jobs import JobManager

        # Create workspace
        workspace_path = tmp_path / "workspaces" / "crash_job"
        workspace_path.mkdir(parents=True)
        (workspace_path / "input").mkdir()
        (workspace_path / "output").mkdir()
        (workspace_path / "temp").mkdir()

        # Create running job
        create_test_job(
            db, "crash_job", state="running", workspace_path=str(workspace_path)
        )

        # Recover
        broadcaster = EventBroadcaster(db)
        job_manager = JobManager(
            db=db,
            broadcaster=broadcaster,
            workspace_base=tmp_path / "workspaces",
        )

        import asyncio

        asyncio.get_event_loop().run_until_complete(job_manager.recover_orphaned_jobs())

        # Check receipt exists
        receipt_path = workspace_path / "receipt.json"
        assert receipt_path.exists(), "Crash receipt should be created"

        # Verify receipt content
        receipt = json.loads(receipt_path.read_text())
        assert receipt["receipt_status"] == "failed"
        assert receipt["exit_code"] == "E_ENGINE_CRASH"
        assert receipt["error_code"] == "E_ENGINE_CRASH"

    def test_receipt_immutable_after_crash(self, db, tmp_path):
        """Crash receipt is chmod 444 (immutable) per Sprint-1-DOD."""
        from redletters.engine_spine.broadcaster import EventBroadcaster
        from redletters.engine_spine.jobs import JobManager

        workspace_path = tmp_path / "workspaces" / "immutable_job"
        workspace_path.mkdir(parents=True)
        (workspace_path / "input").mkdir()
        (workspace_path / "output").mkdir()
        (workspace_path / "temp").mkdir()

        create_test_job(
            db, "immutable_job", state="running", workspace_path=str(workspace_path)
        )

        broadcaster = EventBroadcaster(db)
        job_manager = JobManager(
            db=db,
            broadcaster=broadcaster,
            workspace_base=tmp_path / "workspaces",
        )

        import asyncio

        asyncio.get_event_loop().run_until_complete(job_manager.recover_orphaned_jobs())

        receipt_path = workspace_path / "receipt.json"
        mode = receipt_path.stat().st_mode & 0o777
        assert mode == 0o444, f"Receipt should be 444, got {oct(mode)}"

    def test_sequence_monotonic_across_recovery(self, db, tmp_path):
        """Sequence numbers continue monotonically after crash recovery."""
        from redletters.engine_spine.broadcaster import EventBroadcaster
        from redletters.engine_spine.jobs import JobManager
        from redletters.engine_spine.models import JobLog, LogLevel

        workspace_path = tmp_path / "workspaces" / "seq_job"
        workspace_path.mkdir(parents=True)
        (workspace_path / "input").mkdir()
        (workspace_path / "output").mkdir()
        (workspace_path / "temp").mkdir()

        # Persist some events before "crash"
        create_test_job(
            db, "seq_job", state="running", workspace_path=str(workspace_path)
        )
        pre_crash_seqs = []
        for i in range(3):
            event = JobLog(
                sequence_number=0,
                job_id="seq_job",
                job_sequence=0,
                level=LogLevel.INFO,
                subsystem="test",
                message=f"Pre-crash {i}",
            )
            db.persist_event(event, job_id="seq_job")
            pre_crash_seqs.append(event.sequence_number)

        # Record max sequence before recovery
        max_before = db.get_current_sequence()

        # Recover
        broadcaster = EventBroadcaster(db)
        job_manager = JobManager(
            db=db,
            broadcaster=broadcaster,
            workspace_base=tmp_path / "workspaces",
        )

        import asyncio

        asyncio.get_event_loop().run_until_complete(job_manager.recover_orphaned_jobs())

        # Get events after recovery
        all_events = db.get_events_since(0)

        # Verify all sequences are monotonically increasing
        sequences = [e["sequence"] for e in all_events]
        for i in range(1, len(sequences)):
            assert sequences[i] > sequences[i - 1], "Sequences must be monotonic"

        # Verify new events have sequences > max_before
        post_recovery_events = db.get_events_since(max_before)
        assert len(post_recovery_events) > 0, "Recovery should emit events"
        for e in post_recovery_events:
            assert e["sequence"] > max_before

    def test_multiple_orphaned_jobs_recovered(self, db, tmp_path):
        """Multiple orphaned jobs are all recovered."""
        from redletters.engine_spine.broadcaster import EventBroadcaster
        from redletters.engine_spine.jobs import JobManager

        # Create workspaces and jobs
        job_ids = ["orphan_1", "orphan_2", "orphan_3"]
        for job_id in job_ids:
            workspace_path = tmp_path / "workspaces" / job_id
            workspace_path.mkdir(parents=True)
            (workspace_path / "input").mkdir()
            (workspace_path / "output").mkdir()
            (workspace_path / "temp").mkdir()
            create_test_job(
                db, job_id, state="running", workspace_path=str(workspace_path)
            )

        # Recover
        broadcaster = EventBroadcaster(db)
        job_manager = JobManager(
            db=db,
            broadcaster=broadcaster,
            workspace_base=tmp_path / "workspaces",
        )

        import asyncio

        recovered = asyncio.get_event_loop().run_until_complete(
            job_manager.recover_orphaned_jobs()
        )

        # All should be recovered
        assert set(recovered) == set(job_ids)

        # All should be failed
        for job_id in job_ids:
            job = db.get_job(job_id)
            assert job["state"] == "failed"
            assert job["error_code"] == "E_ENGINE_CRASH"


@pytest.mark.slow
class TestProcessLevelCrashRecovery:
    """Process-level crash recovery tests.

    These tests actually start the engine in a subprocess, create a job,
    kill the process, restart, and verify recovery.

    Marked @pytest.mark.slow - run with: pytest -m slow
    """

    @pytest.fixture
    def engine_subprocess_env(self, tmp_path):
        """Set up environment for subprocess engine."""
        db_path = tmp_path / "engine.db"
        workspace_base = tmp_path / "workspaces"
        workspace_base.mkdir()
        token_path = tmp_path / ".auth_token"

        # Generate a test token
        from redletters.engine_spine.auth import generate_auth_token

        token = generate_auth_token()
        token_path.write_text(token)
        token_path.chmod(0o600)

        return {
            "db_path": str(db_path),
            "workspace_base": str(workspace_base),
            "token_path": str(token_path),
            "token": token,
            "tmp_path": tmp_path,
        }

    def test_engine_crash_job_fails_fast(self, engine_subprocess_env):
        """When engine crashes, running job transitions to failed on restart.

        This is the real CT-08 test: actually kill the process.
        """
        env = engine_subprocess_env

        # Create a Python script that:
        # 1. Starts a minimal engine
        # 2. Creates a job
        # 3. Waits for SIGTERM
        engine_script = f'''
import sys
sys.path.insert(0, "{Path(__file__).parent.parent.parent / "src"}")

import asyncio
import signal
from pathlib import Path
from redletters.engine_spine.database import EngineDatabase
from redletters.engine_spine.broadcaster import EventBroadcaster
from redletters.engine_spine.jobs import JobManager
from redletters.engine_spine.models import JobConfig

async def main():
    db = EngineDatabase(Path("{env["db_path"]}"))
    db.init_schema()

    broadcaster = EventBroadcaster(db)
    job_manager = JobManager(
        db=db,
        broadcaster=broadcaster,
        workspace_base=Path("{env["workspace_base"]}"),
    )

    # Create and start a job
    config = JobConfig(input_paths=["/test/path"])
    job = await job_manager.create_job(config)
    await job_manager.start_job(job.job_id)

    # Write job_id to file so parent can read it
    Path("{env["tmp_path"]}/job_id.txt").write_text(job.job_id)

    # Now wait - we'll be killed
    print("ENGINE_READY", flush=True)
    await asyncio.sleep(60)  # Will be killed before this completes

asyncio.run(main())
'''
        script_path = env["tmp_path"] / "engine_script.py"
        script_path.write_text(engine_script)

        # Start engine subprocess
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            # Wait for engine to be ready
            ready = False
            for _ in range(50):  # 5 seconds timeout
                if proc.poll() is not None:
                    _, stderr = proc.communicate()
                    pytest.fail(f"Engine died early: {stderr}")

                line = proc.stdout.readline()
                if "ENGINE_READY" in line:
                    ready = True
                    break
                time.sleep(0.1)

            if not ready:
                proc.kill()
                pytest.fail("Engine did not become ready")

            # Read job_id
            job_id_path = env["tmp_path"] / "job_id.txt"
            assert job_id_path.exists(), "Job ID file should exist"
            job_id = job_id_path.read_text().strip()

            # Verify job is running
            db = EngineDatabase(Path(env["db_path"]))
            job = db.get_job(job_id)
            assert job["state"] == "running", "Job should be running"

            # KILL the engine (simulate crash)
            proc.kill()
            proc.wait()

        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()

        # Job is still "running" in DB (orphaned)
        job = db.get_job(job_id)
        assert job["state"] == "running", "Job should still show running (orphaned)"

        # Now "restart" engine and recover
        from redletters.engine_spine.broadcaster import EventBroadcaster
        from redletters.engine_spine.jobs import JobManager

        broadcaster = EventBroadcaster(db)
        job_manager = JobManager(
            db=db,
            broadcaster=broadcaster,
            workspace_base=Path(env["workspace_base"]),
        )

        import asyncio

        recovered = asyncio.get_event_loop().run_until_complete(
            job_manager.recover_orphaned_jobs()
        )

        # Verify recovery
        assert job_id in recovered

        # Job should now be failed
        job = db.get_job(job_id)
        assert job["state"] == "failed"
        assert job["error_code"] == "E_ENGINE_CRASH"

        # Receipt should exist
        workspace_path = Path(env["workspace_base"]) / job_id
        receipt_path = workspace_path / "receipt.json"
        assert receipt_path.exists()

        receipt = json.loads(receipt_path.read_text())
        assert receipt["exit_code"] == "E_ENGINE_CRASH"
